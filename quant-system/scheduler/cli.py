"""命令行接口"""

import argparse
from loguru import logger


def run_scheduler(args):
    """启动调度器"""
    from data.db.duckdb_manager import DuckDBManager
    from scheduler.engine import QuantScheduler
    from scheduler.tasks import (
        data_collection_task,
        factor_compute_task,
        monthly_rebalance_task,
        daily_report_task,
        data_validation_task
    )
    from risk import AlertManager

    db = DuckDBManager()
    db.connect()

    # Initialize alert manager
    alert_mgr = AlertManager.from_config("config/alarm.yaml")

    scheduler = QuantScheduler(db, alert_manager=alert_mgr)

    # Register all enabled tasks from config
    from config import get_scheduler_config
    config = get_scheduler_config()
    tasks_config = config.get("tasks", {})

    # Data collection
    if tasks_config.get("data_collection", {}).get("enabled", True):
        scheduler.register_task(
            "data_collection",
            lambda: data_collection_task(db),
            cron=tasks_config["data_collection"].get("cron", "0 18 * * 1-5"),
            timeout=tasks_config["data_collection"].get("timeout", 300),
            retry=tasks_config["data_collection"].get("retry", True)
        )

    # Factor compute
    if tasks_config.get("factor_compute", {}).get("enabled", True):
        scheduler.register_task(
            "factor_compute",
            lambda: factor_compute_task(db),
            cron=tasks_config["factor_compute"].get("cron", "0 19 * * 1-5"),
            timeout=tasks_config["factor_compute"].get("timeout", 600),
            retry=tasks_config["factor_compute"].get("retry", True),
            depends_on=tasks_config["factor_compute"].get("depends_on", [])
        )

    # Monthly rebalance (default disabled)
    if tasks_config.get("monthly_rebalance", {}).get("enabled", False):
        scheduler.register_task(
            "monthly_rebalance",
            lambda: monthly_rebalance_task(db),
            cron=tasks_config["monthly_rebalance"].get("cron", "0 14 L * *"),
            timeout=tasks_config["monthly_rebalance"].get("timeout", 1200),
            retry=tasks_config["monthly_rebalance"].get("retry", False)
        )

    # Daily report
    if tasks_config.get("daily_report", {}).get("enabled", True):
        scheduler.register_task(
            "daily_report",
            lambda: daily_report_task(db),
            cron=tasks_config["daily_report"].get("cron", "30 18 * * 1-5"),
            timeout=tasks_config["daily_report"].get("timeout", 60),
            retry=tasks_config["daily_report"].get("retry", False)
        )

    # Data validation (optional)
    if tasks_config.get("data_validation", {}).get("enabled", False):
        scheduler.register_task(
            "data_validation",
            lambda: data_validation_task(db),
            cron=tasks_config["data_validation"].get("cron", "0 19 * * 1-5"),
            timeout=tasks_config["data_validation"].get("timeout", 300),
            retry=tasks_config["data_validation"].get("retry", False)
        )

    logger.info("Scheduler configured. Press Ctrl+C to stop.")
    scheduler.start()


def trigger_task(args):
    """手动触发任务"""
    task_name = args.task

    from data.db.duckdb_manager import DuckDBManager
    from scheduler.engine import QuantScheduler
    from scheduler.tasks import (
        data_collection_task,
        factor_compute_task,
        monthly_rebalance_task,
        daily_report_task,
        data_validation_task
    )

    db = DuckDBManager()
    db.connect()

    scheduler = QuantScheduler(db)

    # Register task temporarily
    task_map = {
        "data_collection": lambda: data_collection_task(db),
        "factor_compute": lambda: factor_compute_task(db),
        "monthly_rebalance": lambda: monthly_rebalance_task(db),
        "daily_report": lambda: daily_report_task(db),
        "data_validation": lambda: data_validation_task(db),
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

    db.close()
    return success


def show_status(args):
    """显示任务最近执行状态"""
    task_name = args.task

    from data.db.duckdb_manager import DuckDBManager
    from scheduler.store import SchedulerLogStore

    db = DuckDBManager()
    db.connect()

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
            "success": "\033[92m",    # Green
            "failed": "\033[91m",     # Red
            "running": "\033[93m",     # Yellow
            "skipped": "\033[90m",     # Gray
        }.get(row["status"], "")

        status_str = f"{status_color}{row['status']:<10}\033[0m"
        duration = f"{row['duration_seconds']:.2f}" if row["duration_seconds"] else "N/A"
        retries = str(int(row["retry_count"])) if row["retry_count"] else "0"

        print(f"{row['task_name']:<20} {status_str} {str(row['start_time']):<25} {duration:<12} {retries:<8}")

    print()
    db.close()


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="Quant System Scheduler")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'start' command
    start_parser = subparsers.add_parser("start", help="Start the scheduler")

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
