"""数据服务：股票、行情、财务查询."""

from datetime import date
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.stock import DailyQuote, Financial, IndexQuote, Stock
from app.schemas.data import (
    DailyQuoteOut,
    QuoteQueryParams,
    StockListParams,
)


def list_stocks(db: Session, params: StockListParams) -> tuple[list[Stock], int]:
    """分页查询股票列表，支持按代码/名称模糊搜索与行业筛选."""
    query = db.query(Stock)

    if params.keyword:
        keyword = f"%{params.keyword}%"
        query = query.filter(
            or_(Stock.code.ilike(keyword), Stock.name.ilike(keyword))
        )
    if params.industry:
        query = query.filter(Stock.industry == params.industry)

    total = query.count()
    items = (
        query.order_by(Stock.code)
        .offset(params.offset)
        .limit(params.limit)
        .all()
    )
    return items, total


def get_stock(db: Session, code: str) -> Stock:
    """查询单只股票，不存在则抛 NotFoundException."""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise NotFoundException(resource=f"Stock {code}")
    return stock


def list_quotes(db: Session, params: QuoteQueryParams) -> list[DailyQuote]:
    """查询股票日行情，支持日期区间与条数上限."""
    query = db.query(DailyQuote).filter(DailyQuote.code == params.code)

    if params.start_date:
        query = query.filter(DailyQuote.date >= params.start_date)
    if params.end_date:
        query = query.filter(DailyQuote.date <= params.end_date)

    return query.order_by(DailyQuote.date.desc()).limit(params.limit).all()


def list_index_quotes(db: Session, params: QuoteQueryParams) -> list[IndexQuote]:
    """查询指数日行情."""
    query = db.query(IndexQuote).filter(IndexQuote.code == params.code)

    if params.start_date:
        query = query.filter(IndexQuote.date >= params.start_date)
    if params.end_date:
        query = query.filter(IndexQuote.date <= params.end_date)

    return query.order_by(IndexQuote.date.desc()).limit(params.limit).all()


def list_financials(
    db: Session,
    code: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
) -> list[Financial]:
    """查询财务指标."""
    query = db.query(Financial).filter(Financial.code == code)
    if start_date:
        query = query.filter(Financial.date >= start_date)
    if end_date:
        query = query.filter(Financial.date <= end_date)
    return query.order_by(Financial.date.desc()).limit(limit).all()


def get_latest_quote(db: Session, code: str) -> Optional[DailyQuote]:
    """获取股票最新行情."""
    return (
        db.query(DailyQuote)
        .filter(DailyQuote.code == code)
        .order_by(DailyQuote.date.desc())
        .first()
    )


def get_data_overview(db: Session) -> dict:
    """获取数据概览统计."""
    from sqlalchemy import func

    total_stocks = db.query(func.count(Stock.code)).scalar() or 0
    total_quotes = db.query(func.count(DailyQuote.code)).scalar() or 0

    min_date = (
        db.query(func.min(DailyQuote.date)).filter(DailyQuote.date.isnot(None)).scalar()
    )
    max_date = (
        db.query(func.max(DailyQuote.date)).filter(DailyQuote.date.isnot(None)).scalar()
    )

    # 计算数据覆盖天数
    total_days = 0
    if min_date and max_date:
        total_days = (max_date - min_date).days + 1

    return {
        "total_stocks": total_stocks,
        "total_days": total_days,
        "min_date": str(min_date) if min_date else None,
        "max_date": str(max_date) if max_date else None,
        "total_quotes": total_quotes,
        "last_update": str(max_date) if max_date else None,
    }
