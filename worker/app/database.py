from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Worker 侧 ORM 基类。"""


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """确保 Worker 独立启动时也能创建开发期数据表。"""

    # 延迟导入模型，确保 metadata 注册完整；否则只导入 database 时 create_all 看不到业务表。
    from app import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)
