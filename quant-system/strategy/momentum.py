"""动量策略 - 过去N日涨幅排名"""

import pandas as pd
from strategy.base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """动量策略：基于过去N日涨幅生成信号

    过去N日涨幅超过阈值 → 买入信号（趋势延续）
    过去N日跌幅超过阈值 → 卖出信号（趋势延续）
    """

    def __init__(self, lookback: int = 20, buy_threshold: float = 0.05,
                 sell_threshold: float = -0.05):
        super().__init__(name="momentum")
        self.lookback = lookback
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        self.validate_data(df)

        signals = pd.Series(0, index=df.index, dtype=int)

        # 计算过去N日收益率
        returns = df["close"].pct_change(periods=self.lookback)

        # 信号生成
        signals[returns > self.buy_threshold] = 1    # 涨幅超过阈值 → 买入
        signals[returns < self.sell_threshold] = -1   # 跌幅超过阈值 → 卖出

        return signals

    def get_params(self) -> dict:
        return {
            "lookback": self.lookback,
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
        }