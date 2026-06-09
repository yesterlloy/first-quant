"""调度器核心引擎"""

import signal
import sys
from typing import Callable, Dict, Optional
from datetime import datetime
from loguru import logger

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Install with: pip install apscheduler")

from .task_wrapper import TaskWrapper


class QuantScheduler:
    """量化系统调度器"""

    def __init__(self, db, config_path: str = "config/scheduler.yaml", alert_manager = None):
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler is required. Install with: pip install apscheduler")

        self.db = db
        self.alert_manager = alert_manager

        # Load config
        from config import get_scheduler_config
        self.config = get_scheduler_config(config_path)

        scheduler_config = self.config.get("scheduler", {})
        self.timezone = scheduler_config.get("timezone", "Asia/Shanghai")
        self.misfire_grace_time = scheduler_config.get("misfire_grace_time", 3600)
        self.misfire_policy = scheduler_config.get("misfire_policy", "skip")

        # Initialize APScheduler
        self.scheduler = BackgroundScheduler(timezone=self.timezone)

        # Task registry
        self.tasks: Dict[str, Callable] = {}
        self.task_configs: Dict[str, dict] = {}

        # State
        self.running = False

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("QuantScheduler initialized")

    def register_task(self, task_name: str, func: Callable, cron: str = None, timeout: int = 300, retry: bool = True):
        """注册定时任务"""
        if task_name in self.tasks:
            logger.warning(f"Task {task_name} already registered, overwriting")

        self.tasks[task_name] = func
        self.task_configs[task_name] = {"cron": cron, "timeout": timeout, "retry": retry}

        if cron:
            retry_config = self.config.get("scheduler", {}).get("retry", {})
            max_retries = retry_config.get("max_attempts", 3) if retry else 0

            wrapped_func = TaskWrapper(
                self.db, task_name, func,
                max_retries=max_retries,
                initial_delay=retry_config.get("initial_delay", 1.0),
                max_delay=retry_config.get("max_delay", 8.0),
                backoff_multiplier=retry_config.get("backoff_multiplier", 2.0),
                alert_manager=self.alert_manager
            )

            self.scheduler.add_job(
                wrapped_func.execute,
                trigger=CronTrigger.from_crontab(cron),
                id=task_name,
                name=task_name,
                misfire_grace_time=self.misfire_grace_time,
                coalesce=True,  # Merge missed executions
                max_instances=1  # Only one instance per task
            )
            logger.info(f"Registered task {task_name} with cron: {cron}")

    def start(self):
        """启动调度器（阻塞运行）"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting scheduler...")
        self.scheduler.start()
        self.running = True
        logger.info("Scheduler started and running")

        # Keep main thread alive
        try:
            while self.running:
                signal.pause()
        except (KeyboardInterrupt, SystemExit):
            self.shutdown()

    def shutdown(self, wait: bool = True):
        """停止调度器"""
        logger.info("Shutting down scheduler...")
        self.scheduler.shutdown(wait=wait)
        self.running = False
        logger.info("Scheduler stopped")

    def trigger_task(self, task_name: str) -> bool:
        """手动触发任务"""
        if task_name not in self.tasks:
            logger.error(f"Task {task_name} not found")
            return False

        logger.info(f"Manually triggering task: {task_name}")

        # Execute with wrapper
        retry_config = self.config.get("scheduler", {}).get("retry", {})
        task_config = self.task_configs.get(task_name, {})
        max_retries = retry_config.get("max_attempts", 3) if task_config.get("retry", True) else 0

        wrapped_func = TaskWrapper(
            self.db, task_name, self.tasks[task_name],
            max_retries=max_retries,
            alert_manager=self.alert_manager
        )
        result = wrapped_func.execute()

        return result is not None

    def get_task_status(self, task_name: str, limit: int = 10) -> list:
        """获取任务最近执行状态"""
        from .store import SchedulerLogStore
        store = SchedulerLogStore(self.db)
        logs_df = store.get_recent_logs(task_name, limit)
        return logs_df.to_dict("records") if not logs_df.empty else []

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown()
        sys.exit(0)
