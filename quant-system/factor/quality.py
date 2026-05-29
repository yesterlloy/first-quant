"""质量因子 - ROE/ROA/资产负债率/现金流质量"""

import pandas as pd
import numpy as np
from factor.base import BaseFactor, FactorInfo


class ROE(BaseFactor):
    """净资产收益率（Return on Equity）"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="ROE",
            category="quality",
            description="Return on Equity",
            freq="quarterly",
            depends=["financial_ext"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 ROE"""
        return pd.to_numeric(df["roe"], errors="coerce")


class ROA(BaseFactor):
    """总资产净利率（Return on Assets）"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="ROA",
            category="quality",
            description="Return on Assets (net profit / total assets)",
            freq="quarterly",
            depends=["financial_ext"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 ROA = 净利润 / 总资产

        df 需包含: net_profit, total_assets
        """
        net_profit = pd.to_numeric(df["net_profit"], errors="coerce")
        total_assets = pd.to_numeric(df["total_assets"], errors="coerce")
        roa = net_profit / total_assets
        roa[(total_assets <= 0) | total_assets.isna()] = np.nan
        return roa


class DebtRatio(BaseFactor):
    """资产负债率因子"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="DebtRatio",
            category="quality",
            description="Debt-to-Asset ratio (total liability / total assets)",
            freq="quarterly",
            depends=["financial_ext"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 资产负债率

        df 需包含: total_liability, total_assets
        注意：低负债率是好公司特征，所以因子方向为 1 - debt_ratio（越低越好）
        """
        total_liability = pd.to_numeric(df["total_liability"], errors="coerce")
        total_assets = pd.to_numeric(df["total_assets"], errors="coerce")
        debt_ratio = total_liability / total_assets
        debt_ratio[(total_assets <= 0) | total_assets.isna()] = np.nan
        # 翻转方向：低负债率 → 高因子值 → 更好
        return 1.0 - debt_ratio


class CashFlowQuality(BaseFactor):
    """现金流质量因子（经营现金流 / 净利润）"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="CashFlowQuality",
            category="quality",
            description="Operating cash flow / net profit ratio",
            freq="quarterly",
            depends=["financial_ext"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 经营现金流/净利润

        df 需包含: ocf, net_profit
        比值越高，利润含金量越高
        """
        ocf = pd.to_numeric(df["ocf"], errors="coerce")
        net_profit = pd.to_numeric(df["net_profit"], errors="coerce")
        cfq = ocf / net_profit
        # 净利润为负或接近0时，比值无意义
        cfq[(net_profit.abs() < 1e-6) | net_profit.isna()] = np.nan
        return cfq