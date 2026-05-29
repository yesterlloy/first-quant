"""回测引擎 - 基于 vectorbt"""

import pandas as pd
import vectorbt as vbt
from loguru import logger
from strategy.base import BaseStrategy


class BacktestEngine:
    """回测引擎，封装 vectorbt 实现"""

    def __init__(self, initial_capital: float = 1000000,
                 commission: float = 0.001, slippage: float = 0.0005,
                 freq: str = "D"):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.freq = freq

    def run(self, strategy: BaseStrategy, df: pd.DataFrame) -> dict:
        """运行单策略回测

        Args:
            strategy: 策略实例
            df: 行情数据（需含 date, close 列）

        Returns:
            dict: 回测结果（包含统计指标和持仓记录）
        """
        logger.info(f"Running backtest for strategy: {strategy.name}")

        # 生成信号
        signals = strategy.generate_signals(df)

        # 确保数据排序
        df = df.sort_values("date").reset_index(drop=True)
        signals = signals.reset_index(drop=True)

        # 转换为 vectorbt 的 entries/exits
        entries = signals == 1
        exits = signals == -1

        # 用 vectorbt 跑回测
        price = df["close"]
        price.index = pd.DatetimeIndex(df["date"])

        entries.index = price.index
        exits.index = price.index

        pf = vbt.Portfolio.from_signals(
            close=price,
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=self.commission,
            slippage=self.slippage,
            freq=self.freq,
            accumulate=False,  # 不累积信号，新买入先卖出旧持仓
        )

        # 提取结果（兼容 vectorbt 新旧版本：属性可能是方法或属性）
        def _safe_get(obj, name, default=None):
            """安全获取 vectorbt 指标（兼容属性/方法/不存在）"""
            try:
                val = getattr(obj, name, default)
                return val() if callable(val) else val
            except Exception:
                return default

        total_return = _safe_get(pf, 'total_return', 0.0)
        sharpe = _safe_get(pf, 'sharpe_ratio')
        max_dd = _safe_get(pf, 'max_drawdown')
        win_rate = _safe_get(pf.trades, 'win_rate') if hasattr(pf, 'trades') else None
        trade_count = _safe_get(pf.trades, 'count') if hasattr(pf, 'trades') else None
        portfolio_val = _safe_get(pf, 'value')
        returns_val = _safe_get(pf, 'returns')

        result = {
            "strategy_name": strategy.name,
            "strategy_params": strategy.get_params(),
            "total_return": total_return,
            "annualized_return": self._calc_annualized_return(total_return, returns_val),
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "total_trades": trade_count,
            "portfolio_value": portfolio_val,
            "returns": returns_val,
            "trades": pf.trades.records_readable if hasattr(pf, 'trades') and hasattr(pf.trades, 'records_readable') else None,
        }

        logger.info(f"Backtest done: {strategy.name}, return={result['total_return']:.2%}")
        return result

    def run_multi(self, strategies: list, df: pd.DataFrame) -> list:
        """运行多策略对比回测"""
        results = []
        for strategy in strategies:
            result = self.run(strategy, df)
            results.append(result)
        return results

    def _calc_annualized_return(self, total_return, returns) -> float:
        """计算年化收益率"""
        if hasattr(returns, '__len__') and len(returns) > 0:
            n_days = len(returns)
            annual_factor = 365 / n_days
            return (1 + total_return) ** annual_factor - 1
        return total_return