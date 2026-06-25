"""回测模型.

- ``BacktestTask``：一次回测任务的配置与执行状态。
- ``BacktestResult``：回测产出指标，字段对齐 ``backtest/analyzer.py`` 的 result dict
  （total_return / annualized_return / sharpe_ratio / max_drawdown / win_rate / total_trades）。
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
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BacktestTask(Base):
    """回测任务."""

    __tablename__ = "backtest_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, index=True, comment="任务名称")
    strategy_name = Column(String(64), nullable=False, comment="策略名称，如 ma_cross / ml_factor")
    strategy_params = Column(Text, nullable=True, comment="策略参数 JSON 字符串")
    status = Column(
        String(16),
        default="pending",
        index=True,
        comment="状态：pending/running/success/failed/canceled",
    )

    start_date = Column(Date, nullable=False, comment="回测开始日期")
    end_date = Column(Date, nullable=False, comment="回测结束日期")
    benchmark = Column(String(16), default="000300", comment="基准指数代码")
    initial_capital = Column(Float, default=1_000_000.0, comment="初始资金")
    commission = Column(Float, default=0.001, comment="手续费率")
    slippage = Column(Float, default=0.0005, comment="滑点")

    created_by = Column(Integer, nullable=True, comment="创建人用户 ID")
    error_message = Column(Text, nullable=True, comment="失败原因")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # 关联结果（一对一）
    result = relationship(
        "BacktestResult",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BacktestTask {self.id} {self.name} [{self.status}]>"


class BacktestResult(Base):
    """回测结果指标."""

    __tablename__ = "backtest_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        Integer,
        ForeignKey("backtest_task.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="关联任务 ID",
    )

    total_return = Column(Float, nullable=True, comment="总收益率")
    annualized_return = Column(Float, nullable=True, comment="年化收益率")
    sharpe_ratio = Column(Float, nullable=True, comment="夏普比率")
    max_drawdown = Column(Float, nullable=True, comment="最大回撤")
    win_rate = Column(Float, nullable=True, comment="胜率")
    total_trades = Column(Integer, nullable=True, comment="交易次数")

    # 原始明细（净值序列、持仓、交易记录等），以 JSON 文本存储
    result_data = Column(Text, nullable=True, comment="完整结果 JSON")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    task = relationship("BacktestTask", back_populates="result")

    def __repr__(self) -> str:
        return f"<BacktestResult task={self.task_id} return={self.total_return}>"
