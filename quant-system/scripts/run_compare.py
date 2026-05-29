"""策略对比回测入口脚本"""

import yaml
import os
import pandas as pd
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from backtest.compare import StrategyCompare
from factor_test.ic_test import ICAnalyzer


def run_compare(config_path: str = "config/settings.yaml",
                start_date: str = None, end_date: str = None):
    """多策略对比回测"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not start_date:
        start_date = config["data"]["start_date"]
    if not end_date:
        end_date = "2026-05-29"

    db = DuckDBManager(config["data"]["db_path"])
    db.connect()

    try:
        # 读取因子筛选结果获取IC汇总
        screening_file = config["data"]["cache_path"] + "/factor/factor_screening.csv"
        ic_summaries = {}
        if os.path.exists(screening_file):
            screen_df = pd.read_csv(screening_file)
            # 从筛选结果提取IC信息
            for _, row in screen_df.iterrows():
                ic_summaries[row["factor_name"]] = {
                    "ic_mean": row.get("icir", 0),  # 简化，用ICIR近似
                    "icir": row.get("icir", 0),
                }

        # 对比回测
        compare = StrategyCompare(db)
        result = compare.run_comparison(start_date, end_date, ic_summaries)

        if not result.empty:
            # 保存
            cache_dir = config["data"]["cache_path"] + "/ml"
            os.makedirs(cache_dir, exist_ok=True)
            result.to_csv(os.path.join(cache_dir, "strategy_compare.csv"), index=False)
            logger.info(f"Comparison result saved:\n{result.to_string()}")

    except Exception as e:
        logger.error(f"Compare error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str)
    parser.add_argument("--end", type=str)
    args = parser.parse_args()
    run_compare(start_date=args.start, end_date=args.end)