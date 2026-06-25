"""股票数据模型.

对应 quant-system 中 ``data/db`` 已有的 ``stock_info`` / ``daily_quote`` /
``index_quote`` / ``financial`` / ``financial_ext`` / ``dividend`` /
``industry_class`` 表结构，字段命名保持一致，便于后续数据同步。
"""

from datetime import date
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Float,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class Stock(Base):
    """股票基础信息（对应 stock_info 表）."""

    __tablename__ = "stock_info"

    code = Column(String(16), primary_key=True, index=True, comment="股票代码，如 000001")
    name = Column(String(64), nullable=True, comment="股票名称")
    industry = Column(String(64), nullable=True, comment="所属行业")
    list_date = Column(String(10), nullable=True, comment="上市日期")
    delist_date = Column(String(10), nullable=True, comment="退市日期")

    def __repr__(self) -> str:
        return f"<Stock {self.code} {self.name}>"


class DailyQuote(Base):
    """日行情数据（对应 daily_quote 表）."""

    __tablename__ = "daily_quote"

    code = Column(String(16), primary_key=True, nullable=False, index=True, comment="股票代码")
    date = Column(Date, primary_key=True, nullable=False, index=True, comment="交易日期")
    open = Column(Float, nullable=True, comment="开盘价")
    high = Column(Float, nullable=True, comment="最高价")
    low = Column(Float, nullable=True, comment="最低价")
    close = Column(Float, nullable=True, comment="收盘价")
    volume = Column(Float, nullable=True, comment="成交量（股）")
    turnover = Column(Float, nullable=True, comment="成交额（元）")
    change_pct = Column(Float, nullable=True, comment="涨跌幅（%）")
    turnover_rate = Column(Float, nullable=True, comment="换手率（%）")

    def __repr__(self) -> str:
        return f"<DailyQuote {self.code} {self.date} close={self.close}>"


class IndexQuote(Base):
    """指数日行情数据（对应 index_quote 表）."""

    __tablename__ = "index_quote"

    code = Column(String(16), primary_key=True, nullable=False, index=True, comment="指数代码，如 000300")
    date = Column(String(10), primary_key=True, nullable=False, index=True, comment="交易日期")
    open = Column(Float, nullable=True, comment="开盘价")
    high = Column(Float, nullable=True, comment="最高价")
    low = Column(Float, nullable=True, comment="最低价")
    close = Column(Float, nullable=True, comment="收盘价")
    volume = Column(Float, nullable=True, comment="成交量")
    turnover = Column(Float, nullable=True, comment="成交额")

    def __repr__(self) -> str:
        return f"<IndexQuote {self.code} {self.date} close={self.close}>"


class Financial(Base):
    """财务指标（对应 financial 表）."""

    __tablename__ = "financial"

    code = Column(String(16), primary_key=True, nullable=False, index=True, comment="股票代码")
    date = Column(String(10), primary_key=True, nullable=False, index=True, comment="报告期")
    pe = Column(Float, nullable=True, comment="市盈率")
    pb = Column(Float, nullable=True, comment="市净率")
    roe = Column(Float, nullable=True, comment="净资产收益率 ROE")
    revenue = Column(Float, nullable=True, comment="营业收入")
    net_profit = Column(Float, nullable=True, comment="净利润")

    def __repr__(self) -> str:
        return f"<Financial {self.code} {self.date}>"


class FinancialExt(Base):
    """扩展财务指标（对应 financial_ext 表）."""

    __tablename__ = "financial_ext"

    code = Column(String(16), primary_key=True, nullable=False, index=True)
    date = Column(String(10), primary_key=True, nullable=False, index=True)
    pe = Column(Float, nullable=True)
    pb = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    roa = Column(Float, nullable=True, comment="总资产收益率 ROA")
    revenue = Column(Float, nullable=True)
    net_profit = Column(Float, nullable=True)
    total_assets = Column(Float, nullable=True, comment="总资产")
    total_liability = Column(Float, nullable=True, comment="总负债")
    debt_ratio = Column(Float, nullable=True, comment="资产负债率")
    ocf = Column(Float, nullable=True, comment="经营性现金流")


class Dividend(Base):
    """分红数据（对应 dividend 表）."""

    __tablename__ = "dividend"

    code = Column(String(16), primary_key=True, nullable=False, index=True, comment="股票代码")
    year = Column(String(8), primary_key=True, nullable=False, comment="分红年度")
    dividend_per_share = Column(Float, nullable=True, comment="每股股息")
    ex_date = Column(String(10), nullable=True, comment="除权除息日")


class IndustryClass(Base):
    """行业分类（对应 industry_class 表）."""

    __tablename__ = "industry_class"

    code = Column(String(16), primary_key=True, index=True, comment="股票代码")
    name = Column(String(64), nullable=True, comment="股票名称")
    industry_sw = Column(String(64), nullable=True, comment="申万行业分类")

    def __repr__(self) -> str:
        return f"<IndustryClass {self.code} {self.industry_sw}>"
