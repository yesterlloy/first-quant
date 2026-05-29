"""传统因子合成策略 - 等权/IC加权/ICIR加权"""

import pandas as pd
import numpy as np
from loguru import logger
from factor.registry import FactorRegistry
from factor_test.ic_test import ICAnalyzer


class EqualWeightStrategy:
    """等权因子合成策略

    所有有效因子等权相加，最简单的基线。
    """

    def __init__(self, factor_names: list = None):
        self.factor_names = factor_names  # None则用所有因子

    def compute_signal(self, factor_df: pd.DataFrame) -> pd.Series:
        """计算等权合成信号

        Args:
            factor_df: 截面因子值宽表 [code, factor1, factor2, ...]

        Returns:
            Series: 合成信号值（index=code）
        """
        if "code" in factor_df.columns:
            df = factor_df.set_index("code")
        else:
            df = factor_df.copy()

        # 选取因子列
        cols = self.factor_names or [c for c in df.columns if c not in ["date", "name"]]
        cols = [c for c in cols if c in df.columns]

        # Z-score标准化后等权相加
        zscore_df = df[cols].apply(lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0)
        signal = zscore_df.mean(axis=1)
        signal.name = "equal_weight_signal"

        logger.info(f"Equal weight signal: {len(cols)} factors, {len(signal)} stocks")
        return signal


class ICWeightedStrategy:
    """IC加权因子合成策略

    每个因子按历史IC均值加权，IC越高权重越大。
    """

    def __init__(self, ic_summaries: dict, factor_names: list = None):
        """
        Args:
            ic_summaries: {factor_name: {ic_mean, icir, ...}}
        """
        self.ic_summaries = ic_summaries
        self.factor_names = factor_names

    def compute_signal(self, factor_df: pd.DataFrame) -> pd.Series:
        """IC加权合成信号"""
        if "code" in factor_df.columns:
            df = factor_df.set_index("code")
        else:
            df = factor_df.copy()

        cols = self.factor_names or [c for c in df.columns if c not in ["date", "name"]]
        cols = [c for c in cols if c in df.columns]

        # 计算权重：|IC均值| / sum(|IC均值|)
        weights = {}
        total_ic = 0
        for col in cols:
            ic_mean = abs(self.ic_summaries.get(col, {}).get("ic_mean", 0))
            weights[col] = ic_mean
            total_ic += ic_mean

        if total_ic < 1e-10:
            # 全是0 → 等权回退
            return EqualWeightStrategy(cols).compute_signal(factor_df)

        for col in weights:
            weights[col] /= total_ic

        # Z-score标准化后加权
        zscore_df = df[cols].apply(lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0)
        signal = sum(zscore_df[col] * weights[col] for col in cols)
        signal.name = "ic_weighted_signal"

        logger.info(f"IC weighted: top weights = "
                    f"{sorted(weights.items(), key=lambda x: -x[1])[:5]}")
        return signal


class ICIRWeightedStrategy:
    """ICIR加权因子合成策略

    每个因子按ICIR加权，ICIR越高权重越大（风险调整后预测力）。
    """

    def __init__(self, ic_summaries: dict, factor_names: list = None):
        self.ic_summaries = ic_summaries
        self.factor_names = factor_names

    def compute_signal(self, factor_df: pd.DataFrame) -> pd.Series:
        """ICIR加权合成信号"""
        if "code" in factor_df.columns:
            df = factor_df.set_index("code")
        else:
            df = factor_df.copy()

        cols = self.factor_names or [c for c in df.columns if c not in ["date", "name"]]
        cols = [c for c in cols if c in df.columns]

        # 权重：|ICIR| / sum(|ICIR|)
        weights = {}
        total_icir = 0
        for col in cols:
            icir = abs(self.ic_summaries.get(col, {}).get("icir", 0))
            weights[col] = icir
            total_icir += icir

        if total_icir < 1e-10:
            return EqualWeightStrategy(cols).compute_signal(factor_df)

        for col in weights:
            weights[col] /= total_icir

        zscore_df = df[cols].apply(lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0)
        signal = sum(zscore_df[col] * weights[col] for col in cols)
        signal.name = "icir_weighted_signal"

        logger.info(f"ICIR weighted: top weights = "
                    f"{sorted(weights.items(), key=lambda x: -x[1])[:5]}")
        return signal