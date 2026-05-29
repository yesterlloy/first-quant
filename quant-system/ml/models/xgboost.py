"""XGBoost模型封装"""

import pandas as pd
import numpy as np
from loguru import logger

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    logger.warning("xgboost not installed")


class XGBoostModel:
    """XGBoost因子合成模型"""

    DEFAULT_PARAMS = {
        "objective": "reg:squarederror",
        "learning_rate": 0.05,
        "max_depth": 5,
        "min_child_weight": 50,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "seed": 42,
        "verbosity": 0,
    }

    def __init__(self, params: dict = None):
        if not HAS_XGB:
            raise ImportError("xgboost required")

        self.params = params or self.DEFAULT_PARAMS.copy()
        self.model = None
        self.feature_names = None

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: pd.DataFrame = None, y_val: pd.Series = None,
              num_boost_round: int = 500,
              early_stopping_rounds: int = 50) -> dict:
        """训练"""
        self.feature_names = X_train.columns.tolist()

        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)

        evals = [(dtrain, "train")]
        if X_val is not None:
            dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_names)
            evals.append((dval, "val"))

        self.model = xgb.train(
            self.params,
            dtrain,
            num_boost_round=num_boost_round,
            evals=evals,
            early_stopping_rounds=early_stopping_rounds if X_val is not None else None,
            verbose_eval=False,
        )

        # 特征重要性
        importance = self.model.get_score(importance_type="gain")
        feat_imp = pd.DataFrame({
            "feature": list(importance.keys()),
            "importance": list(importance.values()),
        }).sort_values("importance", ascending=False)

        best_round = self.model.best_iteration if hasattr(self.model, "best_iteration") else num_boost_round

        result = {
            "best_round": best_round,
            "feature_importance": feat_imp,
            "num_features": len(self.feature_names),
        }

        logger.info(f"XGBoost trained: best_round={best_round}")
        return result

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """预测"""
        if self.model is None:
            raise ValueError("Model not trained")
        dtest = xgb.DMatrix(X, feature_names=self.feature_names)
        predictions = self.model.predict(dtest)
        return pd.Series(predictions, index=X.index)

    def save(self, path: str):
        self.model.save_model(path)

    def load(self, path: str):
        self.model = xgb.Booster()
        self.model.load_model(path)