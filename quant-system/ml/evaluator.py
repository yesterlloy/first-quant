"""ML模型评估模块 - IC/分层/对比"""

import pandas as pd
import numpy as np
from loguru import logger
from factor_test.ic_test import ICAnalyzer
from factor_test.layer_test import LayerTest


class MLEvaluator:
    """ML模型评估器

    评估维度：
    1. 预测力：Rank IC / ICIR
    2. 选股效果：分层回测多空收益
    3. 过拟合检测：train vs val IC差
    4. 对比基线：ML vs 等权/IC加权
    """

    def __init__(self, forward_period: int = 20, n_layers: int = 5):
        self.ic_analyzer = ICAnalyzer(forward_period=forward_period)
        self.layer_test = LayerTest(n_layers=n_layers, forward_period=forward_period)

    def evaluate_predictions(self, predictions: pd.Series,
                             actual_returns: pd.Series,
                             model_name: str = "unknown") -> dict:
        """评估模型预测

        Args:
            predictions: 预测收益率 Series（index=code）
            actual_returns: 实际收益率 Series（index=code）
            model_name: 模型名

        Returns:
            dict: ic, icir, long_short, layer_returns, overfit_ratio
        """
        # Rank IC
        ic = self.ic_analyzer.compute_rank_ic(predictions, actual_returns)

        # 分层回测
        layer_df = self.layer_test.compute_layers(predictions, actual_returns)
        if not layer_df.empty:
            long_short = float(layer_df["long_short"].values[0])
        else:
            long_short = 0

        # ICIR需要时间序列IC，单期只返回IC值
        result = {
            "model_name": model_name,
            "rank_ic": ic,
            "long_short": long_short,
            "n_stocks": len(predictions),
        }

        logger.info(f"Evaluation {model_name}: IC={ic:.4f}, LS={long_short:.4f}")
        return result

    def compare_models(self, model_results: dict) -> pd.DataFrame:
        """多模型对比

        Args:
            model_results: {model_name: {rank_ic, long_short, ...}}

        Returns:
            DataFrame: 对比表
        """
        rows = []
        for name, metrics in model_results.items():
            rows.append({
                "model": name,
                "rank_ic": metrics.get("rank_ic", 0),
                "long_short": metrics.get("long_short", 0),
                "n_stocks": metrics.get("n_stocks", 0),
            })

        result = pd.DataFrame(rows).sort_values("rank_ic", ascending=False)
        logger.info(f"\n{result.to_string()}")
        return result

    def detect_overfitting(self, train_ic: float, val_ic: float) -> dict:
        """过拟合检测

        如果 train IC 远大于 val IC，说明过拟合。
        """
        gap = train_ic - val_ic
        ratio = train_ic / val_ic if abs(val_ic) > 1e-6 else float("inf")

        if ratio > 3:
            status = "severe_overfit"
        elif ratio > 2:
            status = "moderate_overfit"
        elif ratio > 1.5:
            status = "mild_overfit"
        else:
            status = "healthy"

        result = {
            "train_ic": train_ic,
            "val_ic": val_ic,
            "gap": gap,
            "ratio": ratio,
            "status": status,
        }

        logger.info(f"Overfitting: train_ic={train_ic:.4f}, val_ic={val_ic:.4f}, "
                    f"status={status}")
        return result