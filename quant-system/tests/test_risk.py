"""风控模块测试"""

import pytest
import pandas as pd
from data.db.duckdb_manager import DuckDBManager


class TestSinglePositionLimit:
    """单票仓位上限测试"""

    def test_position_within_limit_passes(self):
        from risk.rules import SinglePositionLimit

        rule = SinglePositionLimit(max_ratio=0.1)
        context = {"target_weight": 0.08, "code": "000001"}
        result = rule.check(context)

        assert result.passed is True
        assert result.level == "info"

    def test_position_exceeds_limit_blocks(self):
        from risk.rules import SinglePositionLimit

        rule = SinglePositionLimit(max_ratio=0.1)
        context = {"target_weight": 0.15, "code": "000001"}
        result = rule.check(context)

        assert result.passed is False
        assert result.level == "block"


class TestStopLossRule:
    """止损规则测试"""

    def test_no_loss_passes(self):
        from risk.rules import StopLossRule

        rule = StopLossRule(max_loss_ratio=-0.05)
        context = {"pnl_ratio": 0.02, "code": "000001"}
        result = rule.check(context)

        assert result.passed is True

    def test_small_loss_passes(self):
        from risk.rules import StopLossRule

        rule = StopLossRule(max_loss_ratio=-0.05)
        context = {"pnl_ratio": -0.03, "code": "000001"}
        result = rule.check(context)

        assert result.passed is True

    def test_exceeds_loss_blocks(self):
        from risk.rules import StopLossRule

        rule = StopLossRule(max_loss_ratio=-0.05)
        context = {"pnl_ratio": -0.08, "code": "000001"}
        result = rule.check(context)

        assert result.passed is False
        assert result.level == "block"


class TestIndustryConcentration:
    """行业集中度测试"""

    def test_within_limit_passes(self):
        from risk.rules import IndustryConcentration

        rule = IndustryConcentration(max_ratio=0.3)
        context = {"industry_weights": {"银行": 0.2, "科技": 0.15}}
        result = rule.check(context)

        assert result.passed is True

    def test_exceeds_limit_warns(self):
        from risk.rules import IndustryConcentration

        rule = IndustryConcentration(max_ratio=0.3)
        context = {"industry_weights": {"银行": 0.4, "科技": 0.1}}
        result = rule.check(context)

        assert result.passed is False
        assert result.level == "warning"


class TestRiskChecker:
    """风控检查器测试"""

    def test_filter_blocked_orders(self):
        from risk.checker import RiskChecker
        from risk.rules import SinglePositionLimit

        db = DuckDBManager(":memory:")
        db.connect()

        checker = RiskChecker(db, rules=[SinglePositionLimit(max_ratio=0.1)])

        orders = pd.DataFrame([
            {"code": "000001", "weight": 0.08},  # 通过
            {"code": "000002", "weight": 0.15},  # 拦截
        ])
        positions = pd.DataFrame()

        passed, blocked, _ = checker.filter_blocked_orders(orders, positions, "2024-01-31")

        assert len(passed) == 1
        assert len(blocked) == 1
        assert blocked.iloc[0]["code"] == "000002"

    def test_risk_event_logged(self):
        from risk.checker import RiskChecker
        from risk.rules import SinglePositionLimit

        db = DuckDBManager(":memory:")
        db.connect()

        checker = RiskChecker(db, rules=[SinglePositionLimit(max_ratio=0.1)])

        orders = pd.DataFrame([{"code": "000001", "weight": 0.15}])
        checker.filter_blocked_orders(orders, pd.DataFrame(), "2024-01-31")

        events = db.query("SELECT * FROM risk_event_log")
        assert len(events) == 1
        assert events.iloc[0]["level"] == "block"


class TestStopLossExecutor:
    """止损执行器测试"""

    def test_stop_loss_triggered(self):
        from risk.stop_loss import StopLossExecutor
        from executor.broker import SimulatedBroker

        db = DuckDBManager(":memory:")
        db.connect()
        broker = SimulatedBroker()
        broker.connect()

        # 插入价格数据
        df = pd.DataFrame({
            "code": ["000001"],
            "date": ["2024-01-31"],
            "open": [9.0],  # 当前价格9元
            "high": [9.0],
            "low": [9.0],
            "close": [9.0],
            "volume": [1000000],
            "turnover": [9000000],
            "change_pct": [-0.1],
            "turnover_rate": [0.01],
        })
        df["date"] = pd.to_datetime(df["date"]).dt.date
        db.conn.execute("INSERT INTO daily_quote SELECT * FROM df")

        # 建仓成本10元
        broker.buy("000001", 1000, 10.0)  # 成本10元，现价9元，浮亏10%

        executor = StopLossExecutor(db, broker, max_loss_ratio=-0.05)
        orders = executor.check_and_execute("2024-01-31")

        assert len(orders) == 1  # 触发止损
        assert orders[0]["code"] == "000001"
        positions = broker.query_positions()
        assert len(positions) == 0  # 已清仓

    def test_no_stop_loss_when_profitable(self):
        from risk.stop_loss import StopLossExecutor
        from executor.broker import SimulatedBroker

        db = DuckDBManager(":memory:")
        db.connect()
        broker = SimulatedBroker()
        broker.connect()

        # 插入价格数据
        df = pd.DataFrame({
            "code": ["000001"],
            "date": ["2024-01-31"],
            "open": [11.0],  # 当前价格11元
            "high": [11.0],
            "low": [11.0],
            "close": [11.0],
            "volume": [1000000],
            "turnover": [11000000],
            "change_pct": [0.1],
            "turnover_rate": [0.01],
        })
        df["date"] = pd.to_datetime(df["date"]).dt.date
        db.conn.execute("INSERT INTO daily_quote SELECT * FROM df")

        # 建仓成本10元
        broker.buy("000001", 1000, 10.0)  # 成本10元，现价11元，盈利10%

        executor = StopLossExecutor(db, broker, max_loss_ratio=-0.05)
        orders = executor.check_and_execute("2024-01-31")

        assert len(orders) == 0  # 不触发止损
        positions = broker.query_positions()
        assert len(positions) == 1


class TestConsoleAlert:
    """控制台告警测试"""

    def test_alert_sends(self):
        from risk.alert import ConsoleAlert, AlertManager

        alert_mgr = AlertManager()
        alert_mgr.add_channel(ConsoleAlert())

        # 不抛异常就算成功
        alert_mgr.warning("Test Warning", "This is a test")
        alert_mgr.block("Test Block", "This is a critical test")
