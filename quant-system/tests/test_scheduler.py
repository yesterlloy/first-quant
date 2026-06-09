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
