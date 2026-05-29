"""截面回归分析模块 - Fama-MacBeth回归"""

import pandas as pd
import numpy as np
from loguru import logger


class RegressionTest:
    """截面回归检验（Fama-MacBeth方法）

    对每个时间截面：
    forward_return = alpha + beta * factor_value + epsilon

    统计：
    - β均值：因子溢价
    - t值：β的显著性（|t|>2为显著）
    """

    def compute_single_regression(self, factor_values: pd.Series,
                                  forward_returns: pd.Series) -> dict:
        """单期截面回归

        Returns:
            dict: alpha, beta, t_value, r_squared, n_stocks
        """
        aligned = pd.DataFrame({
            "factor": factor_values,
            "return": forward_returns,
        }).dropna()

        if len(aligned) < 30:
            return {}

        x = aligned["factor"].values
        y = aligned["return"].values

        # OLS: y = alpha + beta * x
        n = len(x)
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        beta = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
        alpha = y_mean - beta * x_mean

        # 残差和 R²
        residuals = y - alpha - beta * x
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # t值：beta / se(beta)
        se_beta = np.sqrt(ss_res / (n - 2) / np.sum((x - x_mean) ** 2))
        t_value = beta / se_beta if se_beta > 0 else 0

        return {
            "alpha": float(alpha),
            "beta": float(beta),
            "t_value": float(t_value),
            "r_squared": float(r_squared),
            "n_stocks": n,
        }

    def compute_fama_macbeth(self, factor_df: pd.DataFrame,
                             return_df: pd.DataFrame) -> pd.DataFrame:
        """Fama-MacBeth回归（时间序列截面回归）

        Args:
            factor_df: [code, date, raw_value]
            return_df: [code, date, forward_return]

        Returns:
            DataFrame [date, alpha, beta, t_value, r_squared, n_stocks]
        """
        dates = sorted(factor_df["date"].unique())
        results = []

        for d in dates:
            f_cross = factor_df[factor_df["date"] == d].set_index("code")["raw_value"]
            r_cross = return_df[return_df["date"] == d].set_index("code")["forward_return"]

            common = f_cross.index.intersection(r_cross.index)
            if len(common) < 30:
                continue

            reg = self.compute_single_regression(f_cross[common], r_cross[common])
            if reg:
                reg["date"] = d
                results.append(reg)

        result = pd.DataFrame(results)
        logger.info(f"Fama-MacBeth: {len(result)} periods")
        return result

    def summarize_regression(self, fm_df: pd.DataFrame) -> dict:
        """Fama-MacBeth回归汇总

        Returns:
            dict: beta_mean, beta_t, t_value_mean, significant_ratio
        """
        if fm_df.empty:
            return {}

        beta_mean = float(fm_df["beta"].mean())
        beta_std = float(fm_df["beta"].std())
        t_mean = float(fm_df["t_value"].mean())
        significant = float((fm_df["t_value"].abs() > 2).sum() / len(fm_df))

        result = {
            "beta_mean": beta_mean,
            "beta_std": beta_std,
            "t_mean": t_mean,
            "significant_ratio": significant,
            "periods": len(fm_df),
        }

        logger.info(f"Regression summary: beta_mean={beta_mean:.4f}, "
                    f"t_mean={t_mean:.2f}, sig_ratio={significant:.2f}")
        return result