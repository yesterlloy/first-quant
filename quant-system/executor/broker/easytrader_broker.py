"""EasyTrader 实盘券商接口封装

支持的券商:
- 华泰证券(ht)
- 东方财富(ths)
- 同花顺通用版
- 雪球(xueqiu)
"""

import time
from datetime import datetime
from typing import Optional
import pandas as pd
from loguru import logger

from .base import BaseBroker


class EasyTraderBroker(BaseBroker):
    """EasyTrader 实盘券商接口"""

    def __init__(self, broker_type: str = "ths", config_path: str = None, **kwargs):
        """初始化EasyTrader Broker

        Args:
            broker_type: 券商类型: ht(华泰), ths(东方财富), xq(雪球), yh(银河)
            config_path: 配置文件路径
            **kwargs: 其他参数，如交易密码、账户等
        """
        self.broker_type = broker_type
        self.config_path = config_path
        self.kwargs = kwargs
        self._api = None
        self._connected = False
        self._account_info = None

        # 模拟模式：不调用真实easytrader API，只记录日志
        self.simulation_mode = kwargs.get("simulation_mode", True)

        logger.info(f"EasyTraderBroker初始化: broker_type={broker_type}, simulation_mode={self.simulation_mode}")

    def connect(self) -> bool:
        """连接券商"""
        if self._connected:
            return True

        try:
            if self.simulation_mode:
                # 模拟模式
                logger.warning("⚠️ EasyTrader运行在模拟模式下，不会发送真实订单")
                self._account_info = {
                    "account": "SIMULATION_ACCOUNT",
                    "cash": 1000000.0,
                    "total_assets": 1000000.0,
                }
                self._connected = True
                logger.info("✅ EasyTrader模拟模式连接成功")
                return True

            # 真实easytrader API连接
            try:
                import easytrader
            except ImportError:
                logger.error("easytrader未安装，请执行: pip install easytrader")
                raise

            # 根据券商类型创建对应的api实例
            if self.broker_type == "ht":
                self._api = easytrader.use("ht")
            elif self.broker_type == "ths":
                self._api = easytrader.use("ths")
            elif self.broker_type == "xueqiu" or self.broker_type == "xq":
                self._api = easytrader.use("xq")
            elif self.broker_type == "yh":
                self._api = easytrader.use("yh")
            else:
                self._api = easytrader.use(self.broker_type)

            # 登录
            if self.config_path:
                self._api.prepare(self.config_path)
            else:
                logger.warning("未提供配置文件，请手动登录")

            self._connected = True
            logger.info(f"✅ EasyTrader连接成功: broker_type={self.broker_type}")
            return True

        except Exception as e:
            logger.error(f"❌ EasyTrader连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """断开连接"""
        if self._api:
            try:
                self._api.exit()
            except Exception as e:
                logger.warning(f"断开连接时出错: {e}")
        self._connected = False
        self._api = None
        logger.info("EasyTrader已断开连接")

    def buy(self, code: str, shares: int, price: float = None) -> str:
        """买入下单

        Args:
            code: 股票代码
            shares: 股数
            price: 价格，None表示市价

        Returns:
            order_id: 订单ID
        """
        if not self._connected:
            raise RuntimeError("未连接到券商，请先调用connect()")

        order_id = f"buy_{code}_{int(time.time() * 1000)}"

        if self.simulation_mode:
            logger.info(f"📝 [模拟] 买入下单: {code} x {shares} @ {price or '市价'}")
            return order_id

        # 真实下单
        try:
            if price:
                result = self._api.buy(code, price=price, amount=shares)
            else:
                result = self._api.market_buy(code, amount=shares)

            order_id = result.get("entrust_no", order_id)
            logger.info(f"✅ 买入下单成功: {code} x {shares} @ {price or '市价'}, order_id={order_id}")
            return order_id

        except Exception as e:
            logger.error(f"❌ 买入下单失败: {code} x {shares} - {e}")
            raise

    def sell(self, code: str, shares: int, price: float = None) -> str:
        """卖出下单

        Args:
            code: 股票代码
            shares: 股数
            price: 价格，None表示市价

        Returns:
            order_id: 订单ID
        """
        if not self._connected:
            raise RuntimeError("未连接到券商，请先调用connect()")

        order_id = f"sell_{code}_{int(time.time() * 1000)}"

        if self.simulation_mode:
            logger.info(f"📝 [模拟] 卖出下单: {code} x {shares} @ {price or '市价'}")
            return order_id

        # 真实下单
        try:
            if price:
                result = self._api.sell(code, price=price, amount=shares)
            else:
                result = self._api.market_sell(code, amount=shares)

            order_id = result.get("entrust_no", order_id)
            logger.info(f"✅ 卖出下单成功: {code} x {shares} @ {price or '市价'}, order_id={order_id}")
            return order_id

        except Exception as e:
            logger.error(f"❌ 卖出下单失败: {code} x {shares} - {e}")
            raise

    def query_positions(self) -> pd.DataFrame:
        """查询当前持仓"""
        if not self._connected:
            raise RuntimeError("未连接到券商，请先调用connect()")

        if self.simulation_mode:
            # 模拟模式：返回空持仓或从数据库读取
            logger.info("[模拟] 查询持仓")
            return pd.DataFrame(columns=[
                "code", "name", "shares", "available_shares",
                "cost_price", "current_price", "market_value",
                "profit", "profit_pct"
            ])

        # 真实查询
        try:
            positions = self._api.position()

            # 标准化字段
            result = []
            for pos in positions:
                result.append({
                    "code": pos.get("证券代码", ""),
                    "name": pos.get("证券名称", ""),
                    "shares": pos.get("持仓数量", 0),
                    "available_shares": pos.get("可用数量", 0),
                    "cost_price": pos.get("成本价", 0.0),
                    "current_price": pos.get("当前价", 0.0),
                    "market_value": pos.get("市值", 0.0),
                    "profit": pos.get("盈亏", 0.0),
                    "profit_pct": pos.get("盈亏比例", 0.0),
                })

            return pd.DataFrame(result)

        except Exception as e:
            logger.error(f"查询持仓失败: {e}")
            return pd.DataFrame()

    def query_order_status(self, order_id: str) -> str:
        """查询订单状态

        Returns:
            'filled' - 已成交, 'partial' - 部分成交, 'cancelled' - 已撤单, 'pending' - 委托中
        """
        if not self._connected:
            raise RuntimeError("未连接到券商，请先调用connect()")

        if self.simulation_mode:
            logger.info(f"[模拟] 查询订单状态: {order_id}")
            return "filled"  # 模拟模式默认已成交

        # 真实查询
        try:
            today_orders = self._api.today_entrusts()
            for order in today_orders:
                if str(order.get("委托编号", "")) == order_id:
                    status = order.get("状态", "")
                    if "已成交" in status:
                        return "filled"
                    elif "部成" in status:
                        return "partial"
                    elif "已撤" in status:
                        return "cancelled"
                    else:
                        return "pending"

            return "not_found"

        except Exception as e:
            logger.error(f"查询订单状态失败: {order_id} - {e}")
            return "error"

    def get_account_info(self) -> dict:
        """获取账户信息"""
        if self.simulation_mode:
            return self._account_info or {}

        try:
            balance = self._api.balance()
            if isinstance(balance, list) and len(balance) > 0:
                return {
                    "cash": balance[0].get("可用资金", 0.0),
                    "total_assets": balance[0].get("总资产", 0.0),
                    "market_value": balance[0].get("市值", 0.0),
                }
            return {}
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if self.simulation_mode:
            logger.info(f"[模拟] 撤单: {order_id}")
            return True

        try:
            self._api.cancel_entrust(order_id)
            logger.info(f"撤单成功: {order_id}")
            return True
        except Exception as e:
            logger.error(f"撤单失败: {order_id} - {e}")
            return False

    def get_today_trades(self) -> pd.DataFrame:
        """获取今日成交"""
        if self.simulation_mode:
            return pd.DataFrame()

        try:
            trades = self._api.today_trades()
            result = []
            for t in trades:
                result.append({
                    "trade_id": t.get("成交编号", ""),
                    "order_id": t.get("委托编号", ""),
                    "code": t.get("证券代码", ""),
                    "name": t.get("证券名称", ""),
                    "action": "buy" if t.get("买卖标志", "") == "买入" else "sell",
                    "shares": t.get("成交数量", 0),
                    "price": t.get("成交价格", 0.0),
                    "time": t.get("成交时间", ""),
                })
            return pd.DataFrame(result)
        except Exception as e:
            logger.error(f"获取今日成交失败: {e}")
            return pd.DataFrame()


def create_broker(broker_type: str = "simulator", **kwargs) -> BaseBroker:
    """Broker工厂函数

    Args:
        broker_type: 'simulator' - 模拟盘, 'easytrader' 或具体券商类型
        **kwargs: 其他参数

    Returns:
        Broker实例
    """
    if broker_type == "simulator":
        from .simulator import SimulatedBroker
        return SimulatedBroker(kwargs.get("db"))

    elif broker_type in ["easytrader", "ht", "ths", "xq", "xueqiu", "yh"]:
        if broker_type == "easytrader":
            actual_type = kwargs.get("broker_subtype", "ths")
        else:
            actual_type = broker_type

        return EasyTraderBroker(broker_type=actual_type, **kwargs)

    else:
        raise ValueError(f"不支持的Broker类型: {broker_type}")
