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
