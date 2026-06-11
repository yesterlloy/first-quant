"""调度器核心引擎

重要：DuckDB并发限制
- 只读模式：允许多进程并发读取
- 读写模式：同一时间只能有一个写连接
- 最佳实践：每次任务执行时建立连接，执行完立即关闭
"""

import signal
import sys
from typing import Callable, Dict, List, Optional
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
from .dependency import get_dependency_tracker


class QuantScheduler:
    """量化系统调度器

    设计原则：
    - 不持久持有数据库连接
    - 每次任务执行时建立连接，执行完立即关闭
    - 避免与Dashboard等其他进程发生锁冲突
    """

    def __init__(self, db_path: str = "data/db/quant.duckdb", config_path: str = "config/scheduler.yaml", alert_manager = None):
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler is required. Install with: pip install apscheduler")

        # 只保存路径，不保持连接
        self.db_path = db_path
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

        # Dependency tracker
        self.dep_tracker = get_dependency_tracker()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("QuantScheduler initialized (connectionless mode)")

    def _get_db(self):
        """获取一个新的数据库连接 - 每次任务都建立新连接并在任务结束后关闭"""
        from data.db.duckdb_manager import DuckDBManager
        db = DuckDBManager(self.db_path, read_only=False)
        db.connect()
        return db

    def register_task(self, task_name: str, func: Callable, cron: str = None, timeout: int = 300, retry: bool = True, depends_on: List[str] = None):
        """注册定时任务

        Args:
            task_name: 任务名称
            func: 任务函数，接受db参数
            cron: cron表达式
            timeout: 超时时间(秒)
            retry: 是否重试
            depends_on: 依赖的任务列表
        """
        if task_name in self.tasks:
            logger.warning(f"Task {task_name} already registered, overwriting")

        self.tasks[task_name] = func
        self.task_configs[task_name] = {
            "cron": cron,
            "timeout": timeout,
            "retry": retry,
            "depends_on": depends_on or []
        }

        # Register dependencies
        if depends_on:
            self.dep_tracker.register_dependency(task_name, depends_on)

        if cron:
            retry_config = self.config.get("scheduler", {}).get("retry", {})
            max_retries = retry_config.get("max_attempts", 3) if retry else 0

            # 创建包装函数：任务执行时建立连接，执行完立即关闭
            def create_task_wrapper(name, fn, to, mr):
                def wrapped():
                    db = None
                    try:
                        db = self._get_db()
                        wrapped_func = TaskWrapper(
                            db, name, fn,
                            max_retries=mr,
                            initial_delay=retry_config.get("initial_delay", 1.0),
                            max_delay=retry_config.get("max_delay", 8.0),
                            backoff_multiplier=retry_config.get("backoff_multiplier", 2.0),
                            timeout=to,
                            alert_manager=self.alert_manager
                        )
                        wrapped_func.execute()
                    finally:
                        if db:
                            db.close()
                return wrapped

            wrapped_task = create_task_wrapper(task_name, func, timeout, max_retries)

            self.scheduler.add_job(
                wrapped_task,
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
        """手动触发任务（用于CLI命令）"""
        if task_name not in self.tasks:
            logger.error(f"Task {task_name} not found")
            return False

        logger.info(f"Manually triggering task: {task_name}")

        # Execute with wrapper
        retry_config = self.config.get("scheduler", {}).get("retry", {})
        task_config = self.task_configs.get(task_name, {})
        max_retries = retry_config.get("max_attempts", 3) if task_config.get("retry", True) else 0
        timeout = task_config.get("timeout", 300)

        db = None
        try:
            db = self._get_db()
            wrapped_func = TaskWrapper(
                db, task_name, self.tasks[task_name],
                max_retries=max_retries,
                timeout=timeout,
                alert_manager=self.alert_manager
            )
            wrapped_func.execute()
            return True
        finally:
            if db:
                db.close()

    def get_task_status(self, task_name: str, limit: int = 10) -> list:
        """获取任务最近执行状态"""
        from .store import SchedulerLogStore
        db = None
        try:
            db = self._get_db()
            store = SchedulerLogStore(db)
            logs_df = store.get_recent_logs(task_name, limit)
            return logs_df.to_dict("records") if not logs_df.empty else []
        finally:
            if db:
                db.close()

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown()
        sys.exit(0)
