from os import getenv

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """后端运行配置。

    这里不依赖额外的 pydantic-settings，避免在第一版功能里引入过多配置层。
    所有敏感信息只从环境变量读取，不写入代码或接口响应。
    """

    project_name: str = "hakka-stage-ai"
    cors_origins: str | None = None
    postgres_host: str = "localhost"
    postgres_port: str = "5432"
    postgres_db: str = "hakka_stage_ai"
    postgres_user: str = "hakka"
    postgres_password: str = "hakka_password"
    auth_secret_key: str = Field("local-dev-only-change-me-at-least-32-bytes", min_length=32)
    auth_access_token_minutes: int = 480
    auth_cookie_secure: bool = False
    bootstrap_account_email: str = ""
    bootstrap_account_password: str = ""
    bootstrap_account_display_name: str = "平台初始账号"
    bootstrap_account_role: str = "teacher"
    redis_host: str = "localhost"
    redis_port: str = "6379"
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "hakka-stage-ai"
    m08_video_max_upload_mb: int = 200
    # 原媒体工作台使用独立 Mock 开关，避免图生图和克隆音频联调触发第三方计费。
    media_max_upload_mb: int = 200
    media_mock_mode: bool = True
    grsai_api_key: str = ""
    grsai_base_url: str = "https://grsai.dakka.com.cn"
    runninghub_api_key: str = ""
    runninghub_base_url: str = "https://www.runninghub.cn"
    practice_upload_dir: str = "uploads"
    practice_max_upload_mb: int = 200
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # Wan 2.7 视频接口使用百炼原生异步协议，不能复用 OpenAI 兼容接口地址。
    # 建议为视频生成单独创建 API Key，便于独立审计费用与轮换密钥。
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com"
    llm_default_provider: str = "deepseek"
    llm_default_model: str = "deepseek-v4-flash"
    llm_default_reasoning_level: str = "standard"
    llm_mock_mode: bool = False
    # 用户上传的首帧会暂存 MinIO，并通过带签名的公开短链交给 GRS AI 拉取。
    # 生产环境应填写外网可访问的后端根地址，例如 https://api.example.com。
    grsai_public_base_url: str = ""
    grsai_timeout_seconds: float = 30.0
    grsai_mock_mode: bool = False
    grsai_image_max_upload_mb: int = 10
    # 图生视频保留独立配置，避免 GRS AI 图生图与百炼 Wan 2.7 共用开关或密钥。
    video_public_base_url: str = ""
    video_timeout_seconds: float = 30.0
    video_mock_mode: bool = False
    video_image_max_upload_mb: int = 20
    # 动作模仿继续复用百炼视频密钥与公网回源地址，但按官方协议使用更严格的独立素材上限。
    motion_image_max_upload_mb: int = 5
    motion_video_max_upload_mb: int = 200
    motion_result_max_download_mb: int = 500

    @property
    def database_url(self) -> str:
        """生成 SQLAlchemy 使用的 PostgreSQL 连接串。"""

        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """生成 Redis 连接串。"""

        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def practice_max_upload_bytes(self) -> int:
        """练习视频上传大小上限，统一由 MB 转成字节。"""

        return self.practice_max_upload_mb * 1024 * 1024

    @property
    def m08_video_max_upload_bytes(self) -> int:
        """把 M08 视频附件上限从 MB 转换为字节。"""

        return self.m08_video_max_upload_mb * 1024 * 1024

    @property
    def media_max_upload_bytes(self) -> int:
        """把通用媒体素材上传上限从 MB 转换为字节。"""

        return self.media_max_upload_mb * 1024 * 1024

    @property
    def grsai_image_max_upload_bytes(self) -> int:
        """把 GRS AI 首尾帧上传上限从 MB 转换为字节。"""

        return self.grsai_image_max_upload_mb * 1024 * 1024

    @property
    def video_image_max_upload_bytes(self) -> int:
        """把 Wan 图生视频单张首尾帧上传上限从 MB 转换为字节。"""

        return self.video_image_max_upload_mb * 1024 * 1024

    @property
    def motion_image_max_upload_bytes(self) -> int:
        """把动作模仿人物图片上限从 MB 转换为字节。"""

        return self.motion_image_max_upload_mb * 1024 * 1024

    @property
    def motion_video_max_upload_bytes(self) -> int:
        """把动作模仿参考视频上限从 MB 转换为字节。"""

        return self.motion_video_max_upload_mb * 1024 * 1024

    @property
    def motion_result_max_download_bytes(self) -> int:
        """把动作模仿结果转存上限从 MB 转换为字节，防止异常远端响应占满磁盘。"""

        return self.motion_result_max_download_mb * 1024 * 1024

def get_settings() -> Settings:
    """从环境变量读取配置，提供本地开发默认值。"""

    # 兼容已经部署的旧版 Veo 环境变量，便于先升级镜像、再平滑迁移 .env。
    # 新部署应优先使用 VIDEO_*，后续不会再通过旧 GRS AI 视频通道生成。
    legacy_video_public_base_url = getenv("GRSAI_PUBLIC_BASE_URL", "")
    legacy_video_timeout_seconds = getenv("GRSAI_TIMEOUT_SECONDS", "30")
    legacy_video_mock_mode = getenv("GRSAI_MOCK_MODE", "false")
    legacy_video_image_max_upload_mb = getenv("GRSAI_IMAGE_MAX_UPLOAD_MB", "20")

    return Settings(
        project_name=getenv("PROJECT_NAME", "hakka-stage-ai"),
        cors_origins=getenv("CORS_ORIGINS"),
        postgres_host=getenv("POSTGRES_HOST", "localhost"),
        postgres_port=getenv("POSTGRES_PORT", "5432"),
        postgres_db=getenv("POSTGRES_DB", "hakka_stage_ai"),
        postgres_user=getenv("POSTGRES_USER", "hakka"),
        postgres_password=getenv("POSTGRES_PASSWORD", "hakka_password"),
        auth_secret_key=getenv("AUTH_SECRET_KEY", "local-dev-only-change-me-at-least-32-bytes"),
        auth_access_token_minutes=int(getenv("AUTH_ACCESS_TOKEN_MINUTES", "480")),
        auth_cookie_secure=getenv("AUTH_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"},
        bootstrap_account_email=getenv("BOOTSTRAP_ACCOUNT_EMAIL", ""),
        bootstrap_account_password=getenv("BOOTSTRAP_ACCOUNT_PASSWORD", ""),
        bootstrap_account_display_name=getenv("BOOTSTRAP_ACCOUNT_DISPLAY_NAME", "平台初始账号"),
        bootstrap_account_role=getenv("BOOTSTRAP_ACCOUNT_ROLE", "teacher"),
        redis_host=getenv("REDIS_HOST", "localhost"),
        redis_port=getenv("REDIS_PORT", "6379"),
        minio_endpoint=getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        minio_access_key=getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_bucket=getenv("MINIO_BUCKET", "hakka-stage-ai"),
        m08_video_max_upload_mb=int(getenv("M08_VIDEO_MAX_UPLOAD_MB", "200")),
        media_max_upload_mb=int(getenv("MEDIA_MAX_UPLOAD_MB", "200")),
        media_mock_mode=getenv("MEDIA_MOCK_MODE", "true").lower() in {"1", "true", "yes", "on"},
        grsai_api_key=getenv("GRSAI_API_KEY", ""),
        grsai_base_url=getenv("GRSAI_BASE_URL", "https://grsai.dakka.com.cn"),
        runninghub_api_key=getenv("RUNNINGHUB_API_KEY", ""),
        runninghub_base_url=getenv("RUNNINGHUB_BASE_URL", "https://www.runninghub.cn"),
        practice_upload_dir=getenv("PRACTICE_UPLOAD_DIR", "uploads"),
        practice_max_upload_mb=int(getenv("PRACTICE_MAX_UPLOAD_MB", "200")),
        deepseek_api_key=getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        qwen_api_key=getenv("QWEN_API_KEY", ""),
        qwen_base_url=getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        dashscope_api_key=getenv("DASHSCOPE_API_KEY", ""),
        dashscope_base_url=getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com"),
        llm_default_provider=getenv("LLM_DEFAULT_PROVIDER", "deepseek"),
        llm_default_model=getenv("LLM_DEFAULT_MODEL", "deepseek-v4-flash"),
        llm_default_reasoning_level=getenv("LLM_DEFAULT_REASONING_LEVEL", "standard"),
        llm_mock_mode=getenv("LLM_MOCK_MODE", "false").lower() in {"1", "true", "yes", "on"},
        grsai_public_base_url=getenv("GRSAI_PUBLIC_BASE_URL", ""),
        grsai_timeout_seconds=float(getenv("GRSAI_TIMEOUT_SECONDS", "30")),
        grsai_mock_mode=getenv("GRSAI_MOCK_MODE", "false").lower() in {"1", "true", "yes", "on"},
        grsai_image_max_upload_mb=int(getenv("GRSAI_IMAGE_MAX_UPLOAD_MB", "10")),
        video_public_base_url=getenv("VIDEO_PUBLIC_BASE_URL") or legacy_video_public_base_url,
        video_timeout_seconds=float(getenv("VIDEO_TIMEOUT_SECONDS") or legacy_video_timeout_seconds),
        video_mock_mode=(getenv("VIDEO_MOCK_MODE") or legacy_video_mock_mode).lower()
        in {"1", "true", "yes", "on"},
        video_image_max_upload_mb=int(
            getenv("VIDEO_IMAGE_MAX_UPLOAD_MB") or legacy_video_image_max_upload_mb
        ),
        motion_image_max_upload_mb=int(getenv("MOTION_IMAGE_MAX_UPLOAD_MB", "5")),
        motion_video_max_upload_mb=int(getenv("MOTION_VIDEO_MAX_UPLOAD_MB", "200")),
        motion_result_max_download_mb=int(getenv("MOTION_RESULT_MAX_DOWNLOAD_MB", "500")),
    )
