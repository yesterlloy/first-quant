"""仓位计算模块 - 信号强度加权分配仓位"""

import pandas as pd
from loguru import logger


class PositionCalculator:
    """基于信号强度计算目标仓位"""

    def __init__(self, total_ratio: float = 0.8, max_single: float = 0.1):
        self.total_ratio = total_ratio  # 总仓位比例
        self.max_single = max_single    # 单票最大仓位

    def calc_weights(self, portfolio: pd.DataFrame, prices: pd.DataFrame,
                     total_capital: float) -> pd.DataFrame:
        """计算目标仓位

        Args:
            portfolio: [code, predicted_return]
            prices: [code, close]
            total_capital: 总资金

        Returns:
            DataFrame: [code, weight, shares, amount]
        """
        if portfolio.empty:
            logger.warning("Empty portfolio, return empty positions")
            return pd.DataFrame()

        # 合并价格
        df = portfolio.merge(prices, on="code", how="inner")
        if df.empty:
            logger.warning("No price data for portfolio stocks")
            return pd.DataFrame()

        # 1. 信号强度加权
        total_signal = df["predicted_return"].abs().sum()
        if total_signal == 0:
            df["weight"] = 1.0 / len(df)
        else:
            df["weight"] = df["predicted_return"].abs() / total_signal

        # 2. 单票仓位上限处理
        df = self._apply_weight_limits(df)

        # 3. 计算金额和股数
        available_capital = total_capital * self.total_ratio
        df["amount"] = df["weight"] * available_capital

        # 4. 计算股数（向下取整100股）
        df["shares"] = (df["amount"] / df["close"]).astype(int) // 100 * 100

        # 过滤掉0股
        df = df[df["shares"] > 0].copy()

        logger.info(f"Calculated positions for {len(df)} stocks")

        return df[["code", "weight", "shares", "amount"]]

    def _apply_weight_limits(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用单票仓位上限，超额部分分配给其他股票"""
        df = df.copy()
        n = len(df)

        for i in range(n):
            # 找出超额的股票
            over_mask = df["weight"] > self.max_single
            if not over_mask.any():
                break

            # 计算超额总和
            excess = (df.loc[over_mask, "weight"] - self.max_single).sum()
            df.loc[over_mask, "weight"] = self.max_single

            # 将超额部分分配给未达上限的股票
            under_mask = df["weight"] < self.max_single
            if under_mask.any() and excess > 0:
                under_total = df.loc[under_mask, "weight"].sum()
                if under_total > 0:
                    # 按比例分配
                    df.loc[under_mask, "weight"] += (
                        df.loc[under_mask, "weight"] / under_total * excess
                    )

        return df
