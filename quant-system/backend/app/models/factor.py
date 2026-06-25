"""因子模型.

- ``Factor``：因子元信息（注册表持久化），对应 ``factor/base.py::FactorInfo``。
- ``FactorValue``：因子计算结果，对应 DuckDB 的 ``factor_value`` 表。
"""

from datetime import date
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class Factor(Base):
    """因子元信息.

    与 ``factor/base.py::FactorInfo`` 字段对齐，用于持久化因子注册表，
    记录因子的分类、频率、回看期、依赖项与启用状态。
    """

    __tablename__ = "factor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, index=True, nullable=False, comment="因子名称，如 EP / ROE")
    category = Column(
        String(32),
        nullable=False,
        index=True,
        comment="分类：valuation/growth/quality/technical/scale",
    )
    description = Column(Text, nullable=True, comment="因子描述")
    lookback = Column(Integer, default=0, comment="回看期（交易日数），技术因子用")
    freq = Column(String(16), default="daily", comment="频率：daily/quarterly/monthly")
    depends = Column(Text, nullable=True, comment="数据依赖，逗号分隔")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<Factor {self.name} ({self.category})>"


class FactorValue(Base):
    """因子值（对应 factor_value 表）.

    存储某股票某日某因子的原始值与中性化后的值。
    """

    __tablename__ = "factor_value"
    __table_args__ = (
        UniqueConstraint("code", "date", "factor_name", name="uq_factor_value_code_date_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(16), nullable=False, index=True, comment="股票代码")
    date = Column(Date, nullable=False, index=True, comment="交易日期")
    factor_name = Column(String(64), nullable=False, index=True, comment="因子名称")
    raw_value = Column(Float, nullable=True, comment="原始因子值")
    neut_value = Column(Float, nullable=True, comment="中性化后因子值")

    def __repr__(self) -> str:
        return f"<FactorValue {self.factor_name} {self.code} {self.date}>"
