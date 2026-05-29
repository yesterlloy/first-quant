"""LightGBM模型封装"""

import pandas as pd
import numpy as np
from loguru import logger

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    logger.warning("lightgbm not installed, will use sklearn fallback")


class LGBMModel:
    """LightGBM因子合成模型

    回归模式：预测未来收益率
    分类模式：预测top/bottom分组（可选）
    """

    # 默认参数
    DEFAULT_PARAMS = {
        "objective": "regression",
        "metric": "rmse",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": -1,
        "min_child_samples": 50,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "lambda_l1": 0.1,
        "lambda_l2": 0.1,
        "verbosity": -1,
        "seed": 42,
    }

    def __init__(self, params: dict = None, mode: str = "regression"):
        """
        Args:
            params: LightGBM参数，默认用 DEFAULT_PARAMS
            mode: "regression" 或 "classification"
        """
        if not HAS_LGB:
            logger.warning("LightGBM unavailable, using sklearn GradientBoosting fallback")
            self.use_sklearn_fallback = True
        else:
            self.use_sklearn_fallback = False

        self.mode = mode
        self.params = params or self.DEFAULT_PARAMS.copy()

        if mode == "classification":
            self.params["objective"] = "binary"
            self.params["metric"] = "auc"

        self.model = None
        self.feature_names = None

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: pd.DataFrame = None, y_val: pd.Series = None,
              num_boost_round: int = 500,
              early_stopping_rounds: int = 50,
              verbose: int = 0) -> dict:
        """训练模型

        Returns:
            dict: train_loss, val_loss, best_round, feature_importance
        """
        self.feature_names = X_train.columns.tolist()

        if self.use_sklearn_fallback:
            return self._train_sklearn(X_train, y_train, X_val, y_val)

        # LightGBM Dataset
        train_data = lgb.Dataset(X_train, label=y_train, feature_name=self.feature_names)

        valid_data = None
        callbacks = []

        if X_val is not None and y_val is not None:
            valid_data = lgb.Dataset(X_val, label=y_val, feature_name=self.feature_names,
                                     reference=train_data)
            callbacks.append(lgb.early_stopping(early_stopping_rounds))
            callbacks.append(lgb.log_evaluation(verbose))

        # 训练
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[train_data, valid_data] if valid_data else [train_data],
            callbacks=callbacks,
        )

        # 特征重要性
        importance = self.model.feature_importance(importance_type="gain")
        feat_imp = pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False)

        result = {
            "best_round": self.model.best_iteration if hasattr(self.model, "best_iteration") else num_boost_round,
            "feature_importance": feat_imp,
            "num_features": len(self.feature_names),
        }

        logger.info(f"LGBM trained: best_round={result['best_round']}, "
                    f"top features: {feat_imp.head(5)['feature'].tolist()}")
        return result

    def _train_sklearn(self, X_train, y_train, X_val=None, y_val=None):
        """sklearn GradientBoosting回退方案"""
        from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier

        self.feature_names = X_train.columns.tolist()

        if self.mode == "regression":
            self.model = GradientBoostingRegressor(
                n_estimators=500, learning_rate=0.05, max_depth=5,
                min_samples_leaf=50, random_state=42,
            )
        else:
            self.model = GradientBoostingClassifier(
                n_estimators=500, learning_rate=0.05, max_depth=5,
                min_samples_leaf=50, random_state=42,
            )

        self.model.fit(X_train, y_train)

        importance = self.model.feature_importances_
        feat_imp = pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False)

        return {
            "best_round": 500,
            "feature_importance": feat_imp,
            "num_features": len(self.feature_names),
        }

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """预测

        Returns:
            Series: 预测值（回归模式为收益率，分类模式为概率）
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        if self.use_sklearn_fallback:
            predictions = self.model.predict(X)
        else:
            predictions = self.model.predict(X)

        return pd.Series(predictions, index=X.index)

    def save(self, path: str):
        """保存模型"""
        if self.use_sklearn_fallback:
            import joblib
            joblib.dump(self.model, path)
        else:
            self.model.save_model(path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        """加载模型"""
        if self.use_sklearn_fallback:
            import joblib
            self.model = joblib.load(path)
        else:
            self.model = lgb.Booster(model_file=path)
        logger.info(f"Model loaded from {path}")