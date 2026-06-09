"""盈亏计算模块 - PnL 计算引擎"""

import math
import pandas as pd
from loguru import logger
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class TradePnL:
    """单笔交易盈亏"""
    trade_id: str
    code: str
    action: str
    shares: int
    entry_price: float
    exit_price: float
    realized_pnl: float
    realized_pnl_pct: float
    hold_days: int = 0


@dataclass
class PositionPnL:
    """单只持仓盈亏"""
    code: str
    shares: int
    cost_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class PortfolioMetrics:
    """组合风险指标"""
    total_return: float = 0.0          # 累计收益率
    annual_return: float = 0.0         # 年化收益率
    max_drawdown: float = 0.0          # 最大回撤
    sharpe_ratio: float = 0.0          # 夏普比率
    win_rate: float = 0.0              # 胜率
    profit_loss_ratio: float = 0.0     # 盈亏比
    total_trades: int = 0              # 总交易次数


class PnLCalculator:
    """盈亏计算器"""

    def __init__(self, db):
        self.db = db

    def calculate_trade_pnl(self, trade_id: str) -> Optional[TradePnL]:
        """计算单笔交易盈亏"""
        try:
            sql = f"""
                SELECT * FROM trade_log WHERE trade_id = '{trade_id}'
            """
            trade = self.db.query(sql)
            if trade.empty:
                return None

            t = trade.iloc[0]
            return TradePnL(
                trade_id=t["trade_id"],
                code=t["code"],
                action=t["action"],
                shares=t["shares"],
                entry_price=t["price"],
                exit_price=t["price"],
                realized_pnl=0.0,  # 单笔成交不计算盈亏，需要配对
                realized_pnl_pct=0.0,
            )
        except Exception as e:
            logger.error(f"Failed to calculate trade pnl: {e}")
            return None

    def calculate_position_pnl(self, code: str, date: str) -> Optional[PositionPnL]:
        """计算单只持仓浮盈浮亏"""
        try:
            # 获取持仓
            position_sql = f"""
                SELECT * FROM position_log
                WHERE code = '{code}' AND date = '{date}'
            """
            position = self.db.query(position_sql)
            if position.empty:
                return None

            pos = position.iloc[0]
            shares = pos["shares"]
            cost_price = pos.get("cost_price", 0.0) or 0.0
            current_price = pos.get("current_price", 0.0) or 0.0

            if current_price == 0:
                # 从行情表获取最新价格
                price_sql = f"""
                    SELECT close FROM daily_quote
                    WHERE code = '{code}' AND date <= '{date}'
                    ORDER BY date DESC LIMIT 1
                """
                price_result = self.db.query(price_sql)
                if not price_result.empty:
                    current_price = price_result.iloc[0]["close"]

            market_value = shares * current_price
            unrealized_pnl = (current_price - cost_price) * shares

            if cost_price > 0:
                unrealized_pnl_pct = (current_price - cost_price) / cost_price * 100
            else:
                unrealized_pnl_pct = 0.0

            return PositionPnL(
                code=code,
                shares=shares,
                cost_price=cost_price,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
            )
        except Exception as e:
            logger.error(f"Failed to calculate position pnl for {code}: {e}")
            return None

    def calculate_portfolio_pnl(self, date: str) -> Dict:
        """计算组合整体盈亏"""
        try:
            positions = self.db.query(f"""
                SELECT * FROM position_log WHERE date = '{date}'
            """)
            if positions.empty:
                return {
                    "total_market_value": 0.0,
                    "total_unrealized_pnl": 0.0,
                    "total_unrealized_pnl_pct": 0.0,
                    "position_count": 0,
                }

            total_market_value = 0.0
            total_unrealized_pnl = 0.0
            total_cost = 0.0

            for _, pos in positions.iterrows():
                code = pos["code"]
                pos_pnl = self.calculate_position_pnl(code, date)
                if pos_pnl:
                    total_market_value += pos_pnl.market_value
                    total_unrealized_pnl += pos_pnl.unrealized_pnl
                    total_cost += pos_pnl.shares * pos_pnl.cost_price

            if total_cost > 0:
                total_unrealized_pnl_pct = total_unrealized_pnl / total_cost * 100
            else:
                total_unrealized_pnl_pct = 0.0

            return {
                "total_market_value": total_market_value,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_unrealized_pnl_pct": total_unrealized_pnl_pct,
                "position_count": len(positions),
            }
        except Exception as e:
            logger.error(f"Failed to calculate portfolio pnl: {e}")
            return {
                "total_market_value": 0.0,
                "total_unrealized_pnl": 0.0,
                "total_unrealized_pnl_pct": 0.0,
                "position_count": 0,
            }

    def get_portfolio_equity_curve(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取组合净值曲线"""
        try:
            sql = f"""
                SELECT date, SUM(market_value) as equity
                FROM position_log
                WHERE date >= '{start_date}' AND date <= '{end_date}'
                GROUP BY date
                ORDER BY date
            """
            df = self.db.query(sql)
            if df.empty:
                return pd.DataFrame(columns=["date", "equity", "return"])

            df["return"] = df["equity"].pct_change().fillna(0.0)
            return df
        except Exception as e:
            logger.error(f"Failed to get equity curve: {e}")
            return pd.DataFrame(columns=["date", "equity", "return"])

    def calculate_metrics(self, start_date: str, end_date: str,
                          risk_free_rate: float = 0.03) -> PortfolioMetrics:
        """计算组合风险指标"""
        metrics = PortfolioMetrics()

        equity_df = self.get_portfolio_equity_curve(start_date, end_date)
        if equity_df.empty or len(equity_df) < 2:
            return metrics

        # 累计收益率
        initial_equity = equity_df["equity"].iloc[0]
        final_equity = equity_df["equity"].iloc[-1]
        if initial_equity > 0:
            metrics.total_return = (final_equity - initial_equity) / initial_equity

        # 年化收益率（假设每年252个交易日）
        days = len(equity_df)
        if days > 0 and initial_equity > 0:
            metrics.annual_return = (1 + metrics.total_return) ** (252 / days) - 1

        # 最大回撤
        rolling_max = equity_df["equity"].expanding().max()
        drawdown = (equity_df["equity"] - rolling_max) / rolling_max
        metrics.max_drawdown = drawdown.min()

        # 夏普比率
        returns = equity_df["return"].dropna()
        if len(returns) > 0 and returns.std() > 0:
            daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
            excess_returns = returns - daily_rf
            metrics.sharpe_ratio = excess_returns.mean() / returns.std() * math.sqrt(252)

        # 简单交易统计
        metrics.total_trades = self._get_total_trades(start_date, end_date)

        return metrics

    def _get_total_trades(self, start_date: str, end_date: str) -> int:
        """获取交易次数"""
        try:
            sql = f"""
                SELECT COUNT(*) as cnt FROM trade_log
                WHERE date >= '{start_date}' AND date <= '{end_date}'
            """
            result = self.db.query(sql)
            return result.iloc[0]["cnt"] if not result.empty else 0
        except:
            return 0

    def generate_daily_report(self, date: str) -> str:
        """生成日报"""
        portfolio_pnl = self.calculate_portfolio_pnl(date)
        metrics = self.calculate_metrics(date, date)

        report = f"""
===== 交易日报 {date} =====

【组合概况】
持仓数量: {portfolio_pnl['position_count']} 只
总市值: ¥{portfolio_pnl['total_market_value']:,.2f}
浮动盈亏: ¥{portfolio_pnl['total_unrealized_pnl']:,.2f} ({portfolio_pnl['total_unrealized_pnl_pct']:+.2f}%)

【风险指标】
累计收益率: {metrics.total_return*100:+.2f}%
最大回撤: {metrics.max_drawdown*100:.2f}%
夏普比率: {metrics.sharpe_ratio:.2f}
交易次数: {metrics.total_trades}
"""
        return report
