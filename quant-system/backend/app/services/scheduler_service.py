"""调度器服务：任务管理、日志查询、手动触发."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.scheduler import SchedulerTask, SchedulerLog
from app.schemas.scheduler import (
    SchedulerTaskCreate,
    SchedulerTaskUpdate,
    SchedulerStatsOut,
)

logger = logging.getLogger(__name__)


# ========== 调度任务管理 ==========

def get_task(db: Session, task_id: int) -> SchedulerTask:
    """获取单个任务."""
    task = db.query(SchedulerTask).filter(SchedulerTask.id == task_id).first()
    if not task:
        raise NotFoundException(resource=f"SchedulerTask {task_id}")
    return task


def get_task_by_name(db: Session, task_name: str) -> Optional[SchedulerTask]:
    """按名称获取任务."""
    return db.query(SchedulerTask).filter(SchedulerTask.task_name == task_name).first()


def list_tasks(
    db: Session,
    enabled: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[SchedulerTask], int]:
    """获取任务列表."""
    query = db.query(SchedulerTask)

    if enabled is not None:
        query = query.filter(SchedulerTask.enabled == enabled)

    total = query.count()
    items = query.order_by(SchedulerTask.task_name).offset(skip).limit(limit).all()
    return items, total


def create_task(db: Session, task_in: SchedulerTaskCreate) -> SchedulerTask:
    """创建调度任务."""
    if get_task_by_name(db, task_in.task_name):
        raise ValidationException(message=f"任务名称已存在: {task_in.task_name}")

    task = SchedulerTask(
        task_name=task_in.task_name,
        description=task_in.description,
        cron=task_in.cron,
        enabled=task_in.enabled,
        timeout=task_in.timeout,
        retry=task_in.retry,
        retry_max=task_in.retry_max,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task_id: int, task_in: SchedulerTaskUpdate) -> SchedulerTask:
    """更新调度任务."""
    task = get_task(db, task_id)

    update_data = task_in.model_dump(exclude_unset=True)

    # 检查重名
    if "task_name" in update_data:
        existing = get_task_by_name(db, update_data["task_name"])
        if existing and existing.id != task_id:
            raise ValidationException(message=f"任务名称已存在: {update_data['task_name']}")

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: int) -> None:
    """删除调度任务."""
    task = get_task(db, task_id)
    db.delete(task)
    db.commit()


def toggle_task(db: Session, task_id: int, enabled: bool) -> SchedulerTask:
    """启用/禁用任务."""
    task = get_task(db, task_id)
    task.enabled = enabled
    db.commit()
    db.refresh(task)
    return task


def update_task_status(
    db: Session,
    task_name: str,
    status: str,
    last_run_at: Optional[datetime] = None,
    next_run_at: Optional[datetime] = None,
) -> None:
    """更新任务执行状态."""
    task = get_task_by_name(db, task_name)
    if task:
        task.last_status = status
        if last_run_at:
            task.last_run_at = last_run_at
        if next_run_at:
            task.next_run_at = next_run_at
        db.commit()


# ========== 执行日志管理 ==========

def create_log(
    db: Session,
    task_name: str,
    status: str = "running",
    start_time: Optional[datetime] = None,
) -> SchedulerLog:
    """创建执行日志."""
    log = SchedulerLog(
        task_name=task_name,
        status=status,
        start_time=start_time or datetime.now(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_log(
    db: Session,
    log_id: int,
    status: str,
    end_time: Optional[datetime] = None,
    error_message: Optional[str] = None,
    retry_count: int = 0,
) -> SchedulerLog:
    """更新执行日志."""
    log = db.query(SchedulerLog).filter(SchedulerLog.id == log_id).first()
    if not log:
        raise NotFoundException(resource=f"SchedulerLog {log_id}")

    log.status = status
    log.end_time = end_time or datetime.now()
    if log.start_time and log.end_time:
        log.duration_seconds = (log.end_time - log.start_time).total_seconds()
    log.error_message = error_message
    log.retry_count = retry_count

    db.commit()
    db.refresh(log)
    return log


def list_logs(
    db: Session,
    task_name: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[SchedulerLog], int]:
    """获取执行日志列表."""
    query = db.query(SchedulerLog)

    if task_name:
        query = query.filter(SchedulerLog.task_name == task_name)
    if status:
        query = query.filter(SchedulerLog.status == status)
    if start_date:
        query = query.filter(SchedulerLog.start_time >= start_date)
    if end_date:
        query = query.filter(SchedulerLog.start_time <= end_date)

    total = query.count()
    items = query.order_by(desc(SchedulerLog.start_time)).offset(skip).limit(limit).all()
    return items, total


def get_log(db: Session, log_id: int) -> SchedulerLog:
    """获取单条日志."""
    log = db.query(SchedulerLog).filter(SchedulerLog.id == log_id).first()
    if not log:
        raise NotFoundException(resource=f"SchedulerLog {log_id}")
    return log


# ========== 统计信息 ==========

def get_stats(db: Session) -> SchedulerStatsOut:
    """获取调度器统计信息."""
    # 任务统计
    total_tasks = db.query(func.count(SchedulerTask.id)).scalar() or 0
    enabled_tasks = db.query(func.count(SchedulerTask.id)).filter(SchedulerTask.enabled == True).scalar() or 0

    # 今日统计
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_logs = db.query(SchedulerLog).filter(SchedulerLog.start_time >= today_start)

    today_runs = today_logs.count()
    success_count = today_logs.filter(SchedulerLog.status == "success").count()
    failed_count = today_logs.filter(SchedulerLog.status == "failed").count()

    # 平均耗时（最近100次成功执行）
    recent_success = (
        db.query(SchedulerLog)
        .filter(SchedulerLog.status == "success")
        .filter(SchedulerLog.duration_seconds.isnot(None))
        .order_by(desc(SchedulerLog.end_time))
        .limit(100)
        .all()
    )

    avg_duration = 0.0
    if recent_success:
        avg_duration = sum(log.duration_seconds for log in recent_success) / len(recent_success)

    # 正在运行的任务
    running = (
        db.query(SchedulerLog)
        .filter(SchedulerLog.status == "running")
        .filter(SchedulerLog.end_time.is_(None))
        .all()
    )
    running_tasks = [log.task_name for log in running]

    # 最近失败的任务
    recently_failed = (
        db.query(SchedulerLog)
        .filter(SchedulerLog.status == "failed")
        .order_by(desc(SchedulerLog.end_time))
        .limit(5)
        .all()
    )
    failed_list = [
        {
            "task_name": log.task_name,
            "error_message": log.error_message,
            "failed_at": log.end_time.isoformat() if log.end_time else None,
        }
        for log in recently_failed
    ]

    return SchedulerStatsOut(
        total_tasks=total_tasks,
        enabled_tasks=enabled_tasks,
        today_runs=today_runs,
        success_count=success_count,
        failed_count=failed_count,
        avg_duration=round(avg_duration, 2),
        running_tasks=running_tasks,
        recently_failed=failed_list,
    )


# ========== 手动触发任务 ==========

def trigger_task(db: Session, task_name: str) -> Dict[str, Any]:
    """
    手动触发任务执行.

    注意：这里只记录触发事件，实际执行需要由调度器引擎处理
    """
    task = get_task_by_name(db, task_name)
    if not task:
        raise NotFoundException(resource=f"SchedulerTask {task_name}")

    # 记录触发日志
    log = create_log(db, task_name, status="running")

    logger.info(f"手动触发任务: {task_name}, log_id={log.id}")

    # TODO: 实际执行逻辑需要集成 APScheduler
    # 这里可以发送消息到任务队列或直接调用任务函数

    return {
        "task_name": task_name,
        "triggered": True,
        "log_id": log.id,
        "message": f"任务 {task_name} 已触发执行",
    }


# ========== 初始化默认任务 ==========

def init_default_tasks(db: Session) -> None:
    """初始化默认调度任务."""
    default_tasks = [
        {
            "task_name": "daily_data_collection",
            "description": "每日数据采集（收盘后）",
            "cron": "0 18 * * 1-5",  # 周一到周五18:00
            "timeout": 600,
        },
        {
            "task_name": "daily_factor_calc",
            "description": "每日因子计算",
            "cron": "0 19 * * 1-5",  # 周一到周五19:00
            "timeout": 1200,
        },
        {
            "task_name": "daily_ml_predict",
            "description": "每日ML预测",
            "cron": "0 20 * * 1-5",  # 周一到周五20:00
            "timeout": 1800,
        },
        {
            "task_name": "monthly_rebalance",
            "description": "月度调仓",
            "cron": "0 14 L * *",  # 每月最后一天14:00
            "timeout": 3600,
        },
        {
            "task_name": "daily_risk_check",
            "description": "每日风控检查",
            "cron": "30 15 * * 1-5",  # 周一到周五15:30
            "timeout": 300,
        },
        {
            "task_name": "weekly_report",
            "description": "每周策略报告",
            "cron": "0 18 * * 5",  # 每周五18:00
            "timeout": 600,
        },
    ]

    for task_data in default_tasks:
        if not get_task_by_name(db, task_data["task_name"]):
            task = SchedulerTaskCreate(**task_data)
            create_task(db, task)
            logger.info(f"创建默认任务: {task_data['task_name']}")
