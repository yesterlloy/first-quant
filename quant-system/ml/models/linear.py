"""线性基线模型 - Ridge/Lasso回归"""

import pandas as pd
import numpy as np
from loguru import logger

try:
    from sklearn.linear_model import Ridge, Lasso
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("sklearn not installed, linear baselines unavailable")


class LinearModel:
    """线性基线模型（Ridge/Lasso）

    作为ML模型的对比基线，简单可解释。
    """

    def __init__(self, model_type: str = "ridge", alpha: float = 1.0):
        """
        Args:
            model_type: "ridge" 或 "lasso"
            alpha: 正则化强度
        """
        if not HAS_SKLEARN:
            raise ImportError("sklearn required for LinearModel")

        self.model_type = model_type
        self.alpha = alpha
        self.model = None
        self.feature_names = None

        if model_type == "ridge":
            self.model = Ridge(alpha=alpha, random_state=42)
        elif model_type == "lasso":
            self.model = Lasso(alpha=alpha, random_state=42, max_iter=5000)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: pd.DataFrame = None, y_val: pd.Series = None) -> dict:
        """训练"""
        self.feature_names = X_train.columns.tolist()
        self.model.fit(X_train, y_train)

        # 特征重要性 = |系数|
        coefs = np.abs(self.model.coef_)
        feat_imp = pd.DataFrame({
            "feature": self.feature_names,
            "importance": coefs,
        }).sort_values("importance", ascending=False)

        # 验证IC
        val_ic = None
        if X_val is not None and y_val is not None:
            val_pred = self.predict(X_val)
            val_ic = self._compute_ic(val_pred, y_val)

        result = {
            "feature_importance": feat_imp,
            "num_features": len(self.feature_names),
            "val_ic": val_ic,
            "r_squared": self.model.score(X_train, y_train),
        }

        logger.info(f"{self.model_type} trained: R²={result['r_squared']:.4f}, "
                    f"val_ic={val_ic or 0:.4f}")
        return result

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """预测"""
        predictions = self.model.predict(X)
        return pd.Series(predictions, index=X.index)

    def _compute_ic(self, predictions: pd.Series, actual: pd.Series) -> float:
        """计算 Rank IC"""
        aligned = pd.DataFrame({"pred": predictions, "actual": actual}).dropna()
        if len(aligned) < 30:
            return 0.0
        return aligned["pred"].rank().corr(aligned["actual"].rank())