"""事前风控检查器"""

import uuid
import pandas as pd
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from .rules import RiskRule, RuleResult


class RiskChecker:
    """风控检查器"""

    def __init__(self, db: DuckDBManager, rules: list[RiskRule] = None):
        self.db = db
        self.rules = rules or []
        self._ensure_risk_event_table()

    def _ensure_risk_event_table(self):
        """确保风控事件表存在"""
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS risk_event_log (
                event_id VARCHAR PRIMARY KEY,
                date DATE,
                level VARCHAR,
                rule_name VARCHAR,
                code VARCHAR,
                message VARCHAR,
                created_at TIMESTAMP
            )
        """)

    def add_rule(self, rule: RiskRule):
        """添加风控规则"""
        self.rules.append(rule)

    def check_order(self, order: pd.Series, positions: pd.DataFrame) -> list[RuleResult]:
        """检查单个订单"""
        context = {
            "order": order,
            "positions": positions,
            "code": order.get("code", ""),
            "target_weight": order.get("weight", 0),
        }
        return [rule.check(context) for rule in self.rules]

    def check_portfolio(self, target_portfolio: pd.DataFrame) -> list[RuleResult]:
        """检查整个组合"""
        results = []

        # 计算行业权重
        if "industry" in target_portfolio.columns:
            industry_weights = target_portfolio.groupby("industry")["weight"].sum().to_dict()
            context = {"industry_weights": industry_weights}

            for rule in self.rules:
                if rule.rule_name == "IndustryConcentration":
                    results.append(rule.check(context))

        return results

    def filter_blocked_orders(self, orders: pd.DataFrame, positions: pd.DataFrame, date: str):
        """过滤被拦截的订单

        Returns:
            (passed_orders, blocked_orders, all_results)
        """
        passed = []
        blocked = []
        all_results = []

        for _, order in orders.iterrows():
            results = self.check_order(order, positions)
            all_results.extend(results)

            blocked_results = [r for r in results if r.level == "block"]
            if blocked_results:
                blocked.append(order)
                logger.warning(f"Order blocked: {order['code']} - {blocked_results[0].message}")
                self._log_event(date, blocked_results[0])
            else:
                passed.append(order)

        passed_df = pd.DataFrame(passed) if passed else pd.DataFrame()
        blocked_df = pd.DataFrame(blocked) if blocked else pd.DataFrame()

        logger.info(f"Risk check: {len(passed_df)} passed, {len(blocked_df)} blocked")
        return passed_df, blocked_df, all_results

    def _log_event(self, date: str, result: RuleResult):
        """记录风控事件"""
        event = {
            "event_id": str(uuid.uuid4())[:8],
            "date": pd.to_datetime(date).date(),
            "level": result.level,
            "rule_name": result.rule_name,
            "code": result.code,
            "message": result.message,
            "created_at": pd.Timestamp.now(),
        }
        df = pd.DataFrame([event])
        self.db.conn.execute("INSERT INTO risk_event_log SELECT * FROM df")
