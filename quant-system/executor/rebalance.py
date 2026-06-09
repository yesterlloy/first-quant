"""调仓主流程 - 编排从信号到交易的完整链路"""

import pandas as pd
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from .signal_loader import SignalLoader
from .portfolio_builder import PortfolioBuilder
from .position_calc import PositionCalculator
from .order_manager import OrderManager
from .trade_log import TradeLogger
from .broker.base import BaseBroker
from risk import RiskChecker, SinglePositionLimit, StopLossExecutor, AlertManager, ConsoleAlert, AlertContext


class Rebalancer:
    """调仓执行器"""

    def __init__(self, db: DuckDBManager, broker: BaseBroker, config: dict = None):
        self.db = db
        self.broker = broker
        self.config = config or {}

        self.signal_loader = SignalLoader(db)
        self.portfolio_builder = PortfolioBuilder(
            top_n=self.config.get("top_n", 10)
        )
        self.position_calc = PositionCalculator(
            total_ratio=self.config.get("total_ratio", 0.8),
            max_single=self.config.get("max_single", 0.1),
        )
        self.order_manager = OrderManager(
            db,
            price_offset=self.config.get("price_offset", 0.02),
        )
        self.trade_logger = TradeLogger(db)

        # 风控模块
        self.risk_checker = RiskChecker(db, rules=[
            SinglePositionLimit(max_ratio=self.config.get("max_single", 0.1)),
        ])
        self.stop_loss_executor = StopLossExecutor(
            db, broker,
            max_loss_ratio=self.config.get("stop_loss_ratio", -0.05),
        )

        # 告警
        self.alert_mgr = AlertManager()
        if self.config.get("enable_console_alert", True):
            self.alert_mgr.add_channel(ConsoleAlert())

    def run(self, date: str, model_name: str = "lgbm_v1", total_capital: float = 1000000):
        """执行月度调仓全流程

        Args:
            date: 调仓日期
            model_name: 模型版本
            total_capital: 总资金

        Returns:
            dict: 调仓结果统计
        """
        logger.info(f"Starting rebalance on {date}, model={model_name}")

        # 0. 事前风控：先执行止损检查
        stop_loss_orders = self.stop_loss_executor.check_and_execute(date)
        if stop_loss_orders:
            self.alert_mgr.warning(
                "Stop Loss Executed",
                f"Executed {len(stop_loss_orders)} stop loss orders"
            )

        # 1. 加载信号
        signals = self.signal_loader.load_signals(date, model_name)
        if signals.empty:
            logger.warning("No signals found, skip rebalance")
            return {"status": "no_signals"}

        logger.info(f"Loaded {len(signals)} signals")

        # 2. 构建组合
        portfolio = self.portfolio_builder.build_portfolio(signals)
        logger.info(f"Selected {len(portfolio)} stocks for portfolio")

        # 3. 获取价格（取调仓日前一个交易日的收盘价）
        prices = self._get_portfolio_prices(portfolio["code"].tolist(), date)
        if prices.empty:
            logger.error("No price data, abort rebalance")
            return {"status": "no_price_data"}

        # 4. 计算仓位
        target_positions = self.position_calc.calc_weights(portfolio, prices, total_capital)
        logger.info(f"Calculated target positions: {len(target_positions)} stocks")

        # 5. 获取当前持仓（止损后）
        current_positions = self.broker.query_positions()
        logger.info(f"Current positions: {len(current_positions)} stocks")

        # 6. 生成订单
        orders = self.order_manager.generate_orders(target_positions, current_positions, date)
        logger.info(f"Generated {len(orders)} orders")

        if orders.empty:
            logger.info("No orders to execute")
            return {"status": "no_orders", "stop_loss_count": len(stop_loss_orders)}

        # 7. 风控检查
        current_positions = self.broker.query_positions()  # 刷新持仓
        passed_orders, blocked_orders, _ = self.risk_checker.filter_blocked_orders(
            orders, current_positions, date
        )

        if len(blocked_orders) > 0:
            self.alert_mgr.warning(
                "Risk Block Alert",
                f"Blocked {len(blocked_orders)} orders by risk check"
            )

        if passed_orders.empty:
            logger.info("No orders passed risk check")
            return {
                "status": "all_orders_blocked",
                "blocked_count": len(blocked_orders),
                "stop_loss_count": len(stop_loss_orders),
            }

        # 8. 执行通过风控的订单
        trades = self.broker.execute_orders(passed_orders)
        logger.info(f"Executed {len(trades)} trades")

        # 9. 记录交易
        self.trade_logger.log_orders(orders, date)
        self.trade_logger.log_trades(trades, date)
        self.trade_logger.log_positions(target_positions, date)

        result = {
            "status": "completed",
            "signals": len(signals),
            "portfolio": len(portfolio),
            "orders": len(orders),
            "passed_orders": len(passed_orders),
            "blocked_orders": len(blocked_orders),
            "trades": len(trades),
            "stop_loss_count": len(stop_loss_orders),
        }
        logger.info(f"Rebalance completed: {result}")
        return result

    def _get_portfolio_prices(self, codes: list, date: str) -> pd.DataFrame:
        """获取组合内股票的价格"""
        try:
            codes_str = "', '".join(codes)
            sql = f"""
                SELECT code, close FROM daily_quote
                WHERE code IN ('{codes_str}') AND date <= '{date}'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) = 1
            """
            return self.db.query(sql)
        except Exception as e:
            logger.error(f"Failed to get portfolio prices: {e}")
            return pd.DataFrame()
