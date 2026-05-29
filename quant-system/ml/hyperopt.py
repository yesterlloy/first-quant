"""超参搜索模块 - Optuna集成"""

import pandas as pd
import numpy as np
from loguru import logger

try:
    import optuna
    HAS_OPTUNA = True
    optuna.logging.set_verbosity(optuna.logging.WARNING)
except ImportError:
    HAS_OPTUNA = False
    logger.warning("optuna not installed, hyperparameter search unavailable")

from ml.models.lgbm import LGBMModel
from ml.dataset import DatasetBuilder


class HyperOptimizer:
    """超参搜索器

    用Optuna对LightGBM做贝叶斯优化。
    目标：最大化验证集IC。
    """

    def __init__(self, n_trials: int = 50, timeout: int = 600):
        """
        Args:
            n_trials: 搜索次数
            timeout: 搜索超时（秒）
        """
        if not HAS_OPTUNA:
            raise ImportError("optuna required for HyperOptimizer")
        self.n_trials = n_trials
        self.timeout = timeout

    def optimize_lgbm(self, X_train, y_train, X_val, y_val) -> dict:
        """搜索LightGBM最优参数

        Returns:
            dict: best_params, best_ic, study
        """
        def objective(trial):
            params = {
                "objective": "regression",
                "metric": "rmse",
                "verbosity": -1,
                "seed": 42,
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2),
                "num_leaves": trial.suggest_int("num_leaves", 15, 63),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "min_child_samples": trial.suggest_int("min_child_samples", 20, 100),
                "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
                "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
                "bagging_freq": trial.suggest_int("bagging_freq", 1, 10),
                "lambda_l1": trial.suggest_float("lambda_l1", 0.0, 1.0),
                "lambda_l2": trial.suggest_float("lambda_l2", 0.0, 1.0),
            }

            model = LGBMModel(params=params)
            model.train(X_train, y_train, X_val, y_val, num_boost_round=300)

            val_pred = model.predict(X_val)
            ic = self._compute_ic(val_pred, y_val)
            return ic  # 最大化IC

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=self.n_trials, timeout=self.timeout)

        best_params = study.best_params
        best_ic = study.best_value

        logger.info(f"Optuna best IC={best_ic:.4f}, params={best_params}")
        return {
            "best_params": best_params,
            "best_ic": best_ic,
            "n_trials": len(study.trials),
        }

    def _compute_ic(self, predictions, actual) -> float:
        """计算 Rank IC"""
        aligned = pd.DataFrame({"pred": predictions, "actual": actual}).dropna()
        if len(aligned) < 30:
            return 0.0
        return aligned["pred"].rank().corr(aligned["actual"].rank())