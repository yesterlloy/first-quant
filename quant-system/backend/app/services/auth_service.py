"""认证服务：注册、登录、用户查询."""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, ValidationException
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """按用户名查询用户."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """按邮箱查询用户."""
    return db.query(User).filter(User.email == email).first()


def get_user(db: Session, user_id: int) -> Optional[User]:
    """按 ID 查询用户."""
    return db.query(User).filter(User.id == user_id).first()


def register_user(db: Session, user_in: UserCreate) -> User:
    """注册新用户.

    - 校验用户名/邮箱唯一性
    - 密码 bcrypt 哈希存储
    """
    if get_user_by_username(db, user_in.username):
        raise ValidationException(message="用户名已存在")

    if user_in.email and get_user_by_email(db, user_in.email):
        raise ValidationException(message="邮箱已被注册")

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    """校验用户名密码，成功返回 User，失败返回 None."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def login(db: Session, username: str, password: str) -> tuple[User, str]:
    """登录并签发 JWT 令牌.

    Returns:
        (user, access_token)
    """
    user = authenticate(db, username, password)
    if not user:
        raise BusinessException(code=4001, message="用户名或密码错误")
    if not user.is_active:
        raise BusinessException(code=4002, message="用户已被禁用")

    access_token = create_access_token(data={"sub": user.username})
    return user, access_token


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    """更新用户信息."""
    if user_in.email is not None:
        existing = get_user_by_email(db, user_in.email)
        if existing and existing.id != user.id:
            raise ValidationException(message="邮箱已被占用")
        user.email = user_in.email
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.password is not None:
        user.hashed_password = get_password_hash(user_in.password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
