"""ML 模型相关 schema."""

import json
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MLTrainTaskBase(BaseModel):
    """训练任务基础字段."""

    model_name: str = Field(..., max_length=64, description="模型名称")
    start_date: Optional[date] = Field(None, description="训练开始日期")
    end_date: Optional[date] = Field(None, description="训练结束日期")
    factors: Optional[List[str]] = Field(None, description="使用的因子列表")
    params: Optional[Dict[str, Any]] = Field(None, description="超参数")

    @field_validator("params", mode="before")
    @classmethod
    def parse_params(cls, v):
        """将数据库中的JSON字符串解析为字典."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


class MLTrainTaskCreate(MLTrainTaskBase):
    """创建训练任务."""

    pass


class MLTrainTaskResponse(MLTrainTaskBase):
    """训练任务响应."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str = Field(..., description="状态：pending/running/success/failed")

    train_start: Optional[date] = None
    train_end: Optional[date] = None
    val_start: Optional[date] = None
    val_end: Optional[date] = None

    train_samples: Optional[int] = None
    val_samples: Optional[int] = None
    train_auc: Optional[float] = None
    val_auc: Optional[float] = None
    top_return: Optional[float] = None
    feature_count: Optional[int] = None

    model_path: Optional[str] = None
    error_message: Optional[str] = None

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class MLTimingSignalResponse(BaseModel):
    """ML 信号响应."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    code: str
    model_name: str
    signal: Optional[float] = None
    probability: Optional[float] = None
    prediction: Optional[str] = None


class MLFactorImportanceResponse(BaseModel):
    """因子重要性响应."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    feature_name: str
    importance: float
    rank: Optional[int] = None
    created_at: Optional[datetime] = None


class MLModelInfo(BaseModel):
    """模型信息."""

    name: str
    display_name: str
    description: str
    type: str  # lgbm, xgboost, linear, ensemble
    supported_params: List[str]


class MLTrainProgress(BaseModel):
    """训练进度."""

    task_id: str
    status: str
    progress: float  # 0-100
    current_stage: str
    message: Optional[str] = None
