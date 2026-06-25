"""机器学习模型.

- ``MLTrainTask``：模型训练任务，字段对齐 DuckDB ``model_log`` 表。
- ``MLFactorImportance``：特征重要性（模型产出）。
- ``MLTimingSignal``：择时/选股信号，对应 DuckDB ``ml_signal`` 表。
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MLTrainTask(Base):
    """ML 训练任务（对应 model_log）."""

    __tablename__ = "ml_train_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(64), nullable=False, index=True, comment="模型名称")
    status = Column(
        String(16),
        default="pending",
        index=True,
        comment="状态：pending/running/success/failed",
    )

    eval_date = Column(Date, nullable=True, comment="评估日期")
    train_start = Column(Date, nullable=True, comment="训练集开始")
    train_end = Column(Date, nullable=True, comment="训练集结束")
    val_start = Column(Date, nullable=True, comment="验证集开始")
    val_end = Column(Date, nullable=True, comment="验证集结束")

    train_samples = Column(Integer, nullable=True, comment="训练样本数")
    val_samples = Column(Integer, nullable=True, comment="验证样本数")
    train_auc = Column(Float, nullable=True, comment="训练集 AUC")
    val_auc = Column(Float, nullable=True, comment="验证集 AUC")
    top_return = Column(Float, nullable=True, comment="Top 组收益")
    feature_count = Column(Integer, nullable=True, comment="特征数量")

    # 超参与模型路径
    params = Column(Text, nullable=True, comment="超参 JSON")
    model_path = Column(String(255), nullable=True, comment="模型文件路径")
    error_message = Column(Text, nullable=True, comment="失败原因")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # 关联特征重要性
    importances = relationship(
        "MLFactorImportance",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MLTrainTask {self.id} {self.model_name} [{self.status}]>"


class MLFactorImportance(Base):
    """特征重要性."""

    __tablename__ = "ml_factor_importance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        Integer,
        ForeignKey("ml_train_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联训练任务 ID",
    )
    feature_name = Column(String(128), nullable=False, index=True, comment="特征名称")
    importance = Column(Float, nullable=False, comment="重要性分值")
    rank = Column(Integer, nullable=True, comment="重要性排名")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    task = relationship("MLTrainTask", back_populates="importances")

    def __repr__(self) -> str:
        return f"<MLFactorImportance {self.feature_name}={self.importance:.4f}>"


class MLTimingSignal(Base):
    """ML 信号（对应 ml_signal 表）."""

    __tablename__ = "ml_signal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, comment="信号时间")
    code = Column(String(16), nullable=False, index=True, comment="股票代码")
    model_name = Column(String(64), nullable=False, comment="模型名称")
    signal = Column(Float, nullable=True, comment="信号值")
    probability = Column(Float, nullable=True, comment="概率")
    prediction = Column(String(16), nullable=True, comment="预测标签，如 buy/sell/hold")

    def __repr__(self) -> str:
        return f"<MLTimingSignal {self.code} {self.model_name} {self.prediction}>"
