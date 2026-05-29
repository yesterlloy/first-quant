"""A股行业分类数据采集模块"""

import time
import os
import pandas as pd
import akshare as ak
from loguru import logger


class IndustryCollector:
    """A股行业分类采集器

    提供申万行业分类 + 中证行业分类，用于因子中性化
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

    def get_sw_industry(self) -> pd.DataFrame:
        """获取申万行业分类

        Returns: DataFrame [code, name, industry_sw, industry_sw_code]
        """
        logger.info("Fetching Shenwan industry classification...")

        try:
            # 申万行业分类成分股
            # 先获取行业列表
            sw_list = self._fetch_with_retry(ak.stock_board_industry_name_em)
            if sw_list.empty:
                logger.warning("Shenwan industry list empty, trying alternative...")
                return self._get_sw_industry_alt()

            all_data = []

            # 遍历每个行业，获取成分股
            industry_names = sw_list["板块名称"].tolist()
            # 申万一级约30+行业，控制采集量
            for ind_name in industry_names:
                try:
                    members = self._fetch_with_retry(
                        ak.stock_board_industry_cons_em, symbol=ind_name
                    )
                    if not members.empty:
                        sub = pd.DataFrame({
                            "code": members["代码"].str.strip(),
                            "name": members["名称"].str.strip(),
                            "industry_sw": ind_name,
                        })
                        all_data.append(sub)
                    time.sleep(0.3)
                except Exception as e:
                    logger.warning(f"Skip industry {ind_name}: {e}")
                    continue

            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                result = result[result["code"].str.match(r"^(6|0|3)\d{5}$")]
                result.to_csv(os.path.join(self.cache_path, "industry_sw.csv"), index=False)
                logger.info(f"Shenwan industry: {len(result)} stocks, {len(industry_names)} industries")
                return result

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Shenwan industry error: {e}")
            return self._get_sw_industry_alt()

    def _get_sw_industry_alt(self) -> pd.DataFrame:
        """备用方案：通过 stock_info 接口获取行业字段"""
        logger.info("Using alternative industry classification...")

        try:
            # stock_zh_a_spot_em 包含行业字段
            df = self._fetch_with_retry(ak.stock_zh_a_spot_em)
            if df.empty:
                return df

            result = pd.DataFrame({
                "code": df["代码"].str.strip(),
                "name": df["名称"].str.strip(),
                "industry_sw": df.get("所属行业", df.get("行业", pd.Series([None]*len(df)))),
            })

            result = result[~result["name"].str.contains("ST|退|N", na=False)]
            result = result[result["code"].str.match(r"^(6|0|3)\d{5}$")]

            result.to_csv(os.path.join(self.cache_path, "industry_sw.csv"), index=False)
            logger.info(f"Alt industry: {len(result)} stocks")
            return result

        except Exception as e:
            logger.error(f"Alt industry error: {e}")
            return pd.DataFrame()