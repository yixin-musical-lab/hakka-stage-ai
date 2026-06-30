from os import getenv

from pydantic import BaseModel


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
    redis_host: str = "localhost"
    redis_port: str = "6379"
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "hakka-stage-ai"
    practice_upload_dir: str = "uploads"
    practice_max_upload_mb: int = 200
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_default_provider: str = "deepseek"
    llm_default_model: str = "deepseek-v4-flash"
    llm_default_reasoning_level: str = "standard"
    llm_mock_mode: bool = False

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


def get_settings() -> Settings:
    """从环境变量读取配置，提供本地开发默认值。"""

    return Settings(
        project_name=getenv("PROJECT_NAME", "hakka-stage-ai"),
        cors_origins=getenv("CORS_ORIGINS"),
        postgres_host=getenv("POSTGRES_HOST", "localhost"),
        postgres_port=getenv("POSTGRES_PORT", "5432"),
        postgres_db=getenv("POSTGRES_DB", "hakka_stage_ai"),
        postgres_user=getenv("POSTGRES_USER", "hakka"),
        postgres_password=getenv("POSTGRES_PASSWORD", "hakka_password"),
        redis_host=getenv("REDIS_HOST", "localhost"),
        redis_port=getenv("REDIS_PORT", "6379"),
        minio_endpoint=getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        minio_access_key=getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_bucket=getenv("MINIO_BUCKET", "hakka-stage-ai"),
        practice_upload_dir=getenv("PRACTICE_UPLOAD_DIR", "uploads"),
        practice_max_upload_mb=int(getenv("PRACTICE_MAX_UPLOAD_MB", "200")),
        deepseek_api_key=getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        qwen_api_key=getenv("QWEN_API_KEY", ""),
        qwen_base_url=getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        llm_default_provider=getenv("LLM_DEFAULT_PROVIDER", "deepseek"),
        llm_default_model=getenv("LLM_DEFAULT_MODEL", "deepseek-v4-flash"),
        llm_default_reasoning_level=getenv("LLM_DEFAULT_REASONING_LEVEL", "standard"),
        llm_mock_mode=getenv("LLM_MOCK_MODE", "false").lower() in {"1", "true", "yes", "on"},
    )
