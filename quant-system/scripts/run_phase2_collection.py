"""Phase 2 数据采集入口 - 扩展数据（财务/分红/行业/市值）"""

import yaml
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from data.collector.financial_ext import FinancialExtCollector
from data.collector.dividend import DividendCollector
from data.collector.industry import IndustryCollector


def run_phase2_collection(config_path: str = "config/settings.yaml"):
    """采集 Phase 2 所需的扩展数据"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    db = DuckDBManager(config["data"]["db_path"])
    db.connect()

    try:
        # 获取已有股票列表，作为采集范围
        stock_list = db.get_stock_list()
        if stock_list.empty:
            logger.error("No stock list in DB, run Phase 1 collection first")
            return

        codes = stock_list["code"].tolist()
        logger.info(f"Phase 2 collection scope: {len(codes)} stocks")

        # 1. 扩展财务数据
        logger.info("=== Collecting extended financial data ===")
        fin_ext = FinancialExtCollector(
            retry_max=config["collector"]["retry_max"],
            retry_delay=config["collector"]["retry_delay"],
            cache_path=config["data"]["cache_path"],
        )
        # 市值数据（实时）
        cap_df = fin_ext.get_market_cap()
        if not cap_df.empty:
            # 市值存入 daily_quote 的 turnover 字段或其他方式，后续因子计算时用实时接口
            logger.info(f"Market cap data: {len(cap_df)} stocks")

        # 逐只采集扩展财务（太慢全量，先拉前50只做开发测试）
        fin_codes = codes[:50]
        logger.info(f"Financial ext: collecting first {len(fin_codes)} stocks for dev testing")
        fin_ext_df = fin_ext.get_financial_ext_batch(fin_codes)
        if not fin_ext_df.empty:
            db.upsert_financial_ext(fin_ext_df)

        # 2. 分红数据
        logger.info("=== Collecting dividend data ===")
        div = DividendCollector(
            retry_max=config["collector"]["retry_max"],
            retry_delay=config["collector"]["retry_delay"],
            cache_path=config["data"]["cache_path"],
        )
        div_codes = codes[:50]
        div_df = div.get_dividend_batch(div_codes)
        if not div_df.empty:
            db.upsert_dividend(div_df)

        # 3. 行业分类
        logger.info("=== Collecting industry classification ===")
        ind = IndustryCollector(
            retry_max=config["collector"]["retry_max"],
            retry_delay=config["collector"]["retry_delay"],
            cache_path=config["data"]["cache_path"],
        )
        ind_df = ind.get_sw_industry()
        if not ind_df.empty:
            db.upsert_industry_class(ind_df)

        # 统计结果
        tables = ["daily_quote", "financial_ext", "dividend", "industry_class"]
        for t in tables:
            try:
                count = db.query(f"SELECT COUNT(*) as cnt FROM {t}")
                logger.info(f"Table {t}: {int(count['cnt'][0])} rows")
            except Exception:
                logger.info(f"Table {t}: empty or not found")

        logger.info("=== Phase 2 data collection complete ===")

    except Exception as e:
        logger.error(f"Phase 2 collection error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_phase2_collection()