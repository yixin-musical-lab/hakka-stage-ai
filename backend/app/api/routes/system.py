from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas import DependencyConfig, HealthResponse

router = APIRouter(tags=["system"])


def _dependency_config(name: str, endpoint: str, required_values: list[str]) -> DependencyConfig:
    """生成依赖配置摘要。

    required_values 只用于判断必要环境变量是否存在，不在健康检查中泄露密码。
    """

    return DependencyConfig(
        name=name,
        configured=all(required_values),
        endpoint=endpoint,
    )


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """返回后端健康状态和关键依赖配置状态。"""

    settings = get_settings()
    mock_marker = "mock" if settings.llm_mock_mode else ""
    return HealthResponse(
        status="ok",
        service=settings.project_name,
        message="FastAPI 后端已启动，前后端连通检查可用。",
        dependencies=[
            _dependency_config(
                name="postgres",
                endpoint=f"{settings.postgres_host}:{settings.postgres_port}",
                required_values=[
                    settings.postgres_host,
                    settings.postgres_port,
                    settings.postgres_db,
                    settings.postgres_user,
                ],
            ),
            _dependency_config(
                name="redis",
                endpoint=f"{settings.redis_host}:{settings.redis_port}",
                required_values=[settings.redis_host, settings.redis_port],
            ),
            _dependency_config(
                name="minio",
                endpoint=settings.minio_endpoint,
                required_values=[
                    settings.minio_endpoint,
                    settings.minio_access_key,
                    settings.minio_secret_key,
                    settings.minio_bucket,
                ],
            ),
            _dependency_config(
                name="deepseek",
                endpoint=f"deepseek:{settings.llm_default_model}",
                required_values=[
                    settings.deepseek_base_url,
                    settings.deepseek_api_key or mock_marker,
                ],
            ),
            _dependency_config(
                name="qwen",
                endpoint="qwen:qwen3.7-plus",
                required_values=[
                    settings.qwen_base_url,
                    settings.qwen_api_key or mock_marker,
                ],
            ),
        ],
    )
