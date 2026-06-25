"""回测路由：任务 CRUD、执行、结果查询."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.backtest import (
    BacktestListResponse,
    BacktestResultOut,
    BacktestTaskCreate,
    BacktestTaskOut,
    BacktestTaskUpdate,
)
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.services import backtest_service

router = APIRouter()


@router.get("", response_model=ApiResponse[BacktestListResponse])
def list_backtests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    status: Optional[str] = Query(None),
    strategy_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """分页查询回测任务."""
    from app.schemas.backtest import BacktestListParams

    params = PaginationParams(page=page, page_size=page_size)
    bp = BacktestListParams(
        page=page, page_size=page_size, status=status, strategy_name=strategy_name
    )
    items, total = backtest_service.list_backtests(db, bp)
    return ApiResponse.success(
        data=PaginatedResponse[BacktestTaskOut].create(
            items=[BacktestTaskOut.model_validate(t) for t in items],
            total=total,
            params=params,
        )
    )


@router.post("", response_model=ApiResponse[BacktestTaskOut], status_code=status.HTTP_201_CREATED)
def create_backtest(
    task_in: BacktestTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建回测任务（需登录）."""
    task = backtest_service.create_backtest(db, task_in, user_id=current_user.id)
    return ApiResponse.success(data=BacktestTaskOut.model_validate(task), message="创建成功")


@router.get("/{task_id}", response_model=ApiResponse[BacktestTaskOut])
def get_backtest(task_id: int, db: Session = Depends(get_db)):
    """查询单个回测任务."""
    task = backtest_service.get_backtest(db, task_id)
    return ApiResponse.success(data=BacktestTaskOut.model_validate(task))


@router.put("/{task_id}", response_model=ApiResponse[BacktestTaskOut])
def update_backtest(
    task_id: int,
    task_in: BacktestTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新回测任务（需登录，仅 pending 可改）."""
    task = backtest_service.update_backtest(db, task_id, task_in)
    return ApiResponse.success(data=BacktestTaskOut.model_validate(task), message="更新成功")


@router.post("/{task_id}/run", response_model=ApiResponse[BacktestTaskOut])
def run_backtest(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """执行回测任务（需登录）."""
    task = backtest_service.run_backtest(db, task_id)
    return ApiResponse.success(data=BacktestTaskOut.model_validate(task), message="执行完成")


@router.get("/{task_id}/result", response_model=ApiResponse[BacktestResultOut])
def get_backtest_result(task_id: int, db: Session = Depends(get_db)):
    """获取回测结果指标."""
    result = backtest_service.get_backtest_result(db, task_id)
    return ApiResponse.success(data=BacktestResultOut.model_validate(result))


@router.delete("/{task_id}", response_model=ApiResponse[None])
def delete_backtest(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除回测任务（需登录）."""
    backtest_service.delete_backtest(db, task_id)
    return ApiResponse.success(message="删除成功")
