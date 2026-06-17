from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class DependencyConfig(BaseModel):
    """暴露给前端的依赖配置摘要。

    当前骨架阶段只检查配置是否被读取，不主动连接数据库、Redis 或 MinIO。
    这样可以先稳定验证前后端和 Docker 服务启动链路，避免过早引入业务初始化逻辑。
    """

    name: str
    configured: bool
    endpoint: str


class HealthResponse(BaseModel):
    """健康检查响应结构。

    前端会依赖这个稳定结构显示连通状态，后续接入数据库探活时也可以在
    dependencies 字段中扩展，不影响最小页面。
    """

    status: str
    service: str
    message: str
    dependencies: list[DependencyConfig]


def _split_cors_origins(raw_value: str | None) -> list[str]:
    """把逗号分隔的 CORS 配置转成列表，兼容本地和 Docker 两种启动方式。"""

    if not raw_value:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def _local_dev_cors_regex() -> str:
    """允许本地开发常见来源访问 API。

    Vite 用 --host 0.0.0.0 启动后，浏览器可能通过 localhost、127.0.0.1
    或局域网 / Docker / WSL 网段 IP 访问前端。这里仅放开这些私有地址段，
    方便小组联调；正式部署时应改为明确域名白名单。
    """

    return (
        r"^https?://("
        r"localhost|"
        r"127\.0\.0\.1|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?$"
    )


def _dependency_config(name: str, endpoint: str, required_values: list[str]) -> DependencyConfig:
    """生成依赖配置摘要。

    required_values 只用于判断必要环境变量是否存在，不在健康检查中泄露密码。
    """

    return DependencyConfig(
        name=name,
        configured=all(required_values),
        endpoint=endpoint,
    )


def _getenv_with_default(name: str, default: str) -> str:
    """读取环境变量；未设置时使用本地开发默认值。

    Docker Compose 会显式传入容器内地址，例如 postgres、redis、minio；
    宿主机本地启动 backend 时则走 localhost 默认值，减少手动配置成本。
    """

    return getenv(name, default)


app = FastAPI(
    title="客韵智演 API",
    description="AI 歌舞剧教学与排演辅助系统的最小 FastAPI 骨架。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_split_cors_origins(getenv("CORS_ORIGINS")),
    allow_origin_regex=_local_dev_cors_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """返回后端健康状态和关键依赖配置状态。"""

    postgres_host = _getenv_with_default("POSTGRES_HOST", "localhost")
    postgres_port = _getenv_with_default("POSTGRES_PORT", "5432")
    postgres_db = _getenv_with_default("POSTGRES_DB", "hakka_stage_ai")
    postgres_user = _getenv_with_default("POSTGRES_USER", "hakka")
    redis_host = _getenv_with_default("REDIS_HOST", "localhost")
    redis_port = _getenv_with_default("REDIS_PORT", "6379")
    minio_endpoint = _getenv_with_default("MINIO_ENDPOINT", "http://localhost:9000")
    minio_access_key = _getenv_with_default("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = _getenv_with_default("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket = _getenv_with_default("MINIO_BUCKET", "hakka-stage-ai")

    return HealthResponse(
        status="ok",
        service=getenv("PROJECT_NAME", "hakka-stage-ai"),
        message="FastAPI 后端已启动，前后端连通检查可用。",
        dependencies=[
            _dependency_config(
                name="postgres",
                endpoint=f"{postgres_host}:{postgres_port}",
                required_values=[
                    postgres_host,
                    postgres_port,
                    postgres_db,
                    postgres_user,
                ],
            ),
            _dependency_config(
                name="redis",
                endpoint=f"{redis_host}:{redis_port}",
                required_values=[redis_host, redis_port],
            ),
            _dependency_config(
                name="minio",
                endpoint=minio_endpoint,
                required_values=[
                    minio_endpoint,
                    minio_access_key,
                    minio_secret_key,
                    minio_bucket,
                ],
            ),
        ],
    )
