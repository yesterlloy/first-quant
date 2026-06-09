"""任务包装器 - 统一处理重试、日志、异常"""

import time
import traceback
from datetime import datetime
from loguru import logger
from .store import SchedulerLogStore


class TaskWrapper:
    """任务包装器

    包装实际任务函数，提供：
    - 执行日志记录
    - 指数退避重试
    - 异常捕获与告警
    - 当日截止时间（避免跨日数据）
    """

    def __init__(self, db, task_name: str, func,
                 max_retries: int = 3,
                 initial_delay: float = 1.0,
                 max_delay: float = 8.0,
                 backoff_multiplier: float = 2.0,
                 cutoff_hour: int = 18,
                 alert_manager = None):
        self.db = db
        self.task_name = task_name
        self.func = func
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.cutoff_hour = cutoff_hour
        self.alert_manager = alert_manager
        self.log_store = SchedulerLogStore(db)

    def execute(self, *args, **kwargs):
        """执行任务（带重试）"""
        retry_count = 0
        start_time = time.time()

        while retry_count <= self.max_retries:
            log_id = self.log_store.log_start(self.task_name)

            try:
                result = self.func(*args, **kwargs)
                duration = time.time() - start_time
                self.log_store.log_success(log_id, duration)
                logger.info(f"Task {self.task_name} succeeded in {duration:.2f}s")
                return result

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                logger.error(f"Task {self.task_name} failed (attempt {retry_count + 1}): {error_msg}")
                logger.debug(traceback.format_exc())

                if retry_count < self.max_retries and self._should_retry():
                    retry_count += 1
                    self.log_store.log_failed(log_id, duration, error_msg, retry_count)

                    # Calculate delay with exponential backoff
                    delay = min(
                        self.initial_delay * (self.backoff_multiplier ** (retry_count - 1)),
                        self.max_delay
                    )
                    logger.info(f"Retrying in {delay:.1f}s... (attempt {retry_count + 1}/{self.max_retries + 1})")
                    time.sleep(delay)
                    start_time = time.time()  # Reset start time for next attempt
                else:
                    self.log_store.log_failed(log_id, duration, error_msg, retry_count)
                    if self.alert_manager:
                        self.alert_manager.error(
                            f"任务失败: {self.task_name}",
                            f"经过 {retry_count} 次重试后仍然失败: {error_msg}"
                        )
                    return None

    def _should_retry(self) -> bool:
        """检查是否应该重试（不超过当日截止时间）"""
        current_hour = datetime.now().hour
        if current_hour >= self.cutoff_hour:
            logger.warning(f"Skip retry: past daily cutoff hour ({self.cutoff_hour}:00)")
            return False
        return True
