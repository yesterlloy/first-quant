"""策略基类 - 所有策略必须继承此类"""

import pandas as pd
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """策略基类，统一接口规范"""

    def __init__(self, name: str = "base"):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成交易信号

        Args:
            df: 行情数据 DataFrame，必须包含 date, close 列

        Returns:
            pd.Series: 信号序列，1=买入，-1=卖出，0=持有
            索引与 df 的索引对齐
        """
        raise NotImplementedError

    @abstractmethod
    def get_params(self) -> dict:
        """返回策略参数"""
        raise NotImplementedError

    def validate_data(self, df: pd.DataFrame) -> bool:
        """验证输入数据是否满足策略要求"""
        required_cols = ["date", "close"]
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
        if df.empty:
            raise ValueError("DataFrame is empty")
        return True