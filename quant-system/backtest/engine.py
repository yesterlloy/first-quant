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

        # 提取结果
        result = {
            "strategy_name": strategy.name,
            "strategy_params": strategy.get_params(),
            "total_return": pf.total_return,
            "annualized_return": self._calc_annualized_return(pf),
            "sharpe_ratio": pf.sharpe_ratio,
            "max_drawdown": pf.max_drawdown,
            "win_rate": pf.win_rate if hasattr(pf, 'win_rate') else None,
            "total_trades": pf.total_trades,
            "portfolio_value": pf.value,
            "returns": pf.returns,
            "trades": pf.trades.records_readable if hasattr(pf.trades, 'records_readable') else None,
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

    def _calc_annualized_return(self, pf) -> float:
        """计算年化收益率"""
        total_return = pf.total_return
        # 假设回测期为N天，年化 = (1+total)^(365/N) - 1
        if hasattr(pf, 'returns') and len(pf.returns) > 0:
            n_days = len(pf.returns)
            if n_days > 0:
                annual_factor = 365 / n_days
                return (1 + total_return) ** annual_factor - 1
        return total_return