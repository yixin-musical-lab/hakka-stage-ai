import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.core.config import Settings, get_settings


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
M08_OBJECT_PREFIX = "rehearsal-reviews/"
STREAM_CHUNK_SIZE = 1024 * 1024
NOT_FOUND_CODES = {"NoSuchBucket", "NoSuchKey", "NoSuchObject"}
M08_OBJECT_KEY_PATTERN = re.compile(
    r"^rehearsal-reviews/[0-9a-f]{32}\.(?:mp4|mov|m4v|webm|avi|mkv)$"
)


class RehearsalStorageError(RuntimeError):
    """M08 MinIO 存储错误，并携带可映射到 HTTP 的状态码。"""

    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class RehearsalVideoUploadResult:
    """上传完成后写入复盘表单的安全元数据。"""

    object_key: str
    original_file_name: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True)
class RehearsalVideoObjectInfo:
    """MinIO 对象的可校验元数据。"""

    object_key: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True)
class VideoByteRange:
    """浏览器单段 Range 请求的规范化范围。"""

    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1


def create_minio_client(settings: Settings | None = None) -> Minio:
    """根据项目环境变量创建 MinIO 客户端。

    MinIO SDK 的 endpoint 参数不接收 URL path，因此这里统一解析 http/https，
    Docker 内的 ``http://minio:9000`` 和宿主机的 ``http://localhost:9000`` 都可复用。
    """

    active_settings = settings or get_settings()
    parsed = urlparse(active_settings.minio_endpoint)
    endpoint = parsed.netloc or parsed.path
    if not endpoint:
        raise RehearsalStorageError("MinIO 地址配置为空，无法保存排练视频。")
    try:
        return Minio(
            endpoint=endpoint,
            access_key=active_settings.minio_access_key,
            secret_key=active_settings.minio_secret_key,
            secure=parsed.scheme == "https",
        )
    except Exception as exc:  # MinIO SDK 也可能用 ValueError 报告非法 endpoint。
        raise RehearsalStorageError("MinIO 地址配置无效，无法保存排练视频。") from exc


def save_rehearsal_video_upload(
    file: UploadFile,
    settings: Settings,
    client: Minio | None = None,
) -> RehearsalVideoUploadResult:
    """校验视频并直接流式写入 M08 专用 MinIO 目录。"""

    # 浏览器通常只发送 basename，但仍主动兼容 Windows / POSIX 路径写法，
    # 避免把客户端目录信息或控制字符写入数据库和 Content-Disposition。
    original_file_name = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not original_file_name:
        raise RehearsalStorageError("请上传带有文件名的视频文件。", status_code=400)
    if len(original_file_name) > 240 or any(ord(character) < 32 for character in original_file_name):
        raise RehearsalStorageError("视频文件名过长或包含控制字符，请重命名后上传。", status_code=400)

    extension = Path(original_file_name).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = "、".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        raise RehearsalStorageError(f"暂只支持常见视频格式：{allowed}。", status_code=400)

    content_type = file.content_type or "application/octet-stream"
    if not (content_type.startswith("video/") or extension in {".mov", ".m4v"}):
        raise RehearsalStorageError("上传文件看起来不是视频，请选择排练或演出视频片段。", status_code=400)

    try:
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
    except (AttributeError, OSError) as exc:
        raise RehearsalStorageError("无法读取上传视频，请重新选择文件。", status_code=400) from exc

    if size_bytes <= 0:
        raise RehearsalStorageError("上传的视频文件为空，请重新选择文件。", status_code=400)
    if size_bytes > settings.m08_video_max_upload_bytes:
        raise RehearsalStorageError(
            f"视频文件超过 {settings.m08_video_max_upload_mb}MB 上限，请压缩或截取短片段后上传。",
            status_code=413,
        )

    minio_client = client or create_minio_client(settings)
    _ensure_bucket(minio_client, settings.minio_bucket)
    object_key = f"{M08_OBJECT_PREFIX}{uuid4().hex}{extension}"
    try:
        minio_client.put_object(
            bucket_name=settings.minio_bucket,
            object_name=object_key,
            data=file.file,
            length=size_bytes,
            content_type=content_type,
        )
    except S3Error as exc:
        raise RehearsalStorageError("MinIO 暂时不可用，视频附件未能保存。") from exc
    except Exception as exc:  # 网络断开通常由 urllib3 异常报告，而不是 S3Error。
        raise RehearsalStorageError("MinIO 暂时不可用，视频附件未能保存。") from exc

    return RehearsalVideoUploadResult(
        object_key=object_key,
        original_file_name=original_file_name,
        content_type=content_type,
        size_bytes=size_bytes,
    )


def stat_rehearsal_video(
    object_key: str,
    settings: Settings | None = None,
    client: Minio | None = None,
) -> RehearsalVideoObjectInfo:
    """确认对象确实存在于 M08 目录，并返回服务端可信元数据。"""

    _validate_object_key(object_key)
    active_settings = settings or get_settings()
    minio_client = client or create_minio_client(active_settings)
    try:
        stat = minio_client.stat_object(active_settings.minio_bucket, object_key)
    except S3Error as exc:
        if exc.code in NOT_FOUND_CODES:
            raise RehearsalStorageError("排练视频附件不存在，请重新上传。", status_code=404) from exc
        raise RehearsalStorageError("MinIO 暂时不可用，无法读取排练视频附件。") from exc
    except Exception as exc:
        raise RehearsalStorageError("MinIO 暂时不可用，无法读取排练视频附件。") from exc
    return RehearsalVideoObjectInfo(
        object_key=object_key,
        content_type=stat.content_type or "application/octet-stream",
        size_bytes=int(stat.size),
    )


def open_rehearsal_video(
    object_key: str,
    offset: int = 0,
    length: int | None = None,
    settings: Settings | None = None,
    client: Minio | None = None,
) -> Any:
    """从私有桶读取完整对象或指定字节范围，供后端代理播放。"""

    _validate_object_key(object_key)
    active_settings = settings or get_settings()
    minio_client = client or create_minio_client(active_settings)
    kwargs: dict[str, int] = {"offset": offset}
    if length is not None:
        kwargs["length"] = length
    try:
        return minio_client.get_object(active_settings.minio_bucket, object_key, **kwargs)
    except S3Error as exc:
        if exc.code in NOT_FOUND_CODES:
            raise RehearsalStorageError("排练视频附件不存在。", status_code=404) from exc
        raise RehearsalStorageError("MinIO 暂时不可用，无法播放排练视频。") from exc
    except Exception as exc:
        raise RehearsalStorageError("MinIO 暂时不可用，无法播放排练视频。") from exc


def iter_minio_response(response: Any) -> Iterator[bytes]:
    """分块转发 MinIO 响应，并在客户端断开后可靠释放连接。"""

    try:
        while True:
            chunk = response.read(STREAM_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    finally:
        response.close()
        response.release_conn()


def remove_rehearsal_video(
    object_key: str,
    settings: Settings | None = None,
    client: Minio | None = None,
) -> None:
    """幂等删除 M08 视频对象；对象已不存在时视为成功。"""

    if not object_key:
        return
    _validate_object_key(object_key)
    active_settings = settings or get_settings()
    minio_client = client or create_minio_client(active_settings)
    try:
        minio_client.remove_object(active_settings.minio_bucket, object_key)
    except S3Error as exc:
        if exc.code in NOT_FOUND_CODES:
            return
        raise RehearsalStorageError("MinIO 暂时不可用，无法删除排练视频附件。") from exc
    except Exception as exc:
        raise RehearsalStorageError("MinIO 暂时不可用，无法删除排练视频附件。") from exc


def parse_video_range(range_header: str | None, total_size: int) -> VideoByteRange | None:
    """解析单段 HTTP Range；不支持多段范围，非法值统一返回 416。"""

    if not range_header:
        return None
    if total_size <= 0 or not range_header.startswith("bytes=") or "," in range_header:
        raise RehearsalStorageError("视频字节范围无效。", status_code=416)

    value = range_header.removeprefix("bytes=").strip()
    if "-" not in value:
        raise RehearsalStorageError("视频字节范围无效。", status_code=416)
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
        raise RehearsalStorageError("视频字节范围无效。", status_code=416) from exc
    return VideoByteRange(start=start, end=end)


def _ensure_bucket(client: Minio, bucket_name: str) -> None:
    """惰性创建私有桶，避免应用启动因对象存储短暂抖动而失败。"""

    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
    except S3Error as exc:
        if exc.code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            return
        raise RehearsalStorageError("MinIO 暂时不可用，无法准备视频存储桶。") from exc
    except Exception as exc:
        raise RehearsalStorageError("MinIO 暂时不可用，无法准备视频存储桶。") from exc


def _validate_object_key(object_key: str) -> None:
    """阻止通过对象键访问 M08 目录外的任意对象。"""

    if not M08_OBJECT_KEY_PATTERN.fullmatch(object_key):
        raise RehearsalStorageError("视频对象键无效。", status_code=400)
