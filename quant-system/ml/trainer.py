"""滚动训练引擎 - 多期滚动训练+预测"""

import os
import pandas as pd
import numpy as np
from loguru import logger
from ml.dataset import DatasetBuilder
from ml.models.lgbm import LGBMModel
from data.db.duckdb_manager import DuckDBManager


class RollingTrainer:
    """滚动训练引擎

    对每个滚动窗口：
    1. 切分 train/val/test
    2. 训练 LightGBM
    3. 验证集评估 IC
    4. 预测集生成信号
    5. 模型和信号入库
    """

    def __init__(self, db: DuckDBManager,
                 dataset_builder: DatasetBuilder = None,
                 model_params: dict = None,
                 model_dir: str = "data/models"):
        self.db = db
        self.ds_builder = dataset_builder or DatasetBuilder()
        self.model_params = model_params or LGBMModel.DEFAULT_PARAMS.copy()
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    def train_single_window(self, window: dict, model_name: str = "lgbm_v1") -> dict:
        """训练单个滚动窗口

        Args:
            window: {train, val, test, train_start, train_end, val_start, eval_date}
            model_name: 模型版本名

        Returns:
            dict: model_result, ic, predictions
        """
        train_df = window["train"]
        val_df = window["val"]
        test_df = window["test"]

        # 提取 X, y
        X_train, y_train = self.ds_builder.prepare_xy(train_df)
        X_val, y_val = self.ds_builder.prepare_xy(val_df)
        X_test, y_test = self.ds_builder.prepare_xy(test_df)

        if X_train.empty or len(X_train) < 100:
            logger.warning(f"Train data too small ({len(X_train)}), skipping")
            return {}

        # 训练模型
        model = LGBMModel(params=self.model_params)
        train_result = model.train(X_train, y_train, X_val, y_val)

        # 验证集IC评估
        val_pred = model.predict(X_val)
        val_ic = self._compute_ic(val_pred, y_val)

        # 测试集预测
        test_pred = model.predict(X_test)

        # 保存模型
        model_path = os.path.join(
            self.model_dir,
            f"{model_name}_{window['eval_date']}.txt"
        )
        model.save(model_path)

        # 记录训练日志
        log = {
            "model_name": model_name,
            "train_start": window["train_start"],
            "train_end": window["train_end"],
            "val_start": window["val_start"],
            "eval_date": window["eval_date"],
            "train_rows": len(X_train),
            "val_rows": len(X_val),
            "val_ic": val_ic,
            "best_round": train_result.get("best_round", 0),
            "top_features": train_result.get("feature_importance", pd.DataFrame()).head(10).to_dict(),
        }

        logger.info(f"Window {window['eval_date']}: val_ic={val_ic:.4f}, "
                    f"train={len(X_train)}, val={len(X_val)}")

        return {
            "model": model,
            "train_result": train_result,
            "val_ic": val_ic,
            "test_predictions": test_pred,
            "test_codes": test_df["code"] if "code" in test_df.columns else None,
            "test_dates": test_df["date"] if "date" in test_df.columns else None,
            "log": log,
        }

    def train_rolling(self, dataset: pd.DataFrame,
                      model_name: str = "lgbm_v1",
                      step_months: int = 1) -> pd.DataFrame:
        """全量滚动训练

        Returns:
            DataFrame: 训练日志汇总 [eval_date, val_ic, train_rows, ...]
        """
        windows = self.ds_builder.generate_rolling_windows(dataset, step_months=step_months)

        all_logs = []
        all_signals = []

        for i, window in enumerate(windows):
            logger.info(f"=== Rolling window {i+1}/{len(windows)}: {window['eval_date']} ===")

            result = self.train_single_window(window, model_name)
            if not result:
                continue

            # 记录日志
            all_logs.append(result["log"])

            # 收集预测信号
            if result["test_predictions"] is not None:
                codes = result["test_codes"]
                dates = result["test_dates"]
                signal_df = pd.DataFrame({
                    "code": codes,
                    "date": dates,
                    "model_name": model_name,
                    "predicted_return": result["test_predictions"],
                    "signal": np.sign(result["test_predictions"]),  # 1/0/-1
                })
                all_signals.append(signal_df)

        # 汇总日志
        log_df = pd.DataFrame(all_logs)

        # 汇总信号并入库
        if all_signals:
            signal_df = pd.concat(all_signals, ignore_index=True)
            self._save_signals(signal_df)
            logger.info(f"Total signals: {len(signal_df)} rows")

        logger.info(f"Rolling training complete: {len(windows)} windows")
        return log_df

    def _compute_ic(self, predictions: pd.Series, actual: pd.Series) -> float:
        """计算预测值的Rank IC"""
        aligned = pd.DataFrame({
            "pred": predictions,
            "actual": actual,
        }).dropna()

        if len(aligned) < 30:
            return 0.0

        return aligned["pred"].rank().corr(aligned["actual"].rank())

    def _save_signals(self, signal_df: pd.DataFrame):
        """保存预测信号到DB"""
        # 确保表存在
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS ml_signal (
                code VARCHAR,
                date DATE,
                model_name VARCHAR,
                predicted_return DOUBLE,
                signal INTEGER,
                PRIMARY KEY (code, date, model_name)
            )
        """)

        signal_df["code"] = signal_df["code"].astype(str).str.zfill(6)
        signal_df["date"] = pd.to_datetime(signal_df["date"], errors="coerce").dt.date
        signal_df = signal_df.dropna(subset=["date"])
        signal_df = signal_df.drop_duplicates(subset=["code", "date", "model_name"], keep="last")
        self.db.conn.execute("INSERT OR REPLACE INTO ml_signal SELECT * FROM signal_df")
        logger.info(f"Saved {len(signal_df)} signals to ml_signal")

    def _save_model_log(self, log_df: pd.DataFrame):
        """保存训练日志到DB"""
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS model_log (
                model_name VARCHAR,
                train_start DATE,
                train_end DATE,
                val_start DATE,
                eval_date DATE,
                train_rows INTEGER,
                val_rows INTEGER,
                val_ic DOUBLE,
                best_round INTEGER,
                PRIMARY KEY (model_name, eval_date)
            )
        """)

        log_df = log_df.drop_duplicates(subset=["model_name", "eval_date"], keep="last")
        # 只写入定义的列
        cols = ["model_name", "train_start", "train_end", "val_start", "eval_date",
                "train_rows", "val_rows", "val_ic", "best_round"]
        log_df = log_df[[c for c in cols if c in log_df.columns]]
        self.db.conn.execute("INSERT OR REPLACE INTO model_log SELECT * FROM log_df")
        logger.info(f"Saved {len(log_df)} model logs")