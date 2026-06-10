"""增量数据更新模块 - 只采集和计算最新交易日的数据"""

import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
from typing import Tuple, List, Dict


class IncrementalUpdater:
    """增量数据更新器

    功能：
    1. 查询数据库中最新的行情日期
    2. 只采集缺失的交易日数据
    3. 只计算新增交易日的因子
    4. 数据完整性校验
    """

    def __init__(self, db):
        self.db = db

    def get_last_trade_date(self) -> datetime:
        """获取数据库中最新的行情日期"""
        sql = """
            SELECT MAX(date) as last_date FROM daily_quote
        """
        result = self.db.query(sql)
        if result.empty or pd.isna(result.iloc[0]["last_date"]):
            # 如果没有数据，返回一个较早的日期
            return datetime(2020, 1, 1)
        return pd.to_datetime(result.iloc[0]["last_date"])

    def get_missing_dates(self, start_date: datetime = None) -> List[datetime]:
        """获取需要更新的缺失日期列表

        Args:
            start_date: 起始日期，默认从数据库最新日期开始
        """
        if start_date is None:
            start_date = self.get_last_trade_date()

        today = datetime.now()

        # 尝试使用trade_cal表，如果不存在则使用备选方案
        try:
            sql = """
                SELECT cal_date FROM trade_cal
                WHERE cal_date > ? AND cal_date <= ? AND is_open = 1
                ORDER BY cal_date
            """
            result = self.db.query(sql, [start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")])

            if not result.empty:
                return [pd.to_datetime(d) for d in result["cal_date"].tolist()]
        except Exception as e:
            logger.debug(f"trade_cal table not available: {e}")

        # 备选方案：获取最近10天的周一到周五
        dates = []
        for i in range(1, 11):
            d = today - timedelta(days=i)
            if d.weekday() < 5:  # Monday to Friday
                dates.append(d)

        # 过滤掉早于start_date的日期
        dates = [d for d in dates if d > start_date]
        dates.sort()

        return dates

    def get_stock_codes(self) -> List[str]:
        """获取需要更新的股票列表"""
        sql = """
            SELECT DISTINCT code FROM stock_info
            WHERE delist_date IS NULL OR delist_date > CURRENT_DATE
            ORDER BY code
        """
        result = self.db.query(sql)
        if result.empty:
            # 如果没有股票列表，返回常用股票列表
            return []
        return result["code"].tolist()

    def update_daily_quotes(self, codes: List[str] = None, days: int = None) -> Tuple[int, int]:
        """增量更新日线行情

        Args:
            codes: 股票代码列表，None表示全部
            days: 更新最近N天的数据，None表示从上次更新开始

        Returns:
            (更新的天数, 更新的记录数)
        """
        from data.collector.multi_source import MultiSourceCollector

        if codes is None:
            codes = self.get_stock_codes()

        if not codes:
            logger.warning("No stock codes to update")
            return 0, 0

        # 确定起始日期
        if days is not None:
            start_date = datetime.now() - timedelta(days=days)
        else:
            start_date = self.get_last_trade_date()

        end_date = datetime.now()

        logger.info(f"Starting incremental quote update: {start_date.date()} to {end_date.date()}")
        logger.info(f"Stocks to update: {len(codes)}")

        collector = MultiSourceCollector()
        total_rows = 0
        dates_updated = set()

        # 批量更新
        batch_size = 50
        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}/{(len(codes) + batch_size - 1) // batch_size}: {len(batch_codes)} stocks")

            for code in batch_codes:
                try:
                    df = collector.get_daily_quote(
                        code,
                        start_date.strftime("%Y%m%d"),
                        end_date.strftime("%Y%m%d")
                    )
                    if not df.empty:
                        # 去重后插入
                        self.db.insert_quote_data(df)
                        total_rows += len(df)
                        dates_updated.update(df["date"].dt.strftime("%Y-%m-%d").tolist())
                except Exception as e:
                    logger.error(f"Failed to update {code}: {e}")

        logger.info(f"Quote update complete: {len(dates_updated)} days, {total_rows} rows")
        return len(dates_updated), total_rows

    def get_factor_last_date(self, factor_name: str = None) -> datetime:
        """获取因子表中最新的日期"""
        if factor_name:
            sql = """
                SELECT MAX(date) as last_date FROM factor_value
                WHERE factor_name = ?
            """
            result = self.db.query(sql, [factor_name])
        else:
            sql = """
                SELECT MAX(date) as last_date FROM factor_value
            """
            result = self.db.query(sql)

        if result.empty or pd.isna(result.iloc[0]["last_date"]):
            return datetime(2020, 1, 1)
        return pd.to_datetime(result.iloc[0]["last_date"])

    def get_dates_needing_factors(self) -> List[datetime]:
        """获取需要计算因子的日期列表

        有行情但没有因子数据的日期
        """
        sql = """
            SELECT DISTINCT date FROM daily_quote
            WHERE date NOT IN (
                SELECT DISTINCT date FROM factor_value
            )
            ORDER BY date
        """
        result = self.db.query(sql)
        if result.empty:
            return []
        return [pd.to_datetime(d) for d in result["date"].tolist()]

    def update_factors(self, dates: List[datetime] = None) -> Tuple[int, int]:
        """增量计算因子

        Args:
            dates: 需要计算的日期列表，None表示自动检测

        Returns:
            (更新的天数, 更新的记录数)
        """
        from factor.processor import FactorProcessor

        if dates is None:
            dates = self.get_dates_needing_factors()

        if not dates:
            logger.info("No dates need factor calculation")
            return 0, 0

        logger.info(f"Calculating factors for {len(dates)} dates: {[d.strftime('%Y-%m-%d') for d in dates]}")

        processor = FactorProcessor(self.db)
        total_factors = 0

        for date in dates:
            try:
                # 计算该日期的所有因子
                date_str = date.strftime("%Y-%m-%d")
                factors_df = processor.calculate_all_factors(date_str)
                if not factors_df.empty:
                    processor.save_factors(factors_df)
                    total_factors += len(factors_df)
                    logger.info(f"Calculated {len(factors_df)} factors for {date_str}")
            except Exception as e:
                logger.error(f"Failed to calculate factors for {date}: {e}")

        logger.info(f"Factor update complete: {len(dates)} days, {total_factors} records")
        return len(dates), total_factors

    def validate_data_integrity(self) -> Dict:
        """校验数据完整性

        Returns:
            校验结果字典
        """
        logger.info("Running data integrity validation...")

        result = {
            "status": "ok",
            "issues": [],
            "stats": {}
        }

        # 1. 检查行情数据的完整性
        quote_stats = self.db.query("""
            SELECT date, COUNT(*) as count,
                   MIN(code) as min_code, MAX(code) as max_code
            FROM daily_quote
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """)

        if not quote_stats.empty:
            avg_count = quote_stats["count"].mean()
            recent_dates = quote_stats.head(5)
            for _, row in recent_dates.iterrows():
                if row["count"] < avg_count * 0.8:
                    result["issues"].append({
                        "type": "low_quote_count",
                        "date": str(row["date"]),
                        "message": f"Low quote count: {row['count']} vs avg {avg_count:.0f}"
                    })

            result["stats"]["recent_quote_days"] = len(quote_stats)
            result["stats"]["avg_quotes_per_day"] = int(avg_count)

        # 2. 检查因子数据与行情的匹配度
        factor_dates = self.db.query("""
            SELECT date, COUNT(DISTINCT code) as stock_count,
                   COUNT(DISTINCT factor_name) as factor_count
            FROM factor_value
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """)

        if not factor_dates.empty:
            result["stats"]["recent_factor_days"] = len(factor_dates)
            result["stats"]["avg_factors_per_day"] = int(factor_dates["stock_count"].mean())

            # 检查是否有行情但没有因子的日期
            missing_factor_dates = self.get_dates_needing_factors()
            if missing_factor_dates:
                result["issues"].append({
                    "type": "missing_factors",
                    "dates": [d.strftime("%Y-%m-%d") for d in missing_factor_dates[:10]],
                    "message": f"{len(missing_factor_dates)} days have quotes but no factors"
                })

        # 3. 检查股票列表完整性
        stock_count = self.db.query("SELECT COUNT(*) as count FROM stock_info").iloc[0]["count"]
        result["stats"]["total_stocks"] = int(stock_count)

        # 4. 检查最近交易日数据
        last_quote_date = self.get_last_trade_date()
        last_factor_date = self.get_factor_last_date()
        result["stats"]["last_quote_date"] = last_quote_date.strftime("%Y-%m-%d")
        result["stats"]["last_factor_date"] = last_factor_date.strftime("%Y-%m-%d")

        if (datetime.now() - last_quote_date).days > 3:
            result["issues"].append({
                "type": "stale_quotes",
                "message": f"Quotes are { (datetime.now() - last_quote_date).days } days old"
            })

        if result["issues"]:
            result["status"] = "warning"
            logger.warning(f"Found {len(result['issues'])} data integrity issues")
        else:
            logger.info("Data integrity validation passed")

        return result

    def run_full_update(self, force_days: int = None) -> Dict:
        """运行完整的增量更新流程

        Args:
            force_days: 强制更新最近N天的数据，None表示自动检测

        Returns:
            更新结果统计
        """
        logger.info("=" * 60)
        logger.info("Starting full incremental update")
        logger.info("=" * 60)

        result = {
            "quotes_updated": False,
            "factors_updated": False,
            "quote_days": 0,
            "quote_rows": 0,
            "factor_days": 0,
            "factor_rows": 0,
            "validation": None
        }

        # 1. 更新行情数据
        try:
            quote_days, quote_rows = self.update_daily_quotes(days=force_days)
            result["quote_days"] = quote_days
            result["quote_rows"] = quote_rows
            result["quotes_updated"] = True
        except Exception as e:
            logger.error(f"Quote update failed: {e}")

        # 2. 更新因子数据
        try:
            factor_days, factor_rows = self.update_factors()
            result["factor_days"] = factor_days
            result["factor_rows"] = factor_rows
            result["factors_updated"] = True
        except Exception as e:
            logger.error(f"Factor update failed: {e}")

        # 3. 数据完整性校验
        try:
            result["validation"] = self.validate_data_integrity()
        except Exception as e:
            logger.error(f"Validation failed: {e}")

        logger.info("=" * 60)
        logger.info("Incremental update complete")
        logger.info(f"  Quotes: {result['quote_days']} days, {result['quote_rows']} rows")
        logger.info(f"  Factors: {result['factor_days']} days, {result['factor_rows']} rows")
        logger.info(f"  Validation: {result['validation']['status'] if result['validation'] else 'N/A'}")
        logger.info("=" * 60)

        return result
