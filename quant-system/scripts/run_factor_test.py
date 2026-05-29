"""因子检验入口脚本"""

import yaml
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from factor.registry import FactorRegistry, auto_register
from factor_test.report import FactorTestReport


def run_factor_test(config_path: str = "config/settings.yaml",
                    start_date: str = None,
                    end_date: str = None,
                    factor_name: str = None):
    """跑因子检验

    Args:
        start_date/end_date: 检验时间范围
        factor_name: 指定因子名，默认全部
    """
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
        report = FactorTestReport(db)

        if factor_name:
            # 单因子检验
            result = report.run_full_test(factor_name, start_date, end_date)
            if result:
                logger.info(f"\n{result}")
        else:
            # 全量检验
            screen_df = report.run_all_tests(start_date, end_date)
            if not screen_df.empty:
                logger.info(f"\n{screen_df.to_string()}")
                # 保存筛选结果
                screen_df.to_csv("data/cache/factor/factor_screening.csv", index=False)
                logger.info("Screening result saved to data/cache/factor/factor_screening.csv")

    except Exception as e:
        logger.error(f"Factor test error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Factor test")
    parser.add_argument("--start", type=str, help="Start date")
    parser.add_argument("--end", type=str, help="End date")
    parser.add_argument("--factor", type=str, help="Single factor name")
    args = parser.parse_args()
    run_factor_test(start_date=args.start, end_date=args.end, factor_name=args.factor)