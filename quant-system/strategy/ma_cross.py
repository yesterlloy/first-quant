"""均线交叉策略 - MA金叉死叉"""

import pandas as pd
from strategy.base import BaseStrategy


class MACrossStrategy(BaseStrategy):
    """均线交叉策略：短期均线与长期均线交叉

    金叉（短期MA上穿长期MA）→ 买入信号
    死叉（短期MA下穿长期MA）→ 卖出信号
    """

    def __init__(self, short_window: int = 5, long_window: int = 20):
        super().__init__(name="ma_cross")
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        self.validate_data(df)

        signals = pd.Series(0, index=df.index, dtype=int)

        # 计算均线
        short_ma = df["close"].rolling(window=self.short_window, min_periods=1).mean()
        long_ma = df["close"].rolling(window=self.long_window, min_periods=1).mean()

        # 交叉信号
        # 金叉：短期从下方穿越长期
        gold_cross = (short_ma.shift(1) <= long_ma.shift(1)) & (short_ma > long_ma)
        # 死叉：短期从上方穿越长期
        death_cross = (short_ma.shift(1) >= long_ma.shift(1)) & (short_ma < long_ma)

        signals[gold_cross] = 1   # 买入
        signals[death_cross] = -1  # 卖出

        return signals

    def get_params(self) -> dict:
        return {
            "short_window": self.short_window,
            "long_window": self.long_window,
        }