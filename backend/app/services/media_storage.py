from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.core.config import Settings
from app.services.rehearsal_storage import create_minio_client


ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
    ".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv",
}
MEDIA_OBJECT_PREFIX = "media-inputs/"
STREAM_CHUNK_SIZE = 1024 * 1024


class MediaStorageError(RuntimeError):
    """通用媒体存储错误，可直接映射为 HTTP 状态码。"""

    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class MediaUploadResult:
    object_key: str
    original_file_name: str
    content_type: str
    size_bytes: int
    media_type: str


def _infer_media_type(content_type: str, extension: str) -> str:
    for prefix in ("image", "audio", "video"):
        if content_type.startswith(f"{prefix}/"):
            return prefix
    if extension in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return "image"
    if extension in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
        return "audio"
    if extension in {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}:
        return "video"
    return "other"


def save_media_upload(file: UploadFile, settings: Settings, client: Minio | None = None) -> MediaUploadResult:
    """校验用户媒体输入并流式写入 MinIO，不把大文件整体载入内存。"""

    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not filename or len(filename) > 240 or any(ord(char) < 32 for char in filename):
        raise MediaStorageError("媒体文件名为空、过长或包含控制字符", 400)
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise MediaStorageError("暂不支持该媒体格式，请上传常见图片、音频或视频文件", 400)
    content_type = file.content_type or "application/octet-stream"
    media_type = _infer_media_type(content_type, extension)
    if media_type == "other":
        raise MediaStorageError("无法识别媒体类型", 400)
    try:
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
    except (AttributeError, OSError) as exc:
        raise MediaStorageError("无法读取上传文件", 400) from exc
    if size_bytes <= 0:
        raise MediaStorageError("上传文件为空", 400)
    if size_bytes > settings.media_max_upload_bytes:
        raise MediaStorageError(f"文件超过 {settings.media_max_upload_mb}MB 上限", 413)

    minio_client = client or create_minio_client(settings)
    try:
        if not minio_client.bucket_exists(settings.minio_bucket):
            minio_client.make_bucket(settings.minio_bucket)
        object_key = f"{MEDIA_OBJECT_PREFIX}{uuid4().hex}{extension}"
        minio_client.put_object(
            settings.minio_bucket, object_key, file.file, size_bytes, content_type=content_type
        )
    except Exception as exc:
        raise MediaStorageError("MinIO 暂时不可用，媒体文件未保存") from exc
    return MediaUploadResult(object_key, filename, content_type, size_bytes, media_type)


def stat_media_object(object_key: str, settings: Settings, client: Minio | None = None) -> tuple[int, str]:
    """读取受管媒体元信息，同时限制只能访问媒体目录。"""

    if not object_key.startswith(("media-inputs/", "media-results/")):
        raise MediaStorageError("媒体对象键无效", 400)
    try:
        stat = (client or create_minio_client(settings)).stat_object(settings.minio_bucket, object_key)
        return int(stat.size), stat.content_type or "application/octet-stream"
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
            raise MediaStorageError("媒体文件不存在", 404) from exc
        raise MediaStorageError("MinIO 暂时不可用") from exc
    except Exception as exc:
        raise MediaStorageError("MinIO 暂时不可用") from exc


def open_media_object(
    object_key: str, settings: Settings, offset: int = 0, length: int | None = None, client: Minio | None = None
) -> Any:
    """打开完整对象或单段字节范围，供图片、音频、视频统一展示。"""

    if not object_key.startswith(("media-inputs/", "media-results/")):
        raise MediaStorageError("媒体对象键无效", 400)
    kwargs: dict[str, int] = {"offset": offset}
    if length is not None:
        kwargs["length"] = length
    try:
        return (client or create_minio_client(settings)).get_object(settings.minio_bucket, object_key, **kwargs)
    except Exception as exc:
        raise MediaStorageError("MinIO 暂时不可用，无法读取媒体文件") from exc


def iter_media_object(response: Any) -> Iterator[bytes]:
    """分块转发 MinIO 响应并可靠释放连接。"""

    try:
        while chunk := response.read(STREAM_CHUNK_SIZE):
            yield chunk
    finally:
        response.close()
        response.release_conn()
