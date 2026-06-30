"""调度器 API：任务管理、日志查询、手动触发."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.scheduler import (
    SchedulerTaskOut,
    SchedulerTaskCreate,
    SchedulerTaskUpdate,
    SchedulerLogOut,
    SchedulerStatsOut,
)
from app.services import scheduler_service

router = APIRouter(prefix="/scheduler", tags=["调度器"])


# ========== 任务管理 ==========

@router.get("/tasks", response_model=ApiResponse[PaginatedResponse[SchedulerTaskOut]])
def list_tasks(
    enabled: Optional[bool] = Query(None, description="是否启用"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取调度任务列表."""
    params = PaginationParams(page=page, page_size=page_size)
    items, total = scheduler_service.list_tasks(
        db, enabled=enabled, skip=params.offset, limit=params.limit
    )
    return ApiResponse.success(
        data=PaginatedResponse[SchedulerTaskOut].create(
            items=items,
            total=total,
            params=params,
        )
    )


@router.get("/tasks/{task_id}", response_model=ApiResponse[SchedulerTaskOut])
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取单个任务详情."""
    task = scheduler_service.get_task(db, task_id)
    return ApiResponse.success(data=task)


@router.post("/tasks", response_model=ApiResponse[SchedulerTaskOut])
def create_task(
    task_in: SchedulerTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建新的调度任务."""
    task = scheduler_service.create_task(db, task_in)
    return ApiResponse.success(data=task, message="任务创建成功")


@router.put("/tasks/{task_id}", response_model=ApiResponse[SchedulerTaskOut])
def update_task(
    task_id: int,
    task_in: SchedulerTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新调度任务."""
    task = scheduler_service.update_task(db, task_id, task_in)
    return ApiResponse.success(data=task, message="任务更新成功")


@router.delete("/tasks/{task_id}", response_model=ApiResponse)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除调度任务."""
    scheduler_service.delete_task(db, task_id)
    return ApiResponse.success(message="任务删除成功")


@router.post("/tasks/{task_id}/toggle", response_model=ApiResponse[SchedulerTaskOut])
def toggle_task(
    task_id: int,
    enabled: bool = Query(..., description="是否启用"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """启用或禁用任务."""
    task = scheduler_service.toggle_task(db, task_id, enabled)
    status = "启用" if enabled else "禁用"
    return ApiResponse.success(data=task, message=f"任务已{status}")


@router.post("/tasks/{task_name}/trigger", response_model=ApiResponse)
def trigger_task(
    task_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """手动触发任务执行."""
    result = scheduler_service.trigger_task(db, task_name)
    return ApiResponse.success(data=result, message=f"任务 {task_name} 已触发")


# ========== 执行日志 ==========

@router.get("/logs", response_model=ApiResponse[PaginatedResponse[SchedulerLogOut]])
def list_logs(
    task_name: Optional[str] = Query(None, description="任务名称"),
    status: Optional[str] = Query(None, description="状态"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取任务执行日志."""
    params = PaginationParams(page=page, page_size=page_size)
    logs, total = scheduler_service.list_logs(
        db, task_name=task_name, status=status,
        start_date=start_date, end_date=end_date,
        skip=params.offset, limit=params.limit,
    )
    return ApiResponse.success(
        data=PaginatedResponse[SchedulerLogOut].create(
            items=logs,
            total=total,
            params=params,
        )
    )


@router.get("/logs/{log_id}", response_model=ApiResponse[SchedulerLogOut])
def get_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取单条执行日志详情."""
    log = scheduler_service.get_log(db, log_id)
    return ApiResponse.success(data=log)


# ========== 统计信息 ==========

@router.get("/stats", response_model=ApiResponse[SchedulerStatsOut])
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取调度器统计信息."""
    stats = scheduler_service.get_stats(db)
    return ApiResponse.success(data=stats)


# ========== 初始化 ==========

@router.post("/init", response_model=ApiResponse)
def init_default_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """初始化默认调度任务."""
    scheduler_service.init_default_tasks(db)
    return ApiResponse.success(data={"initialized": True}, message="默认任务初始化完成")
