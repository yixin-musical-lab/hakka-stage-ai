from pydantic import BaseModel


class DependencyConfig(BaseModel):
    """暴露给前端的依赖配置摘要。

    当前只检查配置是否被读取，不主动连接数据库、Redis 或 MinIO。这样可以稳定验证
    前后端和 Docker 服务启动链路，后续接入探活时仍复用这个响应结构。
    """

    name: str
    configured: bool
    endpoint: str


class HealthResponse(BaseModel):
    """健康检查响应结构。"""

    status: str
    service: str
    message: str
    dependencies: list[DependencyConfig]
