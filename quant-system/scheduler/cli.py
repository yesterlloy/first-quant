"""命令行接口

设计原则：
- 调度器不持久持有数据库连接
- 每次任务执行时建立连接，执行完立即关闭
- 避免与Dashboard等其他进程发生DuckDB锁冲突
"""

import argparse
from loguru import logger


def run_scheduler(args):
    """启动调度器"""
    from scheduler.engine import QuantScheduler
    from scheduler.tasks import (
        data_collection_task,
        factor_compute_task,
        monthly_rebalance_task,
        daily_report_task,
        data_validation_task,
        db_backup_task
    )
    from risk import AlertManager

    # Initialize alert manager
    alert_mgr = AlertManager.from_config("config/alarm.yaml")

    # Create scheduler (connectionless mode)
    scheduler = QuantScheduler(db_path="data/db/quant.duckdb", alert_manager=alert_mgr)

    # Register all enabled tasks from config
    from config import get_scheduler_config
    config = get_scheduler_config()
    tasks_config = config.get("tasks", {})

    # Data collection
    if tasks_config.get("data_collection", {}).get("enabled", True):
        scheduler.register_task(
            "data_collection",
            data_collection_task,
            cron=tasks_config["data_collection"].get("cron", "0 18 * * 1-5"),
            timeout=tasks_config["data_collection"].get("timeout", 300),
            retry=tasks_config["data_collection"].get("retry", True)
        )

    # Factor compute
    if tasks_config.get("factor_compute", {}).get("enabled", True):
        scheduler.register_task(
            "factor_compute",
            factor_compute_task,
            cron=tasks_config["factor_compute"].get("cron", "0 19 * * 1-5"),
            timeout=tasks_config["factor_compute"].get("timeout", 600),
            retry=tasks_config["factor_compute"].get("retry", True),
            depends_on=tasks_config["factor_compute"].get("depends_on", [])
        )

    # Monthly rebalance (default disabled)
    if tasks_config.get("monthly_rebalance", {}).get("enabled", False):
        scheduler.register_task(
            "monthly_rebalance",
            monthly_rebalance_task,
            cron=tasks_config["monthly_rebalance"].get("cron", "0 14 L * *"),
            timeout=tasks_config["monthly_rebalance"].get("timeout", 1200),
            retry=tasks_config["monthly_rebalance"].get("retry", False)
        )

    # Daily report
    if tasks_config.get("daily_report", {}).get("enabled", True):
        scheduler.register_task(
            "daily_report",
            daily_report_task,
            cron=tasks_config["daily_report"].get("cron", "30 18 * * 1-5"),
            timeout=tasks_config["daily_report"].get("timeout", 60),
            retry=tasks_config["daily_report"].get("retry", False)
        )

    # Data validation (optional)
    if tasks_config.get("data_validation", {}).get("enabled", False):
        scheduler.register_task(
            "data_validation",
            data_validation_task,
            cron=tasks_config["data_validation"].get("cron", "0 19 * * 1-5"),
            timeout=tasks_config["data_validation"].get("timeout", 300),
            retry=tasks_config["data_validation"].get("retry", False)
        )

    # Database backup (daily)
    if tasks_config.get("db_backup", {}).get("enabled", True):
        scheduler.register_task(
            "db_backup",
            db_backup_task,
            cron=tasks_config["db_backup"].get("cron", "0 23 * * *"),
            timeout=tasks_config["db_backup"].get("timeout", 300),
            retry=tasks_config["db_backup"].get("retry", False)
        )

    logger.info("Scheduler configured. Press Ctrl+C to stop.")
    scheduler.start()


def trigger_task(args):
    """手动触发任务"""
    task_name = args.task

    from scheduler.engine import QuantScheduler
    from scheduler.tasks import (
        data_collection_task,
        factor_compute_task,
        monthly_rebalance_task,
        daily_report_task,
        data_validation_task,
        db_backup_task
    )

    scheduler = QuantScheduler(db_path="data/db/quant.duckdb")

    # Register task temporarily
    task_map = {
        "data_collection": data_collection_task,
        "factor_compute": factor_compute_task,
        "monthly_rebalance": monthly_rebalance_task,
        "daily_report": daily_report_task,
        "data_validation": data_validation_task,
        "db_backup": db_backup_task,
    }

    if task_name not in task_map:
        logger.error(f"Unknown task: {task_name}")
        print(f"Available tasks: {list(task_map.keys())}")
        return False

    scheduler.register_task(task_name, task_map[task_name])
    success = scheduler.trigger_task(task_name)

    if success:
        logger.info(f"Task {task_name} executed successfully")
    else:
        logger.error(f"Task {task_name} failed")

    return success


def show_status(args):
    """显示任务最近执行状态"""
    task_name = args.task

    from scheduler.store import SchedulerLogStore
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager("data/db/quant.duckdb", read_only=True)
    db.connect()

    try:
        store = SchedulerLogStore(db)
        logs = store.get_recent_logs(task_name, limit=args.limit)

        if logs.empty:
            print(f"No logs found for task: {task_name or 'all tasks'}")
            return

        print(f"\n===== Task Execution Status: {task_name or 'All Tasks'} =====\n")
        print(f"{'Task':<20} {'Status':<10} {'Start Time':<25} {'Duration(s)':<12} {'Retries':<8}")
        print("-" * 85)

        for _, row in logs.iterrows():
            status_color = {
                "success": "✓",
                "failed": "✗",
                "running": "⚡",
                "skipped": "⊘",
            }.get(row["status"], "?")

            duration = f"{row['duration_seconds']:.2f}" if row["duration_seconds"] else "N/A"
            retries = str(int(row["retry_count"])) if row["retry_count"] else "0"

            print(f"{row['task_name']:<20} {status_color} {row['status']:<8} {str(row['start_time']):<25} {duration:<12} {retries:<8}")

        print()
    finally:
        db.close()


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="Quant System Scheduler")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'start' command
    subparsers.add_parser("start", help="Start the scheduler")

    # 'trigger' command
    trigger_parser = subparsers.add_parser("trigger", help="Manually trigger a task")
    trigger_parser.add_argument("task", help="Task name to trigger")

    # 'status' command
    status_parser = subparsers.add_parser("status", help="Show task execution status")
    status_parser.add_argument("--task", help="Filter by task name", default=None)
    status_parser.add_argument("--limit", type=int, default=10, help="Number of logs to show")

    args = parser.parse_args()

    if args.command == "start":
        run_scheduler(args)
    elif args.command == "trigger":
        trigger_task(args)
    elif args.command == "status":
        show_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
