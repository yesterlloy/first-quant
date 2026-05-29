"""分层回测模块 - 因子分层收益检验"""

import pandas as pd
import numpy as np
from loguru import logger


class LayerTest:
    """分层回测检验

    每月末按因子值排序，分N层，各层等权持仓1个月，
    统计各层收益、多空收益、单调性。
    """

    def __init__(self, n_layers: int = 5, forward_period: int = 20):
        """
        Args:
            n_layers: 分层数，默认5层
            forward_period: 前瞻收益期（交易日），默认20日
        """
        self.n_layers = n_layers
        self.forward_period = forward_period

    def compute_layers(self, factor_values: pd.Series,
                       forward_returns: pd.Series) -> pd.DataFrame:
        """单期分层回测

        Args:
            factor_values: 因子截面值 Series（index=code）
            forward_returns: 未来收益 Series（index=code）

        Returns:
            DataFrame [layer, avg_return, n_stocks, factor_avg]
        """
        aligned = pd.DataFrame({
            "factor": factor_values,
            "return": forward_returns,
        }).dropna()

        if len(aligned) < self.n_layers * 10:
            logger.warning(f"Too few stocks ({len(aligned)}) for {self.n_layers}-layer split")
            return pd.DataFrame()

        # 按因子值排序分层
        aligned = aligned.sort_values("factor")
        aligned["layer"] = pd.qcut(
            aligned["factor"], self.n_layers, labels=False, duplicates="drop"
        )

        # 各层统计
        layer_stats = aligned.groupby("layer").agg(
            avg_return=("return", "mean"),
            n_stocks=("return", "count"),
            factor_avg=("factor", "mean"),
        ).reset_index()

        # 多空收益：top层 - bottom层
        top_return = layer_stats[layer_stats["layer"] == self.n_layers - 1]["avg_return"].values[0]
        bottom_return = layer_stats[layer_stats["layer"] == 0]["avg_return"].values[0]
        layer_stats["long_short"] = top_return - bottom_return

        logger.info(f"Layer test: long_short={layer_stats['long_short'].values[0]:.4f}")
        return layer_stats

    def compute_layer_series(self, factor_df: pd.DataFrame,
                             return_df: pd.DataFrame) -> pd.DataFrame:
        """时间序列分层回测

        Args:
            factor_df: [code, date, raw_value]
            return_df: [code, date, forward_return]

        Returns:
            DataFrame [date, layer, avg_return, n_stocks, long_short, monotonicity]
        """
        dates = sorted(factor_df["date"].unique())
        all_results = []

        for d in dates:
            f_cross = factor_df[factor_df["date"] == d].set_index("code")["raw_value"]
            r_cross = return_df[return_df["date"] == d].set_index("code")["forward_return"]

            common = f_cross.index.intersection(r_cross.index)
            if len(common) < self.n_layers * 10:
                continue

            layer_df = self.compute_layers(f_cross[common], r_cross[common])
            if layer_df.empty:
                continue

            # 单调性：各层收益是否单调递增/递减
            returns = layer_df["avg_return"].values
            monotonic = self._check_monotonic(returns)

            layer_df["date"] = d
            layer_df["monotonic"] = monotonic
            all_results.append(layer_df)

        if all_results:
            result = pd.concat(all_results, ignore_index=True)
            logger.info(f"Layer series: {len(result)} rows, {len(dates)} periods")
            return result

        return pd.DataFrame()

    def _check_monotonic(self, returns: np.ndarray) -> bool:
        """检查收益是否单调递增或递减"""
        # 完全单调
        diffs = np.diff(returns)
        if (diffs >= 0).all() or (diffs <= 0).all():
            return True
        # 允许1个偏差的"基本单调"
        n_violations = sum(diffs < 0) if returns[0] < returns[-1] else sum(diffs > 0)
        return n_violations <= 1

    def summarize_layer(self, layer_series: pd.DataFrame) -> dict:
        """分层回测统计汇总

        Returns:
            dict: avg_long_short, long_short_win_rate, avg_monotonic_ratio, layer_returns
        """
        if layer_series.empty:
            return {}

        # 多空平均收益
        avg_ls = float(layer_series.groupby("date")["long_short"].first().mean())

        # 多空胜率
        ls_series = layer_series.groupby("date")["long_short"].first()
        win_rate = float((ls_series > 0).sum() / len(ls_series))

        # 单调性比例
        mono_series = layer_series.groupby("date")["monotonic"].first()
        mono_ratio = float(mono_series.mean())

        # 各层平均收益
        layer_returns = {}
        for layer in range(self.n_layers):
            avg = float(layer_series[layer_series["layer"] == layer]["avg_return"].mean())
            layer_returns[f"layer_{layer}"] = avg

        result = {
            "avg_long_short": avg_ls,
            "long_short_win_rate": win_rate,
            "monotonic_ratio": mono_ratio,
            "periods": len(ls_series),
            "layer_returns": layer_returns,
        }

        logger.info(f"Layer summary: avg_ls={avg_ls:.4f}, "
                    f"win_rate={win_rate:.2f}, mono={mono_ratio:.2f}")
        return result