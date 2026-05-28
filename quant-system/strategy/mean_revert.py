"""均值回归策略 - 偏离均值时反向操作"""

import pandas as pd
from strategy.base import BaseStrategy


class MeanRevertStrategy(BaseStrategy):
    """均值回归策略：价格偏离均值超过阈值时反向操作

    价格低于均值-N倍标准差 → 买入（低估）
    价格高于均值+N倍标准差 → 卖出（高估）
    """

    def __init__(self, lookback: int = 20, entry_z: float = 2.0,
                 exit_z: float = 0.5):
        super().__init__(name="mean_revert")
        self.lookback = lookback
        self.entry_z = entry_z   # 入场阈值（Z-score）
        self.exit_z = exit_z     # 退出阈值

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        self.validate_data(df)

        signals = pd.Series(0, index=df.index, dtype=int)

        # 计算滚动均值和标准差
        rolling_mean = df["close"].rolling(window=self.lookback, min_periods=1).mean()
        rolling_std = df["close"].rolling(window=self.lookback, min_periods=1).std()

        # Z-score
        z_score = (df["close"] - rolling_mean) / rolling_std

        # 信号生成
        # 价格显著低于均值 → 买入
        signals[z_score < -self.entry_z] = 1
        # 价格显著高于均值 → 卖出
        signals[z_score > self.entry_z] = -1

        return signals

    def get_params(self) -> dict:
        return {
            "lookback": self.lookback,
            "entry_z": self.entry_z,
            "exit_z": self.exit_z,
        }