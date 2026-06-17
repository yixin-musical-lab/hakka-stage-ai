from os import getenv


def _getenv_with_default(name: str, default: str) -> str:
    """读取环境变量；未设置时使用本地开发默认值。

    Docker Compose 会显式传入容器内地址；宿主机本地启动 worker 时，
    默认按 localhost 访问由 Docker 启动的 PostgreSQL、Redis 和 MinIO。
    """

    return getenv(name, default)


def main() -> None:
    """Worker 容器健康检查入口。

    当前骨架阶段只确认关键环境变量能被读取；后续接入 Redis 队列后，
    可以在这里增加 Redis ping、模型目录检查等更真实的探活逻辑。
    """

    required_values = [
        _getenv_with_default("POSTGRES_HOST", "localhost"),
        _getenv_with_default("REDIS_HOST", "localhost"),
        _getenv_with_default("MINIO_ENDPOINT", "http://localhost:9000"),
    ]
    if not all(required_values):
        raise SystemExit("worker dependency environment is incomplete")


if __name__ == "__main__":
    main()
