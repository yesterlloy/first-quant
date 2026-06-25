"""ML 模型 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.ml import MLTrainTask, MLTimingSignal, MLFactorImportance
from app.schemas.ml import (
    MLTrainTaskCreate,
    MLTrainTaskResponse,
    MLTimingSignalResponse,
    MLFactorImportanceResponse,
)
from app.services.ml_service import ml_service

router = APIRouter(prefix="/ml", tags=["ML 模型"])


@router.get("/tasks", response_model=List[MLTrainTaskResponse])
def list_train_tasks(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取训练任务列表"""
    tasks = (
        db.query(MLTrainTask)
        .order_by(MLTrainTask.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return tasks


@router.get("/tasks/{task_id}", response_model=MLTrainTaskResponse)
def get_train_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取训练任务详情"""
    task = db.query(MLTrainTask).filter(MLTrainTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/train", response_model=MLTrainTaskResponse)
def submit_train_task(
    task_in: MLTrainTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """提交训练任务"""
    task = ml_service.create_train_task(
        db,
        model_name=task_in.model_name,
        start_date=task_in.start_date,
        end_date=task_in.end_date,
        factors=task_in.factors,
        params=task_in.params,
        user_id=current_user.id,
    )
    return task


@router.get("/signals", response_model=List[MLTimingSignalResponse])
def list_signals(
    date: str = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取预测信号"""
    query = db.query(MLTimingSignal)
    if date:
        query = query.filter(MLTimingSignal.trade_date == date)
    signals = query.order_by(MLTimingSignal.trade_date.desc()).limit(limit).all()
    return signals


@router.get("/factor-importance", response_model=List[MLFactorImportanceResponse])
def list_factor_importance(
    model_name: str = None,
    top_n: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取因子重要性"""
    query = db.query(MLFactorImportance)
    if model_name:
        query = query.filter(MLFactorImportance.model_name == model_name)
    importance = query.order_by(MLFactorImportance.importance.desc()).limit(top_n).all()
    return importance
