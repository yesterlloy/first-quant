"""ML模块集成测试"""

import pytest
import pandas as pd
import numpy as np

from ml.feature_engine import FeatureEngine
from ml.dataset import DatasetBuilder


class TestFeatureEngine:
    """特征工程测试"""

    def test_fill_missing_industry(self):
        fe = FeatureEngine(fill_method="industry_mean")
        df = pd.DataFrame({
            "EP": [0.1, 0.2, np.nan, 0.4],
            "MOM": [0.05, np.nan, 0.03, 0.01],
        }, index=["A", "B", "C", "D"])
        industry = pd.Series({"A": "金融", "B": "金融", "C": "科技", "D": "科技"})
        result = fe.fill_missing(df, industry)
        # C的EP用科技均值填充
        assert not result.isna().any().any()

    def test_fill_missing_zero(self):
        fe = FeatureEngine(fill_method="zero")
        df = pd.DataFrame({"EP": [0.1, np.nan]})
        result = fe.fill_missing(df)
        assert result["EP"].iloc[1] == 0

    def test_winsorize_mad(self):
        fe = FeatureEngine(n_mad=3.0)
        # 造一个有极值的序列
        values = list(range(1, 50)) + [999]  # 999是极值
        df = pd.DataFrame({"factor": values})
        result = fe.winsorize_mad(df)
        assert result["factor"].max() < 999  # 极值被截断

    def test_cross_section_zscore(self):
        fe = FeatureEngine()
        df = pd.DataFrame({"EP": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = fe.cross_section_zscore(df)
        assert abs(result["EP"].mean()) < 1e-6  # 均值≈0
        assert abs(result["EP"].std() - 1.0) < 0.01  # 标准差≈1

    def test_cross_features(self):
        fe = FeatureEngine()
        df = pd.DataFrame({
            "EP": [0.1, 0.2],
            "MOM_20": [0.05, -0.03],
        })
        result = fe.generate_cross_features(df)
        assert "EP_x_MOM_20" in result.columns

    def test_industry_dummies(self):
        fe = FeatureEngine()
        industry = pd.Series({"A": "金融", "B": "科技", "C": "消费"},
                             index=["A", "B", "C"])
        dummies = fe.generate_industry_dummies(industry)
        assert dummies.shape == (3, 3)

    def test_full_pipeline(self):
        fe = FeatureEngine()
        df = pd.DataFrame({
            "code": ["A", "B", "C", "D"],
            "EP": [0.1, 0.2, np.nan, 0.4],
            "BP": [0.5, np.nan, 0.3, 0.1],
            "MOM_20": [0.05, -0.02, 0.03, -0.01],
        })
        industry = pd.Series({"A": "金融", "B": "金融", "C": "科技", "D": "科技"})
        result = fe.build_features(df, industry)
        assert not result.isna().any().any()  # 全部填充
        assert result.shape[0] == 4


class TestDatasetBuilder:
    """数据集构建测试"""

    def test_prepare_xy(self):
        ds = DatasetBuilder()
        df = pd.DataFrame({
            "code": ["A", "B"],
            "date": ["2026-01-01", "2026-01-01"],
            "label": [0.05, -0.02],
            "EP": [0.1, 0.2],
            "BP": [0.5, 0.3],
        })
        X, y = ds.prepare_xy(df)
        assert X.shape == (2, 2)
        assert len(y) == 2

    def test_split_rolling(self):
        ds = DatasetBuilder(train_months=12, val_months=3)
        # 构造时间序列数据
        dates = pd.date_range("2024-01-01", "2026-05-01", freq="MS")
        rows = []
        for d in dates:
            for code in ["A", "B", "C"]:
                rows.append({
                    "code": code, "date": d,
                    "label": np.random.randn(),
                    "EP": np.random.randn(),
                    "BP": np.random.randn(),
                })
        dataset = pd.DataFrame(rows)

        split = ds.split_rolling(dataset, eval_date="2025-12-01")
        assert len(split["train"]) > 0
        assert len(split["val"]) > 0


class TestLGBMModel:
    """LightGBM模型测试"""

    def test_train_predict(self):
        from ml.models.lgbm import LGBMModel
        np.random.seed(42)
        n = 200
        X = pd.DataFrame({
            "EP": np.random.randn(n),
            "BP": np.random.randn(n),
            "MOM": np.random.randn(n),
        })
        y = pd.Series(X["EP"] * 0.5 + X["MOM"] * 0.3 + np.random.randn(n) * 0.1)

        model = LGBMModel()
        result = model.train(X[:150], y[:150], X[150:], y[150:], num_boost_round=100)
        assert "feature_importance" in result

        predictions = model.predict(X[150:])
        assert len(predictions) == 50


class TestLinearModel:
    """线性模型测试"""

    def test_ridge(self):
        from ml.models.linear import LinearModel
        np.random.seed(42)
        n = 100
        X = pd.DataFrame({
            "EP": np.random.randn(n),
            "BP": np.random.randn(n),
        })
        y = pd.Series(X["EP"] * 0.5 + np.random.randn(n) * 0.1)

        model = LinearModel(model_type="ridge")
        result = model.train(X[:80], y[:80], X[80:], y[80:])
        assert result["val_ic"] is not None

        predictions = model.predict(X[80:])
        assert len(predictions) == 20


class TestStrategies:
    """传统因子合成策略测试"""

    def test_equal_weight(self):
        from strategy.ml_factor import EqualWeightStrategy
        df = pd.DataFrame({
            "code": ["A", "B", "C", "D"],
            "EP": [0.1, 0.2, 0.3, 0.4],
            "BP": [0.5, 0.4, 0.3, 0.2],
        })
        strategy = EqualWeightStrategy(["EP", "BP"])
        signal = strategy.compute_signal(df)
        assert len(signal) == 4

    def test_ic_weighted(self):
        from strategy.ml_factor import ICWeightedStrategy
        ic_summaries = {"EP": {"ic_mean": 0.05}, "BP": {"ic_mean": 0.03}}
        df = pd.DataFrame({
            "code": ["A", "B", "C", "D"],
            "EP": [0.1, 0.2, 0.3, 0.4],
            "BP": [0.5, 0.4, 0.3, 0.2],
        })
        strategy = ICWeightedStrategy(ic_summaries, ["EP", "BP"])
        signal = strategy.compute_signal(df)
        assert len(signal) == 4