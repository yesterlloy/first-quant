"""回测模块 schema."""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse, PaginationParams


class BacktestTaskCreate(BaseModel):
    """创建回测任务."""

    name: str = Field(..., max_length=128, description="任务名称")
    strategy_name: str = Field(..., description="策略名称")
    strategy_params: Optional[dict[str, Any]] = Field(None, description="策略参数")
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    benchmark: str = Field("000300", description="基准指数代码")
    initial_capital: float = Field(1_000_000.0, gt=0, description="初始资金")
    commission: float = Field(0.001, ge=0, description="手续费率")
    slippage: float = Field(0.0005, ge=0, description="滑点")


class BacktestTaskUpdate(BaseModel):
    """更新回测任务（仅限待执行状态）."""

    name: Optional[str] = Field(None, max_length=128)
    strategy_params: Optional[dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class BacktestResultOut(BaseModel):
    """回测结果."""

    model_config = ConfigDict(from_attributes=True)

    task_id: int
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_trades: Optional[int] = None
    result_data: Optional[Any] = None
    created_at: Optional[datetime] = None


class BacktestTaskOut(BaseModel):
    """回测任务响应."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    strategy_name: str
    strategy_params: Optional[str] = None
    status: str
    start_date: date
    end_date: date
    benchmark: str
    initial_capital: float
    commission: float
    slippage: float
    created_by: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[BacktestResultOut] = None


class BacktestListParams(PaginationParams):
    """回测列表查询参数."""

    status: Optional[str] = Field(None, description="按状态筛选")
    strategy_name: Optional[str] = Field(None, description="按策略筛选")


class BacktestListResponse(PaginatedResponse[BacktestTaskOut]):
    """回测分页响应."""
