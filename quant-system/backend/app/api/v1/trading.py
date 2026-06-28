"""交易 API：持仓、订单、成交、账户统计."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.trading import (
    AccountSnapshotOut,
    OrderCreate,
    OrderOut,
    PortfolioSummaryOut,
    PositionOut,
    TradeOut,
    TradingStatsOut,
)
from app.services import trading_service

router = APIRouter(prefix="/trading", tags=["交易"])


@router.get("/positions", response_model=ApiResponse[List[PositionOut]])
def get_positions(
    date: Optional[date] = Query(None, description="指定日期，默认最新日期"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取当前持仓."""
    positions = trading_service.get_current_positions(db, date=date)
    return ApiResponse.success(data=positions)


@router.get("/positions/history", response_model=ApiResponse[PaginatedResponse[PositionOut]])
def get_position_history(
    code: Optional[str] = Query(None, description="股票代码筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取持仓历史."""
    params = PaginationParams(page=page, page_size=page_size)
    positions = trading_service.get_position_history(db, code=code, limit=page_size)
    return ApiResponse.success(
        data=PaginatedResponse[PositionOut].create(
            items=positions,
            total=len(positions),
            params=params,
        )
    )


@router.get("/orders", response_model=ApiResponse[PaginatedResponse[OrderOut]])
def list_orders(
    status: Optional[str] = Query(None, description="状态筛选：pending/filled/canceled/rejected"),
    code: Optional[str] = Query(None, description="股票代码筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取订单列表（分页）."""
    params = PaginationParams(page=page, page_size=page_size)
    items, total = trading_service.get_orders(
        db,
        status=status,
        code=code,
        start_date=start_date,
        end_date=end_date,
        skip=params.offset,
        limit=params.limit,
    )
    return ApiResponse.success(
        data=PaginatedResponse[OrderOut].create(
            items=items,
            total=total,
            params=params,
        )
    )


@router.get("/orders/{order_id}", response_model=ApiResponse[OrderOut])
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取单个订单详情."""
    order = trading_service.get_order(db, order_id)
    return ApiResponse.success(data=order)


@router.post("/orders", response_model=ApiResponse[OrderOut], status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建委托订单（模拟成交）."""
    order = trading_service.create_order(
        db,
        code=order_in.code,
        action=order_in.action,
        shares=order_in.shares,
        price=order_in.price,
    )
    return ApiResponse.success(data=order, message="订单提交成功")


@router.post("/orders/{order_id}/cancel", response_model=ApiResponse[OrderOut])
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """取消订单."""
    order = trading_service.cancel_order(db, order_id)
    return ApiResponse.success(data=order, message="订单已取消")


@router.get("/trades", response_model=ApiResponse[PaginatedResponse[TradeOut]])
def list_trades(
    code: Optional[str] = Query(None, description="股票代码筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取成交记录（分页）."""
    params = PaginationParams(page=page, page_size=page_size)
    items, total = trading_service.get_trades(
        db,
        code=code,
        start_date=start_date,
        end_date=end_date,
        skip=params.offset,
        limit=params.limit,
    )
    return ApiResponse.success(
        data=PaginatedResponse[TradeOut].create(
            items=items,
            total=total,
            params=params,
        )
    )


@router.get("/account/snapshots", response_model=ApiResponse[List[AccountSnapshotOut]])
def get_account_snapshots(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取账户净值快照历史."""
    snapshots = trading_service.get_account_snapshots(db, start_date, end_date, limit)
    return ApiResponse.success(data=snapshots)


@router.get("/account/latest", response_model=ApiResponse[AccountSnapshotOut])
def get_latest_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取最新账户快照."""
    snapshot = trading_service.get_latest_account_snapshot(db)
    return ApiResponse.success(data=snapshot)


@router.get("/portfolio/summary", response_model=ApiResponse[PortfolioSummaryOut])
def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取组合概览统计."""
    summary = trading_service.get_portfolio_summary(db)
    return ApiResponse.success(data=summary)


@router.get("/stats", response_model=ApiResponse[TradingStatsOut])
def get_trading_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取交易统计."""
    stats = trading_service.get_trading_stats(db)
    return ApiResponse.success(data=stats)
