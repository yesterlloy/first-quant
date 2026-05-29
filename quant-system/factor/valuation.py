"""估值因子 - EP/BP/DP/SP"""

import pandas as pd
import numpy as np
from factor.base import BaseFactor, FactorInfo


class EP(BaseFactor):
    """盈利/价格因子（Earnings-to-Price = 1/PE）"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="EP",
            category="valuation",
            description="Earnings-to-Price ratio (1/PE)",
            freq="quarterly",
            depends=["financial_ext", "daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 EP = 1/PE

        df 需包含列: code, pe
        PE 为负或 0 的股票置 NaN
        """
        pe = pd.to_numeric(df["pe"], errors="coerce")
        # PE 为负或过小的不合理，置 NaN
        ep = 1.0 / pe
        ep[(pe <= 0) | (pe.abs() < 1e-6)] = np.nan
        return ep


class BP(BaseFactor):
    """账面/价格因子（Book-to-Price = 1/PB）"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="BP",
            category="valuation",
            description="Book-to-Price ratio (1/PB)",
            freq="quarterly",
            depends=["financial_ext", "daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 BP = 1/PB"""
        pb = pd.to_numeric(df["pb"], errors="coerce")
        bp = 1.0 / pb
        bp[(pb <= 0) | (pb.abs() < 1e-6)] = np.nan
        return bp


class DP(BaseFactor):
    """分红/价格因子（Dividend-to-Price = 股息率）"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="DP",
            category="valuation",
            description="Dividend yield (dividend per share / price)",
            freq="annual",
            depends=["dividend", "daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 DP = 每股分红 / 收盘价

        df 需包含列: code, dividend_per_share, close
        """
        dps = pd.to_numeric(df["dividend_per_share"], errors="coerce")
        close = pd.to_numeric(df["close"], errors="coerce")
        dp = dps / close
        dp[(close <= 0) | dps.isna()] = np.nan
        return dp


class SP(BaseFactor):
    """营收/市值因子（Sales-to-Price = 营收/总市值）"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="SP",
            category="valuation",
            description="Sales-to-Price ratio (revenue / total market cap)",
            freq="quarterly",
            depends=["financial_ext", "daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 SP = 营收 / 总市值

        df 需包含列: code, revenue, total_mv
        """
        revenue = pd.to_numeric(df["revenue"], errors="coerce")
        total_mv = pd.to_numeric(df["total_mv"], errors="coerce")
        sp = revenue / total_mv
        sp[(total_mv <= 0) | total_mv.isna() | revenue.isna()] = np.nan
        return sp