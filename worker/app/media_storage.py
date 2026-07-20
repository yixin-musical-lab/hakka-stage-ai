import base64
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Iterator
from urllib.parse import unquote_to_bytes, urlparse
from uuid import uuid4

import httpx
from minio import Minio

from app.config import WorkerSettings


class WorkerMediaStorage:
    """Worker 使用的 MinIO 与远程结果转存工具。"""

    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings
        parsed = urlparse(settings.minio_endpoint)
        endpoint = parsed.netloc or parsed.path
        self.client = Minio(
            endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key,
            secure=parsed.scheme == "https",
        )

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.settings.minio_bucket):
            self.client.make_bucket(self.settings.minio_bucket)

    def open(self, object_key: str):
        if not object_key.startswith(("media-inputs/", "media-results/")):
            raise RuntimeError("媒体对象键越界")
        return self.client.get_object(self.settings.minio_bucket, object_key)

    @contextmanager
    def staged_upload(
        self,
        object_key: str,
        expected_size: int | None = None,
    ) -> Iterator[tuple[BinaryIO, int]]:
        """把 MinIO 网络响应分块暂存为可定位文件，供 multipart 上传使用。

        MinIO ``get_object`` 返回的是基于 socket 的网络响应，不是普通磁盘文件。
        若直接把它传给 httpx，multipart 长度探测可能误用底层 socket 的
        ``fileno``，从而声明错误的 Content-Length。这里先复制到可 seek 的
        ``SpooledTemporaryFile``：小文件保留在内存，超过 16MB 后自动落临时盘。
        """

        source = self.open(object_key)
        staged = SpooledTemporaryFile(max_size=16 * 1024 * 1024)
        actual_size = 0
        try:
            try:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    staged.write(chunk)
                    actual_size += len(chunk)
            finally:
                source.close()
                source.release_conn()
        except Exception:
            # 下载中断时及时释放可能已经落盘的临时文件。
            staged.close()
            raise

        if actual_size <= 0:
            staged.close()
            raise RuntimeError("待上传的 MinIO 媒体文件为空")
        if expected_size is not None and actual_size != expected_size:
            staged.close()
            raise RuntimeError(
                f"读取 MinIO 媒体文件不完整：记录大小 {expected_size} 字节，实际读取 {actual_size} 字节"
            )

        staged.seek(0)
        try:
            yield staged, actual_size
        finally:
            staged.close()

    def read_data_url(self, object_key: str, content_type: str, max_bytes: int = 12 * 1024 * 1024) -> str:
        """把私有 MinIO 图片编码为 GRS AI unified 接口可消费的 data URL。

        设置独立上限，避免把超大文件 Base64 后塞进供应商请求和 Worker 内存。
        """

        if not object_key.startswith("media-inputs/"):
            raise RuntimeError("只能把用户上传的媒体输入发送给 GRS AI")
        stat = self.client.stat_object(self.settings.minio_bucket, object_key)
        if stat.size <= 0 or stat.size > max_bytes:
            raise RuntimeError("GRS AI 参考图片必须大于 0 且不超过 12MB")
        response = self.open(object_key)
        try:
            data = response.read(max_bytes + 1)
        finally:
            response.close()
            response.release_conn()
        if len(data) != stat.size:
            raise RuntimeError("读取 GRS AI 参考图片失败")
        mime = content_type if content_type.startswith("image/") else "image/png"
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"

    def transfer_result(self, url: str, media_type: str, content_type_hint: str = "") -> tuple[str, str, int, str]:
        """在供应商临时 URL 失效前下载结果，并写入长期 MinIO 对象。"""

        self.ensure_bucket()
        if url.startswith("data:"):
            header, encoded = url.split(",", 1)
            content_type = header[5:].split(";", 1)[0] or content_type_hint or "application/octet-stream"
            data = base64.b64decode(encoded) if ";base64" in header else unquote_to_bytes(encoded)
            stream = BytesIO(data)
            size = len(data)
        else:
            stream = SpooledTemporaryFile(max_size=16 * 1024 * 1024)
            with httpx.stream("GET", url, follow_redirects=True, timeout=self.settings.media_http_timeout_seconds) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0] or content_type_hint or "application/octet-stream"
                for chunk in response.iter_bytes():
                    stream.write(chunk)
            size = stream.tell()
            stream.seek(0)
        if size <= 0:
            stream.close()
            raise RuntimeError("供应商结果文件为空")
        extension = _extension_for(url, content_type, media_type)
        object_key = f"media-results/{uuid4().hex}{extension}"
        self.client.put_object(self.settings.minio_bucket, object_key, stream, size, content_type=content_type)
        stream.close()
        return object_key, content_type, size, Path(object_key).name


def _extension_for(url: str, content_type: str, media_type: str) -> str:
    by_mime = {
        "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
        "audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/flac": ".flac",
        "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
    }
    if content_type in by_mime:
        return by_mime[content_type]
    suffix = Path(urlparse(url).path).suffix.lower()
    if 1 < len(suffix) <= 6:
        return suffix
    return {"image": ".png", "audio": ".wav", "video": ".mp4"}.get(media_type, ".bin")
