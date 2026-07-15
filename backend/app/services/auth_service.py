from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.models import User
from app.schemas import AccountCreateRequest


class EmailAlreadyRegisteredError(Exception):
    """一个或多个待创建邮箱已经存在。"""

    def __init__(self, emails: list[str] | None = None) -> None:
        self.emails = emails or []
        super().__init__("、".join(self.emails))


def find_user_by_email(db: Session, email: str) -> User | None:
    """按规范化邮箱读取账号。"""

    return db.scalar(select(User).where(User.email == email.strip().lower()))


def create_user(db: Session, request: AccountCreateRequest) -> User:
    """创建单个账号，并处理并发写入时的唯一索引冲突。"""

    user = User(
        email=str(request.email).lower(),
        password_hash=hash_password(request.password),
        display_name=request.display_name,
        role=request.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAlreadyRegisteredError([str(request.email)]) from exc
    db.refresh(user)
    return user


def create_users(db: Session, requests: list[AccountCreateRequest]) -> list[User]:
    """在同一事务中批量创建账号。

    先一次性检查数据库冲突，再生成密码哈希；提交阶段仍由唯一索引兜底。
    只要任一邮箱冲突，整个事务都会回滚，避免批量导入产生半成功状态。
    """

    emails = [str(request.email) for request in requests]
    existing_emails = list(db.scalars(select(User.email).where(User.email.in_(emails))).all())
    if existing_emails:
        raise EmailAlreadyRegisteredError(sorted(existing_emails))

    users = [
        User(
            email=str(request.email),
            password_hash=hash_password(request.password),
            display_name=request.display_name,
            role=request.role,
        )
        for request in requests
    ]
    db.add_all(users)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # 并发请求可能在预检查后抢先写入，统一映射为邮箱冲突。
        raise EmailAlreadyRegisteredError from exc
    for user in users:
        db.refresh(user)
    return users


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """验证账号密码，并对不存在的邮箱执行等量哈希校验。"""

    user = find_user_by_email(db, email)
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None
    password_matches = verify_password(password, user.password_hash)
    if not user.is_active or not password_matches:
        return None

    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def update_profile(db: Session, user: User, display_name: str) -> User:
    """保存当前账号的显示名称。"""

    user.display_name = display_name
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
    """校验当前密码后保存新的 Argon2 哈希。"""

    if not verify_password(current_password, user.password_hash):
        return False
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    return True
