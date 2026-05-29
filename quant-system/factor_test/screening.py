"""因子筛选模块 - 自动过滤无效因子"""

import pandas as pd
import numpy as np
from loguru import logger
from factor_test.ic_test import ICAnalyzer
from factor_test.layer_test import LayerTest
from factor_test.regression_test import RegressionTest
from factor_test.decay_test import DecayTest


class FactorScreening:
    """因子筛选器

    综合IC、分层、回归三个维度，自动筛出有效因子。

    筛选标准：
    - ICIR ≥ 0.5（中等有效）或 ≥ 0.3（弱有效）
    - IC正比例 > 50%
    - |IC|>0.03比例 > 30%
    - 多空收益 > 0 且胜率 > 50%
    - |t|均值 > 2（回归显著）
    """

    # 筛选阈值
    STRONG_THRESH = {
        "icir": 0.5,
        "ic_positive_ratio": 0.5,
        "ic_abs003_ratio": 0.3,
        "long_short": 0.0,
        "ls_win_rate": 0.5,
        "t_mean": 2.0,
    }

    MODERATE_THRESH = {
        "icir": 0.3,
        "ic_positive_ratio": 0.4,
        "ic_abs003_ratio": 0.2,
        "long_short": 0.0,
        "ls_win_rate": 0.4,
        "t_mean": 1.5,
    }

    def screen_factor(self, ic_summary: dict, layer_summary: dict,
                      reg_summary: dict) -> dict:
        """筛选单个因子

        Args:
            ic_summary: IC分析汇总 dict
            layer_summary: 分层回测汇总 dict
            reg_summary: 回归分析汇总 dict

        Returns:
            dict: name, effectiveness, passed_checks, details
        """
        checks = {}

        # IC检验
        checks["icir"] = abs(ic_summary.get("icir", 0))
        checks["ic_positive_ratio"] = ic_summary.get("ic_positive_ratio", 0)
        checks["ic_abs003_ratio"] = ic_summary.get("ic_abs003_ratio", 0)

        # 分层检验
        checks["long_short"] = layer_summary.get("avg_long_short", 0)
        checks["ls_win_rate"] = layer_summary.get("long_short_win_rate", 0)

        # 回归检验
        checks["t_mean"] = abs(reg_summary.get("t_mean", 0))

        # 强有效判断
        strong_pass = all(
            checks[k] >= self.STRONG_THRESH[k]
            for k in ["icir", "ic_positive_ratio", "ic_abs003_ratio", "ls_win_rate", "t_mean"]
        ) and checks["long_short"] > self.STRONG_THRESH["long_short"]

        # 中等有效判断
        moderate_pass = all(
            checks[k] >= self.MODERATE_THRESH[k]
            for k in ["icir", "ic_positive_ratio", "ic_abs003_ratio", "ls_win_rate", "t_mean"]
        ) and checks["long_short"] > self.MODERATE_THRESH["long_short"]

        if strong_pass:
            effectiveness = "strong"
        elif moderate_pass:
            effectiveness = "moderate"
        else:
            effectiveness = "weak"

        result = {
            "effectiveness": effectiveness,
            "checks": checks,
            "passed_strong": strong_pass,
            "passed_moderate": moderate_pass,
        }

        logger.info(f"Factor screening: {effectiveness} (ICIR={checks['icir']:.4f})")
        return result

    def screen_all_factors(self, factor_names: list,
                           ic_summaries: dict, layer_summaries: dict,
                           reg_summaries: dict) -> pd.DataFrame:
        """批量筛选所有因子

        Returns:
            DataFrame [factor_name, effectiveness, icir, ic_positive_ratio,
                       long_short, ls_win_rate, t_mean]
        """
        results = []

        for name in factor_names:
            ic_s = ic_summaries.get(name, {})
            layer_s = layer_summaries.get(name, {})
            reg_s = reg_summaries.get(name, {})

            screen = self.screen_factor(ic_s, layer_s, reg_s)
            results.append({
                "factor_name": name,
                "effectiveness": screen["effectiveness"],
                "icir": screen["checks"]["icir"],
                "ic_positive_ratio": screen["checks"]["ic_positive_ratio"],
                "ic_abs003_ratio": screen["checks"]["ic_abs003_ratio"],
                "long_short": screen["checks"]["long_short"],
                "ls_win_rate": screen["checks"]["ls_win_rate"],
                "t_mean": screen["checks"]["t_mean"],
            })

        result = pd.DataFrame(results)

        # 按有效性排序
        order = {"strong": 0, "moderate": 1, "weak": 2}
        result["sort_key"] = result["effectiveness"].map(order)
        result = result.sort_values("sort_key").drop(columns="sort_key")

        strong_count = (result["effectiveness"] == "strong").sum()
        moderate_count = (result["effectiveness"] == "moderate").sum()
        logger.info(f"Screening result: {strong_count} strong, "
                    f"{moderate_count} moderate, "
                    f"{len(result) - strong_count - moderate_count} weak")

        return result