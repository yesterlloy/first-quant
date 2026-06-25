"""调度器模型.

- ``SchedulerTask``：调度任务定义（对应 ``config/scheduler.yaml`` 中的任务）。
- ``SchedulerLog``：任务执行日志，对应 DuckDB ``scheduler_log`` 表，
  字段对齐 ``scheduler/store.py::SchedulerLogStore``。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class SchedulerTask(Base):
    """调度任务定义."""

    __tablename__ = "scheduler_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(100), unique=True, index=True, nullable=False, comment="任务名称")
    description = Column(Text, nullable=True, comment="任务描述")
    cron = Column(String(64), nullable=False, comment="cron 表达式")
    enabled = Column(Boolean, default=True, index=True, comment="是否启用")
    timeout = Column(Integer, default=300, comment="超时时间（秒）")
    retry = Column(Boolean, default=True, comment="是否重试")
    retry_max = Column(Integer, default=3, comment="最大重试次数")

    last_run_at = Column(DateTime(timezone=True), nullable=True, comment="上次执行时间")
    next_run_at = Column(DateTime(timezone=True), nullable=True, comment="下次执行时间")
    last_status = Column(String(20), nullable=True, comment="上次执行状态")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<SchedulerTask {self.task_name} cron={self.cron} enabled={self.enabled}>"


class SchedulerLog(Base):
    """调度执行日志（对应 scheduler_log 表）."""

    __tablename__ = "scheduler_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(100), nullable=False, index=True, comment="任务名称")
    status = Column(
        String(20),
        nullable=False,
        index=True,
        comment="状态：running/success/failed/skipped",
    )
    start_time = Column(DateTime(timezone=True), nullable=False, comment="开始时间")
    end_time = Column(DateTime(timezone=True), nullable=True, comment="结束时间")
    duration_seconds = Column(Float, nullable=True, comment="耗时（秒）")
    retry_count = Column(Integer, default=0, comment="重试次数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<SchedulerLog {self.task_name} [{self.status}] {self.start_time}>"
