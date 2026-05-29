"""A股行情数据采集模块 - 基于 akshare"""

import time
import os

# 绕过代理直连国内数据源（东方财富等）
os.environ["no_proxy"] = "eastmoney.com,push2.eastmoney.com,*.eastmoney.com,sina.com.cn,*.sina.com.cn,tushare.cn"
os.environ["NO_PROXY"] = os.environ["no_proxy"]

import pandas as pd
import akshare as ak
from loguru import logger


class AkshareCollector:
    """akshare 数据采集器，支持增量更新"""

    def __init__(self, retry_max: int = 3, retry_delay: int = 5,
                 cache_path: str = "data/cache"):
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        self.cache_path = cache_path
        os.makedirs(cache_path, exist_ok=True)

    def _fetch_with_retry(self, func, *args, **kwargs) -> pd.DataFrame:
        """带重试的数据获取（指数退避）"""
        for attempt in range(1, self.retry_max + 1):
            try:
                df = func(*args, **kwargs)
                if df is not None and not df.empty:
                    return df
                logger.warning(f"Empty result on attempt {attempt}")
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.retry_max} failed: {e}")
                if attempt < self.retry_max:
                    wait = self.retry_delay * attempt  # 指数退避：5s, 10s, 15s
                    logger.info(f"Waiting {wait}s before retry...")
                    time.sleep(wait)

        logger.error(f"All {self.retry_max} attempts failed")
        return pd.DataFrame()

    def get_stock_list(self) -> pd.DataFrame:
        """获取A股股票列表"""
        logger.info("Fetching stock list...")
        df = self._fetch_with_retry(ak.stock_zh_a_spot_em)

        if df.empty:
            return df

        # 标准化列名
        result = pd.DataFrame({
            "code": df["代码"].str.strip(),
            "name": df["名称"].str.strip(),
        })

        # 过滤：去掉ST、退市、停牌等异常股票
        result = result[~result["name"].str.contains("ST|退|N", na=False)]
        # 只保留主板+创业板+科创板（6/0/3开头）
        result = result[result["code"].str.match(r"^(6|0|3)\d{5}$")]

        # 缓存
        result.to_csv(os.path.join(self.cache_path, "stock_list.csv"), index=False)
        logger.info(f"Stock list: {len(result)} stocks")
        return result

    def get_daily_quote(self, code: str, start_date: str,
                        end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取单只股票日线行情

        Args:
            code: 股票代码，如 "000001"
            start_date: 开始日期，如 "20200101"
            end_date: 结束日期，如 "20260528"
            adjust: 复权方式，qfq=前复权
        """
        logger.info(f"Fetching daily quote: {code} {start_date}-{end_date}")

        # akshare 的股票代码需要带市场标识
        symbol = code
        if code.startswith("6"):
            symbol = code  # 沪市
        elif code.startswith("0") or code.startswith("3"):
            symbol = code  # 深市

        df = self._fetch_with_retry(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )

        if df.empty:
            return df

        # 标准化列名
        result = pd.DataFrame({
            "code": code,
            "date": pd.to_datetime(df["日期"]),
            "open": df["开盘"],
            "high": df["最高"],
            "low": df["最低"],
            "close": df["收盘"],
            "volume": df["成交量"],
            "turnover": df["成交额"],
            "change_pct": df["涨跌幅"],
            "turnover_rate": df["换手率"],
        })

        # 缓存单只股票
        cache_file = os.path.join(self.cache_path, f"daily_{code}.csv")
        if os.path.exists(cache_file):
            old = pd.read_csv(cache_file)
            combined = pd.concat([old, result]).drop_duplicates(subset=["code", "date"])
            combined.to_csv(cache_file, index=False)
            result = combined
        else:
            result.to_csv(cache_file, index=False)

        logger.info(f"Daily quote: {code}, {len(result)} rows")
        return result

    def get_daily_quote_batch(self, codes: list, start_date: str,
                              end_date: str, batch_size: int = 50) -> pd.DataFrame:
        """批量获取日线行情"""
        all_data = []
        total = len(codes)

        for i, code in enumerate(codes):
            if (i + 1) % batch_size == 0:
                logger.info(f"Progress: {i+1}/{total} stocks")

            df = self.get_daily_quote(code, start_date, end_date)
            if not df.empty:
                all_data.append(df)

            # 避免请求过快被限流
            time.sleep(1.0)

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"Batch complete: {len(result)} total rows from {len(all_data)} stocks")
            return result

        return pd.DataFrame()

    def get_index_quote(self, code: str, start_date: str,
                        end_date: str) -> pd.DataFrame:
        """获取指数日线行情

        Args:
            code: 指数代码，如 "000300"（沪深300）
        """
        logger.info(f"Fetching index quote: {code}")

        df = self._fetch_with_retry(
            ak.stock_zh_index_daily_em,
            symbol=code
        )

        if df.empty:
            return df

        # 标准化列名
        result = pd.DataFrame({
            "code": code,
            "date": pd.to_datetime(df["日期"]),
            "open": df["开盘"],
            "high": df["最高"],
            "low": df["最低"],
            "close": df["收盘"],
            "volume": df["成交量"],
            "turnover": df["成交额"],
        })

        # 过滤日期范围
        result = result[
            (result["date"] >= pd.Timestamp(start_date)) &
            (result["date"] <= pd.Timestamp(end_date))
        ]

        # 缓存
        result.to_csv(os.path.join(self.cache_path, f"index_{code}.csv"), index=False)
        logger.info(f"Index {code}: {len(result)} rows")
        return result