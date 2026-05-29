"""因子模块集成测试"""

import pytest
import pandas as pd
import numpy as np
from factor.base import BaseFactor, FactorInfo
from factor.valuation import EP, BP, DP, SP
from factor.quality import ROE, ROA, DebtRatio, CashFlowQuality
from factor.growth import RevenueGrowth, ProfitGrowth, ROEChange
from factor.technical import MOM, REV, VOL, TURN, LIQ
from factor.scale import MCAP, FCAP
from factor.registry import FactorRegistry


class TestFactorBase:
    """因子基类测试"""

    def test_factor_info(self):
        ep = EP()
        info = ep.info()
        assert info.name == "EP"
        assert info.category == "valuation"

    def test_neutralize_industry(self):
        factor = pd.Series({
            "A": 1.0, "B": 2.0, "C": 3.0,
            "D": 4.0, "E": 5.0, "F": 6.0,
        })
        industry = pd.Series({
            "A": "金融", "B": "金融", "C": "科技",
            "D": "科技", "E": "消费", "F": "消费",
        })
        result = EP().neutralize(factor, industry, method="industry")
        # 金融均值=1.5, 科技均值=3.5, 消费均值=5.5
        assert abs(result["A"] - (1.0 - 1.5)) < 1e-6
        assert abs(result["C"] - (3.0 - 3.5)) < 1e-6


class TestValuationFactors:
    """估值因子测试"""

    def test_ep_compute(self):
        df = pd.DataFrame({
            "code": ["000001", "000002", "000003"],
            "pe": [10.0, 20.0, -5.0],
        })
        ep = EP()
        result = ep.compute(df)
        assert abs(result.iloc[0] - 0.1) < 1e-6  # 1/10
        assert abs(result.iloc[1] - 0.05) < 1e-6  # 1/20
        assert np.isnan(result.iloc[2])  # PE负值 → NaN

    def test_bp_compute(self):
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "pb": [2.0, 0.5],
        })
        bp = BP()
        result = bp.compute(df)
        assert abs(result.iloc[0] - 0.5) < 1e-6  # 1/2
        assert abs(result.iloc[1] - 2.0) < 1e-6  # 1/0.5

    def test_dp_compute(self):
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "dividend_per_share": [1.0, 0.5],
            "close": [20.0, 10.0],
        })
        dp = DP()
        result = dp.compute(df)
        assert abs(result.iloc[0] - 0.05) < 1e-6  # 1/20
        assert abs(result.iloc[1] - 0.05) < 1e-6  # 0.5/10


class TestQualityFactors:
    """质量因子测试"""

    def test_roe_compute(self):
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "roe": [15.0, 8.0],
        })
        roe = ROE()
        result = roe.compute(df)
        assert abs(result.iloc[0] - 15.0) < 1e-6

    def test_debt_ratio_compute(self):
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "total_liability": [50.0, 80.0],
            "total_assets": [100.0, 100.0],
        })
        dr = DebtRatio()
        result = dr.compute(df)
        # 1 - 0.5 = 0.5, 1 - 0.8 = 0.2
        assert abs(result.iloc[0] - 0.5) < 1e-6
        assert abs(result.iloc[1] - 0.2) < 1e-6


class TestTechnicalFactors:
    """技术因子测试"""

    def test_mom_compute(self):
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "close": [10.0, 20.0],
            "close_prev": [8.0, 22.0],
        })
        mom = MOM(lookback=20)
        result = mom.compute(df)
        assert abs(result.iloc[0] - 0.25) < 1e-6  # 10/8 - 1
        assert abs(result.iloc[1] - (-0.091)) < 0.01  # 20/22 - 1

    def test_rev_compute(self):
        df = pd.DataFrame({
            "code": ["000001"],
            "close": [10.0],
            "close_prev": [8.0],
        })
        rev = REV(lookback=5)
        result = rev.compute(df)
        # REV = -MOM
        assert abs(result.iloc[0]) > 0

    def test_turn_compute(self):
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "turnover_rate": [3.5, 1.2],
        })
        turn = TURN()
        result = turn.compute(df)
        assert abs(result.iloc[0] - 3.5) < 1e-6


class TestScaleFactors:
    """规模因子测试"""

    def test_mcap_compute(self):
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "total_mv": [1e10, 5e8],
        })
        mcap = MCAP()
        result = mcap.compute(df)
        assert abs(result.iloc[0] - np.log(1e10)) < 1e-6


class TestRegistry:
    """因子注册表测试"""

    def test_register_and_get(self):
        FactorRegistry.clear()
        ep = EP()
        FactorRegistry.register(ep)
        assert FactorRegistry.count() == 1
        assert FactorRegistry.get("EP") == ep

    def test_list_factors(self):
        FactorRegistry.clear()
        FactorRegistry.register(EP())
        FactorRegistry.register(BP())
        infos = FactorRegistry.list_factors(category="valuation")
        assert len(infos) == 2

    def test_auto_register(self):
        FactorRegistry.clear()
        from factor.registry import auto_register
        auto_register()
        assert FactorRegistry.count() >= 17  # 17个因子


class TestICAnalyzer:
    """IC分析器测试"""

    def test_rank_ic(self):
        from factor_test.ic_test import ICAnalyzer
        analyzer = ICAnalyzer()

        # 生成测试数据：因子和收益正相关
        np.random.seed(42)
        n = 200
        factor = pd.Series(np.random.randn(n), index=[f"code_{i}" for i in range(n)])
        # 加噪声的正相关
        returns = factor * 0.05 + np.random.randn(n) * 0.1
        returns = pd.Series(returns, index=factor.index)

        ic = analyzer.compute_rank_ic(factor, returns)
        assert ic > 0  # 正相关 → IC > 0


class TestLayerTest:
    """分层回测测试"""

    def test_compute_layers(self):
        from factor_test.layer_test import LayerTest
        lt = LayerTest(n_layers=5)

        np.random.seed(42)
        n = 500
        factor = pd.Series(np.random.randn(n), index=[f"code_{i}" for i in range(n)])
        # 因子值越高 → 收益越高（构造单调）
        returns = factor * 0.02 + np.random.randn(n) * 0.05
        returns = pd.Series(returns, index=factor.index)

        result = lt.compute_layers(factor, returns)
        assert not result.empty
        assert result["long_short"].values[0] > 0


class TestRegressionTest:
    """回归分析测试"""

    def test_single_regression(self):
        from factor_test.regression_test import RegressionTest
        rt = RegressionTest()

        np.random.seed(42)
        n = 200
        factor = pd.Series(np.random.randn(n), index=[f"code_{i}" for i in range(n)])
        returns = factor * 0.05 + np.random.randn(n) * 0.1
        returns = pd.Series(returns, index=factor.index)

        result = rt.compute_single_regression(factor, returns)
        assert result["beta"] > 0  # 正相关
        assert abs(result["t_value"]) > 2  # 显著


class TestScreening:
    """筛选测试"""

    def test_screen_factor(self):
        from factor_test.screening import FactorScreening
        sc = FactorScreening()

        # 构造有效因子
        ic_summary = {"icir": 0.6, "ic_positive_ratio": 0.55, "ic_abs003_ratio": 0.4}
        layer_summary = {"avg_long_short": 0.02, "long_short_win_rate": 0.55}
        reg_summary = {"t_mean": 2.5}

        result = sc.screen_factor(ic_summary, layer_summary, reg_summary)
        assert result["effectiveness"] in ("strong", "moderate")