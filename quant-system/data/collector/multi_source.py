"""多数据源采集器 - 自动切换，某源失败自动尝试下一个"""

import os
import time
import concurrent.futures

os.environ["no_proxy"] = "eastmoney.com,push2.eastmoney.com,*.eastmoney.com,sina.com.cn,*.sina.com.cn,tushare.cn"
os.environ["NO_PROXY"] = os.environ["no_proxy"]

import pandas as pd
from loguru import logger


class MultiSourceCollector:
    """多数据源采集器，支持自动降级切换

    数据源优先级：
    - 股票列表：adata → akshare(sina) → akshare(eastmoney)
    - 日线行情：baostock → akshare(eastmoney)
    - 指数行情：baostock → akshare(eastmoney)
    """

    def __init__(self, retry_max: int = 3, retry_delay: int = 10,
                 cache_path: str = "data/cache"):
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        self.cache_path = cache_path
        os.makedirs(cache_path, exist_ok=True)

    def _try_source(self, name: str, func, timeout: int = 30) -> pd.DataFrame:
        """尝试单个数据源，带超时保护，失败返回空 DataFrame"""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func)
                df = future.result(timeout=timeout)
            if df is not None and not df.empty:
                logger.info(f"[{name}] OK: {len(df)} rows")
                return df
            logger.warning(f"[{name}] returned empty")
        except concurrent.futures.TimeoutError:
            logger.warning(f"[{name}] timed out after {timeout}s")
        except Exception as e:
            logger.warning(f"[{name}] failed: {type(e).__name__}: {e}")
        return pd.DataFrame()

    # ── 股票列表 ────────────────────────────────────────────

    def get_stock_list(self) -> pd.DataFrame:
        """获取A股股票列表，多源自动切换"""
        logger.info("=== Fetching stock list ===")
        result = self._try_source("adata", self._stock_list_adata)
        if result.empty:
            result = self._try_source("baostock", self._stock_list_baostock)
        if result.empty:
            result = self._try_source("akshare-sina", self._stock_list_akshare_sina)
        if result.empty:
            result = self._try_source("akshare-em", self._stock_list_akshare_em)
        # 最后尝试读缓存
        if result.empty:
            cache_file = os.path.join(self.cache_path, "stock_list.csv")
            if os.path.exists(cache_file):
                logger.info("[cache] Using cached stock_list.csv")
                result = pd.read_csv(cache_file, dtype={"code": str})
                result["code"] = result["code"].astype(str).str.zfill(6)
        if not result.empty:
            result.to_csv(os.path.join(self.cache_path, "stock_list.csv"), index=False)
        return result

    def _stock_list_adata(self) -> pd.DataFrame:
        import adata
        df = adata.stock.info.all_code()
        # 动态查找上市日期列（adata 版本间列名可能不同）
        date_col = next((c for c in df.columns if "list" in c.lower() and "date" in c.lower()), None)
        result = pd.DataFrame({
            "code": df["stock_code"].str.strip(),
            "name": df["short_name"].str.strip(),
        })
        if date_col:
            result["list_date"] = pd.to_datetime(df[date_col], errors="coerce")
        else:
            result["list_date"] = pd.NaT
        return self._filter_stock_list(result)

    def _stock_list_baostock(self) -> pd.DataFrame:
        import baostock as bs
        lg = bs.login()
        if lg is None or (hasattr(lg, 'error_code') and lg.error_code != '0'):
            raise RuntimeError(f"baostock login failed: {lg}")
        try:
            rs = bs.query_stock_basic()
            if rs is None:
                return pd.DataFrame()
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
        finally:
            bs.logout()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=rs.fields)
        # baostock 代码格式 sh.600000 → 取后6位
        result = pd.DataFrame({
            "code": df["code"].str.extract(r"\.(\d{6})$")[0],
            "name": df["code_name"].str.strip() if "code_name" in df.columns else "",
            "list_date": pd.to_datetime(df.get("ipoDate", pd.NaT), format="%Y-%m-%d", errors="coerce"),
        })
        result = result[result["code"].notna()]
        return self._filter_stock_list(result)

    def _stock_list_akshare_sina(self) -> pd.DataFrame:
        import akshare as ak
        df = ak.stock_zh_a_spot()
        result = pd.DataFrame({
            "code": df["代码"].str.strip(),
            "name": df["名称"].str.strip(),
        })
        result["list_date"] = pd.NaT
        return self._filter_stock_list(result)

    def _stock_list_akshare_em(self) -> pd.DataFrame:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        result = pd.DataFrame({
            "code": df["代码"].str.strip(),
            "name": df["名称"].str.strip(),
        })
        result["list_date"] = pd.NaT
        return self._filter_stock_list(result)

    def _filter_stock_list(self, df: pd.DataFrame) -> pd.DataFrame:
        """过滤股票列表：去ST/退市，只保留主板+创业板+科创板"""
        df = df[~df["name"].str.contains("ST|退", na=False)]
        df = df[df["code"].str.match(r"^(6|0|3)\d{5}$")]
        # 补齐 stock_info 表需要的列
        if "industry" not in df.columns:
            df["industry"] = None
        if "list_date" not in df.columns:
            df["list_date"] = pd.NaT
        if "delist_date" not in df.columns:
            df["delist_date"] = pd.NaT
        # 确保列顺序与 stock_info 表一致
        df = df[["code", "name", "industry", "list_date", "delist_date"]]
        logger.info(f"Filtered stock list: {len(df)} stocks")
        return df

    # ── 日线行情（单只） ────────────────────────────────────

    def get_daily_quote(self, code: str, start_date: str,
                        end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取单只股票日线行情，多源自动切换"""
        result = self._try_source("baostock", lambda: self._daily_quote_baostock(code, start_date, end_date), timeout=30)
        if result.empty:
            result = self._try_source("akshare-em", lambda: self._daily_quote_akshare(code, start_date, end_date, adjust), timeout=30)

        # 缓存
        if not result.empty:
            # 确保 code 为6位零填充字符串
            result["code"] = result["code"].astype(str).str.zfill(6)
            result["date"] = pd.to_datetime(result["date"])
            cache_file = os.path.join(self.cache_path, f"daily_{code}.csv")
            if os.path.exists(cache_file):
                old = pd.read_csv(cache_file, dtype={"code": str})
                old["code"] = old["code"].astype(str).str.zfill(6)
                old["date"] = pd.to_datetime(old["date"], format="ISO8601")
                combined = pd.concat([old, result]).drop_duplicates(subset=["code", "date"])
                combined.to_csv(cache_file, index=False)
                result = combined
            else:
                result.to_csv(cache_file, index=False)
        return result

    def _daily_quote_adata(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        import adata
        start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
        df = adata.stock.market.get_market(stock_code=code, start_date=start, end_date=end, k_type=1)
        if df.empty:
            return df
        return pd.DataFrame({
            "code": code,
            "date": pd.to_datetime(df["trade_date"]),
            "open": df["open"].astype(float),
            "high": df["high"].astype(float),
            "low": df["low"].astype(float),
            "close": df["close"].astype(float),
            "volume": df["volume"].astype(float),
            "turnover": df["amount"].astype(float),
            "change_pct": df["change_pct"].astype(float),
            "turnover_rate": df["turnover_ratio"].astype(float),
        })

    def _daily_quote_baostock(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        import baostock as bs
        prefix = "sh" if code.startswith("6") else "sz"
        bs_code = f"{prefix}.{code}"
        start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

        lg = bs.login()
        if lg is None or (hasattr(lg, 'error_code') and lg.error_code != '0'):
            raise RuntimeError(f"baostock login failed: {lg}")
        try:
            rs = bs.query_history_k_data_plus(
                bs_code, "date,open,high,low,close,volume,amount,pctChg,turn",
                start_date=start, end_date=end, frequency="d", adjustflag="2"
            )
            if rs is None:
                return pd.DataFrame()
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
        finally:
            bs.logout()

        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "turnover", "change_pct", "turnover_rate"])
        # baostock 可能有空字符串
        for col in ["open", "high", "low", "close", "volume", "turnover", "change_pct", "turnover_rate"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        df["code"] = code
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["volume"] > 0]  # 过滤停牌日
        return df[["code", "date", "open", "high", "low", "close", "volume", "turnover", "change_pct", "turnover_rate"]]

    def _daily_quote_akshare(self, code: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
        if df.empty:
            return df
        return pd.DataFrame({
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

    # ── 批量日线行情 ────────────────────────────────────────

    def get_daily_quote_batch(self, codes: list, start_date: str,
                              end_date: str, batch_size: int = 50) -> pd.DataFrame:
        """批量获取日线行情，支持断点续传（跳过已缓存的股票）"""
        all_data = []
        skipped = 0
        failed = 0
        total = len(codes)

        # 找出还没缓存的股票
        pending_codes = []
        for code in codes:
            cache_file = os.path.join(self.cache_path, f"daily_{code}.csv")
            if os.path.exists(cache_file):
                skipped += 1
            else:
                pending_codes.append(code)

        if skipped > 0:
            logger.info(f"Resume: skipping {skipped} cached stocks, {len(pending_codes)} remaining")

        pending_total = len(pending_codes)
        for i, code in enumerate(pending_codes):
            if (i + 1) % 20 == 0 or i == 0:
                logger.info(f"Progress: {i+1}/{pending_total} (collected: {len(all_data)}, failed: {failed}, skipped: {skipped})")

            df = self.get_daily_quote(code, start_date, end_date)
            if not df.empty:
                all_data.append(df)
            else:
                failed += 1

            # 控制请求频率
            time.sleep(0.3)

        logger.info(f"Batch complete: {len(all_data)} stocks collected, {failed} failed, {skipped} skipped (cached)")
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"Total rows: {len(result)}")
            return result
        return pd.DataFrame()

    # ── 指数行情 ────────────────────────────────────────────

    def get_index_quote(self, code: str, start_date: str,
                        end_date: str) -> pd.DataFrame:
        """获取指数日线行情，多源自动切换"""
        logger.info(f"Fetching index quote: {code}")
        result = self._try_source("baostock", lambda: self._index_quote_baostock(code, start_date, end_date))
        if result.empty:
            result = self._try_source("akshare-em", lambda: self._index_quote_akshare(code, start_date, end_date))
        if not result.empty:
            result.to_csv(os.path.join(self.cache_path, f"index_{code}.csv"), index=False)
        return result

    def _index_quote_baostock(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        import baostock as bs
        bs_code = f"sh.{code}"
        start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

        lg = bs.login()
        if lg is None or (hasattr(lg, 'error_code') and lg.error_code != '0'):
            raise RuntimeError(f"baostock login failed: {lg}")
        try:
            rs = bs.query_history_k_data_plus(
                bs_code, "date,open,high,low,close,volume,amount",
                start_date=start, end_date=end, frequency="d"
            )
            if rs is None:
                return pd.DataFrame()
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
        finally:
            bs.logout()

        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "turnover"])
        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        df["code"] = code
        df["date"] = pd.to_datetime(df["date"])
        return df[["code", "date", "open", "high", "low", "close", "volume", "turnover"]]

    def _index_quote_akshare(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        import akshare as ak
        df = ak.stock_zh_index_daily_em(symbol=code)
        if df.empty:
            return df
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
        return result[
            (result["date"] >= pd.Timestamp(start_date)) &
            (result["date"] <= pd.Timestamp(end_date))
        ]
