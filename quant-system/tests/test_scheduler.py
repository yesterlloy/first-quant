import pytest
from data.db.duckdb_manager import DuckDBManager


def test_scheduler_log_table_exists():
    db = DuckDBManager(":memory:")
    db.connect()
    result = db.query("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='main' AND table_name='scheduler_log'
    """)
    assert len(result) == 1
    db.close()


def test_store_log_running():
    from scheduler.store import SchedulerLogStore
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager(":memory:")
    db.connect()
    store = SchedulerLogStore(db)

    log_id = store.log_start("test_task")
    assert log_id > 0

    result = db.query("SELECT * FROM scheduler_log WHERE id = ?", [log_id])
    assert len(result) == 1
    assert result.iloc[0]["task_name"] == "test_task"
    assert result.iloc[0]["status"] == "running"
    db.close()


def test_store_log_success():
    from scheduler.store import SchedulerLogStore
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager(":memory:")
    db.connect()
    store = SchedulerLogStore(db)

    log_id = store.log_start("test_task")
    store.log_success(log_id, duration_seconds=2.5)

    result = db.query("SELECT * FROM scheduler_log WHERE id = ?", [log_id])
    assert result.iloc[0]["status"] == "success"
    assert result.iloc[0]["duration_seconds"] == 2.5
    db.close()


def test_store_log_failed():
    from scheduler.store import SchedulerLogStore
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager(":memory:")
    db.connect()
    store = SchedulerLogStore(db)

    log_id = store.log_start("test_task")
    store.log_failed(log_id, duration_seconds=1.0, error_message="Test error", retry_count=1)

    result = db.query("SELECT * FROM scheduler_log WHERE id = ?", [log_id])
    assert result.iloc[0]["status"] == "failed"
    assert result.iloc[0]["error_message"] == "Test error"
    assert result.iloc[0]["retry_count"] == 1
    db.close()


def test_get_recent_logs():
    from scheduler.store import SchedulerLogStore
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager(":memory:")
    db.connect()
    store = SchedulerLogStore(db)

    for i in range(5):
        log_id = store.log_start(f"task_{i}")
        store.log_success(log_id, duration_seconds=1.0)

    logs = store.get_recent_logs("task_0", limit=3)
    assert len(logs) == 1  # Only 1 task_0 log
    all_logs = store.get_recent_logs(limit=10)
    assert len(all_logs) == 5  # All 5 tasks
    db.close()


def test_task_wrapper_success():
    from scheduler.task_wrapper import TaskWrapper
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager(":memory:")
    db.connect()

    calls = []
    def test_func():
        calls.append(1)
        return "done"

    wrapper = TaskWrapper(db, "test_task", test_func)
    result = wrapper.execute()

    assert result == "done"
    assert len(calls) == 1
    db.close()


def test_task_wrapper_retry_on_failure():
    from scheduler.task_wrapper import TaskWrapper
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager(":memory:")
    db.connect()

    calls = []
    def flaky_func():
        calls.append(1)
        if len(calls) < 3:
            raise Exception(f"Fail attempt {len(calls)}")
        return "success"

    wrapper = TaskWrapper(db, "test_task", flaky_func, max_retries=3, cutoff_hour=23)
    result = wrapper.execute()

    assert result == "success"
    assert len(calls) == 3  # 2 failures + 1 success
    db.close()


def test_task_wrapper_exhaust_retries():
    from scheduler.task_wrapper import TaskWrapper
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager(":memory:")
    db.connect()

    calls = []
    def always_fail():
        calls.append(1)
        raise Exception("Always fails")

    wrapper = TaskWrapper(db, "test_task", always_fail, max_retries=2, cutoff_hour=23)
    result = wrapper.execute()

    assert result is None  # Failed after retries
    assert len(calls) == 3  # 1 original + 2 retries
    db.close()


def test_task_wrapper_logs_to_db():
    from scheduler.task_wrapper import TaskWrapper
    from data.db.duckdb_manager import DuckDBManager

    db = DuckDBManager(":memory:")
    db.connect()

    def success_func():
        return "ok"

    wrapper = TaskWrapper(db, "test_task", success_func)
    wrapper.execute()

    logs = db.query("SELECT * FROM scheduler_log")
    assert len(logs) == 1
    assert logs.iloc[0]["status"] == "success"
    db.close()


def test_load_scheduler_config():
    from config import get_scheduler_config

    config = get_scheduler_config()
    assert "scheduler" in config
    assert "tasks" in config
    assert "data_collection" in config["tasks"]
