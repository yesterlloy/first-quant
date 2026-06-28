"""交易相关 Schema."""

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class PositionOut(BaseModel):
    """持仓输出."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    code: str
    shares: Optional[int] = None
    weight: Optional[float] = None
    cost_price: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    profit_pct: Optional[float] = None  # 持仓收益率（计算字段）
    profit_amount: Optional[float] = None  # 持仓收益金额


class OrderOut(BaseModel):
    """订单输出."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    date: date
    code: str
    action: str  # buy/sell
    shares: int
    price: Optional[float] = None
    status: str  # pending/filled/canceled/rejected
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OrderCreate(BaseModel):
    """创建订单."""

    code: str = Field(..., description="股票代码")
    action: str = Field(..., description="操作方向：buy/sell")
    shares: int = Field(..., gt=0, description="委托股数")
    price: Optional[float] = Field(None, gt=0, description="委托价格，None表示市价")


class TradeOut(BaseModel):
    """成交记录输出."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_id: str
    order_id: Optional[str] = None
    date: date
    code: str
    action: str
    shares: int
    price: float
    filled_at: Optional[datetime] = None
    amount: Optional[float] = None  # 成交金额（计算字段）


class AccountSnapshotOut(BaseModel):
    """账户快照输出."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    total_value: Optional[float] = None
    cash: Optional[float] = None
    market_value: Optional[float] = None
    return_pct: Optional[float] = None
    created_at: Optional[datetime] = None


class TradingStatsOut(BaseModel):
    """交易统计."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    avg_profit_per_trade: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0


class PortfolioSummaryOut(BaseModel):
    """组合概览."""

    total_value: float = 0.0
    cash: float = 0.0
    market_value: float = 0.0
    position_count: int = 0
    today_pnl: float = 0.0
    today_return_pct: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
