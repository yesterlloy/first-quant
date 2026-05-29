"""A股财务数据扩展采集 - 更完整的财务指标"""

import time
import os
import pandas as pd
import akshare as ak
from loguru import logger


class FinancialExtCollector:
    """扩展财务数据采集器，补充 Phase 2 因子计算所需的财务指标

    相比 Phase 1 的 FundamentalCollector，增加了：
    - 总资产/总负债（资产负债率）
    - 经营现金流
    - 流通市值/总市值
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

    def get_financial_ext(self, code: str) -> pd.DataFrame:
        """获取单只股票扩展财务指标

        Returns: DataFrame [code, date, pe, pb, roe, roa, revenue, net_profit,
                            total_assets, total_liability, debt_ratio, ocf]
        """
        logger.info(f"Fetching extended financial data: {code}")

        try:
            # 主要财务指标
            df = self._fetch_with_retry(ak.stock_financial_analysis_thi, symbol=code)
            if df.empty:
                return df

            result = pd.DataFrame()
            result["code"] = code
            result["date"] = pd.to_datetime(df["日期"], format="mixed", errors="coerce")

            # 标准化列映射（akshare列名可能变化，做多候选兼容）
            col_map = {
                "pe": ["市盈率", "PE", "pe_ratio"],
                "pb": ["市净率", "PB", "pb_ratio"],
                "roe": ["净资产收益率", "ROE", "roe"],
                "roa": ["总资产净利率", "ROA", "roa"],
                "revenue": ["营业收入", "总营收", "revenue"],
                "net_profit": ["净利润", "归母净利润", "net_profit"],
                "total_assets": ["总资产", "资产总计", "total_assets"],
                "total_liability": ["总负债", "负债合计", "负债总计", "total_liability"],
                "debt_ratio": ["资产负债率", "负债率", "debt_ratio"],
                "ocf": ["经营现金流", "经营活动产生的现金流量净额", "ocf"],
            }

            for target, sources in col_map.items():
                for src in sources:
                    if src in df.columns:
                        result[target] = pd.to_numeric(df[src], errors="coerce")
                        break
                if target not in result.columns:
                    result[target] = None

            # 如果没有 debt_ratio，手动计算
            if "debt_ratio" not in result.columns or result["debt_ratio"].isna().all():
                if "total_assets" in result.columns and "total_liability" in result.columns:
                    result["debt_ratio"] = result["total_liability"] / result["total_assets"]

            result = result.dropna(subset=["date"])

            cache_file = os.path.join(self.cache_path, f"financial_ext_{code}.csv")
            result.to_csv(cache_file, index=False)
            logger.info(f"Financial ext {code}: {len(result)} rows")
            return result

        except Exception as e:
            logger.error(f"Financial ext error for {code}: {e}")
            return pd.DataFrame()

    def get_financial_ext_batch(self, codes: list, batch_size: int = 50) -> pd.DataFrame:
        """批量获取扩展财务数据"""
        all_data = []
        total = len(codes)

        for i, code in enumerate(codes):
            if (i + 1) % batch_size == 0:
                logger.info(f"Financial ext progress: {i+1}/{total}")

            df = self.get_financial_ext(code)
            if not df.empty:
                all_data.append(df)

            time.sleep(0.5)

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"Financial ext batch: {len(result)} rows from {len(all_data)} stocks")
            return result

        return pd.DataFrame()

    def get_market_cap(self) -> pd.DataFrame:
        """获取全市场市值数据（实时，用于规模因子）

        Returns: DataFrame [code, total_mv, circ_mv]
        """
        logger.info("Fetching market cap data...")

        try:
            df = self._fetch_with_retry(ak.stock_zh_a_spot_em)
            if df.empty:
                return df

            result = pd.DataFrame()
            result["code"] = df["代码"].str.strip()
            result["name"] = df["名称"].str.strip()

            # 总市值 / 流通市值（akshare字段名）
            cap_cols = {
                "total_mv": ["总市值", "总市值(元)"],
                "circ_mv": ["流通市值", "流通市值(元)"],
            }

            for target, sources in cap_cols.items():
                for src in sources:
                    if src in df.columns:
                        result[target] = pd.to_numeric(df[src], errors="coerce")
                        break
                if target not in result.columns:
                    result[target] = None

            # 过滤异常股票
            result = result[~result["name"].str.contains("ST|退|N", na=False)]
            result = result[result["code"].str.match(r"^(6|0|3)\d{5}$")]

            result.to_csv(os.path.join(self.cache_path, "market_cap.csv"), index=False)
            logger.info(f"Market cap: {len(result)} stocks")
            return result

        except Exception as e:
            logger.error(f"Market cap error: {e}")
            return pd.DataFrame()