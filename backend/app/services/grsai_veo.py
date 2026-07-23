import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import jwt
import redis
from fastapi import UploadFile
from jwt import InvalidTokenError
from minio import Minio
from minio.error import S3Error

from app.core.config import Settings, get_settings


WAN_VIDEO_MODEL = "wan2.7-i2v-2026-04-25"
WAN_VIDEO_MODELS = {WAN_VIDEO_MODEL}
WAN_VIDEO_RESOLUTIONS = {"720P", "1080P"}
WAN_VIDEO_DURATION_MIN_SECONDS = 2
WAN_VIDEO_DURATION_MAX_SECONDS = 15
# `auto` 是 Wan 2.7 的真实行为：输出比例跟随首帧。另两个值只用于读取升级前的历史任务。
VIDEO_ASPECT_RATIOS = {"auto", "16:9", "9:16"}
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
VEO_INPUT_PREFIX = "media-studio/veo-inputs/"
VEO_TASK_KEY_PREFIX = "media:veo:task:"
VEO_USER_TASKS_PREFIX = "media:veo:user:"
VEO_TASK_RETENTION_SECONDS = 24 * 60 * 60
# 百炼结果 URL 保留 24 小时；成功后仍建议尽快转存到项目对象存储。
VEO_RESULT_TTL_SECONDS = 24 * 60 * 60
VEO_INPUT_TOKEN_SECONDS = 2 * 60 * 60
STREAM_CHUNK_SIZE = 1024 * 1024


class GrsaiVeoError(RuntimeError):
    """可安全返回给前端的视频供应商 / 媒体工作台错误。

    类名暂时保留是为了兼容现有路由导入；真实视频供应商已经切换为阿里云百炼 Wan 2.7。
    """

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class VeoInputImage:
    """已保存首尾帧的可信元数据。"""

    object_key: str
    original_file_name: str
    content_type: str
    size_bytes: int


def create_veo_options(settings: Settings | None = None) -> dict[str, Any]:
    """返回 Wan 视频能力；只报告是否配置，不返回密钥、节点或内部对象地址。"""

    active_settings = settings or get_settings()
    return {
        "provider": "dashscope",
        "configured": bool(active_settings.video_mock_mode or active_settings.dashscope_api_key),
        "mock_mode": active_settings.video_mock_mode,
        "file_upload_available": bool(
            active_settings.video_mock_mode
            or _valid_public_base_url(active_settings.video_public_base_url)
        ),
        "image_max_upload_mb": active_settings.video_image_max_upload_mb,
        "accepted_image_types": list(ALLOWED_IMAGE_TYPES),
        "models": [
            {
                "code": WAN_VIDEO_MODEL,
                "name": "万相 Wan 2.7 图生视频",
                "description": "支持首帧或首尾帧、720P/1080P 与 2–15 秒异步生成。",
            },
        ],
        "aspect_ratios": ["auto"],
        "resolutions": ["720P", "1080P"],
        "duration_min_seconds": WAN_VIDEO_DURATION_MIN_SECONDS,
        "duration_max_seconds": WAN_VIDEO_DURATION_MAX_SECONDS,
        "default_duration_seconds": 5,
        "output_ratio_note": "输出画幅跟随首帧图片比例；如需竖屏视频，请上传竖版首帧。",
        "supports_last_frame": True,
        "supports_reference_images": False,
        "reference_images_note": "当前接入 Wan 2.7 首帧 / 首尾帧协议；参考生视频需另接 wan2.7-r2v。",
        "result_url_ttl_hours": 24,
    }


def create_task_record(
    *,
    owner_id: UUID,
    prompt: str,
    model: str,
    aspect_ratio: str,
    resolution: str,
    duration_seconds: int,
    source_mode: str,
    source_file_name: str,
    has_last_frame: bool,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """在访问计费接口前创建本地记录，保证后续任务只能由创建者查询。"""

    _validate_generation_fields(prompt, model, aspect_ratio, resolution, duration_seconds)
    if source_mode not in {"upload", "url"}:
        raise GrsaiVeoError("首帧来源类型无效。", status_code=400)

    active_settings = settings or get_settings()
    client = _redis_client(active_settings)
    _ensure_redis_available(client)
    now = datetime.now(timezone.utc)
    record = {
        "id": str(uuid4()),
        "provider_task_id": "",
        "owner_id": str(owner_id),
        "status": "submitting",
        "progress": 0,
        "model": model,
        "provider": "dashscope",
        "prompt": prompt.strip(),
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "duration_seconds": duration_seconds,
        "source_file_name": source_file_name,
        "source_mode": source_mode,
        "has_last_frame": has_last_frame,
        "video_url": "",
        "failure_reason": "",
        "error_message": "",
        "input_object_keys": [],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=VEO_RESULT_TTL_SECONDS)).isoformat(),
    }
    save_task_record(record, active_settings, client)
    return record


def save_task_record(
    record: dict[str, Any],
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> None:
    """保存任务并维护用户最近任务索引；敏感请求字段不会写入 Redis。"""

    active_settings = settings or get_settings()
    redis_client = client or _redis_client(active_settings)
    task_key = f"{VEO_TASK_KEY_PREFIX}{record['id']}"
    user_key = f"{VEO_USER_TASKS_PREFIX}{record['owner_id']}"
    score = datetime.fromisoformat(record["created_at"]).timestamp()
    try:
        with redis_client.pipeline() as pipeline:
            pipeline.setex(task_key, VEO_TASK_RETENTION_SECONDS, json.dumps(record, ensure_ascii=False))
            pipeline.zadd(user_key, {record["id"]: score})
            pipeline.expire(user_key, VEO_TASK_RETENTION_SECONDS)
            pipeline.execute()
    except redis.RedisError as exc:
        raise GrsaiVeoError("Redis 暂不可用，媒体任务状态无法保存。", status_code=503) from exc


def get_task_record(task_id: str, owner_id: UUID, settings: Settings | None = None) -> dict[str, Any]:
    """读取当前账号的任务；即使知道别人的任务 ID 也不能越权查询。"""

    active_settings = settings or get_settings()
    client = _redis_client(active_settings)
    try:
        raw_record = client.get(f"{VEO_TASK_KEY_PREFIX}{task_id}")
    except redis.RedisError as exc:
        raise GrsaiVeoError("Redis 暂不可用，无法读取媒体任务。", status_code=503) from exc
    if not raw_record:
        raise GrsaiVeoError("媒体任务不存在或本地记录已过期。", status_code=404)
    record = json.loads(raw_record)
    if record.get("owner_id") != str(owner_id):
        # 统一返回 404，避免通过状态码枚举其他账号的任务 ID。
        raise GrsaiVeoError("媒体任务不存在或本地记录已过期。", status_code=404)
    return record


def list_task_records(owner_id: UUID, settings: Settings | None = None, limit: int = 12) -> list[dict[str, Any]]:
    """读取当前账号最近的视频任务，供页面刷新后恢复轮询。"""

    active_settings = settings or get_settings()
    client = _redis_client(active_settings)
    user_key = f"{VEO_USER_TASKS_PREFIX}{owner_id}"
    try:
        task_ids = client.zrevrange(user_key, 0, max(limit - 1, 0))
        if not task_ids:
            return []
        rows = client.mget([f"{VEO_TASK_KEY_PREFIX}{task_id}" for task_id in task_ids])
    except redis.RedisError as exc:
        raise GrsaiVeoError("Redis 暂不可用，无法读取媒体任务列表。", status_code=503) from exc
    records: list[dict[str, Any]] = []
    for row in rows:
        if not row:
            continue
        record = json.loads(row)
        if record.get("owner_id") == str(owner_id):
            records.append(record)
    return records


def save_input_image(
    file: UploadFile,
    settings: Settings | None = None,
    client: Minio | None = None,
) -> VeoInputImage:
    """校验并暂存 Wan 首尾帧；不把 Base64 或二进制写入数据库/Redis。"""

    active_settings = settings or get_settings()
    original_file_name = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not original_file_name:
        raise GrsaiVeoError("请上传带有文件名的图片。", status_code=400)
    content_type = (file.content_type or "").lower()
    if content_type == "image/jpg":
        content_type = "image/jpeg"
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise GrsaiVeoError("暂只支持 JPG、PNG、WEBP 图片。", status_code=400)
    try:
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
    except (AttributeError, OSError) as exc:
        raise GrsaiVeoError("无法读取上传图片，请重新选择文件。", status_code=400) from exc
    if size_bytes <= 0:
        raise GrsaiVeoError("上传图片为空，请重新选择文件。", status_code=400)
    if size_bytes > active_settings.video_image_max_upload_bytes:
        raise GrsaiVeoError(
            f"图片超过 {active_settings.video_image_max_upload_mb}MB 上限，请压缩后重试。",
            status_code=413,
        )

    minio_client = client or _minio_client(active_settings)
    _ensure_bucket(minio_client, active_settings.minio_bucket)
    object_key = f"{VEO_INPUT_PREFIX}{uuid4().hex}{extension}"
    try:
        minio_client.put_object(
            active_settings.minio_bucket,
            object_key,
            file.file,
            size_bytes,
            content_type=content_type,
        )
    except (S3Error, OSError) as exc:
        raise GrsaiVeoError("MinIO 暂不可用，首帧图片未能保存。", status_code=503) from exc
    except Exception as exc:
        raise GrsaiVeoError("MinIO 暂不可用，首帧图片未能保存。", status_code=503) from exc
    return VeoInputImage(object_key, original_file_name, content_type, size_bytes)


def create_public_input_url(image: VeoInputImage, settings: Settings | None = None) -> str:
    """为供应商创建限时、只读的图片地址；地址中不暴露 MinIO 凭据。"""

    active_settings = settings or get_settings()
    if not _valid_public_base_url(active_settings.video_public_base_url):
        raise GrsaiVeoError(
            "本地图片上传尚未配置外网回源地址，请设置 VIDEO_PUBLIC_BASE_URL，或改用公网图片 URL。",
            status_code=503,
        )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": image.object_key,
            "type": "veo_input",
            "content_type": image.content_type,
            "iat": now,
            "exp": now + timedelta(seconds=VEO_INPUT_TOKEN_SECONDS),
            "iss": "hakka-stage-ai",
            "aud": "grsai-veo-input",
        },
        active_settings.auth_secret_key,
        algorithm="HS256",
    )
    return (
        f"{active_settings.video_public_base_url.rstrip('/')}"
        f"/api/public/media-studio/veo-inputs/{quote(token, safe='')}"
    )


def open_public_input(token: str, settings: Settings | None = None) -> tuple[Any, str]:
    """验证供应商回源令牌并打开 MinIO 对象。"""

    active_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            active_settings.auth_secret_key,
            algorithms=["HS256"],
            audience="grsai-veo-input",
            issuer="hakka-stage-ai",
            options={"require": ["sub", "type", "iat", "exp", "iss", "aud"]},
        )
    except InvalidTokenError as exc:
        raise GrsaiVeoError("图片临时访问地址无效或已过期。", status_code=404) from exc
    object_key = str(payload.get("sub") or "")
    content_type = str(payload.get("content_type") or "application/octet-stream")
    if payload.get("type") != "veo_input" or not object_key.startswith(VEO_INPUT_PREFIX):
        raise GrsaiVeoError("图片临时访问地址无效或已过期。", status_code=404)
    try:
        response = _minio_client(active_settings).get_object(active_settings.minio_bucket, object_key)
    except Exception as exc:
        raise GrsaiVeoError("图片不存在或暂时无法读取。", status_code=404) from exc
    return response, content_type


def iter_minio_object(response: Any) -> Iterator[bytes]:
    """流式转发首尾帧，并在供应商断开后释放 MinIO 连接。"""

    try:
        while True:
            chunk = response.read(STREAM_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    finally:
        response.close()
        response.release_conn()


def submit_task(
    record: dict[str, Any],
    first_frame_url: str,
    last_frame_url: str = "",
    input_object_keys: list[str] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """提交百炼 Wan 2.7 异步任务；接口立即返回，不在请求中等待视频生成。"""

    active_settings = settings or get_settings()
    if active_settings.video_mock_mode:
        provider_task_id = f"mock-{uuid4()}"
    else:
        if not active_settings.dashscope_api_key:
            raise GrsaiVeoError("服务端尚未配置 DASHSCOPE_API_KEY。", status_code=503)

        # Wan 2.7 新协议通过 media 数组区分首帧与尾帧；输出比例会跟随首帧素材。
        media = [
            {
                "type": "first_frame",
                "url": _validate_remote_image_url(first_frame_url, "首帧"),
            }
        ]
        if last_frame_url:
            media.append(
                {
                    "type": "last_frame",
                    "url": _validate_remote_image_url(last_frame_url, "尾帧"),
                }
            )
        payload = {
            "model": record["model"],
            "input": {
                "prompt": record["prompt"],
                "media": media,
            },
            "parameters": {
                "resolution": record["resolution"],
                "duration": record["duration_seconds"],
                "prompt_extend": True,
                "watermark": False,
            },
        }
        data = _request_json(
            _dashscope_api_url(active_settings, "services/aigc/video-generation/video-synthesis"),
            payload,
            active_settings,
        )
        if data.get("code") not in {None, 0, "0", ""}:
            raise GrsaiVeoError(f"百炼拒绝创建 Wan 视频任务：{_error_message(data)}")
        provider_task_id = _extract_task_id(data)
        if not provider_task_id:
            raise GrsaiVeoError(f"百炼未返回 Wan 视频任务 ID：{_error_message(data)}")

    record.update(
        {
            "provider_task_id": provider_task_id,
            "status": "running",
            "progress": 0,
            "input_object_keys": input_object_keys or [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_task_record(record, active_settings)
    return record


def refresh_task(record: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    """查询一次百炼异步结果并归一化状态；前端可低频轮询本接口。"""

    if record["status"] in {"succeeded", "failed"}:
        return record
    active_settings = settings or get_settings()

    # 升级前仍在运行的 GRS AI 任务无法通过百炼任务接口继续查询，明确结束而不是误请求新供应商。
    if record.get("model") not in WAN_VIDEO_MODELS:
        record.update(
            {
                "status": "failed",
                "progress": 100,
                "failure_reason": "LEGACY_PROVIDER_RETIRED",
                "error_message": "该任务来自已停用的 GRS AI Veo 通道，请使用 Wan 2.7 重新创建。",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        save_task_record(record, active_settings)
        return record

    if active_settings.video_mock_mode:
        data: dict[str, Any] = {
            "output": {
                "task_id": record["provider_task_id"],
                "task_status": "SUCCEEDED",
                "video_url": "",
            },
        }
    else:
        data = _request_json(
            _dashscope_api_url(
                active_settings,
                f"tasks/{quote(str(record['provider_task_id']), safe='')}",
            ),
            None,
            active_settings,
            method="GET",
        )
    body = data.get("output") if isinstance(data.get("output"), dict) else data
    provider_status = str(body.get("task_status") or body.get("status") or "RUNNING").strip().upper()
    failure_reason = str(body.get("code") or "")[:200]
    error_message = str(body.get("message") or "")[:500]
    progress = {
        "PENDING": 10,
        "RUNNING": 50,
        "SUCCEEDED": 100,
        "FAILED": 100,
        "CANCELED": 100,
        "UNKNOWN": 100,
    }.get(provider_status, 50)
    refreshed_at = datetime.now(timezone.utc)
    expires_at = record["expires_at"]
    if data.get("code") not in {None, 0, "0", ""}:
        provider_status = "FAILED"
        failure_reason = str(data.get("code") or "DASHSCOPE_REQUEST_FAILED")[:200]
        error_message = _error_message(data)
    if provider_status == "SUCCEEDED":
        raw_status = "succeeded"
        video_url = str(body.get("video_url") or "")
        if video_url and urlparse(video_url).scheme not in {"http", "https"}:
            raw_status = "failed"
            failure_reason = "INVALID_VIDEO_URL"
            error_message = "百炼返回了无法识别的视频地址。"
            video_url = ""
        elif not video_url and not active_settings.video_mock_mode:
            raw_status = "failed"
            failure_reason = "VIDEO_URL_MISSING"
            error_message = "百炼任务已完成，但响应中没有视频地址。"
        record["video_url"] = video_url
        progress = 100
        # 百炼的 24 小时从结果生成后计算；成功时重新校准页面提醒所依据的过期时间。
        expires_at = (refreshed_at + timedelta(seconds=VEO_RESULT_TTL_SECONDS)).isoformat()
    elif provider_status in {"FAILED", "CANCELED", "UNKNOWN"}:
        raw_status = "failed"
        progress = 100
        if not failure_reason:
            failure_reason = provider_status
        if not error_message:
            error_message = {
                "CANCELED": "百炼视频任务已取消。",
                "UNKNOWN": "百炼视频任务不存在或任务 ID 已超过 24 小时有效期。",
            }.get(provider_status, "百炼视频任务生成失败。")
    else:
        raw_status = "running"
    record.update(
        {
            "status": raw_status,
            "progress": progress,
            "failure_reason": failure_reason,
            "error_message": error_message,
            "updated_at": refreshed_at.isoformat(),
            "expires_at": expires_at,
        }
    )
    save_task_record(record, active_settings)
    return record


def mark_task_failed(record: dict[str, Any], error: Exception, settings: Settings | None = None) -> None:
    """提交失败也保留可读终态，便于页面和日志定位问题。"""

    record.update(
        {
            "status": "failed",
            "progress": 100,
            "error_message": str(error)[:500],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_task_record(record, settings)


def public_task_record(record: dict[str, Any]) -> dict[str, Any]:
    """剔除供应商任务 ID、账号 ID、对象键等内部字段后再返回前端。"""

    allowed_keys = {
        "id",
        "status",
        "progress",
        "provider",
        "model",
        "prompt",
        "aspect_ratio",
        "resolution",
        "duration_seconds",
        "source_file_name",
        "source_mode",
        "has_last_frame",
        "video_url",
        "failure_reason",
        "error_message",
        "created_at",
        "updated_at",
        "expires_at",
    }
    public_record = {key: record[key] for key in allowed_keys if key in record}
    # Redis 中可能仍有升级前的 Veo 任务；补默认值可以继续展示历史终态而不触发响应校验错误。
    public_record.setdefault("provider", "grsai" if str(record.get("model", "")).startswith("veo") else "dashscope")
    public_record.setdefault("aspect_ratio", "auto")
    public_record.setdefault("resolution", "720P")
    public_record.setdefault("duration_seconds", 5)
    return public_record


def _request_json(
    url: str,
    payload: dict[str, Any] | None,
    settings: Settings,
    *,
    method: str = "POST",
) -> dict[str, Any]:
    """使用标准库调用百炼原生异步接口，避免仅为两个请求增加后端依赖。"""

    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Accept": "application/json",
    }
    request_body = None
    if payload is not None:
        request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if method == "POST":
        # 百炼视频 HTTP 接口只支持异步调用，缺少此请求头会被拒绝。
        headers["X-DashScope-Async"] = "enable"
    request = Request(
        url,
        data=request_body,
        method=method,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=settings.video_timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(raw_body)
        except json.JSONDecodeError:
            error_data = {}
        raise GrsaiVeoError(f"百炼请求失败：{_error_message(error_data, f'HTTP {exc.code}')}") from exc
    except (URLError, TimeoutError) as exc:
        raise GrsaiVeoError("无法连接阿里云百炼，请稍后重试或检查 DASHSCOPE_BASE_URL。") from exc
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise GrsaiVeoError("百炼返回了无法解析的数据。") from exc
    if not isinstance(data, dict):
        raise GrsaiVeoError("百炼返回结构异常。")
    return data


def _extract_task_id(data: dict[str, Any]) -> str:
    body = data.get("data")
    candidates = [data.get("id"), data.get("taskId"), data.get("task_id")]
    output = data.get("output")
    if isinstance(output, dict):
        candidates.extend([output.get("task_id"), output.get("taskId"), output.get("id")])
    if isinstance(body, dict):
        candidates.extend([body.get("id"), body.get("taskId"), body.get("task_id")])
    elif isinstance(body, str):
        candidates.append(body)
    return next((str(value) for value in candidates if value), "")


def _error_message(data: dict[str, Any], fallback: str = "未知错误") -> str:
    body = data.get("data") if isinstance(data.get("data"), dict) else {}
    output = data.get("output") if isinstance(data.get("output"), dict) else {}
    return str(
        data.get("error")
        or data.get("message")
        or data.get("msg")
        or body.get("error")
        or body.get("message")
        or body.get("msg")
        or output.get("error")
        or output.get("message")
        or output.get("msg")
        or fallback
    )[:500]


def _validate_generation_fields(
    prompt: str,
    model: str,
    aspect_ratio: str,
    resolution: str,
    duration_seconds: int,
) -> None:
    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise GrsaiVeoError("请填写视频提示词。", status_code=400)
    if len(normalized_prompt) > 2000:
        raise GrsaiVeoError("视频提示词不能超过 2000 个字符。", status_code=400)
    if model not in WAN_VIDEO_MODELS:
        raise GrsaiVeoError(f"暂只支持 {WAN_VIDEO_MODEL}。", status_code=400)
    if aspect_ratio not in VIDEO_ASPECT_RATIOS:
        raise GrsaiVeoError("视频画幅参数无效。", status_code=400)
    if resolution not in WAN_VIDEO_RESOLUTIONS:
        raise GrsaiVeoError("Wan 视频分辨率只支持 720P 或 1080P。", status_code=400)
    if not WAN_VIDEO_DURATION_MIN_SECONDS <= duration_seconds <= WAN_VIDEO_DURATION_MAX_SECONDS:
        raise GrsaiVeoError("Wan 视频时长必须在 2 到 15 秒之间。", status_code=400)


def _dashscope_api_url(settings: Settings, path: str) -> str:
    """拼接百炼原生 API 地址，并对误填 OpenAI 兼容地址给出明确错误。"""

    base_url = settings.dashscope_base_url.strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise GrsaiVeoError("DASHSCOPE_BASE_URL 必须是有效的 HTTP(S) 根地址。", status_code=503)
    if "/compatible-mode" in parsed.path:
        raise GrsaiVeoError(
            "DASHSCOPE_BASE_URL 不能填写 Qwen 的 /compatible-mode/v1 地址，请填写百炼业务空间根地址。",
            status_code=503,
        )
    api_root = base_url if base_url.endswith("/api/v1") else f"{base_url}/api/v1"
    return f"{api_root}/{path.lstrip('/')}"


def _validate_remote_image_url(value: str, label: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise GrsaiVeoError(f"{label}图片地址必须是可公开访问的 HTTP(S) URL。", status_code=400)
    return value.strip()


def _valid_public_base_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _redis_client(settings: Settings) -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _ensure_redis_available(client: redis.Redis) -> None:
    try:
        client.ping()
    except redis.RedisError as exc:
        raise GrsaiVeoError("Redis 暂不可用，不能安全创建媒体任务。", status_code=503) from exc


def _minio_client(settings: Settings) -> Minio:
    parsed = urlparse(settings.minio_endpoint)
    endpoint = parsed.netloc or parsed.path
    if not endpoint:
        raise GrsaiVeoError("MinIO 地址无效，无法保存首尾帧。", status_code=503)
    return Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=parsed.scheme == "https",
    )


def _ensure_bucket(client: Minio, bucket_name: str) -> None:
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
    except S3Error as exc:
        if exc.code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise GrsaiVeoError("MinIO 暂不可用，无法准备媒体存储桶。", status_code=503) from exc
    except Exception as exc:
        # 连接拒绝、DNS 失败等错误不是 S3Error，也要转换为稳定的业务错误，避免接口泄露内部异常。
        raise GrsaiVeoError("MinIO 暂不可用，无法准备媒体存储桶。", status_code=503) from exc
