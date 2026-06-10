"""任务依赖管理 - 处理任务间的依赖关系"""

import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from loguru import logger


class DependencyTracker:
    """任务依赖跟踪器

    记录任务执行状态，管理任务之间的依赖关系
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._task_success: Dict[str, datetime] = {}  # task_name -> success_time
        self._task_failed: Dict[str, datetime] = {}   # task_name -> fail_time
        self._dependencies: Dict[str, List[str]] = {}  # task_name -> [dependencies]

    def register_dependency(self, task_name: str, depends_on: List[str]):
        """注册任务依赖关系"""
        with self._lock:
            self._dependencies[task_name] = depends_on
            logger.info(f"Task {task_name} depends on: {depends_on}")

    def mark_success(self, task_name: str):
        """标记任务执行成功"""
        with self._lock:
            self._task_success[task_name] = datetime.now()
            self._task_failed.pop(task_name, None)

    def mark_failed(self, task_name: str):
        """标记任务执行失败"""
        with self._lock:
            self._task_failed[task_name] = datetime.now()

    def check_dependencies(self, task_name: str) -> tuple[bool, List[str]]:
        """检查任务的依赖是否都满足

        Returns:
            (all_satisfied, missing_dependencies)
        """
        with self._lock:
            dependencies = self._dependencies.get(task_name, [])
            if not dependencies:
                return True, []

            missing = []
            for dep in dependencies:
                if not self._is_dependency_satisfied(dep):
                    missing.append(dep)

            return len(missing) == 0, missing

    def _is_dependency_satisfied(self, dep_name: str) -> bool:
        """检查单个依赖是否满足（已在今日成功执行）"""
        if dep_name not in self._task_success:
            return False

        success_time = self._task_success[dep_name]
        now = datetime.now()

        # 检查是否是今天执行的（允许跨天的情况，比如凌晨执行）
        today = now.date()
        success_date = success_time.date()

        # 如果是今天执行的，或者是昨天很晚执行的（跨天场景）
        if success_date == today:
            return True
        if success_date == today - timedelta(days=1) and success_time.hour >= 20:
            return True

        return False

    def clear_old_records(self, hours: int = 24):
        """清理旧的执行记录"""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._lock:
            for task_name in list(self._task_success.keys()):
                if self._task_success[task_name] < cutoff:
                    del self._task_success[task_name]
            for task_name in list(self._task_failed.keys()):
                if self._task_failed[task_name] < cutoff:
                    del self._task_failed[task_name]


# 全局单例
_dependency_tracker = DependencyTracker()


def get_dependency_tracker() -> DependencyTracker:
    """获取全局依赖跟踪器实例"""
    return _dependency_tracker
