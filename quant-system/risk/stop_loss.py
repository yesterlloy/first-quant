"""止损执行器"""

import pandas as pd
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from .rules import StopLossRule


class StopLossExecutor:
    """止损执行器"""

    def __init__(self, db: DuckDBManager, broker, max_loss_ratio: float = -0.05):
        self.db = db
        self.broker = broker
        self.stop_loss_rule = StopLossRule(max_loss_ratio)

    def check_and_execute(self, date: str) -> list:
        """检查所有持仓，执行止损

        Returns:
            list: 执行的止损订单列表
        """
        positions = self.broker.query_positions()
        if positions.empty:
            logger.info("No positions to check stop loss")
            return []

        executed_orders = []

        for _, pos in positions.iterrows():
            code = pos["code"]
            cost_price = pos.get("cost_price", 0)
            current_price = self._get_current_price(code, date)

            if current_price is None or cost_price == 0:
                continue

            pnl_ratio = (current_price - cost_price) / cost_price
            context = {"pnl_ratio": pnl_ratio, "code": code}
            result = self.stop_loss_rule.check(context)

            if result.level == "block":
                # 触发止损，执行卖出
                shares = pos["shares"]
                order_id = self.broker.sell(code, shares, current_price)
                logger.warning(f"Executed stop loss: {code} x {shares} @ {current_price}, PnL {pnl_ratio:.1%}")

                executed_orders.append({
                    "code": code,
                    "shares": shares,
                    "price": current_price,
                    "pnl_ratio": pnl_ratio,
                    "order_id": order_id,
                })

        logger.info(f"Stop loss check completed: {len(executed_orders)} orders executed")
        return executed_orders

    def _get_current_price(self, code: str, date: str) -> float:
        """获取股票当前价格"""
        try:
            sql = f"""
                SELECT close FROM daily_quote
                WHERE code = '{code}' AND date <= '{date}'
                ORDER BY date DESC LIMIT 1
            """
            result = self.db.query(sql)
            if not result.empty:
                return result.iloc[0]["close"]
        except Exception as e:
            logger.debug(f"Failed to get price for {code}: {e}")
        return None
