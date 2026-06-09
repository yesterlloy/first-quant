"""交易记录模块 - 记录订单、成交、持仓到数据库"""

import pandas as pd
from loguru import logger
from data.db.duckdb_manager import DuckDBManager


class TradeLogger:
    """交易记录器"""

    def __init__(self, db: DuckDBManager):
        self.db = db

    def log_orders(self, orders: pd.DataFrame, date: str):
        """记录订单到 order_log 表"""
        if orders.empty:
            logger.debug("No orders to log")
            return

        df = orders.copy()
        df["date"] = pd.to_datetime(date).date()
        df["created_at"] = pd.Timestamp.now()
        df["updated_at"] = pd.Timestamp.now()

        # 确保列存在并按表顺序排列
        cols = ["order_id", "date", "code", "action", "shares", "price", "status", "created_at", "updated_at"]
        for col in cols:
            if col not in df.columns:
                logger.warning(f"Missing column {col} in orders")
                return

        df = df[cols]
        self.db.conn.execute("INSERT INTO order_log SELECT * FROM df")
        logger.info(f"Logged {len(df)} orders to order_log")

    def log_trades(self, trades: pd.DataFrame, date: str):
        """记录成交到 trade_log 表"""
        if trades.empty:
            logger.debug("No trades to log")
            return

        df = trades.copy()
        df["date"] = pd.to_datetime(date).date()
        df["filled_at"] = pd.Timestamp.now()

        cols = ["trade_id", "order_id", "date", "code", "action", "shares", "price", "filled_at"]
        for col in cols:
            if col not in df.columns:
                logger.warning(f"Missing column {col} in trades")
                return

        df = df[cols]
        self.db.conn.execute("INSERT INTO trade_log SELECT * FROM df")
        logger.info(f"Logged {len(df)} trades to trade_log")

    def log_positions(self, positions: pd.DataFrame, date: str):
        """记录持仓快照到 position_log 表"""
        if positions.empty:
            logger.debug("No positions to log")
            return

        df = positions.copy()
        df["date"] = pd.to_datetime(date).date()

        # 补全可选列
        if "cost_price" not in df.columns:
            df["cost_price"] = 0.0
        if "current_price" not in df.columns:
            df["current_price"] = 0.0
        if "market_value" not in df.columns:
            df["market_value"] = 0.0

        # 按表顺序排列
        cols = ["date", "code", "shares", "weight", "cost_price", "current_price", "market_value"]
        for col in cols:
            if col not in df.columns:
                logger.warning(f"Missing column {col} in positions")
                return

        df = df[cols]
        self.db.conn.execute("INSERT OR REPLACE INTO position_log SELECT * FROM df")
        logger.info(f"Logged {len(df)} positions to position_log")

    def get_latest_positions(self) -> pd.DataFrame:
        """获取最新持仓"""
        try:
            sql = """
                SELECT * FROM position_log
                WHERE date = (SELECT MAX(date) FROM position_log)
            """
            return self.db.query(sql)
        except Exception as e:
            logger.error(f"Failed to get latest positions: {e}")
            return pd.DataFrame()
