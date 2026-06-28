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


@router.get("/strategies", response_model=ApiResponse[list])
def get_strategy_list(db: Session = Depends(get_db)):
    """获取策略列表（暂返回示例数据）."""
    # TODO: 实现策略管理服务
    strategies = [
        {"id": "1", "name": "双均线策略", "description": "基于均线交叉策略"},
        {"id": "2", "name": "RSI 超买超卖策略", "description": "RSI 指标策略"},
        {"id": "3", "name": "MACD 背离策略", "description": "MACD 指标策略"},
    ]
    return ApiResponse.success(data=strategies)


@router.get("/history", response_model=ApiResponse[BacktestListResponse])
def get_backtest_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """获取回测历史（同 list_backtests）."""
    from app.schemas.backtest import BacktestListParams

    params = PaginationParams(page=page, page_size=page_size)
    bp = BacktestListParams(page=page, page_size=page_size)
    items, total = backtest_service.list_backtests(db, bp)
    return ApiResponse.success(
        data=PaginatedResponse[BacktestTaskOut].create(
            items=[BacktestTaskOut.model_validate(t) for t in items],
            total=total,
            params=params,
        )
    )


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


@router.post("/run", response_model=ApiResponse[BacktestTaskOut])
def submit_backtest(
    strategy_id: str = Query(...),
    stock_code: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    initial_capital: float = Query(100000.0),
    commission: float = Query(0.001),
    slippage: float = Query(0.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """提交回测任务（直接执行）."""
    task_in = BacktestTaskCreate(
        strategy_name=f"策略 {strategy_id}",
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage,
    )
    task = backtest_service.create_backtest(db, task_in, user_id=current_user.id)
    task = backtest_service.run_backtest(db, task.id)
    return ApiResponse.success(data=BacktestTaskOut.model_validate(task), message="执行完成")


@router.get("/tasks/{task_id}", response_model=ApiResponse[BacktestTaskOut])
def get_backtest_task(task_id: int, db: Session = Depends(get_db)):
    """查询回测任务状态."""
    task = backtest_service.get_backtest(db, task_id)
    return ApiResponse.success(data=BacktestTaskOut.model_validate(task))


@router.get("/result/{task_id}", response_model=ApiResponse[BacktestResultOut])
def get_backtest_result(task_id: int, db: Session = Depends(get_db)):
    """获取回测结果指标."""
    result = backtest_service.get_backtest_result(db, task_id)
    return ApiResponse.success(data=BacktestResultOut.model_validate(result))


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


@router.delete("/{task_id}", response_model=ApiResponse[None])
def delete_backtest(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除回测任务（需登录）."""
    backtest_service.delete_backtest(db, task_id)
    return ApiResponse.success(message="删除成功")
