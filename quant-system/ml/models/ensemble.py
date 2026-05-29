"""多模型融合（Ensemble）"""

import pandas as pd
import numpy as np
from loguru import logger
from ml.models.lgbm import LGBMModel
from ml.models.linear import LinearModel


try:
    from ml.models.xgboost import XGBoostModel
    HAS_XGB = True
except ImportError:
    HAS_XGB = False


class EnsembleModel:
    """多模型融合

    融合方式：
    - 等权平均：各模型预测等权平均
    - IC加权平均：各模型按验证IC加权
    - Stacking：用线性模型对多个预测值做二次拟合
    """

    def __init__(self, models: list = None, method: str = "equal"):
        """
        Args:
            models: 模型实例列表
            method: "equal"/"ic_weighted"/"stacking"
        """
        self.models = models or []
        self.method = method
        self.val_ics = []  # 各模型验证IC

    def add_model(self, model, val_ic: float = None):
        """添加模型"""
        self.models.append(model)
        if val_ic is not None:
            self.val_ics.append(val_ic)
        logger.info(f"Added model to ensemble, total={len(self.models)}")

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """融合预测"""
        if not self.models:
            raise ValueError("No models in ensemble")

        # 各模型预测
        predictions = []
        for model in self.models:
            pred = model.predict(X)
            predictions.append(pred)

        if self.method == "equal":
            # 等权平均
            result = pd.concat(predictions, axis=1).mean(axis=1)
            logger.info(f"Ensemble (equal): {len(self.models)} models")

        elif self.method == "ic_weighted" and self.val_ics:
            # IC加权平均
            total_ic = sum(abs(ic) for ic in self.val_ics)
            if total_ic < 1e-10:
                result = pd.concat(predictions, axis=1).mean(axis=1)
            else:
                weights = [abs(ic) / total_ic for ic in self.val_ics]
                result = sum(pred * w for pred, w in zip(predictions, weights))
            logger.info(f"Ensemble (IC-weighted): weights={weights}")

        elif self.method == "stacking":
            # Stacking: 用Ridge对预测值做二次拟合
            pred_matrix = pd.concat(predictions, axis=1)
            pred_matrix.columns = [f"model_{i}" for i in range(len(self.models))]
            # 需要有训练标签来拟合stacking模型，这里简化用等权
            result = pred_matrix.mean(axis=1)
            logger.info("Ensemble (stacking fallback to equal)")

        else:
            result = pd.concat(predictions, axis=1).mean(axis=1)

        result.name = "ensemble_signal"
        return result