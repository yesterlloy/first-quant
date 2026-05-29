"""因子计算入口脚本"""

import yaml
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from factor.processor import FactorEngine


def run_factor_compute(config_path: str = "config/settings.yaml",
                       date: str = None,
                       factor_name: str = None,
                       neutralize_method: str = None):
    """计算因子值

    Args:
        date: 指定日期截面，默认取最近
        factor_name: 指定因子名，默认全部
        neutralize_method: 中性化方式 None/industry/market_cap/both
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    db = DuckDBManager(config["data"]["db_path"])
    db.connect()

    try:
        engine = FactorEngine(db, cache_path=config["data"]["cache_path"] + "/factor")

        if factor_name:
            # 单因子计算
            result = engine.compute_and_save(factor_name, date=date)
            logger.info(f"Factor {factor_name} computed: {len(result)} rows")
        else:
            # 全量计算
            result = engine.compute_all_factors(date=date, neutralize_method=neutralize_method)
            if not result.empty:
                db.upsert_factor_value(result)
                logger.info(f"All factors: {len(result)} rows saved to DB")

        # 统计
        try:
            count = db.query("SELECT COUNT(*) as cnt, COUNT(DISTINCT factor_name) as factors FROM factor_value")
            logger.info(f"Factor DB: {int(count['cnt'][0])} rows, {int(count['factors'][0])} factors")
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Factor compute error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Factor computation")
    parser.add_argument("--date", type=str, help="Cross-section date")
    parser.add_argument("--factor", type=str, help="Single factor name")
    parser.add_argument("--neutralize", type=str, choices=["industry", "market_cap", "both"],
                        help="Neutralization method")
    args = parser.parse_args()
    run_factor_compute(date=args.date, factor_name=args.factor,
                       neutralize_method=args.neutralize)