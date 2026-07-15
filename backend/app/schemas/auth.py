from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

AccountRole = Literal["teacher", "student"]


def _validate_password_strength(value: str) -> str:
    """执行首版统一密码规则，避免账号创建和改密出现规则漂移。"""

    if not any(character.isalpha() for character in value) or not any(character.isdigit() for character in value):
        raise ValueError("密码至少需要包含一个字母和一个数字")
    return value


class AccountCreateRequest(BaseModel):
    """已登录用户创建单个账号的请求。"""

    email: EmailStr = Field(description="登录邮箱；系统会自动去除首尾空格并转为小写")
    password: str = Field(min_length=8, max_length=128, description="登录密码，8-128 位且至少包含字母和数字")
    display_name: str = Field(min_length=2, max_length=40, description="平台内显示名称")
    role: AccountRole = Field(default="teacher", description="账号身份：teacher 老师，student 学生")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        """在 EmailStr 校验前统一邮箱格式。"""

        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        """去除显示名称两端空格，并拒绝全空白名称。"""

        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("显示名称至少需要 2 个字符")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """校验新账号初始密码强度。"""

        return _validate_password_strength(value)


class BatchAccountCreateRequest(BaseModel):
    """批量创建账号的 JSON 请求，整批最多包含 50 个账号。"""

    accounts: list[AccountCreateRequest] = Field(
        min_length=1,
        max_length=50,
        description="待创建账号列表；任一账号校验失败或邮箱冲突时整批不创建",
    )

    @model_validator(mode="after")
    def ensure_unique_emails(self) -> "BatchAccountCreateRequest":
        """在访问数据库前拒绝同一批次中的重复邮箱。"""

        emails = [str(account.email) for account in self.accounts]
        duplicate_emails = sorted({email for email in emails if emails.count(email) > 1})
        if duplicate_emails:
            raise ValueError(f"批量数据中存在重复邮箱：{'、'.join(duplicate_emails)}")
        return self


class LoginRequest(BaseModel):
    """使用邮箱和密码登录的请求。"""

    email: EmailStr = Field(description="账号登录邮箱")
    password: str = Field(min_length=1, max_length=128, description="账号密码")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        """登录时允许用户输入不同大小写的邮箱。"""

        return value.strip().lower() if isinstance(value, str) else value


class UserResponse(BaseModel):
    """前端可读取的账号资料，不包含密码哈希。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str
    role: AccountRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AuthTokenResponse(BaseModel):
    """登录成功后的会话响应。"""

    access_token: str = Field(description="后续请求放入 Authorization: Bearer 请求头的访问令牌")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="访问令牌有效期，单位秒")
    user: UserResponse


class BatchAccountCreateResponse(BaseModel):
    """批量创建账号成功后的响应。"""

    created_count: int = Field(description="本次成功创建的账号数量")
    users: list[UserResponse] = Field(description="已创建账号的安全字段，不包含初始密码")


class ProfileUpdateRequest(BaseModel):
    """修改当前账号基础资料的请求。"""

    display_name: str = Field(min_length=2, max_length=40, description="新的平台显示名称")

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        """保存前清理显示名称两端空格。"""

        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("显示名称至少需要 2 个字符")
        return normalized


class PasswordChangeRequest(BaseModel):
    """修改当前账号密码的请求。"""

    current_password: str = Field(min_length=1, max_length=128, description="当前密码")
    new_password: str = Field(min_length=8, max_length=128, description="新密码，8-128 位且至少包含字母和数字")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """校验新密码强度。"""

        return _validate_password_strength(value)

    @model_validator(mode="after")
    def ensure_password_changed(self) -> "PasswordChangeRequest":
        """拒绝把新密码设置为当前密码。"""

        if self.current_password == self.new_password:
            raise ValueError("新密码不能与当前密码相同")
        return self
