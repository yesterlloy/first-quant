"""模型训练入口脚本"""

import yaml
import os
import pandas as pd
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from ml.dataset import DatasetBuilder
from ml.trainer import RollingTrainer


def run_train(config_path: str = "config/settings.yaml",
              model_name: str = "lgbm_v1",
              step_months: int = 1):
    """训练ML模型"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    db = DuckDBManager(config["data"]["db_path"])
    db.connect()

    try:
        # 加载预构建的数据集
        cache_dir = config["data"]["cache_path"] + "/ml"
        dataset_file = os.path.join(cache_dir, "ml_dataset.csv")

        if not os.path.exists(dataset_file):
            logger.error("Dataset not found, run run_feature_build.py first")
            return

        dataset = pd.read_csv(dataset_file)
        logger.info(f"Dataset loaded: {len(dataset)} rows")

        # 滚动训练
        ds_builder = DatasetBuilder()
        trainer = RollingTrainer(db, dataset_builder=ds_builder,
                                 model_dir=config["data"]["cache_path"] + "/models")
        log_df = trainer.train_rolling(dataset, model_name=model_name,
                                        step_months=step_months)

        # 保存训练日志
        if not log_df.empty:
            log_df.to_csv(os.path.join(cache_dir, "training_log.csv"), index=False)
            # 保存到DB
            trainer._save_model_log(log_df)
            logger.info(f"Training log saved: {len(log_df)} windows")

    except Exception as e:
        logger.error(f"Train error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="lgbm_v1")
    parser.add_argument("--step", type=int, default=1)
    args = parser.parse_args()
    run_train(model_name=args.model, step_months=args.step)