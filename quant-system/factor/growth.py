"""成长因子 - 营收增长率/净利润增长率/ROE变化率"""

import pandas as pd
import numpy as np
from factor.base import BaseFactor, FactorInfo


class RevenueGrowth(BaseFactor):
    """营收同比增长率因子"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="RevenueGrowth",
            category="growth",
            description="Revenue YoY growth rate",
            freq="quarterly",
            depends=["financial_ext"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算营收同比增长率

        df 需包含: code, date, revenue
        同一股票相邻年度同期 revenue 的增长率
        """
        revenue = pd.to_numeric(df["revenue"], errors="coerce")
        if "revenue_prev_y" in df.columns:
            # 已提供上年同期营收
            prev = pd.to_numeric(df["revenue_prev_y"], errors="coerce")
            growth = (revenue - prev) / (prev.abs() + 1e-10)
            growth[(prev.abs() < 1e-6) | prev.isna()] = np.nan
            return growth
        else:
            # 无法直接计算同比，返回 NaN（需引擎预计算）
            return pd.Series(np.nan, index=df.index)


class ProfitGrowth(BaseFactor):
    """净利润同比增长率因子"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="ProfitGrowth",
            category="growth",
            description="Net profit YoY growth rate",
            freq="quarterly",
            depends=["financial_ext"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算净利润同比增长率

        df 需包含: code, date, net_profit, net_profit_prev_y
        """
        net_profit = pd.to_numeric(df["net_profit"], errors="coerce")
        if "net_profit_prev_y" in df.columns:
            prev = pd.to_numeric(df["net_profit_prev_y"], errors="coerce")
            growth = (net_profit - prev) / (prev.abs() + 1e-10)
            growth[(prev.abs() < 1e-6) | prev.isna()] = np.nan
            return growth
        else:
            return pd.Series(np.nan, index=df.index)


class ROEChange(BaseFactor):
    """ROE变化率因子（ΔROE）"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="ROEChange",
            category="growth",
            description="ROE change rate (ΔROE = ROE_t - ROE_t-1)",
            freq="quarterly",
            depends=["financial_ext"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 ROE 变化率

        df 需包含: code, roe, roe_prev
        """
        roe = pd.to_numeric(df["roe"], errors="coerce")
        if "roe_prev" in df.columns:
            prev = pd.to_numeric(df["roe_prev"], errors="coerce")
            return roe - prev
        else:
            return pd.Series(np.nan, index=df.index)