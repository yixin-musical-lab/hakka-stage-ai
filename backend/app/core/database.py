from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类。"""


settings = get_settings()

# pool_pre_ping 可以在 Docker 服务重启后自动丢弃失效连接，减少本地联调假死。
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """开发期自动建表。

    第一版先保证异步链路能跑通；后续表结构稳定后再补 Alembic 正式迁移。
    """

    # 确保 SQLAlchemy metadata 中已经注册业务模型，否则 create_all 看不到表定义。
    from app import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：为每个请求提供独立数据库会话。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
