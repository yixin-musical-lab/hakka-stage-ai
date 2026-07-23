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


VEO_MODELS = {"veo3.1-fast", "veo3.1-pro"}
VEO_ASPECT_RATIOS = {"16:9", "9:16"}
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
VEO_INPUT_PREFIX = "media-studio/veo-inputs/"
VEO_TASK_KEY_PREFIX = "media:veo:task:"
VEO_USER_TASKS_PREFIX = "media:veo:user:"
VEO_TASK_RETENTION_SECONDS = 24 * 60 * 60
# GRS AI 文档说明结果资源仅保证两小时有效；页面据此提醒用户及时下载。
VEO_RESULT_TTL_SECONDS = 2 * 60 * 60
VEO_INPUT_TOKEN_SECONDS = 2 * 60 * 60
STREAM_CHUNK_SIZE = 1024 * 1024


class GrsaiVeoError(RuntimeError):
    """可安全返回给前端的 GRS AI / 媒体工作台错误。"""

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
    """返回页面可用能力；只报告是否配置，不返回密钥、节点或内部对象地址。"""

    active_settings = settings or get_settings()
    return {
        "provider": "grsai",
        "configured": bool(active_settings.grsai_mock_mode or active_settings.grsai_api_key),
        "mock_mode": active_settings.grsai_mock_mode,
        "file_upload_available": bool(
            active_settings.grsai_mock_mode or _valid_public_base_url(active_settings.grsai_public_base_url)
        ),
        "image_max_upload_mb": active_settings.grsai_image_max_upload_mb,
        "accepted_image_types": list(ALLOWED_IMAGE_TYPES),
        "models": [
            {
                "code": "veo3.1-fast",
                "name": "Veo 3.1 Fast",
                "description": "适合快速预演、分镜试做与多轮迭代。",
            },
            {
                "code": "veo3.1-pro",
                "name": "Veo 3.1 Pro",
                "description": "适合对画面细节、稳定性和最终质感要求更高的片段。",
            },
        ],
        "aspect_ratios": ["16:9", "9:16"],
        "supports_last_frame": True,
        "supports_reference_images": True,
        "reference_images_note": "GRS AI 还支持 Fast 模型最多三张参考图，但参考图模式不能与首尾帧混用，本页首版不开放该模式。",
        "result_url_ttl_hours": 2,
    }


def create_task_record(
    *,
    owner_id: UUID,
    prompt: str,
    model: str,
    aspect_ratio: str,
    source_mode: str,
    source_file_name: str,
    has_last_frame: bool,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """在访问计费接口前创建本地记录，保证后续任务只能由创建者查询。"""

    _validate_generation_fields(prompt, model, aspect_ratio)
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
        "prompt": prompt.strip(),
        "aspect_ratio": aspect_ratio,
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
    """读取当前账号最近的 Veo 任务，供页面刷新后恢复轮询。"""

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
    """校验并暂存 GRS AI 首尾帧；不把 Base64 或二进制写入数据库/Redis。"""

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
    if size_bytes > active_settings.grsai_image_max_upload_bytes:
        raise GrsaiVeoError(
            f"图片超过 {active_settings.grsai_image_max_upload_mb}MB 上限，请压缩后重试。",
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
    if not _valid_public_base_url(active_settings.grsai_public_base_url):
        raise GrsaiVeoError(
            "本地图片上传尚未配置外网回源地址，请设置 GRSAI_PUBLIC_BASE_URL，或改用公网图片 URL。",
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
        f"{active_settings.grsai_public_base_url.rstrip('/')}"
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
    """使用轮询模式提交任务；接口立即返回，不在 FastAPI 请求中等待视频生成。"""

    active_settings = settings or get_settings()
    if active_settings.grsai_mock_mode:
        provider_task_id = f"mock-{uuid4()}"
    else:
        if not active_settings.grsai_api_key:
            raise GrsaiVeoError("服务端尚未配置 GRSAI_API_KEY。", status_code=503)
        payload = {
            "model": record["model"],
            "prompt": record["prompt"],
            "firstFrameUrl": _validate_remote_image_url(first_frame_url, "首帧"),
            "lastFrameUrl": _validate_remote_image_url(last_frame_url, "尾帧") if last_frame_url else "",
            "urls": [],
            "aspectRatio": record["aspect_ratio"],
            # 官方文档约定 -1 表示立即返回任务 ID，后续由 /v1/draw/result 轮询。
            "webHook": "-1",
            "shutProgress": True,
        }
        data = _request_json(
            f"{active_settings.grsai_base_url.rstrip('/')}/v1/video/veo",
            payload,
            active_settings,
        )
        if data.get("code") not in {None, 0, "0"}:
            raise GrsaiVeoError(f"GRS AI 拒绝创建任务：{_error_message(data)}")
        provider_task_id = _extract_task_id(data)
        if not provider_task_id:
            raise GrsaiVeoError(f"GRS AI 未返回任务 ID：{_error_message(data)}")

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
    """查询一次 GRS AI 结果并归一化状态；前端可低频轮询本接口。"""

    if record["status"] in {"succeeded", "failed"}:
        return record
    active_settings = settings or get_settings()
    if active_settings.grsai_mock_mode:
        data: dict[str, Any] = {
            "code": 0,
            "data": {
                "id": record["provider_task_id"],
                "url": "",
                "progress": 100,
                "status": "succeeded",
                "failure_reason": "",
                "error": "",
            },
        }
    else:
        data = _request_json(
            f"{active_settings.grsai_base_url.rstrip('/')}/v1/draw/result",
            {"id": record["provider_task_id"]},
            active_settings,
        )
    body = data.get("data") if isinstance(data.get("data"), dict) else data
    raw_status = str(body.get("status") or "running").strip().lower()
    failure_reason = str(body.get("failure_reason") or "")[:200]
    error_message = str(body.get("error") or "")[:500]
    progress = _safe_progress(body.get("progress"))
    refreshed_at = datetime.now(timezone.utc)
    expires_at = record["expires_at"]
    if data.get("code") not in {None, 0, "0"}:
        raw_status = "failed"
        error_message = _error_message(data)
    if raw_status in {"success", "succeeded", "completed", "finished"}:
        raw_status = "succeeded"
        video_url = str(body.get("url") or "")
        if video_url and urlparse(video_url).scheme not in {"http", "https"}:
            raw_status = "failed"
            error_message = "GRS AI 返回了无法识别的视频地址。"
            video_url = ""
        record["video_url"] = video_url
        progress = 100
        # 文档中的两小时从结果生成后计算；成功时重新校准页面提醒所依据的过期时间。
        expires_at = (refreshed_at + timedelta(seconds=VEO_RESULT_TTL_SECONDS)).isoformat()
    elif raw_status in {"failed", "failure", "error", "violation"} or failure_reason or error_message:
        raw_status = "failed"
        progress = 100
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
        "model",
        "prompt",
        "aspect_ratio",
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
    return {key: record[key] for key in allowed_keys}


def _request_json(url: str, payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """使用标准库调用 GRS AI，避免只为两个轻量代理接口增加后端依赖。"""

    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.grsai_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=settings.grsai_timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(raw_body)
        except json.JSONDecodeError:
            error_data = {}
        raise GrsaiVeoError(f"GRS AI 请求失败：{_error_message(error_data, f'HTTP {exc.code}')}") from exc
    except (URLError, TimeoutError) as exc:
        raise GrsaiVeoError("无法连接 GRS AI，请稍后重试或检查节点配置。") from exc
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise GrsaiVeoError("GRS AI 返回了无法解析的数据。") from exc
    if not isinstance(data, dict):
        raise GrsaiVeoError("GRS AI 返回结构异常。")
    return data


def _extract_task_id(data: dict[str, Any]) -> str:
    body = data.get("data")
    candidates = [data.get("id"), data.get("taskId"), data.get("task_id")]
    if isinstance(body, dict):
        candidates.extend([body.get("id"), body.get("taskId"), body.get("task_id")])
    elif isinstance(body, str):
        candidates.append(body)
    return next((str(value) for value in candidates if value), "")


def _error_message(data: dict[str, Any], fallback: str = "未知错误") -> str:
    body = data.get("data") if isinstance(data.get("data"), dict) else {}
    return str(
        data.get("error")
        or data.get("message")
        or data.get("msg")
        or body.get("error")
        or body.get("message")
        or body.get("msg")
        or fallback
    )[:500]


def _safe_progress(value: Any) -> int:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return 0


def _validate_generation_fields(prompt: str, model: str, aspect_ratio: str) -> None:
    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise GrsaiVeoError("请填写视频提示词。", status_code=400)
    if len(normalized_prompt) > 2000:
        raise GrsaiVeoError("视频提示词不能超过 2000 个字符。", status_code=400)
    if model not in VEO_MODELS:
        raise GrsaiVeoError("暂只支持 veo3.1-fast 与 veo3.1-pro。", status_code=400)
    if aspect_ratio not in VEO_ASPECT_RATIOS:
        raise GrsaiVeoError("视频画幅只支持 16:9 或 9:16。", status_code=400)


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
