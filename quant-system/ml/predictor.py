"""预测信号生成模块"""

import pandas as pd
import numpy as np
import os
from loguru import logger
from ml.feature_engine import FeatureEngine
from ml.models.lgbm import LGBMModel
from data.db.duckdb_manager import DuckDBManager


class Predictor:
    """ML信号预测器

    从DB读取最新数据，特征工程处理后用训练好的模型生成选股信号。
    """

    def __init__(self, db: DuckDBManager, feature_engine: FeatureEngine = None,
                 model_dir: str = "data/models"):
        self.db = db
        self.fe = feature_engine or FeatureEngine()
        self.model_dir = model_dir

    def predict_with_model(self, model_name: str, date: str = None) -> pd.DataFrame:
        """用指定模型生成预测信号

        Args:
            model_name: 模型名称，如 "lgbm_v1"
            date: 截面日期

        Returns:
            DataFrame [code, date, predicted_return, signal, model_name]
        """
        if not date:
            # 取最近有数据的日期
            coverage = self.db.get_data_coverage()
            date = coverage.get("max_date", "2026-05-29")

        # 加载模型
        model_path = os.path.join(self.model_dir, f"{model_name}_{date}.txt")
        model = LGBMModel()
        try:
            model.load(model_path)
        except Exception as e:
            logger.error(f"Cannot load model {model_path}: {e}")
            return pd.DataFrame()

        # 获取截面数据
        factor_df = self.db.query(f"""
            SELECT code, date, factor_name, raw_value
            FROM factor_value
            WHERE date = '{date}'
        """)

        if factor_df.empty:
            logger.warning(f"No factor data at {date}")
            return pd.DataFrame()

        # 构宽表
        pivot = factor_df.pivot_table(
            index="code", columns="factor_name", values="raw_value"
        ).reset_index()

        # 特征工程处理
        industry_df = self._get_industry()
        features = self.fe.build_features(pivot, industry_df=industry_df)

        # 预测
        predictions = model.predict(features)
        predictions.name = "predicted_return"

        # 生成信号：1=买入, 0=持有, -1=卖出
        signal = np.sign(predictions)
        # 只选预测值top30%的股票做多
        threshold = predictions.quantile(0.7)
        signal = pd.Series(0, index=predictions.index)
        signal[predictions >= threshold] = 1
        signal[predictions <= predictions.quantile(0.3)] = -1

        result = pd.DataFrame({
            "code": features.index,
            "date": date,
            "model_name": model_name,
            "predicted_return": predictions,
            "signal": signal,
        })

        logger.info(f"Predicted {len(result)} stocks, "
                    f"long={int((signal==1).sum())}, short={int((signal==-1).sum())}")
        return result

    def _get_industry(self) -> pd.Series:
        """获取行业分类"""
        try:
            ind = self.db.query("SELECT code, industry_sw FROM industry_class")
            if not ind.empty:
                return pd.Series(ind["industry_sw"].values, index=ind["code"])
        except Exception:
            pass
        return pd.Series(dtype=str)