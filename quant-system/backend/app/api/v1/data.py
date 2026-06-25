"""数据路由：股票、行情、财务查询."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.data import (
    DailyQuoteOut,
    FinancialOut,
    IndexQuoteOut,
    QuoteListResponse,
    StockListResponse,
    StockOut,
)
from app.services import data_service

router = APIRouter()


@router.get("/overview", response_model=ApiResponse[dict])
def get_overview(db: Session = Depends(get_db)):
    """获取数据概览统计."""
    return ApiResponse.success(data=data_service.get_data_overview(db))


@router.get("/stocks", response_model=ApiResponse[StockListResponse])
def list_stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    keyword: Optional[str] = Query(None, description="代码/名称模糊搜索"),
    industry: Optional[str] = Query(None, description="行业筛选"),
    db: Session = Depends(get_db),
):
    """分页查询股票列表."""
    params = PaginationParams(page=page, page_size=page_size)
    from app.schemas.data import StockListParams

    sp = StockListParams(page=page, page_size=page_size, keyword=keyword, industry=industry)
    items, total = data_service.list_stocks(db, sp)
    return ApiResponse.success(
        data=PaginatedResponse[StockOut].create(
            items=[StockOut.model_validate(s) for s in items],
            total=total,
            params=params,
        )
    )


@router.get("/stocks/{code}", response_model=ApiResponse[StockOut])
def get_stock(code: str, db: Session = Depends(get_db)):
    """查询单只股票基础信息."""
    stock = data_service.get_stock(db, code)
    return ApiResponse.success(data=StockOut.model_validate(stock))


@router.get("/quotes", response_model=ApiResponse[QuoteListResponse])
def list_quotes(
    code: str = Query(..., description="股票代码"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """查询股票日行情."""
    from app.schemas.data import QuoteQueryParams

    params = QuoteQueryParams(code=code, start_date=start_date, end_date=end_date, limit=limit)
    items = data_service.list_quotes(db, params)
    return ApiResponse.success(
        data=QuoteListResponse(
            code=code,
            items=[DailyQuoteOut.model_validate(q) for q in items],
        )
    )


@router.get("/index-quotes", response_model=ApiResponse[QuoteListResponse])
def list_index_quotes(
    code: str = Query(..., description="指数代码，如 000300"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """查询指数日行情."""
    from app.schemas.data import QuoteQueryParams

    params = QuoteQueryParams(code=code, start_date=start_date, end_date=end_date, limit=limit)
    items = data_service.list_index_quotes(db, params)
    return ApiResponse.success(
        data=QuoteListResponse(
            code=code,
            items=[IndexQuoteOut.model_validate(q) for q in items],
        )
    )


@router.get("/financials/{code}", response_model=ApiResponse[list[FinancialOut]])
def list_financials(
    code: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """查询财务指标."""
    items = data_service.list_financials(db, code, start_date, end_date, limit)
    return ApiResponse.success(data=[FinancialOut.model_validate(f) for f in items])
