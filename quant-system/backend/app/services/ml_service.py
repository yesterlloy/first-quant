"""ML 模型服务：训练任务管理、预测信号、特征重要性查询."""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.ml import MLFactorImportance, MLTimingSignal, MLTrainTask
from app.schemas.ml import MLTrainTaskCreate


class MLService:
    """ML 服务类."""

    # 支持的模型列表
    SUPPORTED_MODELS = {
        "lgbm": {
            "name": "lgbm",
            "display_name": "LightGBM",
            "description": "梯度提升决策树模型，适合结构化数据",
            "type": "lgbm",
            "supported_params": ["n_estimators", "max_depth", "learning_rate", "num_leaves"],
        },
        "xgboost": {
            "name": "xgboost",
            "display_name": "XGBoost",
            "description": "极端梯度提升模型，高性能",
            "type": "xgboost",
            "supported_params": ["n_estimators", "max_depth", "learning_rate", "subsample"],
        },
        "linear": {
            "name": "linear",
            "display_name": "线性模型",
            "description": "Ridge/Lasso 线性回归，可解释性强",
            "type": "linear",
            "supported_params": ["alpha", "solver"],
        },
        "ensemble": {
            "name": "ensemble",
            "display_name": "集成模型",
            "description": "多模型加权集成，稳定性高",
            "type": "ensemble",
            "supported_params": ["weights", "models"],
        },
    }

    def get_supported_models(self) -> List[dict]:
        """获取支持的模型列表."""
        return list(self.SUPPORTED_MODELS.values())

    def create_train_task(
        self,
        db: Session,
        model_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        factors: Optional[List[str]] = None,
        params: Optional[dict] = None,
        user_id: Optional[int] = None,
    ) -> MLTrainTask:
        """创建训练任务.

        Args:
            db: 数据库会话
            model_name: 模型名称
            start_date: 训练开始日期
            end_date: 训练结束日期
            factors: 使用的因子列表
            params: 超参数
            user_id: 创建用户ID

        Returns:
            创建的训练任务
        """
        if model_name not in self.SUPPORTED_MODELS:
            raise ValidationException(
                message=f"不支持的模型: {model_name}, 支持的模型: {list(self.SUPPORTED_MODELS.keys())}"
            )

        task = MLTrainTask(
            model_name=model_name,
            status="pending",
            train_start=start_date,
            train_end=end_date,
            params=json.dumps(params) if params else None,
        )

        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def get_train_task(self, db: Session, task_id: int) -> MLTrainTask:
        """获取训练任务详情."""
        task = db.query(MLTrainTask).filter(MLTrainTask.id == task_id).first()
        if not task:
            raise NotFoundException(resource=f"MLTrainTask {task_id}")
        return task

    def list_train_tasks(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Tuple[List[MLTrainTask], int]:
        """获取训练任务列表."""
        query = db.query(MLTrainTask)

        if status:
            query = query.filter(MLTrainTask.status == status)
        if model_name:
            query = query.filter(MLTrainTask.model_name == model_name)

        total = query.count()
        items = query.order_by(MLTrainTask.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def run_train_task(self, db: Session, task_id: int) -> MLTrainTask:
        """执行训练任务（简化版，实际应使用Celery异步任务）.

        TODO: 集成实际的训练引擎，使用 Celery 异步执行
        """
        task = self.get_train_task(db, task_id)

        if task.status != "pending":
            raise ValidationException(message=f"任务状态不是待执行: {task.status}")

        # 更新状态为运行中
        task.status = "running"
        task.started_at = datetime.now()
        db.commit()

        try:
            # ========== 简化版训练逻辑 ==========
            # TODO: 集成 ml/trainer.py 中的实际训练逻辑

            # 模拟训练过程（实际应调用 ml.trainer.train_model）
            import time

            time.sleep(2)  # 模拟训练耗时

            # 模拟训练结果
            task.status = "success"
            task.train_samples = 10000
            task.val_samples = 2000
            task.train_auc = 0.72
            task.val_auc = 0.68
            task.top_return = 0.15
            task.feature_count = 17

            # 模拟生成特征重要性
            importance_data = [
                ("RET_5", 0.15),
                ("VOL_20", 0.12),
                ("RSI_14", 0.10),
                ("PE", 0.09),
                ("MACD", 0.08),
            ]
            for idx, (feature_name, importance) in enumerate(importance_data):
                fi = MLFactorImportance(
                    task_id=task.id,
                    feature_name=feature_name,
                    importance=importance,
                    rank=idx + 1,
                )
                db.add(fi)

            # 模拟生成预测信号
            for day_offset in range(5):
                signal_date = datetime.now() - timedelta(days=day_offset)
                sig = MLTimingSignal(
                    timestamp=signal_date,
                    code="000001",
                    model_name=task.model_name,
                    signal=0.6 + day_offset * 0.05,
                    probability=0.7 + day_offset * 0.03,
                    prediction="buy" if day_offset % 2 == 0 else "hold",
                )
                db.add(sig)

            task.finished_at = datetime.now()
            db.commit()
            db.refresh(task)

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.finished_at = datetime.now()
            db.commit()
            raise

        return task

    def get_signals(
        self,
        db: Session,
        date: Optional[str] = None,
        code: Optional[str] = None,
        model_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[MLTimingSignal]:
        """获取预测信号."""
        query = db.query(MLTimingSignal)

        if date:
            query = query.filter(db.func.date(MLTimingSignal.timestamp) == date)
        if code:
            query = query.filter(MLTimingSignal.code == code)
        if model_name:
            query = query.filter(MLTimingSignal.model_name == model_name)

        return query.order_by(MLTimingSignal.timestamp.desc()).limit(limit).all()

    def get_factor_importance(
        self,
        db: Session,
        task_id: Optional[int] = None,
        model_name: Optional[str] = None,
        top_n: int = 20,
    ) -> List[MLFactorImportance]:
        """获取因子重要性."""
        query = db.query(MLFactorImportance)

        if task_id:
            query = query.filter(MLFactorImportance.task_id == task_id)
        if model_name:
            query = query.join(MLTrainTask).filter(MLTrainTask.model_name == model_name)

        return query.order_by(MLFactorImportance.importance.desc()).limit(top_n).all()

    def delete_train_task(self, db: Session, task_id: int) -> None:
        """删除训练任务."""
        task = self.get_train_task(db, task_id)
        db.delete(task)
        db.commit()


# 单例实例
ml_service = MLService()
