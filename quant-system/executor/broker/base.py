"""Broker 抽象基类"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseBroker(ABC):
    """Broker 接口定义"""

    @abstractmethod
    def connect(self) -> bool:
        """连接券商/模拟系统"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    def buy(self, code: str, shares: int, price: float) -> str:
        """买入下单，返回 order_id"""
        pass

    @abstractmethod
    def sell(self, code: str, shares: int, price: float) -> str:
        """卖出下单，返回 order_id"""
        pass

    @abstractmethod
    def query_positions(self) -> pd.DataFrame:
        """查询当前持仓"""
        pass

    @abstractmethod
    def query_order_status(self, order_id: str) -> str:
        """查询订单状态"""
        pass

    def execute_orders(self, orders: pd.DataFrame) -> pd.DataFrame:
        """批量执行订单

        Args:
            orders: [order_id, code, action, shares, price]

        Returns:
            DataFrame: [trade_id, order_id, code, action, shares, price]
        """
        trades = []
        for _, row in orders.iterrows():
            if row["action"] == "buy":
                order_id = self.buy(row["code"], row["shares"], row["price"])
            else:
                order_id = self.sell(row["code"], row["shares"], row["price"])

            trades.append({
                "trade_id": f"t_{order_id}",
                "order_id": order_id,
                "code": row["code"],
                "action": row["action"],
                "shares": row["shares"],
                "price": row["price"],
            })

        return pd.DataFrame(trades)
