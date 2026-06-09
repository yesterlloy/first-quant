"""组合构建模块 - 筛选Top N股票构建目标组合"""

import pandas as pd
from loguru import logger


class PortfolioBuilder:
    """构建目标投资组合"""

    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    def build_portfolio(self, signals: pd.DataFrame) -> pd.DataFrame:
        """构建目标组合

        Args:
            signals: [code, predicted_return, signal]

        Returns:
            DataFrame: [code, predicted_return, rank]
        """
        if signals.empty:
            logger.warning("Empty signals, return empty portfolio")
            return pd.DataFrame()

        # 按 predicted_return 降序排序
        sorted_signals = signals.sort_values("predicted_return", ascending=False)

        # 选取 Top N
        portfolio = sorted_signals.head(self.top_n).copy()

        # 添加排名
        portfolio["rank"] = range(1, len(portfolio) + 1)

        logger.info(f"Built portfolio with {len(portfolio)} stocks (top {self.top_n})")

        return portfolio[["code", "predicted_return", "rank"]]