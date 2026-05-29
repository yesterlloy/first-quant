"""因子计算引擎 - 批量计算+缓存+入库"""

import os
import pandas as pd
import numpy as np
from loguru import logger
from factor.registry import FactorRegistry, auto_register
from factor.base import BaseFactor
from data.db.duckdb_manager import DuckDBManager


class FactorEngine:
    """因子计算引擎

    职责：
    - 从DB读取原始数据
    - 按日期/季度批量计算所有因子
    - 结果缓存+入库
    - 支持单因子计算和全量计算
    """

    def __init__(self, db: DuckDBManager, cache_path: str = "data/cache/factor"):
        self.db = db
        self.cache_path = cache_path
        os.makedirs(cache_path, exist_ok=True)

        # 自动注册所有因子
        auto_register()
        logger.info(f"FactorEngine initialized with {FactorRegistry.count()} factors")

    def compute_factor(self, factor_name: str, date: str = None,
                       neutralize_method: str = None) -> pd.DataFrame:
        """计算单个因子在某日期的截面值

        Args:
            factor_name: 因子名称
            date: 日期（日频因子）或季度末日期（季频因子）
            neutralize_method: 中性化方式 None/industry/market_cap/both

        Returns:
            DataFrame [code, date, factor_name, raw_value, neut_value]
        """
        factor = FactorRegistry.get(factor_name)
        info = factor.info()

        # 获取截面数据
        cross_df = self._get_cross_section(info, date)
        if cross_df.empty:
            logger.warning(f"No cross-section data for {factor_name} at {date}")
            return pd.DataFrame()

        # 计算因子原始值
        raw_values = factor.compute(cross_df)
        raw_values.name = "raw_value"

        # 构建结果 DataFrame
        result = pd.DataFrame({
            "code": cross_df["code"],
            "date": date or str(cross_df.get("date", pd.Timestamp.today())),
            "factor_name": factor_name,
            "raw_value": raw_values,
            "neut_value": np.nan,  # 先填NaN，后面中性化时填充
        })

        # 中性化（可选）
        if neutralize_method:
            industry_df = self._get_industry_series()
            mcap_df = self._get_mcap_series(date)
            neut_values = factor.neutralize(
                raw_values, industry_df, mcap_df, method=neutralize_method
            )
            result["neut_value"] = neut_values

        # 去除 NaN
        result = result.dropna(subset=["raw_value"])
        logger.info(f"Computed {factor_name}: {len(result)} valid values at {date}")
        return result

    def compute_all_factors(self, date: str = None,
                            neutralize_method: str = None) -> pd.DataFrame:
        """批量计算所有因子在某日期的截面值

        Returns:
            合并后的 DataFrame [code, date, factor_name, raw_value, neut_value]
        """
        all_results = []
        for info in FactorRegistry.list_factors():
            try:
                df = self.compute_factor(
                    info.name, date=date, neutralize_method=neutralize_method
                )
                if not df.empty:
                    all_results.append(df)
            except Exception as e:
                logger.warning(f"Skip {info.name}: {e}")

        if all_results:
            result = pd.concat(all_results, ignore_index=True)
            logger.info(f"All factors computed: {len(result)} rows, "
                        f"{len(all_results)} factors at {date}")
            return result

        return pd.DataFrame()

    def compute_factor_series(self, factor_name: str,
                              start_date: str, end_date: str,
                              freq: str = "monthly") -> pd.DataFrame:
        """计算单个因子在时间序列上的值

        Args:
            factor_name: 因子名
            start_date/end_date: 起止日期
            freq: "monthly"（月末截面）或 "daily"（每日截面）

        Returns:
            合并的 DataFrame
        """
        # 根据频率生成日期序列
        if freq == "monthly":
            dates = pd.date_range(start_date, end_date, freq="ME").strftime("%Y-%m-%d")
        elif freq == "daily":
            dates = pd.date_range(start_date, end_date, freq="B").strftime("%Y-%m-%d")
        else:
            dates = [start_date, end_date]

        all_results = []
        for d in dates:
            try:
                df = self.compute_factor(factor_name, date=d)
                if not df.empty:
                    all_results.append(df)
            except Exception:
                continue

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()

    def compute_and_save(self, factor_name: str, date: str = None) -> pd.DataFrame:
        """计算因子并存入DB"""
        result = self.compute_factor(factor_name, date=date)
        if not result.empty:
            self.db.upsert_factor_value(result)
            # 缓存
            cache_file = os.path.join(
                self.cache_path,
                f"{factor_name}_{date or 'latest'}.csv"
            )
            result.to_csv(cache_file, index=False)
        return result

    # ---- 数据获取辅助 ----

    def _get_cross_section(self, info, date: str = None) -> pd.DataFrame:
        """获取因子所需的截面数据

        根据因子元信息，从不同表拼接截面数据
        """
        if not date:
            date = "2026-05-29"  # 默认最近

        cross = pd.DataFrame()

        if "daily_quote" in info.depends:
            # 日线行情截面
            daily = self.db.query(f"""
                SELECT code, close, volume, turnover, change_pct, turnover_rate
                FROM daily_quote
                WHERE date = '{date}'
            """)
            if not daily.empty:
                cross = daily if cross.empty else cross.merge(daily, on="code", how="outer")

        if "financial_ext" in info.depends:
            # 最近一期财务数据截面
            # 取每只股票最近的财务记录
            fin = self.db.query("""
                SELECT code, date, pe, pb, roe, roa, revenue, net_profit,
                       total_assets, total_liability, debt_ratio, ocf
                FROM financial_ext
            """)
            if not fin.empty:
                # 取每只股票最近的财务日期
                fin["date"] = pd.to_datetime(fin["date"])
                fin_latest = fin.sort_values("date").groupby("code").last().reset_index()
                cross = fin_latest if cross.empty else cross.merge(fin_latest, on="code", how="outer")

        if "dividend" in info.depends:
            # 最近一年分红数据
            div = self.db.query("SELECT code, year, dividend_per_share, ex_date FROM dividend")
            if not div.empty:
                div_latest = div.sort_values("year", ascending=False).groupby("code").first().reset_index()
                cross = div_latest if cross.empty else cross.merge(div_latest, on="code", how="outer")

        if "daily_quote" in info.depends and not cross.empty and "close" in cross.columns:
            # 合并市值数据（如果有的话）
            try:
                cap = self.db.query(f"SELECT code, total_mv, circ_mv FROM daily_quote WHERE date = '{date}'")
                if not cap.empty and "total_mv" in cap.columns:
                    cross = cross.merge(cap[["code", "total_mv", "circ_mv"]], on="code", how="left")
            except Exception:
                pass

        return cross.dropna(subset=["code"])

    def _get_industry_series(self) -> pd.Series:
        """获取行业分类 Series"""
        try:
            ind = self.db.query("SELECT code, industry_sw FROM industry_class")
            if not ind.empty:
                return pd.Series(ind["industry_sw"].values, index=ind["code"])
        except Exception:
            pass
        return pd.Series(dtype=str)

    def _get_mcap_series(self, date: str) -> pd.Series:
        """获取市值 Series"""
        try:
            cap = self.db.query(f"""
                SELECT code, total_mv FROM daily_quote WHERE date = '{date}'
            """)
            if not cap.empty and "total_mv" in cap.columns:
                return pd.Series(cap["total_mv"].values, index=cap["code"])
        except Exception:
            pass
        return pd.Series(dtype=float)