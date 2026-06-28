"""调度器相关 Schema."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


class SchedulerTaskOut(BaseModel):
    """调度任务输出."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_name: str
    description: Optional[str] = None
    cron: str
    enabled: bool
    timeout: int
    retry: bool
    retry_max: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SchedulerTaskCreate(BaseModel):
    """创建调度任务."""

    task_name: str = Field(..., max_length=100, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    cron: str = Field(..., max_length=64, description="cron表达式")
    enabled: bool = Field(True, description="是否启用")
    timeout: int = Field(300, ge=1, description="超时时间（秒）")
    retry: bool = Field(True, description="是否重试")
    retry_max: int = Field(3, ge=0, description="最大重试次数")


class SchedulerTaskUpdate(BaseModel):
    """更新调度任务."""

    task_name: Optional[str] = None
    description: Optional[str] = None
    cron: Optional[str] = None
    enabled: Optional[bool] = None
    timeout: Optional[int] = None
    retry: Optional[bool] = None
    retry_max: Optional[int] = None


class SchedulerLogOut(BaseModel):
    """调度日志输出."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_name: str
    status: str  # running/success/failed/skipped
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class SchedulerStatsOut(BaseModel):
    """调度器统计."""

    total_tasks: int = 0
    enabled_tasks: int = 0
    today_runs: int = 0
    success_count: int = 0
    failed_count: int = 0
    avg_duration: float = 0.0
    running_tasks: List[str] = []
    recently_failed: List[Dict[str, Any]] = []
