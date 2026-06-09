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


class TestSignalLoader:
    """信号加载测试"""

    def test_load_signals_success(self):
        from executor.signal_loader import SignalLoader

        db = DuckDBManager(":memory:")
        db.connect()

        # 插入测试信号
        df = pd.DataFrame({
            "code": ["000001", "000002", "000003"],
            "date": ["2024-01-31", "2024-01-31", "2024-01-31"],
            "model_name": ["lgbm_v1", "lgbm_v1", "lgbm_v1"],
            "predicted_return": [0.05, 0.03, 0.01],
            "signal": [1, 1, 0],
        })
        df["date"] = pd.to_datetime(df["date"]).dt.date
        db.conn.execute("CREATE TABLE ml_signal AS SELECT * FROM df")

        loader = SignalLoader(db)
        result = loader.load_signals("2024-01-31", "lgbm_v1")

        assert len(result) == 3
        assert "code" in result.columns
        assert "predicted_return" in result.columns
        db.close()

    def test_load_signals_empty(self):
        from executor.signal_loader import SignalLoader

        db = DuckDBManager(":memory:")
        db.connect()
        db.conn.execute("""
            CREATE TABLE ml_signal (
                code VARCHAR,
                date DATE,
                model_name VARCHAR,
                predicted_return DOUBLE,
                signal INTEGER
            )
        """)

        loader = SignalLoader(db)
        result = loader.load_signals("2024-01-31", "lgbm_v1")

        assert result.empty
        db.close()


class TestPortfolioBuilder:
    """组合构建测试"""

    def test_build_portfolio_top10(self):
        from executor.portfolio_builder import PortfolioBuilder

        builder = PortfolioBuilder(top_n=10)

        # 15只股票信号
        signals = pd.DataFrame({
            "code": [f"00000{i}" for i in range(15)],
            "predicted_return": [0.10 - i * 0.005 for i in range(15)],
            "signal": [1] * 15,
        })

        result = builder.build_portfolio(signals)

        assert len(result) == 10
        assert result.iloc[0]["code"] == "000000"  # 最高收益
        assert "rank" in result.columns

    def test_build_portfolio_empty_input(self):
        from executor.portfolio_builder import PortfolioBuilder

        builder = PortfolioBuilder(top_n=10)
        result = builder.build_portfolio(pd.DataFrame())

        assert result.empty