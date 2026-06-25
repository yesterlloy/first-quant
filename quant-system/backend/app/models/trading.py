"""交易模型.

对应 DuckDB 的 ``position_log`` / ``order_log`` / ``trade_log`` 表，
并补充 ``AccountSnapshot`` 用于记录每日账户净值快照。
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class Position(Base):
    """持仓快照（对应 position_log 表）."""

    __tablename__ = "position_log"
    __table_args__ = (
        UniqueConstraint("date", "code", name="uq_position_date_code"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True, comment="日期")
    code = Column(String(16), nullable=False, index=True, comment="股票代码")
    shares = Column(Integer, nullable=True, comment="持仓股数")
    weight = Column(Float, nullable=True, comment="持仓权重")
    cost_price = Column(Float, nullable=True, comment="成本价")
    current_price = Column(Float, nullable=True, comment="最新价")
    market_value = Column(Float, nullable=True, comment="市值")

    def __repr__(self) -> str:
        return f"<Position {self.code} {self.date} shares={self.shares}>"


class Order(Base):
    """委托订单（对应 order_log 表）."""

    __tablename__ = "order_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), unique=True, index=True, nullable=False, comment="订单 ID")
    date = Column(Date, nullable=False, index=True, comment="下单日期")
    code = Column(String(16), nullable=False, index=True, comment="股票代码")
    action = Column(String(16), nullable=False, comment="方向：buy/sell")
    shares = Column(Integer, nullable=False, comment="委托股数")
    price = Column(Float, nullable=True, comment="委托价")
    status = Column(
        String(16),
        default="pending",
        comment="状态：pending/filled/canceled/rejected",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<Order {self.order_id} {self.action} {self.code} {self.shares}>"


class Trade(Base):
    """成交记录（对应 trade_log 表）."""

    __tablename__ = "trade_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(64), unique=True, index=True, nullable=False, comment="成交 ID")
    order_id = Column(String(64), nullable=True, index=True, comment="关联订单 ID")
    date = Column(Date, nullable=False, index=True, comment="成交日期")
    code = Column(String(16), nullable=False, index=True, comment="股票代码")
    action = Column(String(16), nullable=False, comment="方向：buy/sell")
    shares = Column(Integer, nullable=False, comment="成交股数")
    price = Column(Float, nullable=False, comment="成交价")
    filled_at = Column(DateTime(timezone=True), nullable=True, comment="成交时间")

    def __repr__(self) -> str:
        return f"<Trade {self.trade_id} {self.action} {self.code} {self.shares}@{self.price}>"


class AccountSnapshot(Base):
    """账户每日净值快照."""

    __tablename__ = "account_snapshot"
    __table_args__ = (
        UniqueConstraint("date", name="uq_account_snapshot_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True, comment="日期")
    total_value = Column(Float, nullable=True, comment="总资产")
    cash = Column(Float, nullable=True, comment="现金")
    market_value = Column(Float, nullable=True, comment="持仓市值")
    return_pct = Column(Float, nullable=True, comment="当日收益率")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<AccountSnapshot {self.date} total={self.total_value}>"
