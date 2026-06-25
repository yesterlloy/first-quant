"""数据模块 schema：股票、行情、财务."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse, PaginationParams


# ---------- 股票 ----------
class StockOut(BaseModel):
    """股票基础信息."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: Optional[str] = None
    industry: Optional[str] = None
    list_date: Optional[date] = None
    delist_date: Optional[date] = None


class StockListParams(PaginationParams):
    """股票列表查询参数."""

    keyword: Optional[str] = Field(None, description="按代码/名称模糊搜索")
    industry: Optional[str] = Field(None, description="按行业筛选")


# ---------- 行情 ----------
class DailyQuoteOut(BaseModel):
    """日行情."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None


class QuoteQueryParams(BaseModel):
    """行情查询参数."""

    code: str = Field(..., description="股票/指数代码")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    limit: int = Field(500, ge=1, le=5000, description="返回条数上限")


class IndexQuoteOut(BaseModel):
    """指数行情."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None


# ---------- 财务 ----------
class FinancialOut(BaseModel):
    """财务指标."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    date: date
    pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    revenue: Optional[float] = None
    net_profit: Optional[float] = None


# ---------- 聚合响应 ----------
class StockListResponse(PaginatedResponse[StockOut]):
    """股票分页响应."""


class QuoteListResponse(BaseModel):
    """行情列表响应."""

    code: str
    items: List[DailyQuoteOut] = Field(default_factory=list)
