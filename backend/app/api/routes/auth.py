from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas import (
    AccountCreateRequest,
    AuthTokenResponse,
    BatchAccountCreateRequest,
    BatchAccountCreateResponse,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    UserResponse,
)
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    authenticate_user,
    change_password,
    create_user,
    create_users,
    find_user_by_email,
    update_profile,
)

router = APIRouter(tags=["账号与鉴权"])


def _session_response(user, response: Response) -> AuthTokenResponse:
    """组织会话响应，并为原生媒体播放写入同源 HttpOnly Cookie。"""

    access_token, expires_in = create_access_token(user.id)
    settings = get_settings()
    response.set_cookie(
        key="hakka_access_token",
        value=access_token,
        max_age=expires_in,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/api",
    )
    return AuthTokenResponse(access_token=access_token, expires_in=expires_in, user=user)


@router.post(
    "/api/auth/login",
    response_model=AuthTokenResponse,
    summary="登录平台账号",
    responses={401: {"description": "邮箱或密码错误"}},
)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthTokenResponse:
    """校验邮箱和密码并签发限时访问令牌。"""

    user = authenticate_user(db, str(request.email), request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误。",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _session_response(user, response)


def _email_conflict(exc: EmailAlreadyRegisteredError) -> HTTPException:
    """把数据库邮箱冲突转换成前端可读的 409 响应。"""

    detail = f"以下邮箱已经存在：{'、'.join(exc.emails)}。" if exc.emails else "待创建账号中存在已注册邮箱。"
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


@router.post(
    "/api/accounts",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="登录后创建单个账号",
    responses={409: {"description": "邮箱已存在"}},
)
def create_account(
    request: AccountCreateRequest,
    _current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> UserResponse:
    """由当前登录用户创建老师或学生账号，不为新账号自动建立会话。"""

    if find_user_by_email(db, str(request.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已经存在。")
    try:
        return create_user(db, request)
    except EmailAlreadyRegisteredError as exc:
        raise _email_conflict(exc) from exc


@router.post(
    "/api/accounts/batch",
    response_model=BatchAccountCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="通过 JSON 批量创建账号",
    responses={409: {"description": "一个或多个邮箱已存在"}},
)
def create_accounts_batch(
    request: BatchAccountCreateRequest,
    _current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BatchAccountCreateResponse:
    """由当前登录用户批量创建账号，任一项失败时整批回滚。"""

    try:
        users = create_users(db, request.accounts)
    except EmailAlreadyRegisteredError as exc:
        raise _email_conflict(exc) from exc
    return BatchAccountCreateResponse(created_count=len(users), users=users)


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="退出当前登录")
def logout(response: Response, _current_user: CurrentUser) -> Response:
    """清除用于原生媒体请求的 HttpOnly Cookie；前端同时清理 Bearer 令牌。"""

    response.delete_cookie(key="hakka_access_token", path="/api", samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/api/account/me", response_model=UserResponse, summary="读取当前账号资料")
def get_my_account(current_user: CurrentUser) -> UserResponse:
    """返回当前登录账号的安全字段。"""

    return current_user


@router.patch("/api/account/profile", response_model=UserResponse, summary="修改当前账号资料")
def update_my_profile(
    request: ProfileUpdateRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> UserResponse:
    """修改当前账号显示名称；邮箱和身份暂不允许自行变更。"""

    return update_profile(db, current_user, request.display_name)


@router.post(
    "/api/account/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="修改当前账号密码",
    responses={400: {"description": "当前密码错误"}},
)
def update_my_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    """校验当前密码后更新密码哈希。"""

    if not change_password(db, current_user, request.current_password, request.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
