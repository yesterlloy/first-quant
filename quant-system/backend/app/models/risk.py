"""风控模型.

- ``RiskRule``：风控规则定义，对应 ``risk/rules.py`` 中的规则
  （SinglePositionLimit / IndustryConcentration / StopLossRule）。
- ``RiskEvent``：风控事件日志，对应 DuckDB ``risk_event_log`` 表。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class RiskRule(Base):
    """风控规则."""

    __tablename__ = "risk_rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_name = Column(String(100), unique=True, index=True, nullable=False, comment="规则名称")
    rule_type = Column(String(64), nullable=False, comment="规则类型/类名")
    level = Column(
        String(16),
        default="warning",
        comment="触发等级：info/warning/block",
    )
    params = Column(Text, nullable=True, comment="规则参数 JSON")
    enabled = Column(Boolean, default=True, index=True, comment="是否启用")
    description = Column(Text, nullable=True, comment="规则描述")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<RiskRule {self.rule_name} level={self.level} enabled={self.enabled}>"


class RiskEvent(Base):
    """风控事件日志（对应 risk_event_log 表）."""

    __tablename__ = "risk_event_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, comment="事件时间")
    level = Column(String(16), nullable=False, comment="等级：info/warning/block")
    type = Column(String(64), nullable=True, comment="事件类型/规则名")
    code = Column(String(16), nullable=True, comment="相关股票代码")
    message = Column(Text, nullable=True, comment="事件描述")
    details = Column(Text, nullable=True, comment="详情 JSON")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<RiskEvent [{self.level}] {self.type} {self.code}>"
