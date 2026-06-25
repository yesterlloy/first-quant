"""认证路由：注册、登录、当前用户."""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.common import ApiResponse, Token
from app.schemas.user import LoginResponse, UserCreate, UserOut, UserUpdate
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=ApiResponse[UserOut], status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """注册新用户."""
    user = auth_service.register_user(db, user_in)
    return ApiResponse.success(data=UserOut.model_validate(user), message="注册成功")


@router.post("/login", response_model=LoginResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 兼容登录（表单 username/password），返回 JWT 令牌与用户信息."""
    user, access_token = auth_service.login(db, form_data.username, form_data.password)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=ApiResponse[UserOut])
def get_me(current_user: User = Depends(get_current_active_user)):
    """获取当前登录用户."""
    return ApiResponse.success(data=UserOut.model_validate(current_user))


@router.put("/me", response_model=ApiResponse[UserOut])
def update_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """更新当前用户信息."""
    user = auth_service.update_user(db, current_user, user_in)
    return ApiResponse.success(data=UserOut.model_validate(user), message="更新成功")
