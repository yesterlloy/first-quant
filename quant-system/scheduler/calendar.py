"""交易日历工具 - 判断是否是A股交易日"""

from datetime import datetime
from typing import Optional
from loguru import logger


class TradeCalendar:
    """A股交易日历判断器"""

    def __init__(self, db):
        self.db = db
        self._cache = {}  # date_str -> is_trade_day

    def is_trade_day(self, date: Optional[datetime] = None) -> bool:
        """判断是否是交易日

        Args:
            date: 要检查的日期，默认是今天
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")

        if date_str in self._cache:
            return self._cache[date_str]

        try:
            # 查询trade_cal表
            sql = """
                SELECT is_open FROM trade_cal
                WHERE cal_date = ?
            """
            result = self.db.query(sql, [date_str])

            if result.empty:
                # 如果没有记录，默认周一到周五是交易日
                weekday = date.weekday()
                is_trade = weekday < 5  # 0=Monday, 4=Friday
                logger.warning(f"No trade calendar data for {date_str}, using weekday fallback: {is_trade}")
            else:
                is_trade = bool(result.iloc[0]["is_open"])

            self._cache[date_str] = is_trade
            return is_trade

        except Exception as e:
            logger.error(f"Failed to check trade calendar: {e}")
            # 出错时回退到周一到周五判断
            weekday = date.weekday()
            return weekday < 5

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
