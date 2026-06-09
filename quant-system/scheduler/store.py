"""调度器日志存储"""

import pandas as pd
from datetime import datetime
from loguru import logger


class SchedulerLogStore:
    """调度执行日志存储"""

    def __init__(self, db):
        self.db = db

    def log_start(self, task_name: str) -> int:
        """记录任务开始，返回 log_id"""
        sql = """
            INSERT INTO scheduler_log (task_name, status, start_time)
            VALUES (?, ?, ?)
        """
        self.db.conn.execute(sql, [task_name, "running", datetime.now()])

        # Get last insert id using DuckDB sequence
        result = self.db.query("SELECT currval('scheduler_log_id_seq') as id")
        return int(result.iloc[0]["id"])

    def log_success(self, log_id: int, duration_seconds: float):
        """记录任务成功"""
        sql = """
            UPDATE scheduler_log
            SET status = 'success', end_time = ?, duration_seconds = ?
            WHERE id = ?
        """
        self.db.conn.execute(sql, [datetime.now(), duration_seconds, log_id])
        logger.debug(f"Task {log_id} succeeded in {duration_seconds:.2f}s")

    def log_failed(self, log_id: int, duration_seconds: float, error_message: str, retry_count: int = 0):
        """记录任务失败"""
        sql = """
            UPDATE scheduler_log
            SET status = 'failed', end_time = ?, duration_seconds = ?, error_message = ?, retry_count = ?
            WHERE id = ?
        """
        self.db.conn.execute(sql, [datetime.now(), duration_seconds, error_message, retry_count, log_id])
        logger.error(f"Task {log_id} failed after {duration_seconds:.2f}s: {error_message}")

    def log_skipped(self, task_name: str, reason: str) -> int:
        """记录任务跳过"""
        sql = """
            INSERT INTO scheduler_log (task_name, status, start_time, end_time, error_message)
            VALUES (?, ?, ?, ?, ?)
        """
        now = datetime.now()
        self.db.conn.execute(sql, [task_name, "skipped", now, now, reason])
        logger.debug(f"Task {task_name} skipped: {reason}")

        result = self.db.query("SELECT currval('scheduler_log_id_seq') as id")
        return int(result.iloc[0]["id"])

    def get_recent_logs(self, task_name: str = None, limit: int = 10) -> pd.DataFrame:
        """获取最近的执行日志"""
        if task_name:
            sql = """
                SELECT * FROM scheduler_log
                WHERE task_name = ?
                ORDER BY start_time DESC
                LIMIT ?
            """
            return self.db.query(sql, [task_name, limit])
        else:
            sql = """
                SELECT * FROM scheduler_log
                ORDER BY start_time DESC
                LIMIT ?
            """
            return self.db.query(sql, [limit])
