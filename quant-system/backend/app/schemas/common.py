"""通用 schema：统一响应、分页、令牌.

统一响应结构 ``ApiResponse`` 与 ``app/core/exceptions.py`` 中的异常处理器
输出保持一致：``{code, message, details, data, timestamp}``。
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, ConfigDict


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应封装."""

    code: int = Field(0, description="业务状态码，0 表示成功")
    message: str = Field("success", description="提示信息")
    data: Optional[T] = Field(None, description="业务数据")
    details: Optional[Any] = Field(None, description="附加详情")
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()), description="时间戳")

    @classmethod
    def success(cls, data: Optional[T] = None, message: str = "success") -> "ApiResponse[T]":
        """构造成功响应."""
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(cls, message: str, code: int = 5001, details: Optional[Any] = None) -> "ApiResponse[T]":
        """构造失败响应."""
        return cls(code=code, message=message, data=None, details=details)


class PaginationParams(BaseModel):
    """分页查询参数."""

    page: int = Field(1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(20, ge=1, le=500, description="每页条数")

    @property
    def offset(self) -> int:
        """计算 SQL offset."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """计算 SQL limit."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应."""

    items: List[T] = Field(default_factory=list, description="当前页数据")
    total: int = Field(0, description="总条数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页条数")
    total_pages: int = Field(0, description="总页数")

    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams) -> "PaginatedResponse[T]":
        """根据分页参数构造分页响应."""
        total_pages = (total + params.page_size - 1) // params.page_size if params.page_size else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )


class Token(BaseModel):
    """访问令牌."""

    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field("bearer", description="令牌类型")


class TokenData(BaseModel):
    """令牌载荷."""

    username: Optional[str] = None


class ORMModel(BaseModel):
    """支持从 ORM 对象构造的基类."""

    model_config = ConfigDict(from_attributes=True)
