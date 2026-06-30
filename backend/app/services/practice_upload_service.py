from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
CHUNK_SIZE = 1024 * 1024


class PracticeUploadError(ValueError):
    """练习视频上传校验失败。

    服务层只描述业务错误，不直接依赖 HTTPException，方便后续替换为 MinIO / OSS 存储时复用。
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class PracticeVideoUploadResult:
    """练习视频落盘后的结果，供路由层拼接公开访问地址。"""

    original_file_name: str
    stored_file_name: str
    relative_path: str
    content_type: str
    size_bytes: int


def save_practice_video_upload(
    file: UploadFile,
    upload_root: Path,
    max_bytes: int,
) -> PracticeVideoUploadResult:
    """保存练习视频文件。

    当前阶段使用开发期本地目录保存，保持接口和返回结构稳定；后续接 MinIO 时只需要替换本函数内部
    的存储实现，路由、前端和提交记录仍可沿用同一套字段。
    """

    original_file_name = Path(file.filename or "").name.strip()
    if not original_file_name:
        raise PracticeUploadError("请上传带有文件名的视频文件。")

    extension = Path(original_file_name).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = "、".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        raise PracticeUploadError(f"暂只支持常见视频格式：{allowed}。")

    content_type = file.content_type or "application/octet-stream"
    if not (content_type.startswith("video/") or extension in {".mov", ".m4v"}):
        raise PracticeUploadError("上传文件看起来不是视频，请选择手机录制的视频文件。")

    practice_dir = upload_root / "practice"
    practice_dir.mkdir(parents=True, exist_ok=True)

    stored_file_name = f"{uuid4().hex}{extension}"
    target_path = practice_dir / stored_file_name
    size_bytes = 0

    try:
        with target_path.open("wb") as target:
            while True:
                chunk = file.file.read(CHUNK_SIZE)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise PracticeUploadError(
                        f"视频文件超过 {max_bytes // 1024 // 1024}MB 上限，请压缩或截取 15-60 秒短片段后再上传。",
                        status_code=413,
                    )
                target.write(chunk)
    except PracticeUploadError:
        target_path.unlink(missing_ok=True)
        raise

    if size_bytes == 0:
        target_path.unlink(missing_ok=True)
        raise PracticeUploadError("上传的视频文件为空，请重新选择文件。")

    return PracticeVideoUploadResult(
        original_file_name=original_file_name,
        stored_file_name=stored_file_name,
        relative_path=f"practice/{stored_file_name}",
        content_type=content_type,
        size_bytes=size_bytes,
    )
