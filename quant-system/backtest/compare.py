"""多策略对比回测"""

import pandas as pd
import numpy as np
from loguru import logger
from strategy.ml_factor import EqualWeightStrategy, ICWeightedStrategy, ICIRWeightedStrategy
from ml.evaluator import MLEvaluator
from data.db.duckdb_manager import DuckDBManager


class StrategyCompare:
    """多策略对比回测

    对比策略：
    1. 等权合成
    2. IC加权合成
    3. ICIR加权合成
    4. LightGBM ML
    5. XGBoost ML（可选）
    6. Ensemble融合

    每个策略：
    - 每月末生成截面信号
    - top30%做多，bottom30%做空
    - 持有1个月
    - 统计IC/多空收益/胜率
    """

    def __init__(self, db: DuckDBManager, forward_period: int = 20):
        self.db = db
        self.evaluator = MLEvaluator(forward_period=forward_period)

    def run_comparison(self, start_date: str, end_date: str,
                       ic_summaries: dict = None) -> pd.DataFrame:
        """跑所有策略对比

        Args:
            ic_summaries: {factor_name: {ic_mean, icir, ...}} 用于IC/ICIR加权

        Returns:
            DataFrame: 对比结果 [strategy, rank_ic, long_short, n_periods, win_rate]
        """
        # 获取因子数据
        factor_df = self.db.query(f"""
            SELECT code, date, factor_name, raw_value
            FROM factor_value
            WHERE date >= '{start_date}' AND date <= '{end_date}'
        """)

        # 获取行情数据算收益
        price_df = self.db.query(f"""
            SELECT code, date, close
            FROM daily_quote
            WHERE date >= '{start_date}' AND date <= '{end_date}'
        """)

        if factor_df.empty or price_df.empty:
            logger.error("No data for comparison")
            return pd.DataFrame()

        # 计算前瞻收益
        ret_df = self.evaluator.ic_analyzer.compute_forward_returns(price_df)

        # 按月截面计算
        dates = sorted(factor_df["date"].unique())
        model_results = {}

        # 1. 等权策略
        ew_strategy = EqualWeightStrategy()
        ew_ics = []
        ew_ls = []
        for d in dates:
            f_cross = factor_df[factor_df["date"] == d].pivot_table(
                index="code", columns="factor_name", values="raw_value"
            ).reset_index()
            r_cross = ret_df[ret_df["date"] == d].set_index("code")["forward_return"]

            signal = ew_strategy.compute_signal(f_cross)
            common = signal.index.intersection(r_cross.index)
            if len(common) < 50:
                continue

            eval_result = self.evaluator.evaluate_predictions(
                signal[common], r_cross[common], "equal_weight"
            )
            ew_ics.append(eval_result["rank_ic"])
            ew_ls.append(eval_result["long_short"])

        if ew_ics:
            model_results["equal_weight"] = {
                "rank_ic": np.mean(ew_ics),
                "long_short": np.mean(ew_ls),
                "n_stocks": len(common),
                "n_periods": len(ew_ics),
                "win_rate": sum(ic > 0 for ic in ew_ics) / len(ew_ics),
            }

        # 2. IC加权策略
        if ic_summaries:
            ic_strategy = ICWeightedStrategy(ic_summaries)
            ic_ics = []
            ic_ls = []
            for d in dates:
                f_cross = factor_df[factor_df["date"] == d].pivot_table(
                    index="code", columns="factor_name", values="raw_value"
                ).reset_index()
                r_cross = ret_df[ret_df["date"] == d].set_index("code")["forward_return"]

                signal = ic_strategy.compute_signal(f_cross)
                common = signal.index.intersection(r_cross.index)
                if len(common) < 50:
                    continue

                eval_result = self.evaluator.evaluate_predictions(
                    signal[common], r_cross[common], "ic_weighted"
                )
                ic_ics.append(eval_result["rank_ic"])
                ic_ls.append(eval_result["long_short"])

            if ic_ics:
                model_results["ic_weighted"] = {
                    "rank_ic": np.mean(ic_ics),
                    "long_short": np.mean(ic_ls),
                    "n_stocks": len(common),
                    "n_periods": len(ic_ics),
                    "win_rate": sum(ic > 0 for ic in ic_ics) / len(ic_ics),
                }

        # 3. ML信号（从 ml_signal 表读取）
        try:
            ml_df = self.db.query(f"""
                SELECT code, date, model_name, predicted_return
                FROM ml_signal
                WHERE date >= '{start_date}' AND date <= '{end_date}'
            """)
            if not ml_df.empty:
                for model_name in ml_df["model_name"].unique():
                    model_signals = ml_df[ml_df["model_name"] == model_name]
                    ml_ics = []
                    ml_ls = []
                    for d in model_signals["date"].unique():
                        m_cross = model_signals[model_signals["date"] == d].set_index("code")["predicted_return"]
                        r_cross = ret_df[ret_df["date"] == d].set_index("code")["forward_return"]
                        common = m_cross.index.intersection(r_cross.index)
                        if len(common) < 50:
                            continue
                        eval_result = self.evaluator.evaluate_predictions(
                            m_cross[common], r_cross[common], model_name
                        )
                        ml_ics.append(eval_result["rank_ic"])
                        ml_ls.append(eval_result["long_short"])

                    if ml_ics:
                        model_results[model_name] = {
                            "rank_ic": np.mean(ml_ics),
                            "long_short": np.mean(ml_ls),
                            "n_stocks": len(common),
                            "n_periods": len(ml_ics),
                            "win_rate": sum(ic > 0 for ic in ml_ics) / len(ml_ics),
                        }
        except Exception:
            logger.info("No ML signals in DB yet")

        # 对比汇总
        result = self.evaluator.compare_models(model_results)
        logger.info(f"=== Strategy comparison: {len(model_results)} strategies ===")
        return result