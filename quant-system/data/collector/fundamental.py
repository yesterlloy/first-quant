"""财务数据采集模块"""

import time
import os
import pandas as pd
import akshare as ak
from loguru import logger


class FundamentalCollector:
    """A股财务数据采集"""

    def __init__(self, retry_max: int = 3, retry_delay: int = 5,
                 cache_path: str = "data/cache"):
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        self.cache_path = cache_path
        os.makedirs(cache_path, exist_ok=True)

    def _fetch_with_retry(self, func, *args, **kwargs) -> pd.DataFrame:
        for attempt in range(1, self.retry_max + 1):
            try:
                df = func(*args, **kwargs)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt < self.retry_max:
                    time.sleep(self.retry_delay)
        return pd.DataFrame()

    def get_financial(self, code: str) -> pd.DataFrame:
        """获取单只股票财务指标

        Returns: DataFrame with columns [code, date, pe, pb, roe, revenue, net_profit]
        """
        logger.info(f"Fetching financial data: {code}")

        try:
            # 获取主要财务指标
            df = self._fetch_with_retry(ak.stock_financial_analysis_thi, symbol=code)

            if df.empty:
                return df

            # 标准化
            result = pd.DataFrame()
            result["code"] = code
            result["date"] = pd.to_datetime(df["日期"], format="mixed", errors="coerce")

            # 映射财务指标（akshare返回的列名可能变化，做兼容处理）
            col_map = {
                "pe": ["市盈率", "PE", "pe_ratio"],
                "pb": ["市净率", "PB", "pb_ratio"],
                "roe": ["净资产收益率", "ROE", "roe"],
                "revenue": ["营业收入", "总营收", "revenue"],
                "net_profit": ["净利润", "归母净利润", "net_profit"],
            }

            for target, sources in col_map.items():
                for src in sources:
                    if src in df.columns:
                        result[target] = pd.to_numeric(df[src], errors="coerce")
                        break
                if target not in result.columns:
                    result[target] = None

            result = result.dropna(subset=["date"])

            # 缓存
            result.to_csv(os.path.join(self.cache_path, f"financial_{code}.csv"), index=False)
            logger.info(f"Financial {code}: {len(result)} rows")
            return result

        except Exception as e:
            logger.error(f"Financial data error for {code}: {e}")
            return pd.DataFrame()

    def get_financial_batch(self, codes: list, batch_size: int = 50) -> pd.DataFrame:
        """批量获取财务数据"""
        all_data = []
        total = len(codes)

        for i, code in enumerate(codes):
            if (i + 1) % batch_size == 0:
                logger.info(f"Financial progress: {i+1}/{total}")

            df = self.get_financial(code)
            if not df.empty:
                all_data.append(df)

            time.sleep(0.5)

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"Financial batch: {len(result)} rows")
            return result

        return pd.DataFrame()