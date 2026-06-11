"""任务包装器 - 统一处理重试、日志、异常"""

import time
import traceback
import threading
from datetime import datetime
from loguru import logger
from .store import SchedulerLogStore


class TaskWrapper:
    """任务包装器

    包装实际任务函数，提供：
    - 执行日志记录
    - 指数退避重试
    - 异常捕获与告警
    - 超时控制
    - 当日截止时间（避免跨日数据）
    """

    def __init__(self, db, task_name: str, func,
                 max_retries: int = 3,
                 initial_delay: float = 1.0,
                 max_delay: float = 8.0,
                 backoff_multiplier: float = 2.0,
                 cutoff_hour: int = 18,
                 timeout: int = 300,
                 alert_manager = None):
        self.db = db
        self.task_name = task_name
        self.func = func
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.cutoff_hour = cutoff_hour
        self.timeout = timeout
        self.alert_manager = alert_manager
        self.log_store = SchedulerLogStore(db)

    def execute(self, *args, **kwargs):
        """执行任务（带交易日检查、依赖检查、重试和超时）"""
        from .dependency import get_dependency_tracker
        dep_tracker = get_dependency_tracker()
        from .calendar import TradeCalendar

        # Check if today is a trade day
        cal = TradeCalendar(self.db)
        if not cal.is_trade_day():
            logger.info(f"Task {self.task_name} skipped - not a trade day")
            self.log_store.log_skipped(self.task_name, reason="Not a trade day")
            return None

        # Check dependencies
        deps_ok, missing = dep_tracker.check_dependencies(self.task_name)
        if not deps_ok:
            logger.warning(f"Task {self.task_name} skipped - dependencies not satisfied: {missing}")
            self.log_store.log_skipped(self.task_name, reason=f"Dependencies not met: {missing}")
            return None

        retry_count = 0
        start_time = time.time()

        while retry_count <= self.max_retries:
            log_id = self.log_store.log_start(self.task_name)

            try:
                result = self._execute_with_timeout(*args, **kwargs)
                duration = time.time() - start_time
                self.log_store.log_success(log_id, duration)
                dep_tracker.mark_success(self.task_name)
                logger.info(f"Task {self.task_name} succeeded in {duration:.2f}s")
                return result

            except TimeoutError as e:
                duration = time.time() - start_time
                error_msg = f"Task timed out after {self.timeout}s"
                logger.error(f"Task {self.task_name} timeout (attempt {retry_count + 1}): {error_msg}")

                if retry_count < self.max_retries and self._should_retry():
                    retry_count += 1
                    self.log_store.log_failed(log_id, duration, error_msg, retry_count)
                    delay = min(
                        self.initial_delay * (self.backoff_multiplier ** (retry_count - 1)),
                        self.max_delay
                    )
                    logger.info(f"Retrying in {delay:.1f}s... (attempt {retry_count + 1}/{self.max_retries + 1})")
                    time.sleep(delay)
                    start_time = time.time()
                else:
                    self.log_store.log_failed(log_id, duration, error_msg, retry_count)
                    dep_tracker.mark_failed(self.task_name)
                    if self.alert_manager:
                        self.alert_manager.error(
                            f"任务超时: {self.task_name}",
                            f"任务执行超过 {self.timeout} 秒超时"
                        )
                    return None

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
                    dep_tracker.mark_failed(self.task_name)
                    if self.alert_manager:
                        self.alert_manager.error(
                            f"任务失败: {self.task_name}",
                            f"经过 {retry_count} 次重试后仍然失败: {error_msg}"
                        )
                    return None

    def _execute_with_timeout(self, *args, **kwargs):
        """带超时控制的任务执行"""
        import inspect

        result_container = []
        exception_container = []

        def target():
            try:
                # 智能判断：检查函数签名
                sig = inspect.signature(self.func)
                params = list(sig.parameters.keys())

                # 如果函数接受参数，传递db；否则直接调用
                if len(params) > 0:
                    result_container.append(self.func(self.db, *args, **kwargs))
                else:
                    result_container.append(self.func(*args, **kwargs))
            except Exception as e:
                exception_container.append(e)

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            raise TimeoutError(f"Task execution exceeded {self.timeout} seconds")

        if exception_container:
            raise exception_container[0]

        return result_container[0] if result_container else None

    def _should_retry(self) -> bool:
        """检查是否应该重试（不超过当日截止时间）"""
        current_hour = datetime.now().hour
        if current_hour >= self.cutoff_hour:
            logger.warning(f"Skip retry: past daily cutoff hour ({self.cutoff_hour}:00)")
            return False
        return True
