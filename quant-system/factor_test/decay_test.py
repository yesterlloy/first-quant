"""因子衰减分析模块 - 预测力半衰期"""

import pandas as pd
import numpy as np
from loguru import logger
from factor_test.ic_test import ICAnalyzer


class DecayTest:
    """因子衰减分析

    计算不同前瞻期的IC，看因子预测力随时间衰减的速度。
    半衰期 = IC下降到初始值一半所需的前瞻期数。
    """

    def __init__(self, max_period: int = 120, step: int = 10):
        """
        Args:
            max_period: 最大前瞻期（交易日），默认120（约半年）
            step: 前瞻期步长
        """
        self.max_period = max_period
        self.step = step

    def compute_decay(self, factor_df: pd.DataFrame,
                      price_df: pd.DataFrame) -> pd.DataFrame:
        """计算因子衰减曲线

        Args:
            factor_df: [code, date, raw_value]
            price_df: [code, date, close]

        Returns:
            DataFrame [forward_period, ic_mean, icir]
        """
        ic_analyzer = ICAnalyzer()
        results = []

        for period in range(1, self.max_period + 1, self.step):
            # 计算该前瞻期的收益
            price_sorted = price_df.sort_values(["code", "date"])
            price_sorted["close_future"] = price_sorted.groupby("code")["close"].shift(-period)
            price_sorted["forward_return"] = (
                price_sorted["close_future"] / price_sorted["close"] - 1.0
            )
            ret_df = price_sorted[["code", "date", "forward_return"]].dropna()

            # 计算IC序列
            ic_series = ic_analyzer.compute_ic_series(factor_df, ret_df)
            if ic_series.empty:
                continue

            summary = ic_analyzer.summarize_ic(ic_series)
            if summary:
                results.append({
                    "forward_period": period,
                    "ic_mean": summary.get("ic_mean", 0),
                    "icir": summary.get("icir", 0),
                    "ic_abs003_ratio": summary.get("ic_abs003_ratio", 0),
                })

        result = pd.DataFrame(results)
        logger.info(f"Decay curve: {len(result)} periods computed")
        return result

    def compute_half_life(self, decay_df: pd.DataFrame) -> float:
        """估算半衰期

        用IC随前瞻期的衰减拟合指数衰减模型：
        IC(t) = IC(0) * exp(-t / half_life)

        Returns:
            半衰期（交易日数），NaN表示无法估算
        """
        if decay_df.empty or len(decay_df) < 3:
            return np.nan

        ic_values = decay_df["ic_mean"].values
        periods = decay_df["forward_period"].values

        # 找IC最大值对应的期作为 IC(0)
        max_idx = np.argmax(np.abs(ic_values))
        ic_initial = ic_values[max_idx]

        if abs(ic_initial) < 1e-6:
            return np.nan

        # 拟合: log(|IC/IC0|) = -period / half_life
        ratio = np.abs(ic_values / ic_initial)
        # 只取 ratio < 1 的点
        valid_mask = (ratio > 0) & (ratio < 1)
        if valid_mask.sum() < 2:
            return np.nan

        log_ratio = np.log(ratio[valid_mask])
        valid_periods = periods[valid_mask] - periods[max_idx]

        # OLS: log_ratio = -valid_periods / half_life
        if np.var(valid_periods) < 1e-10:
            return np.nan

        slope = np.cov(log_ratio, valid_periods)[0, 1] / np.var(valid_periods)
        half_life = -1.0 / slope if slope < 0 else np.nan

        logger.info(f"Half-life estimate: {half_life:.1f} trading days")
        return half_life