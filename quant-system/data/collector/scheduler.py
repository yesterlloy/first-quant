"""定时采集调度器"""

import yaml
import schedule
import time
from loguru import logger
from data.collector.multi_source import MultiSourceCollector
from data.collector.fundamental import FundamentalCollector
from data.db.duckdb_manager import DuckDBManager


class CollectorScheduler:
    """数据采集定时任务管理"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        data_cfg = self.config["data"]
        collector_cfg = self.config["collector"]

        self.db = DuckDBManager(data_cfg["db_path"])
        self.collector = MultiSourceCollector(
            retry_max=collector_cfg["retry_max"],
            retry_delay=collector_cfg["retry_delay"],
            cache_path=data_cfg["cache_path"],
        )
        self.fundamental = FundamentalCollector(
            retry_max=collector_cfg["retry_max"],
            retry_delay=collector_cfg["retry_delay"],
            cache_path=data_cfg["cache_path"],
        )
        self.start_date = data_cfg["start_date"]
        self.end_date = data_cfg["end_date"]

    def run_daily_collection(self):
        """每日数据采集"""
        logger.info("=== Starting daily data collection ===")

        self.db.connect()

        try:
            # 1. 获取股票列表
            stock_list = self.collector.get_stock_list()
            if stock_list.empty:
                logger.error("股票列表获取失败，跳过本次采集")
                return

            self.db.upsert_stock_info(stock_list)

            # 2. 采集日线行情（增量）
            codes = stock_list["code"].tolist()
            # 获取已有数据的最新日期，只拉缺失的数据
            coverage = self.db.get_data_coverage()
            start = coverage["max_date"] if coverage["max_date"] != "N/A" else self.start_date

            # 统一日期格式: YYYY-MM-DD -> YYYYMMDD
            if len(start) == 10 and start[4] == '-':
                start = start.replace('-', '')
            end = self.end_date
            if len(end) == 10 and end[4] == '-':
                end = end.replace('-', '')

            daily_df = self.collector.get_daily_quote_batch(codes, start, end)
            if not daily_df.empty:
                self.db.upsert_daily_quote(daily_df)

            # 3. 采集指数行情
            for idx_code in self.config["data"]["indices"]:
                idx_df = self.collector.get_index_quote(idx_code, start, end)
                if not idx_df.empty:
                    self.db.upsert_index_quote(idx_df)

            logger.info("=== Daily collection complete ===")

        except Exception as e:
            logger.error(f"Collection error: {e}")
        finally:
            self.db.close()

    def run_initial_collection(self):
        """首次全量采集"""
        logger.info("=== Starting INITIAL full collection ===")

        self.db.connect()

        try:
            # 1. 股票列表
            stock_list = self.collector.get_stock_list()
            if stock_list.empty:
                logger.error("股票列表获取失败，跳过本次全量采集")
                return

            self.db.upsert_stock_info(stock_list)

            # 2. 全量日线行情 - 确保日期格式正确
            codes = stock_list["code"].tolist()
            logger.info(f"Collecting daily quotes for {len(codes)} stocks...")

            # 统一日期格式: YYYY-MM-DD -> YYYYMMDD
            start = self.start_date
            if len(start) == 10 and start[4] == '-':
                start = start.replace('-', '')
            end = self.end_date
            if len(end) == 10 and end[4] == '-':
                end = end.replace('-', '')

            daily_df = self.collector.get_daily_quote_batch(codes, start, end)
            if not daily_df.empty:
                self.db.upsert_daily_quote(daily_df)

            # 3. 指数行情
            for idx_code in self.config["data"]["indices"]:
                idx_df = self.collector.get_index_quote(idx_code, start, end)
                if not idx_df.empty:
                    self.db.upsert_index_quote(idx_df)

            # 4. 财务数据（可选，首次可只拉部分）
            logger.info("Financial data: skipping for initial run (add later)")

            coverage = self.db.get_data_coverage()
            logger.info(f"Collection result: {coverage}")
            logger.info("=== Initial collection complete ===")

        except Exception as e:
            logger.error(f"Initial collection error: {e}")
        finally:
            self.db.close()

    def schedule_daily(self):
        """设置每日定时采集（18:00）"""
        schedule.every().day.at("18:00").do(self.run_daily_collection)
        logger.info("Scheduled daily collection at 18:00")

        while True:
            schedule.run_pending()
            time.sleep(60)