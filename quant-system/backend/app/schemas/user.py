"""用户相关 schema."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import Token


class UserBase(BaseModel):
    """用户基础字段."""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="姓名")


class UserCreate(UserBase):
    """创建用户（注册）."""

    password: str = Field(..., min_length=6, max_length=128, description="密码")


class UserUpdate(BaseModel):
    """更新用户."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class UserOut(UserBase):
    """用户响应."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserLogin(BaseModel):
    """登录请求（JSON 形式，兼容 OAuth2 表单登录）."""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class LoginResponse(Token):
    """登录响应（含用户信息）."""

    user: UserOut = Field(..., description="用户信息")
