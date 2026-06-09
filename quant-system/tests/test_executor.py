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


class TestPositionCalculator:
    """仓位计算测试"""

    def test_calc_weights_signal_strength(self):
        from executor.position_calc import PositionCalculator
        # 用较大的max_single来测试信号强度加权逻辑
        calc = PositionCalculator(total_ratio=0.8, max_single=0.6)
        portfolio = pd.DataFrame({
            "code": ["000001", "000002", "000003"],
            "predicted_return": [0.05, 0.03, 0.02],
        })
        prices = pd.DataFrame({
            "code": ["000001", "000002", "000003"],
            "close": [10.0, 20.0, 15.0],
        })
        result = calc.calc_weights(portfolio, prices, total_capital=100000)
        assert len(result) == 3
        assert "weight" in result.columns
        assert "shares" in result.columns
        # 信号强度加权: 0.05/(0.05+0.03+0.02) = 0.5
        assert abs(result.iloc[0]["weight"] - 0.5) < 0.01

    def test_calc_weights_max_single_limit(self):
        from executor.position_calc import PositionCalculator
        calc = PositionCalculator(total_ratio=0.8, max_single=0.1)
        portfolio = pd.DataFrame({
            "code": ["000001", "000002"],
            "predicted_return": [0.20, 0.01],  # 000001占比95%
        })
        prices = pd.DataFrame({
            "code": ["000001", "000002"],
            "close": [10.0, 20.0],
        })
        result = calc.calc_weights(portfolio, prices, total_capital=100000)
        assert result.iloc[0]["weight"] <= 0.1

    def test_calc_weights_empty_portfolio(self):
        from executor.position_calc import PositionCalculator
        calc = PositionCalculator()
        result = calc.calc_weights(pd.DataFrame(), pd.DataFrame(), 100000)
        assert result.empty


class TestOrderManager:
    """订单管理测试"""

    def _setup_test_price(self, db, code, date, price):
        """插入测试价格数据"""
        df = pd.DataFrame({
            "code": [code],
            "date": [date],
            "open": [price],
            "high": [price],
            "low": [price],
            "close": [price],
            "volume": [1000000],
            "turnover": [1000000 * price],
            "change_pct": [0.0],
            "turnover_rate": [0.01],
        })
        df["date"] = pd.to_datetime(df["date"]).dt.date
        db.conn.execute("INSERT INTO daily_quote SELECT * FROM df")

    def test_generate_orders_new_position(self):
        from executor.order_manager import OrderManager
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()
        self._setup_test_price(db, "000001", "2024-01-31", 10.0)
        order_manager = OrderManager(db, price_offset=0.02)

        target = pd.DataFrame({
            "code": ["000001"],
            "shares": [1000],
            "weight": [1.0],
        })
        current = pd.DataFrame()  # 无持仓

        orders = order_manager.generate_orders(target, current, "2024-01-31")

        assert len(orders) == 1
        assert orders.iloc[0]["action"] == "buy"
        assert orders.iloc[0]["shares"] == 1000
        assert "order_id" in orders.columns

    def test_generate_orders_add_position(self):
        from executor.order_manager import OrderManager
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()
        self._setup_test_price(db, "000001", "2024-01-31", 10.0)
        order_manager = OrderManager(db, price_offset=0.02)

        target = pd.DataFrame({"code": ["000001"], "shares": [2000], "weight": [1.0]})
        current = pd.DataFrame({"code": ["000001"], "shares": [1000]})

        orders = order_manager.generate_orders(target, current, "2024-01-31")

        assert len(orders) == 1
        assert orders.iloc[0]["action"] == "buy"
        assert orders.iloc[0]["shares"] == 1000  # 加仓1000

    def test_generate_orders_reduce_position(self):
        from executor.order_manager import OrderManager
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()
        self._setup_test_price(db, "000001", "2024-01-31", 10.0)
        order_manager = OrderManager(db, price_offset=0.02)

        target = pd.DataFrame({"code": ["000001"], "shares": [500], "weight": [0.5]})
        current = pd.DataFrame({"code": ["000001"], "shares": [1500]})

        orders = order_manager.generate_orders(target, current, "2024-01-31")

        assert len(orders) == 1
        assert orders.iloc[0]["action"] == "sell"
        assert orders.iloc[0]["shares"] == 1000  # 减仓1000

    def test_generate_orders_close_position(self):
        from executor.order_manager import OrderManager
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()
        self._setup_test_price(db, "000001", "2024-01-31", 10.0)
        order_manager = OrderManager(db, price_offset=0.02)

        target = pd.DataFrame()  # 清仓
        current = pd.DataFrame({"code": ["000001"], "shares": [1000]})

        orders = order_manager.generate_orders(target, current, "2024-01-31")

        assert len(orders) == 1
        assert orders.iloc[0]["action"] == "sell"
        assert orders.iloc[0]["shares"] == 1000


class TestTradeLogger:
    """交易记录测试"""

    def test_log_orders(self):
        from executor.trade_log import TradeLogger
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()
        logger = TradeLogger(db)

        orders = pd.DataFrame({
            "order_id": ["o1", "o2"],
            "code": ["000001", "000002"],
            "action": ["buy", "sell"],
            "shares": [1000, 500],
            "price": [10.0, 20.0],
            "status": ["pending", "pending"],
        })
        date = "2024-01-31"

        logger.log_orders(orders, date)

        result = db.query("SELECT * FROM order_log")
        assert len(result) == 2
        assert result.iloc[0]["order_id"] == "o1"

    def test_log_positions(self):
        from executor.trade_log import TradeLogger
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()
        logger = TradeLogger(db)

        positions = pd.DataFrame({
            "code": ["000001", "000002"],
            "shares": [1000, 500],
            "weight": [0.6, 0.4],
        })
        date = "2024-01-31"

        logger.log_positions(positions, date)

        result = db.query("SELECT * FROM position_log")
        assert len(result) == 2
        assert result.iloc[0]["code"] == "000001"
        assert result.iloc[0]["shares"] == 1000

    def test_get_latest_positions(self):
        from executor.trade_log import TradeLogger
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()
        logger = TradeLogger(db)

        # 插入两天的持仓
        for date in ["2024-01-30", "2024-01-31"]:
            positions = pd.DataFrame({
                "code": ["000001"],
                "shares": [1000 if date == "2024-01-31" else 500],
                "weight": [1.0],
            })
            logger.log_positions(positions, date)

        latest = logger.get_latest_positions()
        assert len(latest) == 1
        assert latest.iloc[0]["shares"] == 1000  # 最新持仓


class TestSimulatedBroker:
    """模拟 Broker 测试"""

    def test_buy_updates_position(self):
        from executor.broker import SimulatedBroker

        broker = SimulatedBroker()
        broker.connect()

        order_id = broker.buy("000001", 1000, 10.0)
        positions = broker.query_positions()

        assert len(positions) == 1
        assert positions.iloc[0]["code"] == "000001"
        assert positions.iloc[0]["shares"] == 1000
        assert broker.query_order_status(order_id) == "filled"

    def test_sell_reduces_position(self):
        from executor.broker import SimulatedBroker

        broker = SimulatedBroker()
        broker.connect()

        broker.buy("000001", 1000, 10.0)
        broker.sell("000001", 400, 10.5)

        positions = broker.query_positions()
        assert positions.iloc[0]["shares"] == 600

    def test_sell_all_closes_position(self):
        from executor.broker import SimulatedBroker

        broker = SimulatedBroker()
        broker.connect()

        broker.buy("000001", 1000, 10.0)
        broker.sell("000001", 1000, 10.5)

        positions = broker.query_positions()
        assert len(positions) == 0

    def test_execute_orders_batch(self):
        from executor.broker import SimulatedBroker

        broker = SimulatedBroker()
        broker.connect()

        orders = pd.DataFrame([
            {"order_id": "o1", "code": "000001", "action": "buy", "shares": 1000, "price": 10.0},
            {"order_id": "o2", "code": "000002", "action": "buy", "shares": 500, "price": 20.0},
        ])

        trades = broker.execute_orders(orders)

        assert len(trades) == 2
        positions = broker.query_positions()
        assert len(positions) == 2


class TestRebalancer:
    """调仓主流程集成测试"""

    def test_full_rebalance_flow(self):
        from executor.rebalance import Rebalancer
        from executor.broker import SimulatedBroker
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()
        broker = SimulatedBroker()
        broker.connect()

        # 插入测试价格数据
        for code in ["000001", "000002", "000003"]:
            df = pd.DataFrame({
                "code": [code],
                "date": ["2024-01-31"],
                "open": [10.0],
                "high": [10.0],
                "low": [10.0],
                "close": [10.0],
                "volume": [1000000],
                "turnover": [10000000],
                "change_pct": [0.0],
                "turnover_rate": [0.01],
            })
            df["date"] = pd.to_datetime(df["date"]).dt.date
            db.conn.execute("INSERT INTO daily_quote SELECT * FROM df")

        # 插入测试信号
        signals = pd.DataFrame({
            "code": ["000001", "000002", "000003"],
            "date": ["2024-01-31", "2024-01-31", "2024-01-31"],
            "model_name": ["lgbm_v1", "lgbm_v1", "lgbm_v1"],
            "predicted_return": [0.05, 0.03, 0.01],
            "signal": [1, 1, 1],
        })
        signals["date"] = pd.to_datetime(signals["date"]).dt.date
        db.conn.execute("CREATE TABLE ml_signal AS SELECT * FROM signals")

        rebalancer = Rebalancer(db, broker, config={"top_n": 2, "max_single": 0.6})
        result = rebalancer.run("2024-01-31", "lgbm_v1", total_capital=100000)

        assert result["status"] == "completed"
        assert result["signals"] == 3
        assert result["portfolio"] == 2  # Top 2
        assert result["orders"] > 0
        assert result["trades"] > 0

        # 验证持仓已记录
        positions = db.query("SELECT * FROM position_log")
        assert len(positions) == 2