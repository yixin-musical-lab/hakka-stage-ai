from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import User
from app.schemas import AccountCreateRequest
from app.services.auth_service import create_user


def ensure_bootstrap_account() -> bool:
    """在全新数据库中按环境变量创建首个账号。

    HTTP 层不提供匿名注册，因此首次部署可以临时设置 BOOTSTRAP_ACCOUNT_*。
    只有数据库完全没有账号时才会创建；创建成功后应从部署环境移除初始密码。
    """

    settings = get_settings()
    email = settings.bootstrap_account_email.strip()
    password = settings.bootstrap_account_password
    if not email and not password:
        return False
    with SessionLocal() as db:
        # 已有账号时完全忽略引导配置，便于首账号创建后立即删除密码变量。
        if db.scalar(select(User.id).limit(1)) is not None:
            return False
        if not email or not password:
            raise RuntimeError("账号表为空时，BOOTSTRAP_ACCOUNT_EMAIL 和 BOOTSTRAP_ACCOUNT_PASSWORD 必须同时配置。")
        request = AccountCreateRequest(
            email=email,
            password=password,
            display_name=settings.bootstrap_account_display_name,
            role=settings.bootstrap_account_role,
        )
        create_user(db, request)
        return True
