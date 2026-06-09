"""模拟 Broker 实现"""

import uuid
import pandas as pd
from loguru import logger
from .base import BaseBroker


class SimulatedBroker(BaseBroker):
    """模拟交易 Broker"""

    def __init__(self, db=None):
        self.db = db
        self._positions = pd.DataFrame(columns=["code", "shares", "cost_price"])
        self._orders = {}  # order_id -> status

    def connect(self) -> bool:
        """连接模拟系统"""
        logger.info("SimulatedBroker connected")
        return True

    def disconnect(self):
        """断开连接"""
        logger.info("SimulatedBroker disconnected")

    def buy(self, code: str, shares: int, price: float) -> str:
        """模拟买入"""
        order_id = str(uuid.uuid4())[:8]
        logger.info(f"Simulated BUY: {code} x {shares} @ {price}, order={order_id}")

        # 更新持仓
        if code in self._positions["code"].values:
            idx = self._positions[self._positions["code"] == code].index[0]
            old_shares = self._positions.loc[idx, "shares"]
            old_cost = self._positions.loc[idx, "cost_price"]
            total_shares = old_shares + shares
            new_cost = (old_shares * old_cost + shares * price) / total_shares
            self._positions.loc[idx, "shares"] = total_shares
            self._positions.loc[idx, "cost_price"] = new_cost
        else:
            new_row = pd.DataFrame([{
                "code": code,
                "shares": shares,
                "cost_price": price,
            }])
            self._positions = pd.concat([self._positions, new_row], ignore_index=True)

        self._orders[order_id] = "filled"
        return order_id

    def sell(self, code: str, shares: int, price: float) -> str:
        """模拟卖出"""
        order_id = str(uuid.uuid4())[:8]
        logger.info(f"Simulated SELL: {code} x {shares} @ {price}, order={order_id}")

        # 更新持仓
        if code in self._positions["code"].values:
            idx = self._positions[self._positions["code"] == code].index[0]
            current_shares = self._positions.loc[idx, "shares"]
            if shares >= current_shares:
                # 清仓
                self._positions = self._positions.drop(idx).reset_index(drop=True)
            else:
                # 减仓
                self._positions.loc[idx, "shares"] -= shares

        self._orders[order_id] = "filled"
        return order_id

    def query_positions(self) -> pd.DataFrame:
        """查询当前持仓"""
        return self._positions.copy()

    def query_order_status(self, order_id: str) -> str:
        """查询订单状态"""
        return self._orders.get(order_id, "unknown")
