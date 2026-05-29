"""A股分红数据采集模块"""

import time
import os
import pandas as pd
import akshare as ak
from loguru import logger


class DividendCollector:
    """A股分红数据采集器

    用于计算 DP（股息率）因子
    """

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
                    time.sleep(self.retry_delay * attempt)
        return pd.DataFrame()

    def get_dividend(self, code: str) -> pd.DataFrame:
        """获取单只股票分红历史

        Returns: DataFrame [code, year, dividend_per_share, ex_date]
        """
        logger.info(f"Fetching dividend data: {code}")

        try:
            df = self._fetch_with_retry(ak.stock_dividend_hist_cninfo, symbol=code)
            if df.empty:
                return df

            result = pd.DataFrame()
            result["code"] = code

            # 标准化列名（akshare分红接口返回列名不固定）
            col_map = {
                "year": ["分红年度", "年度", "year", "报告期"],
                "dividend_per_share": ["每股派息", "每股分红", "分红金额", "每股股利", "现金分红"],
                "ex_date": ["除权除息日", "除息日", "ex_date", "派息日期"],
            }

            for target, sources in col_map.items():
                for src in sources:
                    if src in df.columns:
                        if target == "year":
                            result[target] = df[src]
                        elif target == "ex_date":
                            result[target] = pd.to_datetime(df[src], errors="coerce")
                        else:
                            result[target] = pd.to_numeric(df[src], errors="coerce")
                        break
                if target not in result.columns:
                    result[target] = None

            # 如果有报告期，提取年份
            if "year" not in result.columns or result["year"].isna().all():
                if "报告期" in df.columns:
                    result["year"] = df["报告期"].str[:4]

            result = result.dropna(subset=["dividend_per_share"], how="all")

            cache_file = os.path.join(self.cache_path, f"dividend_{code}.csv")
            result.to_csv(cache_file, index=False)
            logger.info(f"Dividend {code}: {len(result)} rows")
            return result

        except Exception as e:
            logger.error(f"Dividend error for {code}: {e}")
            return pd.DataFrame()

    def get_dividend_batch(self, codes: list, batch_size: int = 50) -> pd.DataFrame:
        """批量获取分红数据"""
        all_data = []
        total = len(codes)

        for i, code in enumerate(codes):
            if (i + 1) % batch_size == 0:
                logger.info(f"Dividend progress: {i+1}/{total}")

            df = self.get_dividend(code)
            if not df.empty:
                all_data.append(df)

            time.sleep(0.5)

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"Dividend batch: {len(result)} rows")
            return result

        return pd.DataFrame()