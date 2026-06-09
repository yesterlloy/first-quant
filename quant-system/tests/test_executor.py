"""交易执行模块测试"""

import pytest
import pandas as pd
from data.db.duckdb_manager import DuckDBManager


class TestExecutorTables:
    """交易记录表测试"""

    def test_order_log_table_exists(self):
        db = DuckDBManager(":memory:")
        db.connect()
        result = db.query("SELECT * FROM information_schema.tables WHERE table_name='order_log'")
        assert len(result) == 1
        db.close()

    def test_trade_log_table_exists(self):
        db = DuckDBManager(":memory:")
        db.connect()
        result = db.query("SELECT * FROM information_schema.tables WHERE table_name='trade_log'")
        assert len(result) == 1
        db.close()

    def test_position_log_table_exists(self):
        db = DuckDBManager(":memory:")
        db.connect()
        result = db.query("SELECT * FROM information_schema.tables WHERE table_name='position_log'")
        assert len(result) == 1
        db.close()