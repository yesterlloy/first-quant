"""IC分析模块 - 因子信息系数检验"""

import pandas as pd
import numpy as np
from loguru import logger


class ICAnalyzer:
    """IC（Information Coefficient）分析器

    计算因子值与未来收益的秩相关系数，评估因子预测力。

    检验指标：
    - Rank IC：因子值与未来收益的Spearman秩相关
    - IC均值：时间序列IC的平均值
    - IC标准差：IC的波动性
    - ICIR：IC均值/IC标准差（风险调整后预测力）
    - IC正比例：IC>0的比例（一致性）
    - |IC|>0.03比例：有效IC的比例
    """

    def __init__(self, forward_period: int = 20):
        """
        Args:
            forward_period: 前瞻收益期（交易日），默认20日（约1个月）
        """
        self.forward_period = forward_period

    def compute_rank_ic(self, factor_values: pd.Series,
                        forward_returns: pd.Series) -> float:
        """计算单期 Rank IC（Spearman秩相关）

        Args:
            factor_values: 因子截面值 Series（index=code）
            forward_returns: 未来N日收益 Series（index=code）

        Returns:
            Rank IC 值
        """
        aligned = pd.DataFrame({
            "factor": factor_values,
            "return": forward_returns,
        }).dropna()

        if len(aligned) < 30:  # 样本太少，IC不可靠
            return np.nan

        # Spearman秩相关 = Pearson相关(rank_x, rank_y)
        return aligned["factor"].rank().corr(aligned["return"].rank())

    def compute_ic_series(self, factor_df: pd.DataFrame,
                          return_df: pd.DataFrame) -> pd.DataFrame:
        """计算时间序列IC

        Args:
            factor_df: 因子值 DataFrame [code, date, raw_value]
            return_df: 收益率 DataFrame [code, date, forward_return]

        Returns:
            DataFrame [date, rank_ic, normal_ic]
        """
        # 对每个日期截面计算IC
        dates = sorted(factor_df["date"].unique())
        ic_list = []

        for d in dates:
            f_cross = factor_df[factor_df["date"] == d].set_index("code")["raw_value"]
            r_cross = return_df[return_df["date"] == d].set_index("code")["forward_return"]

            # 对齐
            common = f_cross.index.intersection(r_cross.index)
            if len(common) < 30:
                continue

            rank_ic = self.compute_rank_ic(f_cross[common], r_cross[common])
            normal_ic = f_cross[common].corr(r_cross[common])  # Pearson IC

            ic_list.append({
                "date": d,
                "rank_ic": rank_ic,
                "normal_ic": normal_ic,
                "sample_size": len(common),
            })

        result = pd.DataFrame(ic_list)
        logger.info(f"IC series: {len(result)} periods computed")
        return result

    def summarize_ic(self, ic_series: pd.DataFrame) -> dict:
        """IC统计汇总

        Returns:
            dict: ic_mean, ic_std, icir, ic_positive_ratio, ic_abs003_ratio
        """
        rank_ic = ic_series["rank_ic"].dropna()

        if len(rank_ic) < 5:
            logger.warning("Too few IC observations for summary")
            return {}

        result = {
            "ic_mean": float(rank_ic.mean()),
            "ic_std": float(rank_ic.std()),
            "icir": float(rank_ic.mean() / rank_ic.std()) if rank_ic.std() > 0 else 0,
            "ic_positive_ratio": float((rank_ic > 0).sum() / len(rank_ic)),
            "ic_abs003_ratio": float((rank_ic.abs() > 0.03).sum() / len(rank_ic)),
            "periods": len(rank_ic),
        }

        # 判断因子有效性
        if abs(result["icir"]) >= 0.5:
            result["effectiveness"] = "strong"
        elif abs(result["icir"]) >= 0.3:
            result["effectiveness"] = "moderate"
        else:
            result["effectiveness"] = "weak"

        logger.info(f"IC Summary: IC_mean={result['ic_mean']:.4f}, "
                    f"ICIR={result['icir']:.4f}, effect={result['effectiveness']}")
        return result

    def compute_forward_returns(self, price_df: pd.DataFrame,
                                period: int = None) -> pd.DataFrame:
        """计算前瞻收益率

        Args:
            price_df: 日线行情 DataFrame [code, date, close]
            period: 前瞻期，默认用 self.forward_period

        Returns:
            DataFrame [code, date, forward_return]
        """
        period = period or self.forward_period
        price_df = price_df.sort_values(["code", "date"])

        # 每只股票计算N日后收益率
        price_df["close_future"] = price_df.groupby("code")["close"].shift(-period)
        price_df["forward_return"] = (
            price_df["close_future"] / price_df["close"] - 1.0
        )

        result = price_df[["code", "date", "forward_return"]].dropna()
        logger.info(f"Forward returns computed: {len(result)} rows, period={period}")
        return result