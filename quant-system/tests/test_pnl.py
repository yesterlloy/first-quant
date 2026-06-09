"""PnL 盈亏计算测试"""

import pytest
import pandas as pd


class TestPositionPnL:
    """持仓盈亏测试"""

    def test_calculate_position_pnl_profit(self):
        from executor.pnl_calc import PnLCalculator
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()

        # 插入行情数据
        prices = pd.DataFrame([{
            "code": "000001",
            "date": "2024-01-31",
            "open": 11.0,
            "high": 11.0,
            "low": 11.0,
            "close": 11.0,
            "volume": 1000000,
            "turnover": 11000000,
            "change_pct": 0.0,
            "turnover_rate": 0.01,
        }])
        prices["date"] = pd.to_datetime(prices["date"]).dt.date
        db.conn.execute("INSERT INTO daily_quote SELECT * FROM prices")

        # 插入持仓（成本10元，现价11元）
        positions = pd.DataFrame([{
            "code": "000001",
            "shares": 1000,
            "weight": 1.0,
            "cost_price": 10.0,
            "current_price": 11.0,
            "market_value": 11000.0,
        }])
        from executor.trade_log import TradeLogger
        logger = TradeLogger(db)
        logger.log_positions(positions, "2024-01-31")

        calc = PnLCalculator(db)
        pnl = calc.calculate_position_pnl("000001", "2024-01-31")

        assert pnl is not None
        assert pnl.code == "000001"
        assert pnl.shares == 1000
        assert pnl.cost_price == 10.0
        assert pnl.current_price == 11.0
        assert pnl.unrealized_pnl == 1000.0  # 1元 * 1000股
        assert abs(pnl.unrealized_pnl_pct - 10.0) < 0.01  # 10% 盈利

    def test_calculate_position_pnl_loss(self):
        from executor.pnl_calc import PnLCalculator
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()

        # 插入行情数据
        prices = pd.DataFrame([{
            "code": "000001",
            "date": "2024-01-31",
            "open": 9.0,
            "high": 9.0,
            "low": 9.0,
            "close": 9.0,
            "volume": 1000000,
            "turnover": 9000000,
            "change_pct": -0.1,
            "turnover_rate": 0.01,
        }])
        prices["date"] = pd.to_datetime(prices["date"]).dt.date
        db.conn.execute("INSERT INTO daily_quote SELECT * FROM prices")

        # 插入持仓（成本10元，现价9元）
        positions = pd.DataFrame([{
            "code": "000001",
            "shares": 1000,
            "weight": 1.0,
            "cost_price": 10.0,
            "current_price": 9.0,
            "market_value": 9000.0,
        }])
        from executor.trade_log import TradeLogger
        logger = TradeLogger(db)
        logger.log_positions(positions, "2024-01-31")

        calc = PnLCalculator(db)
        pnl = calc.calculate_position_pnl("000001", "2024-01-31")

        assert pnl is not None
        assert pnl.unrealized_pnl == -1000.0  # 浮亏1000
        assert abs(pnl.unrealized_pnl_pct + 10.0) < 0.01  # -10%

    def test_calculate_position_pnl_missing_price(self):
        from executor.pnl_calc import PnLCalculator
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()

        # 持仓中的 current_price 为0，从行情表获取
        positions = pd.DataFrame([{
            "code": "000001",
            "shares": 1000,
            "weight": 1.0,
            "cost_price": 10.0,
            "current_price": 0.0,  # 没有价格
            "market_value": 0.0,
        }])
        from executor.trade_log import TradeLogger
        logger = TradeLogger(db)
        logger.log_positions(positions, "2024-01-31")

        # 插入行情数据
        prices = pd.DataFrame([{
            "code": "000001",
            "date": "2024-01-31",
            "open": 11.0,
            "high": 11.0,
            "low": 11.0,
            "close": 11.0,
            "volume": 1000000,
            "turnover": 11000000,
            "change_pct": 0.0,
            "turnover_rate": 0.01,
        }])
        prices["date"] = pd.to_datetime(prices["date"]).dt.date
        db.conn.execute("INSERT INTO daily_quote SELECT * FROM prices")

        calc = PnLCalculator(db)
        pnl = calc.calculate_position_pnl("000001", "2024-01-31")

        assert pnl is not None
        assert pnl.current_price == 11.0  # 从行情表获取


class TestPortfolioPnL:
    """组合盈亏测试"""

    def test_calculate_portfolio_pnl(self):
        from executor.pnl_calc import PnLCalculator
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()

        # 插入行情数据
        prices = pd.DataFrame([
            {"code": "000001", "date": "2024-01-31", "open": 11.0, "high": 11.0, "low": 11.0, "close": 11.0, "volume": 1000000, "turnover": 11000000, "change_pct": 0.0, "turnover_rate": 0.01},
            {"code": "000002", "date": "2024-01-31", "open": 25.0, "high": 25.0, "low": 25.0, "close": 25.0, "volume": 1000000, "turnover": 25000000, "change_pct": 0.0, "turnover_rate": 0.01},
        ])
        prices["date"] = pd.to_datetime(prices["date"]).dt.date
        db.conn.execute("INSERT INTO daily_quote SELECT * FROM prices")

        # 插入持仓
        positions = pd.DataFrame([
            {"code": "000001", "shares": 1000, "weight": 0.5, "cost_price": 10.0, "current_price": 11.0, "market_value": 11000.0},
            {"code": "000002", "shares": 500, "weight": 0.5, "cost_price": 20.0, "current_price": 25.0, "market_value": 12500.0},
        ])
        from executor.trade_log import TradeLogger
        logger = TradeLogger(db)
        logger.log_positions(positions, "2024-01-31")

        calc = PnLCalculator(db)
        result = calc.calculate_portfolio_pnl("2024-01-31")

        assert result["position_count"] == 2
        assert result["total_market_value"] == 23500.0  # 11000 + 12500
        # 000001 盈利1000, 000002 盈利2500，总成本 10*1000+20*500 = 20000
        assert result["total_unrealized_pnl"] == 3500.0
        assert abs(result["total_unrealized_pnl_pct"] - 17.5) < 0.01  # 3500/20000 = 17.5%

    def test_empty_portfolio_returns_zero(self):
        from executor.pnl_calc import PnLCalculator
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()

        calc = PnLCalculator(db)
        result = calc.calculate_portfolio_pnl("2024-01-31")

        assert result["position_count"] == 0
        assert result["total_market_value"] == 0.0


class TestPortfolioMetrics:
    """组合风险指标测试"""

    def test_get_equity_curve(self):
        from executor.pnl_calc import PnLCalculator
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()

        # 插入多日持仓
        dates = ["2024-01-29", "2024-01-30", "2024-01-31"]
        from executor.trade_log import TradeLogger
        logger = TradeLogger(db)

        for i, date in enumerate(dates):
            positions = pd.DataFrame([{
                "code": "000001",
                "shares": 1000,
                "weight": 1.0,
                "cost_price": 10.0,
                "current_price": 10.0 + i,
                "market_value": 1000 * (10.0 + i),
            }])
            logger.log_positions(positions, date)

        calc = PnLCalculator(db)
        curve = calc.get_portfolio_equity_curve("2024-01-29", "2024-01-31")

        assert len(curve) == 3
        assert "date" in curve.columns
        assert "equity" in curve.columns
        assert "return" in curve.columns

    def test_calculate_metrics(self):
        from executor.pnl_calc import PnLCalculator
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()

        # 插入多日持仓模拟净值增长
        from executor.trade_log import TradeLogger
        logger = TradeLogger(db)

        # 连续10天，每天涨1%
        for i in range(10):
            date = f"2024-01-{i+1:02d}"
            price = 10.0 * (1.01 ** i)
            positions = pd.DataFrame([{
                "code": "000001",
                "shares": 1000,
                "weight": 1.0,
                "cost_price": 10.0,
                "current_price": price,
                "market_value": 1000 * price,
            }])
            logger.log_positions(positions, date)

        calc = PnLCalculator(db)
        metrics = calc.calculate_metrics("2024-01-01", "2024-01-10")

        assert metrics.total_return > 0  # 正收益
        assert metrics.total_trades == 0  # 没有交易记录


class TestDailyReport:
    """日报测试"""

    def test_generate_daily_report(self):
        from executor.pnl_calc import PnLCalculator
        from data.db.duckdb_manager import DuckDBManager

        db = DuckDBManager(":memory:")
        db.connect()

        # 插入持仓
        positions = pd.DataFrame([{
            "code": "000001",
            "shares": 1000,
            "weight": 1.0,
            "cost_price": 10.0,
            "current_price": 11.0,
            "market_value": 11000.0,
        }])
        from executor.trade_log import TradeLogger
        logger = TradeLogger(db)
        logger.log_positions(positions, "2024-01-31")

        calc = PnLCalculator(db)
        report = calc.generate_daily_report("2024-01-31")

        assert "交易日报" in report
        assert "持仓数量" in report
        assert "总市值" in report
        assert "浮动盈亏" in report
