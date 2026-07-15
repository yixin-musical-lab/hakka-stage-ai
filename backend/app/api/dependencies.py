from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="登录后填写访问令牌，格式由 Swagger UI 自动补充为 Bearer <token>。",
)


def _unauthorized(detail: str = "登录状态无效或已过期，请重新登录。") -> HTTPException:
    """生成统一的 401 响应，并提示客户端使用 Bearer 认证。"""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖：解析令牌并读取当前启用的账号。

    常规 API 优先使用 Authorization 请求头；原生 video 标签无法设置该请求头，
    因此允许回退到登录接口写入的 HttpOnly Cookie，以保持 MinIO Range 播放链路可用。
    """

    token = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    if token is None:
        token = request.cookies.get("hakka_access_token")
    if token is None:
        raise _unauthorized("请先登录后再访问该接口。")
    try:
        user_id = decode_access_token(token)
    except InvalidTokenError as exc:
        raise _unauthorized() from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
