from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings, get_settings

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "hakka-stage-ai"
JWT_AUDIENCE = "hakka-stage-ai-web"

# PasswordHash.recommended() 当前使用 Argon2。由成熟库管理参数，避免项目自造哈希方案。
password_hash = PasswordHash.recommended()
# 未注册邮箱也执行一次同等量级的哈希校验，减少通过响应耗时枚举账号的风险。
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-account-password-2026")


def hash_password(password: str) -> str:
    """生成只用于数据库保存的密码哈希。"""

    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """校验明文密码是否匹配数据库中的哈希。"""

    return password_hash.verify(password, stored_hash)


def create_access_token(user_id: UUID, settings: Settings | None = None) -> tuple[str, int]:
    """为账号签发带有效期、签发方和受众约束的访问令牌。"""

    active_settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=active_settings.auth_access_token_minutes)
    expires_at = now + expires_delta
    token = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": expires_at,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        active_settings.auth_secret_key,
        algorithm=JWT_ALGORITHM,
    )
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str, settings: Settings | None = None) -> UUID:
    """验证访问令牌并返回账号 ID；任何非法声明都按无效令牌处理。"""

    active_settings = settings or get_settings()
    payload = jwt.decode(
        token,
        active_settings.auth_secret_key,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": ["sub", "type", "iat", "exp", "iss", "aud"]},
    )
    if payload.get("type") != "access":
        raise InvalidTokenError("令牌类型无效")
    try:
        return UUID(str(payload["sub"]))
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError("账号标识无效") from exc
