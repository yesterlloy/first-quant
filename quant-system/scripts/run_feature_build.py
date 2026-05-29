"""特征构建+数据集构建入口脚本"""

import yaml
import os
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from factor.registry import FactorRegistry, auto_register
from ml.feature_engine import FeatureEngine
from ml.dataset import DatasetBuilder


def run_feature_build(config_path: str = "config/settings.yaml",
                      start_date: str = None, end_date: str = None):
    """构建特征数据集"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not start_date:
        start_date = config["data"]["start_date"]
    if not end_date:
        end_date = "2026-05-29"

    db = DuckDBManager(config["data"]["db_path"])
    db.connect()

    try:
        auto_register()

        # 获取因子值
        factor_df = db.query(f"""
            SELECT code, date, factor_name, raw_value
            FROM factor_value
            WHERE date >= '{start_date}' AND date <= '{end_date}'
        """)

        # 获取行情数据
        price_df = db.query(f"""
            SELECT code, date, close
            FROM daily_quote
            WHERE date >= '{start_date}' AND date <= '{end_date}'
        """)

        # 获取行业分类
        try:
            ind_df = db.query("SELECT code, industry_sw FROM industry_class")
            industry_series = pd.Series(ind_df["industry_sw"].values, index=ind_df["code"]) if not ind_df.empty else None
        except Exception:
            industry_series = None

        if factor_df.empty or price_df.empty:
            logger.error("No data available, run factor compute first")
            return

        # 构建数据集
        fe = FeatureEngine()
        ds = DatasetBuilder(feature_engine=fe)
        dataset = ds.build_dataset(factor_df, price_df, industry_series)

        if not dataset.empty:
            # 保存
            cache_dir = config["data"]["cache_path"] + "/ml"
            os.makedirs(cache_dir, exist_ok=True)
            dataset.to_csv(os.path.join(cache_dir, "ml_dataset.csv"), index=False)
            logger.info(f"Dataset saved: {len(dataset)} rows, {dataset.shape[1]} columns")

        # 显示滚动窗口
        windows = ds.generate_rolling_windows(dataset)
        logger.info(f"Available rolling windows: {len(windows)}")

    except Exception as e:
        logger.error(f"Feature build error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    import pandas as pd
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str)
    parser.add_argument("--end", type=str)
    args = parser.parse_args()
    run_feature_build(start_date=args.start, end_date=args.end)