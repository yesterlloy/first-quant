"""ML 模型 API"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.ml import (
    MLFactorImportanceResponse,
    MLModelInfo,
    MLTimingSignalResponse,
    MLTrainTaskCreate,
    MLTrainTaskResponse,
)
from app.services.ml_service import ml_service

router = APIRouter(prefix="/ml", tags=["ML 模型"])


@router.get("/models", response_model=ApiResponse[List[MLModelInfo]])
def get_supported_models():
    """获取支持的模型列表."""
    models = ml_service.get_supported_models()
    return ApiResponse.success(data=models)


@router.get("/tasks", response_model=ApiResponse[PaginatedResponse[MLTrainTaskResponse]])
def list_train_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    model_name: Optional[str] = Query(None, description="模型名称筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取训练任务列表（分页）."""
    from app.schemas.common import PaginationParams

    params = PaginationParams(page=page, page_size=page_size)
    items, total = ml_service.list_train_tasks(
        db, skip=params.offset, limit=params.limit, status=status, model_name=model_name
    )
    return ApiResponse.success(
        data=PaginatedResponse[MLTrainTaskResponse].create(
            items=[MLTrainTaskResponse.model_validate(t) for t in items],
            total=total,
            params=params,
        )
    )


@router.get("/tasks/{task_id}", response_model=ApiResponse[MLTrainTaskResponse])
def get_train_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取训练任务详情."""
    task = ml_service.get_train_task(db, task_id)
    return ApiResponse.success(data=MLTrainTaskResponse.model_validate(task))


@router.post("/train", response_model=ApiResponse[MLTrainTaskResponse], status_code=status.HTTP_201_CREATED)
def submit_train_task(
    task_in: MLTrainTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """提交训练任务."""
    task = ml_service.create_train_task(
        db,
        model_name=task_in.model_name,
        start_date=task_in.start_date,
        end_date=task_in.end_date,
        factors=task_in.factors,
        params=task_in.params,
        user_id=current_user.id,
    )
    return ApiResponse.success(data=MLTrainTaskResponse.model_validate(task), message="任务已提交")


@router.post("/tasks/{task_id}/run", response_model=ApiResponse[MLTrainTaskResponse])
def run_train_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """执行训练任务（同步执行，生产环境应使用异步任务）."""
    task = ml_service.run_train_task(db, task_id)
    return ApiResponse.success(data=MLTrainTaskResponse.model_validate(task), message="训练完成")


@router.delete("/tasks/{task_id}", response_model=ApiResponse[None])
def delete_train_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除训练任务."""
    ml_service.delete_train_task(db, task_id)
    return ApiResponse.success(message="删除成功")


@router.get("/signals", response_model=ApiResponse[PaginatedResponse[MLTimingSignalResponse]])
def list_signals(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    date: Optional[str] = Query(None, description="日期筛选，格式 YYYY-MM-DD"),
    code: Optional[str] = Query(None, description="股票代码筛选"),
    model_name: Optional[str] = Query(None, description="模型名称筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取预测信号（分页）."""
    from app.schemas.common import PaginationParams

    params = PaginationParams(page=page, page_size=page_size)
    signals = ml_service.get_signals(db, date=date, code=code, model_name=model_name, limit=params.limit)
    return ApiResponse.success(
        data=PaginatedResponse[MLTimingSignalResponse].create(
            items=[MLTimingSignalResponse.model_validate(s) for s in signals],
            total=len(signals),
            params=params,
        )
    )


@router.get("/factor-importance", response_model=ApiResponse[List[MLFactorImportanceResponse]])
def list_factor_importance(
    task_id: Optional[int] = Query(None, description="训练任务ID"),
    model_name: Optional[str] = Query(None, description="模型名称"),
    top_n: int = Query(20, ge=1, le=100, description="返回前N个重要因子"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取因子重要性."""
    importance = ml_service.get_factor_importance(db, task_id=task_id, model_name=model_name, top_n=top_n)
    return ApiResponse.success(
        data=[MLFactorImportanceResponse.model_validate(i) for i in importance]
    )
