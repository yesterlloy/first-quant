"""因子检验报告汇总"""

import pandas as pd
from loguru import logger
from factor.registry import FactorRegistry
from factor_test.ic_test import ICAnalyzer
from factor_test.layer_test import LayerTest
from factor_test.regression_test import RegressionTest
from factor_test.decay_test import DecayTest
from factor_test.screening import FactorScreening
from data.db.duckdb_manager import DuckDBManager


class FactorTestReport:
    """因子检验报告生成器

    对所有因子统一跑 IC + 分层 + 回归 + 衰减 + 筛选，
    输出完整检验报告。
    """

    def __init__(self, db: DuckDBManager, forward_period: int = 20):
        self.db = db
        self.ic_analyzer = ICAnalyzer(forward_period=forward_period)
        self.layer_test = LayerTest(n_layers=5, forward_period=forward_period)
        self.regression_test = RegressionTest()
        self.decay_test = DecayTest(max_period=120, step=10)
        self.screening = FactorScreening()

    def run_full_test(self, factor_name: str,
                      start_date: str, end_date: str) -> dict:
        """对单个因子跑完整检验

        Returns:
            dict: ic, layer, regression, decay, screening
        """
        logger.info(f"=== Full test for {factor_name} ===")

        # 获取因子值
        factor_df = self.db.query(f"""
            SELECT code, date, raw_value
            FROM factor_value
            WHERE factor_name = '{factor_name}'
            AND date >= '{start_date}' AND date <= '{end_date}'
        """)

        if factor_df.empty:
            logger.warning(f"No factor data for {factor_name}")
            return {}

        # 获取行情数据（算前瞻收益）
        price_df = self.db.query(f"""
            SELECT code, date, close
            FROM daily_quote
            WHERE date >= '{start_date}' AND date <= '{end_date}'
        """)

        if price_df.empty:
            logger.warning("No price data")
            return {}

        # 计算前瞻收益
        ret_df = self.ic_analyzer.compute_forward_returns(price_df)

        # 1. IC分析
        ic_series = self.ic_analyzer.compute_ic_series(factor_df, ret_df)
        ic_summary = self.ic_analyzer.summarize_ic(ic_series) if not ic_series.empty else {}

        # 2. 分层回测
        layer_series = self.layer_test.compute_layer_series(factor_df, ret_df)
        layer_summary = self.layer_test.summarize_layer(layer_series) if not layer_series.empty else {}

        # 3. 截面回归
        fm_df = self.regression_test.compute_fama_macbeth(factor_df, ret_df)
        reg_summary = self.regression_test.summarize_regression(fm_df) if not fm_df.empty else {}

        # 4. 衰减分析
        decay_df = self.decay_test.compute_decay(factor_df, price_df)
        half_life = self.decay_test.compute_half_life(decay_df)

        # 5. 筛选
        screen = self.screening.screen_factor(ic_summary, layer_summary, reg_summary)

        report = {
            "factor_name": factor_name,
            "ic": ic_summary,
            "layer": layer_summary,
            "regression": reg_summary,
            "decay": {"half_life": half_life, "decay_curve": decay_df},
            "screening": screen,
        }

        logger.info(f"=== {factor_name}: {screen['effectiveness']} ===")
        return report

    def run_all_tests(self, start_date: str, end_date: str) -> pd.DataFrame:
        """对所有因子跑完整检验，输出汇总报告

        Returns:
            DataFrame: 筛选结果表
        """
        factor_names = FactorRegistry.list_names()
        ic_summaries = {}
        layer_summaries = {}
        reg_summaries = {}
        all_reports = {}

        for name in factor_names:
            report = self.run_full_test(name, start_date, end_date)
            if report:
                all_reports[name] = report
                ic_summaries[name] = report["ic"]
                layer_summaries[name] = report["layer"]
                reg_summaries[name] = report["regression"]

        # 批量筛选
        screen_result = self.screening.screen_all_factors(
            factor_names, ic_summaries, layer_summaries, reg_summaries
        )

        logger.info(f"=== Full report: {len(all_reports)} factors tested ===")
        return screen_result