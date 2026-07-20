from os import getenv

from pydantic import BaseModel


class WorkerSettings(BaseModel):
    """Worker 运行配置。

    Worker 是唯一直接调用大模型的进程，API Key 只从环境变量读取，不写入日志。
    """

    project_name: str = "hakka-stage-ai"
    postgres_host: str = "localhost"
    postgres_port: str = "5432"
    postgres_db: str = "hakka_stage_ai"
    postgres_user: str = "hakka"
    postgres_password: str = "hakka_password"
    redis_host: str = "localhost"
    redis_port: str = "6379"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_default_provider: str = "deepseek"
    llm_default_model: str = "deepseek-v4-flash"
    llm_default_reasoning_level: str = "standard"
    llm_mock_mode: bool = False
    llm_timeout_seconds: float = 120.0
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "hakka-stage-ai"
    grsai_api_key: str = ""
    grsai_base_url: str = "https://grsai.dakka.com.cn"
    runninghub_api_key: str = ""
    runninghub_base_url: str = "https://www.runninghub.cn"
    media_mock_mode: bool = True
    media_http_timeout_seconds: float = 120.0
    media_poll_interval_seconds: int = 5
    media_poll_max_count: int = 720
    # GRS AI 的真实图生图通常需要几十秒到数分钟。独立使用较低频率轮询，
    # 避免沿用 RunningHub 的 5 秒间隔产生不必要请求；100 分钟上限也小于
    # 供应商异步查询结果约 2 小时的有效期，便于在结果失效前明确结束任务。
    grsai_poll_interval_seconds: int = 15
    grsai_poll_max_count: int = 400

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


def get_settings() -> WorkerSettings:
    """读取 Worker 环境变量。"""

    return WorkerSettings(
        project_name=getenv("PROJECT_NAME", "hakka-stage-ai"),
        postgres_host=getenv("POSTGRES_HOST", "localhost"),
        postgres_port=getenv("POSTGRES_PORT", "5432"),
        postgres_db=getenv("POSTGRES_DB", "hakka_stage_ai"),
        postgres_user=getenv("POSTGRES_USER", "hakka"),
        postgres_password=getenv("POSTGRES_PASSWORD", "hakka_password"),
        redis_host=getenv("REDIS_HOST", "localhost"),
        redis_port=getenv("REDIS_PORT", "6379"),
        deepseek_api_key=getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        qwen_api_key=getenv("QWEN_API_KEY", ""),
        qwen_base_url=getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        llm_default_provider=getenv("LLM_DEFAULT_PROVIDER", "deepseek"),
        llm_default_model=getenv("LLM_DEFAULT_MODEL", "deepseek-v4-flash"),
        llm_default_reasoning_level=getenv("LLM_DEFAULT_REASONING_LEVEL", "standard"),
        llm_mock_mode=getenv("LLM_MOCK_MODE", "false").lower() in {"1", "true", "yes", "on"},
        llm_timeout_seconds=float(getenv("LLM_TIMEOUT_SECONDS", "120")),
        minio_endpoint=getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        minio_access_key=getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_bucket=getenv("MINIO_BUCKET", "hakka-stage-ai"),
        grsai_api_key=getenv("GRSAI_API_KEY", ""),
        grsai_base_url=getenv("GRSAI_BASE_URL", "https://grsai.dakka.com.cn"),
        runninghub_api_key=getenv("RUNNINGHUB_API_KEY", ""),
        runninghub_base_url=getenv("RUNNINGHUB_BASE_URL", "https://www.runninghub.cn"),
        media_mock_mode=getenv("MEDIA_MOCK_MODE", "true").lower() in {"1", "true", "yes", "on"},
        media_http_timeout_seconds=float(getenv("MEDIA_HTTP_TIMEOUT_SECONDS", "120")),
        media_poll_interval_seconds=int(getenv("MEDIA_POLL_INTERVAL_SECONDS", "5")),
        media_poll_max_count=int(getenv("MEDIA_POLL_MAX_COUNT", "720")),
        grsai_poll_interval_seconds=int(getenv("GRSAI_POLL_INTERVAL_SECONDS", "15")),
        grsai_poll_max_count=int(getenv("GRSAI_POLL_MAX_COUNT", "400")),
    )
