"""订单管理模块 - 生成、跟踪订单状态"""

import uuid
import pandas as pd
from loguru import logger
from data.db.duckdb_manager import DuckDBManager


class OrderManager:
    """订单管理器"""

    def __init__(self, db: DuckDBManager, price_offset: float = 0.02):
        self.db = db
        self.price_offset = price_offset  # 限价偏移比例

    def generate_orders(self, target_positions: pd.DataFrame,
                        current_positions: pd.DataFrame, date: str) -> pd.DataFrame:
        """生成调仓订单

        Args:
            target_positions: 目标持仓 [code, shares, weight]
            current_positions: 当前持仓 [code, shares]
            date: 调仓日期

        Returns:
            DataFrame: [order_id, code, action, shares, price, status]
        """
        if target_positions.empty and current_positions.empty:
            logger.info("No positions, no orders")
            return pd.DataFrame()

        # 确保列存在
        if target_positions.empty:
            target_positions = pd.DataFrame(columns=["code", "shares", "weight"])
        if current_positions.empty:
            current_positions = pd.DataFrame(columns=["code", "shares"])

        merged = target_positions.merge(
            current_positions[["code", "shares"]],
            on="code",
            how="outer",
            suffixes=("_target", "_current"),
        )
        merged = merged.fillna(0)

        orders = []
        for _, row in merged.iterrows():
            code = row["code"]
            target_shares = int(row.get("shares_target", 0))
            current_shares = int(row.get("shares_current", 0))
            diff = target_shares - current_shares

            if diff == 0:
                continue

            action = "buy" if diff > 0 else "sell"
            shares = abs(diff)

            # 获取当前价格
            price = self._get_price(code, date)
            if price is None:
                logger.warning(f"No price for {code} on {date}, skip")
                continue

            # 限价偏移
            if action == "buy":
                limit_price = price * (1 + self.price_offset)
            else:
                limit_price = price * (1 - self.price_offset)

            order_id = str(uuid.uuid4())[:8]
            orders.append({
                "order_id": order_id,
                "code": code,
                "action": action,
                "shares": shares,
                "price": round(limit_price, 2),
                "status": "pending",
            })

        result = pd.DataFrame(orders)
        logger.info(f"Generated {len(result)} orders")
        return result

    def _get_price(self, code: str, date: str) -> float:
        """获取股票价格"""
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
            logger.debug(f"Failed to get price: {e}")
        return None

    def update_status(self, order_id: str, status: str):
        """更新订单状态"""
        try:
            sql = f"""
                UPDATE order_log
                SET status = '{status}', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = '{order_id}'
            """
            self.conn.execute(sql)
            logger.info(f"Order {order_id} status updated to {status}")
        except Exception as e:
            logger.error(f"Failed to update order status: {e}")

    def get_pending_orders(self) -> pd.DataFrame:
        """获取待执行订单"""
        try:
            sql = "SELECT * FROM order_log WHERE status = 'pending'"
            return self.db.query(sql)
        except Exception as e:
            logger.error(f"Failed to get pending orders: {e}")
            return pd.DataFrame()
