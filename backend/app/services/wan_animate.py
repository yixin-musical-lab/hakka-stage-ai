import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryFile
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
from app.services.grsai_veo import (
    _dashscope_api_url,
    _error_message,
    _extract_task_id,
    _request_json,
)


WAN_ANIMATE_MODEL = "wan2.2-animate-move"
WAN_ANIMATE_MODES = {"wan-std", "wan-pro"}
MOTION_DURATION_MIN_SECONDS = 2
MOTION_DURATION_MAX_SECONDS = 30
MOTION_IMAGE_DIMENSION_MIN_PIXELS = 200
MOTION_IMAGE_DIMENSION_MAX_PIXELS = 4096
MOTION_VIDEO_DIMENSION_MIN_PIXELS = 200
MOTION_VIDEO_DIMENSION_MAX_PIXELS = 2048
MOTION_ASPECT_RATIO_MIN = 1 / 3
MOTION_ASPECT_RATIO_MAX = 3
MOTION_INPUT_PREFIX = "media-studio/motion-inputs/"
MOTION_RESULT_PREFIX = "media-studio/motion-results/"
MOTION_TASK_KEY_PREFIX = "media:motion-transfer:task:"
MOTION_USER_TASKS_PREFIX = "media:motion-transfer:user:"
MOTION_TASK_RETENTION_SECONDS = 24 * 60 * 60
MOTION_INPUT_TOKEN_SECONDS = 2 * 60 * 60
MOTION_RESULT_TTL_SECONDS = 24 * 60 * 60
STREAM_CHUNK_SIZE = 1024 * 1024
RESULT_DOWNLOAD_CHUNK_SIZE = 4 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}
ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
}


class MotionTransferError(RuntimeError):
    """可安全映射到 HTTP 响应的动作模仿业务错误。"""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class MotionInputAsset:
    """已经写入 MinIO 的人物图片或动作视频可信元数据。"""

    object_key: str
    original_file_name: str
    content_type: str
    size_bytes: int
    media_kind: str


@dataclass(frozen=True)
class MotionResultInfo:
    """从百炼临时地址转存到 MinIO 后的结果元数据。"""

    object_key: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True)
class MotionVideoByteRange:
    """浏览器播放结果视频时使用的单段字节范围。"""

    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1


def create_motion_transfer_options(settings: Settings | None = None) -> dict[str, Any]:
    """返回前端可公开展示的能力边界，不返回密钥和内部对象地址。"""

    active_settings = settings or get_settings()
    has_public_input = _valid_public_base_url(active_settings.video_public_base_url)
    configured = bool(
        active_settings.video_mock_mode
        or (active_settings.dashscope_api_key and has_public_input)
    )
    return {
        "provider": "dashscope",
        "configured": configured,
        "mock_mode": active_settings.video_mock_mode,
        "file_upload_available": bool(active_settings.video_mock_mode or has_public_input),
        "model": WAN_ANIMATE_MODEL,
        "modes": [
            {
                "code": "wan-std",
                "name": "标准模式",
                "description": "生成更快，适合排练预览和动作确认。",
                "frames_per_second": 15,
                "price_cny_per_second": 0.4,
            },
            {
                "code": "wan-pro",
                "name": "专业模式",
                "description": "动作更流畅，适合确认后的最终示范。",
                "frames_per_second": 25,
                "price_cny_per_second": 0.6,
            },
        ],
        "image_max_upload_mb": active_settings.motion_image_max_upload_mb,
        "video_max_upload_mb": active_settings.motion_video_max_upload_mb,
        "accepted_image_types": list(ALLOWED_IMAGE_EXTENSIONS.values()),
        "accepted_video_types": list(ALLOWED_VIDEO_EXTENSIONS.values()),
        "duration_min_seconds": MOTION_DURATION_MIN_SECONDS,
        "duration_max_seconds": MOTION_DURATION_MAX_SECONDS,
        "image_dimension_min_pixels": MOTION_IMAGE_DIMENSION_MIN_PIXELS,
        "image_dimension_max_pixels": MOTION_IMAGE_DIMENSION_MAX_PIXELS,
        "video_dimension_min_pixels": MOTION_VIDEO_DIMENSION_MIN_PIXELS,
        "video_dimension_max_pixels": MOTION_VIDEO_DIMENSION_MAX_PIXELS,
        "aspect_ratio_min": MOTION_ASPECT_RATIO_MIN,
        "aspect_ratio_max": MOTION_ASPECT_RATIO_MAX,
        "resolution": "720P",
        "result_url_ttl_hours": 24,
        "input_guidance": [
            "人物图片建议只包含一人，正面或轻微侧身，肩部到脚踝清晰可见。",
            "参考视频建议使用固定镜头、完整人体、少遮挡的单人动作片段。",
            "图片与视频人物的取景比例越接近，动作迁移通常越稳定。",
        ],
    }


def create_motion_task_record(
    *,
    owner_id: UUID,
    mode: str,
    watermark: bool,
    person_file_name: str,
    motion_file_name: str,
    motion_duration_seconds: float | None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """在调用计费接口前保存任务归属，确保后续查询不能跨账号。"""

    if mode not in WAN_ANIMATE_MODES:
        raise MotionTransferError("动作模仿质量模式无效。", status_code=400)
    if motion_duration_seconds is not None and not (
        MOTION_DURATION_MIN_SECONDS <= motion_duration_seconds <= MOTION_DURATION_MAX_SECONDS
    ):
        raise MotionTransferError("参考视频时长必须在 2 到 30 秒之间。", status_code=400)

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
        "provider": "dashscope",
        "model": WAN_ANIMATE_MODEL,
        "mode": mode,
        "resolution": "720P",
        "watermark": watermark,
        "person_file_name": _safe_file_name(person_file_name),
        "motion_file_name": _safe_file_name(motion_file_name),
        "motion_duration_seconds": motion_duration_seconds,
        "input_object_keys": [],
        "result_object_key": "",
        "result_content_type": "",
        "result_size_bytes": 0,
        "result_available": False,
        "result_persisted": False,
        "video_url": "",
        "storage_warning": "",
        "failure_reason": "",
        "error_message": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=MOTION_RESULT_TTL_SECONDS)).isoformat(),
    }
    save_motion_task_record(record, active_settings, client)
    return record


def save_motion_task_record(
    record: dict[str, Any],
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> None:
    """保存任务及当前账号最近任务索引，二进制与供应商密钥不会进入 Redis。"""

    active_settings = settings or get_settings()
    redis_client = client or _redis_client(active_settings)
    task_key = f"{MOTION_TASK_KEY_PREFIX}{record['id']}"
    user_key = f"{MOTION_USER_TASKS_PREFIX}{record['owner_id']}"
    score = datetime.fromisoformat(record["created_at"]).timestamp()
    try:
        with redis_client.pipeline() as pipeline:
            pipeline.setex(
                task_key,
                MOTION_TASK_RETENTION_SECONDS,
                json.dumps(record, ensure_ascii=False),
            )
            pipeline.zadd(user_key, {record["id"]: score})
            pipeline.expire(user_key, MOTION_TASK_RETENTION_SECONDS)
            pipeline.execute()
    except redis.RedisError as exc:
        raise MotionTransferError("Redis 暂不可用，动作模仿任务状态无法保存。", status_code=503) from exc


def get_motion_task_record(
    task_id: str,
    owner_id: UUID,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """读取当前账号任务；未知任务和越权访问统一返回 404。"""

    active_settings = settings or get_settings()
    try:
        raw_record = _redis_client(active_settings).get(f"{MOTION_TASK_KEY_PREFIX}{task_id}")
    except redis.RedisError as exc:
        raise MotionTransferError("Redis 暂不可用，无法读取动作模仿任务。", status_code=503) from exc
    if not raw_record:
        raise MotionTransferError("动作模仿任务不存在或记录已过期。", status_code=404)
    record = json.loads(raw_record)
    if record.get("owner_id") != str(owner_id):
        raise MotionTransferError("动作模仿任务不存在或记录已过期。", status_code=404)
    return record


def list_motion_task_records(
    owner_id: UUID,
    settings: Settings | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """读取当前账号最近的动作模仿任务，支持刷新页面后恢复轮询。"""

    active_settings = settings or get_settings()
    client = _redis_client(active_settings)
    user_key = f"{MOTION_USER_TASKS_PREFIX}{owner_id}"
    try:
        task_ids = client.zrevrange(user_key, 0, max(limit - 1, 0))
        if not task_ids:
            return []
        rows = client.mget([f"{MOTION_TASK_KEY_PREFIX}{task_id}" for task_id in task_ids])
    except redis.RedisError as exc:
        raise MotionTransferError("Redis 暂不可用，无法读取动作模仿任务列表。", status_code=503) from exc
    records: list[dict[str, Any]] = []
    for row in rows:
        if not row:
            continue
        record = json.loads(row)
        if record.get("owner_id") == str(owner_id):
            records.append(record)
    return records


def save_motion_input(
    file: UploadFile,
    media_kind: str,
    settings: Settings | None = None,
    client: Minio | None = None,
) -> MotionInputAsset:
    """校验人物图片或参考视频，并从 UploadFile 直接流式写入 MinIO。"""

    if media_kind not in {"image", "video"}:
        raise MotionTransferError("动作模仿素材类型无效。", status_code=400)
    active_settings = settings or get_settings()
    original_file_name = _safe_file_name(file.filename or "")
    extension = Path(original_file_name).suffix.lower()
    allowed = ALLOWED_IMAGE_EXTENSIONS if media_kind == "image" else ALLOWED_VIDEO_EXTENSIONS
    content_type = allowed.get(extension)
    if content_type is None:
        label = "JPG、JPEG、PNG、BMP、WEBP" if media_kind == "image" else "MP4、AVI、MOV"
        raise MotionTransferError(f"该素材格式不受支持，请上传 {label} 文件。", status_code=400)

    uploaded_content_type = (file.content_type or "").lower()
    if uploaded_content_type and uploaded_content_type != "application/octet-stream":
        expected_prefix = "image/" if media_kind == "image" else "video/"
        if not uploaded_content_type.startswith(expected_prefix):
            raise MotionTransferError("文件扩展名与浏览器识别的媒体类型不一致，请重新导出后上传。", status_code=400)

    try:
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
    except (AttributeError, OSError) as exc:
        raise MotionTransferError("无法读取上传素材，请重新选择文件。", status_code=400) from exc
    if size_bytes <= 0:
        raise MotionTransferError("上传素材为空，请重新选择文件。", status_code=400)
    max_bytes = (
        active_settings.motion_image_max_upload_bytes
        if media_kind == "image"
        else active_settings.motion_video_max_upload_bytes
    )
    max_mb = (
        active_settings.motion_image_max_upload_mb
        if media_kind == "image"
        else active_settings.motion_video_max_upload_mb
    )
    if size_bytes > max_bytes:
        raise MotionTransferError(f"上传素材超过 {max_mb}MB 上限，请压缩或截取后重试。", status_code=413)

    minio_client = client or _minio_client(active_settings)
    _ensure_bucket(minio_client, active_settings.minio_bucket)
    object_key = f"{MOTION_INPUT_PREFIX}{uuid4().hex}{extension}"
    try:
        minio_client.put_object(
            active_settings.minio_bucket,
            object_key,
            file.file,
            size_bytes,
            content_type=content_type,
        )
    except Exception as exc:
        raise MotionTransferError("MinIO 暂不可用，动作模仿素材未能保存。", status_code=503) from exc
    return MotionInputAsset(
        object_key=object_key,
        original_file_name=original_file_name,
        content_type=content_type,
        size_bytes=size_bytes,
        media_kind=media_kind,
    )


def create_motion_public_input_url(
    asset: MotionInputAsset,
    settings: Settings | None = None,
) -> str:
    """创建供应商可回源的两小时签名短链，不暴露 MinIO 凭据。

    百炼会结合 URL 路径后缀识别媒体格式，因此签名令牌后必须保留 MinIO
    对象的真实扩展名；只返回无后缀 JWT 会被误判为不支持的视频类型。
    """

    active_settings = settings or get_settings()
    if not _valid_public_base_url(active_settings.video_public_base_url):
        raise MotionTransferError(
            "动作模仿上传尚未配置公网回源地址，请设置 VIDEO_PUBLIC_BASE_URL。",
            status_code=503,
        )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": asset.object_key,
            "type": "motion_input",
            "content_type": asset.content_type,
            "iat": now,
            "exp": now + timedelta(seconds=MOTION_INPUT_TOKEN_SECONDS),
            "iss": "hakka-stage-ai",
            "aud": "wan-animate-input",
        },
        active_settings.auth_secret_key,
        algorithm="HS256",
    )
    extension = Path(asset.object_key).suffix.lower()
    allowed_extensions = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
    if extension not in allowed_extensions:
        raise MotionTransferError("动作模仿素材扩展名无效，无法创建临时地址。", status_code=500)
    return (
        f"{active_settings.video_public_base_url.rstrip('/')}"
        f"/api/public/media-studio/motion-inputs/{quote(token, safe='')}{extension}"
    )


def split_motion_public_input_path(signed_asset: str) -> tuple[str, str]:
    """从带真实媒体后缀的公开路径中拆出 JWT 和扩展名。"""

    extension = Path(signed_asset).suffix.lower()
    allowed_extensions = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
    if extension not in allowed_extensions:
        raise MotionTransferError("动作模仿素材临时地址无效或已过期。", status_code=404)
    token = signed_asset[: -len(extension)]
    if not token:
        raise MotionTransferError("动作模仿素材临时地址无效或已过期。", status_code=404)
    return token, extension


def open_motion_public_input(
    token: str,
    settings: Settings | None = None,
    expected_extension: str | None = None,
) -> tuple[Any, str, int]:
    """验证供应商回源令牌并打开对应的私有 MinIO 对象。"""

    active_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            active_settings.auth_secret_key,
            algorithms=["HS256"],
            audience="wan-animate-input",
            issuer="hakka-stage-ai",
            options={"require": ["sub", "type", "iat", "exp", "iss", "aud"]},
        )
    except InvalidTokenError as exc:
        raise MotionTransferError("动作模仿素材临时地址无效或已过期。", status_code=404) from exc
    object_key = str(payload.get("sub") or "")
    if payload.get("type") != "motion_input" or not object_key.startswith(MOTION_INPUT_PREFIX):
        raise MotionTransferError("动作模仿素材临时地址无效或已过期。", status_code=404)
    # URL 后缀既供百炼识别格式，也必须与签名对象一致，不能由请求方任意伪造。
    if expected_extension and Path(object_key).suffix.lower() != expected_extension.lower():
        raise MotionTransferError("动作模仿素材临时地址无效或已过期。", status_code=404)
    try:
        client = _minio_client(active_settings)
        stat = client.stat_object(active_settings.minio_bucket, object_key)
        response = client.get_object(active_settings.minio_bucket, object_key)
    except Exception as exc:
        raise MotionTransferError("动作模仿素材不存在或暂时无法读取。", status_code=404) from exc
    content_type = str(payload.get("content_type") or stat.content_type or "application/octet-stream")
    return response, content_type, int(stat.size)


def submit_motion_task(
    record: dict[str, Any],
    image_url: str,
    video_url: str,
    input_object_keys: list[str],
    settings: Settings | None = None,
) -> dict[str, Any]:
    """提交 Wan 2.2 图生动作异步任务，创建请求不等待视频生成完成。"""

    active_settings = settings or get_settings()
    if active_settings.video_mock_mode:
        provider_task_id = f"mock-motion-{uuid4()}"
    else:
        if not active_settings.dashscope_api_key:
            raise MotionTransferError("服务端尚未配置 DASHSCOPE_API_KEY。", status_code=503)
        payload = {
            "model": WAN_ANIMATE_MODEL,
            "input": {
                "image_url": _validate_remote_media_url(image_url, "人物图片"),
                "video_url": _validate_remote_media_url(video_url, "参考视频"),
                "watermark": bool(record["watermark"]),
            },
            "parameters": {
                "check_image": True,
                "mode": record["mode"],
            },
        }
        try:
            data = _request_json(
                _dashscope_api_url(
                    active_settings,
                    "services/aigc/image2video/video-synthesis",
                ),
                payload,
                active_settings,
            )
        except Exception as exc:
            raise MotionTransferError(str(exc)) from exc
        if data.get("code") not in {None, 0, "0", ""}:
            raise MotionTransferError(f"百炼拒绝创建动作模仿任务：{_error_message(data)}")
        provider_task_id = _extract_task_id(data)
        if not provider_task_id:
            raise MotionTransferError(f"百炼未返回动作模仿任务 ID：{_error_message(data)}")

    record.update(
        {
            "provider_task_id": provider_task_id,
            "status": "running",
            "progress": 5,
            "input_object_keys": input_object_keys,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_motion_task_record(record, active_settings)
    return record


def refresh_motion_task(
    record: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    """查询一次百炼状态；成功后优先把临时结果流式转存到 MinIO。"""

    if record["status"] in {"succeeded", "failed"}:
        return record
    active_settings = settings or get_settings()
    if active_settings.video_mock_mode:
        data: dict[str, Any] = {
            "output": {
                "task_id": record["provider_task_id"],
                "task_status": "SUCCEEDED",
                "video_url": "",
            }
        }
    else:
        try:
            data = _request_json(
                _dashscope_api_url(
                    active_settings,
                    f"tasks/{quote(str(record['provider_task_id']), safe='')}",
                ),
                None,
                active_settings,
                method="GET",
            )
        except Exception as exc:
            raise MotionTransferError(str(exc)) from exc

    body = data.get("output") if isinstance(data.get("output"), dict) else data
    provider_status = str(body.get("task_status") or body.get("status") or "RUNNING").upper()
    failure_reason = str(body.get("code") or "")[:200]
    error_message = str(body.get("message") or "")[:500]
    progress = {"PENDING": 10, "RUNNING": 55}.get(provider_status, 100)
    refreshed_at = datetime.now(timezone.utc)

    if data.get("code") not in {None, 0, "0", ""}:
        provider_status = "FAILED"
        failure_reason = str(data.get("code") or "DASHSCOPE_REQUEST_FAILED")[:200]
        error_message = _error_message(data)

    if provider_status == "SUCCEEDED":
        raw_status = "succeeded"
        # wan2.2-animate-move 的正式响应位于 output.results.video_url；
        # 同时兼容早期示例和 Mock 可能返回的 output.video_url，避免已创建任务因响应差异丢失结果。
        provider_results = body.get("results") if isinstance(body.get("results"), dict) else {}
        remote_video_url = str(
            provider_results.get("video_url") or body.get("video_url") or ""
        ).strip()
        if active_settings.video_mock_mode:
            record["result_available"] = False
        elif not _is_http_url(remote_video_url):
            raw_status = "failed"
            failure_reason = "VIDEO_URL_MISSING"
            error_message = "百炼任务已完成，但响应中没有可读取的视频地址。"
        else:
            record["video_url"] = remote_video_url
            record["result_available"] = True
            try:
                result = persist_motion_result(remote_video_url, record["id"], active_settings)
                record.update(
                    {
                        "result_object_key": result.object_key,
                        "result_content_type": result.content_type,
                        "result_size_bytes": result.size_bytes,
                        "result_persisted": True,
                        # 转存后不再把供应商临时 URL 暴露给前端，统一通过鉴权结果接口播放。
                        "video_url": "",
                    }
                )
            except MotionTransferError as exc:
                # 生成成功不应因转存抖动变成失败；保留临时地址并明确提醒用户及时下载。
                record["storage_warning"] = str(exc)[:500]
        progress = 100
        record["expires_at"] = (
            refreshed_at + timedelta(seconds=MOTION_RESULT_TTL_SECONDS)
        ).isoformat()
    elif provider_status in {"FAILED", "CANCELED", "UNKNOWN"}:
        raw_status = "failed"
        progress = 100
        failure_reason = failure_reason or provider_status
        error_message = error_message or {
            "CANCELED": "百炼动作模仿任务已取消。",
            "UNKNOWN": "百炼任务不存在或供应商任务 ID 已过期。",
        }.get(provider_status, "百炼动作模仿任务生成失败。")
    else:
        raw_status = "running"

    record.update(
        {
            "status": raw_status,
            "progress": progress,
            "failure_reason": failure_reason,
            "error_message": error_message,
            "updated_at": refreshed_at.isoformat(),
        }
    )
    if raw_status in {"succeeded", "failed"}:
        _cleanup_input_objects(record, active_settings)
    save_motion_task_record(record, active_settings)
    return record


def persist_motion_result(
    remote_video_url: str,
    task_id: str,
    settings: Settings | None = None,
    client: Minio | None = None,
) -> MotionResultInfo:
    """下载百炼 24 小时临时结果并转存，严格限制最大字节数。"""

    active_settings = settings or get_settings()
    request = Request(
        _validate_remote_media_url(remote_video_url, "结果视频"),
        headers={"Accept": "video/mp4,video/*;q=0.9,*/*;q=0.1", "User-Agent": "hakka-stage-ai/1.0"},
    )
    try:
        with urlopen(request, timeout=active_settings.video_timeout_seconds) as response:
            declared_size = int(response.headers.get("Content-Length") or 0)
            if declared_size > active_settings.motion_result_max_download_bytes:
                raise MotionTransferError(
                    f"生成结果超过 {active_settings.motion_result_max_download_mb}MB 转存上限，请使用临时地址下载。"
                )
            content_type = str(response.headers.get("Content-Type") or "video/mp4").split(";", 1)[0]
            if not content_type.startswith("video/"):
                content_type = "video/mp4"
            with TemporaryFile() as temporary:
                total_size = 0
                while True:
                    chunk = response.read(RESULT_DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > active_settings.motion_result_max_download_bytes:
                        raise MotionTransferError(
                            f"生成结果超过 {active_settings.motion_result_max_download_mb}MB 转存上限，请使用临时地址下载。"
                        )
                    temporary.write(chunk)
                if total_size <= 0:
                    raise MotionTransferError("百炼结果视频为空，暂时无法转存。")
                temporary.seek(0)
                minio_client = client or _minio_client(active_settings)
                _ensure_bucket(minio_client, active_settings.minio_bucket)
                object_key = f"{MOTION_RESULT_PREFIX}{task_id}.mp4"
                minio_client.put_object(
                    active_settings.minio_bucket,
                    object_key,
                    temporary,
                    total_size,
                    content_type=content_type,
                )
    except MotionTransferError:
        raise
    except HTTPError as exc:
        raise MotionTransferError(f"百炼结果下载失败：HTTP {exc.code}。") from exc
    except (URLError, TimeoutError) as exc:
        raise MotionTransferError("百炼结果下载超时，当前仍可使用供应商临时地址。") from exc
    except Exception as exc:
        raise MotionTransferError("结果暂时无法转存到 MinIO，请及时下载临时文件。") from exc
    return MotionResultInfo(object_key=object_key, content_type=content_type, size_bytes=total_size)


def open_motion_result(
    record: dict[str, Any],
    offset: int = 0,
    length: int | None = None,
    settings: Settings | None = None,
) -> Any:
    """打开当前任务已转存的视频对象，调用方必须先完成任务归属校验。"""

    object_key = str(record.get("result_object_key") or "")
    expected_prefix = f"{MOTION_RESULT_PREFIX}{record['id']}"
    if not object_key.startswith(expected_prefix):
        raise MotionTransferError("动作模仿结果尚未转存。", status_code=404)
    active_settings = settings or get_settings()
    kwargs: dict[str, int] = {"offset": offset}
    if length is not None:
        kwargs["length"] = length
    try:
        return _minio_client(active_settings).get_object(
            active_settings.minio_bucket,
            object_key,
            **kwargs,
        )
    except Exception as exc:
        raise MotionTransferError("动作模仿结果暂时无法读取。", status_code=404) from exc


def parse_motion_video_range(
    range_header: str | None,
    total_size: int,
) -> MotionVideoByteRange | None:
    """解析浏览器单段 Range 请求；非法或多段范围统一返回 416。"""

    if not range_header:
        return None
    if total_size <= 0 or not range_header.startswith("bytes=") or "," in range_header:
        raise MotionTransferError("视频字节范围无效。", status_code=416)
    value = range_header.removeprefix("bytes=").strip()
    if "-" not in value:
        raise MotionTransferError("视频字节范围无效。", status_code=416)
    start_text, end_text = value.split("-", 1)
    try:
        if not start_text:
            suffix_length = int(end_text)
            if suffix_length <= 0:
                raise ValueError
            start = max(total_size - suffix_length, 0)
            end = total_size - 1
        else:
            start = int(start_text)
            end = int(end_text) if end_text else total_size - 1
            if start < 0 or start >= total_size or end < start:
                raise ValueError
            end = min(end, total_size - 1)
    except ValueError as exc:
        raise MotionTransferError("视频字节范围无效。", status_code=416) from exc
    return MotionVideoByteRange(start=start, end=end)


def iter_motion_object(response: Any) -> Iterator[bytes]:
    """分块返回 MinIO 对象，并在请求结束时释放底层连接。"""

    try:
        while True:
            chunk = response.read(STREAM_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    finally:
        response.close()
        response.release_conn()


def mark_motion_task_failed(
    record: dict[str, Any],
    error: Exception,
    settings: Settings | None = None,
) -> None:
    """提交失败仍保存终态，方便页面向用户解释具体原因。"""

    record.update(
        {
            "status": "failed",
            "progress": 100,
            "error_message": str(error)[:500],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _cleanup_input_objects(record, settings or get_settings())
    save_motion_task_record(record, settings)


def public_motion_task_record(record: dict[str, Any]) -> dict[str, Any]:
    """移除任务归属、供应商 ID、对象键等内部字段后再返回浏览器。"""

    allowed_keys = {
        "id",
        "status",
        "progress",
        "provider",
        "model",
        "mode",
        "resolution",
        "watermark",
        "person_file_name",
        "motion_file_name",
        "motion_duration_seconds",
        "result_available",
        "result_persisted",
        "storage_warning",
        "failure_reason",
        "error_message",
        "created_at",
        "updated_at",
        "expires_at",
    }
    return {key: record[key] for key in allowed_keys if key in record}


def remove_motion_inputs(
    object_keys: list[str],
    settings: Settings | None = None,
) -> None:
    """幂等清理本次请求已经写入的精确输入对象，避免失败上传长期占用空间。"""

    if not object_keys:
        return
    active_settings = settings or get_settings()
    client = _minio_client(active_settings)
    for object_key in object_keys:
        if not object_key.startswith(MOTION_INPUT_PREFIX):
            continue
        try:
            client.remove_object(active_settings.minio_bucket, object_key)
        except Exception:
            # 清理属于非关键补偿动作，不能覆盖原始供应商或上传错误。
            continue


def _cleanup_input_objects(record: dict[str, Any], settings: Settings) -> None:
    object_keys = [str(value) for value in record.get("input_object_keys") or []]
    remove_motion_inputs(object_keys, settings)
    record["input_object_keys"] = []


def _safe_file_name(value: str) -> str:
    file_name = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not file_name:
        raise MotionTransferError("请上传带有文件名的素材。", status_code=400)
    if len(file_name) > 240 or any(ord(character) < 32 for character in file_name):
        raise MotionTransferError("素材文件名过长或包含控制字符，请重命名后上传。", status_code=400)
    return file_name


def _validate_remote_media_url(value: str, label: str) -> str:
    if not _is_http_url(value):
        raise MotionTransferError(f"{label}地址必须是可公开访问的 HTTP(S) URL。", status_code=400)
    return value.strip()


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _valid_public_base_url(value: str) -> bool:
    return _is_http_url(value)


def _redis_client(settings: Settings) -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _ensure_redis_available(client: redis.Redis) -> None:
    try:
        client.ping()
    except redis.RedisError as exc:
        raise MotionTransferError("Redis 暂不可用，不能安全创建动作模仿任务。", status_code=503) from exc


def _minio_client(settings: Settings) -> Minio:
    parsed = urlparse(settings.minio_endpoint)
    endpoint = parsed.netloc or parsed.path
    if not endpoint:
        raise MotionTransferError("MinIO 地址无效，无法保存动作模仿素材。", status_code=503)
    try:
        return Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=parsed.scheme == "https",
        )
    except Exception as exc:
        raise MotionTransferError("MinIO 地址无效，无法保存动作模仿素材。", status_code=503) from exc


def _ensure_bucket(client: Minio, bucket_name: str) -> None:
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
    except S3Error as exc:
        if exc.code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            return
        raise MotionTransferError("MinIO 暂不可用，无法准备媒体存储桶。", status_code=503) from exc
    except Exception as exc:
        raise MotionTransferError("MinIO 暂不可用，无法准备媒体存储桶。", status_code=503) from exc
