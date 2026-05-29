"""特征工程模块 - 数据清洗+标准化+因子交叉+滞后特征"""

import pandas as pd
import numpy as np
from loguru import logger
from factor.registry import FactorRegistry, auto_register


class FeatureEngine:
    """特征工程引擎

    处理步骤：
    1. 缺失值填充（行业均值 → 0）
    2. 去极值（MAD法 winsorize）
    3. 截面Z-score标准化
    4. 因子交叉特征（EP×MOM等）
    5. 滞后特征（1月/3月/6月）
    6. 行业虚拟变量
    """

    def __init__(self, n_mad: float = 3.0, fill_method: str = "industry_mean"):
        """
        Args:
            n_mad: MAD去极值阈值，默认3倍
            fill_method: 缺失值填充方式，"industry_mean"/"zero"/"median"
        """
        self.n_mad = n_mad
        self.fill_method = fill_method

    def fill_missing(self, df: pd.DataFrame, industry_df: pd.Series = None) -> pd.DataFrame:
        """缺失值填充

        Args:
            df: 特征 DataFrame（index=code, columns=factor_names）
            industry_df: 行业分类 Series（index=code）

        Returns:
            填充后的 DataFrame
        """
        if self.fill_method == "industry_mean" and industry_df is not None:
            # 行业均值填充
            for col in df.columns:
                if df[col].isna().any():
                    industry_mean = df[col].groupby(industry_df).mean()
                    # 用行业均值填充，无行业信息的用全局均值
                    global_mean = df[col].mean()
                    fill_values = industry_df.map(industry_mean).fillna(global_mean)
                    df[col] = df[col].fillna(fill_values)
        elif self.fill_method == "median":
            df = df.fillna(df.median())
        elif self.fill_method == "zero":
            df = df.fillna(0)

        # 仍存在的NaN（某行业全缺失等）用0兜底
        df = df.fillna(0)
        return df

    def winsorize_mad(self, df: pd.DataFrame) -> pd.DataFrame:
        """MAD法去极值

        对每列做 winsorize：超过 n_mad * MAD 的值被截断到边界
        """
        result = df.copy()
        for col in result.columns:
            series = result[col]
            median = series.median()
            mad = np.median(np.abs(series - median))  # MAD = median(|x - median(x)|)
            if mad < 1e-10:
                continue  # 常数列不做处理
            upper = median + self.n_mad * mad * 1.4826  # 1.4826是MAD→标准差的换算系数
            lower = median - self.n_mad * mad * 1.4826
            result[col] = series.clip(lower, upper)

        return result

    def cross_section_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        """截面Z-score标准化

        每列减均值除标准差，使得因子值在同一量纲下可比较
        """
        result = df.copy()
        for col in result.columns:
            mean = result[col].mean()
            std = result[col].std()
            if std < 1e-10:
                result[col] = 0  # 常数列标准化为0
            else:
                result[col] = (result[col] - mean) / std
        return result

    def generate_cross_features(self, df: pd.DataFrame,
                                 cross_pairs: list = None) -> pd.DataFrame:
        """因子交叉特征

        Args:
            df: 因子值 DataFrame（columns=factor_names）
            cross_pairs: 需要交叉的因子对列表，如 [("EP", "MOM")]
                        默认自动生成所有有效因子的两两交叉

        Returns:
            添加了交叉特征的 DataFrame
        """
        if cross_pairs is None:
            # 自动选取关键交叉组合（估值×技术，质量×技术）
            cross_pairs = [
                ("EP", "MOM_20"), ("BP", "MOM_20"),
                ("ROE", "MOM_20"), ("EP", "VOL_20"),
                ("BP", "TURN_20"), ("ROE", "VOL_20"),
            ]

        result = df.copy()
        for f1, f2 in cross_pairs:
            if f1 in df.columns and f2 in df.columns:
                result[f"{f1}_x_{f2}"] = df[f1] * df[f2]

        # 新列数
        new_cols = [f"{f1}_x_{f2}" for f1, f2 in cross_pairs
                    if f1 in df.columns and f2 in df.columns]
        if new_cols:
            logger.info(f"Generated {len(new_cols)} cross features: {new_cols}")
        return result

    def generate_lag_features(self, factor_series: pd.DataFrame,
                               lag_months: list = [1, 3, 6]) -> pd.DataFrame:
        """滞后特征

        Args:
            factor_series: 因子时间序列 [code, date, factor_name, raw_value]
            lag_months: 滞后月数列表

        Returns:
            添加了滞后特征的截面 DataFrame
        """
        result = factor_series.copy()
        factor_series["date"] = pd.to_datetime(factor_series["date"])
        factor_series = factor_series.sort_values(["code", "date"])

        for lag in lag_months:
            lag_days = lag * 20  # 近似：1月≈20交易日
            lagged = factor_series.groupby("code")["raw_value"].shift(lag_days)
            # 为每行添加滞后值
            factor_series[f"lag_{lag}m"] = lagged

        # 构宽表：每行是(code, date)，每列是因子名
        pivoted = factor_series.pivot_table(
            index=["code", "date"],
            columns="factor_name",
            values="raw_value",
        ).reset_index()

        # 添加滞后列（从factor_series中的lag列）
        lag_cols = factor_series.pivot_table(
            index=["code", "date"],
            columns="factor_name",
            values=[f"lag_{lag}m" for lag in lag_months],
        ).reset_index()

        if not lag_cols.empty:
            pivoted = pivoted.merge(lag_cols, on=["code", "date"], how="left")

        logger.info(f"Lag features: {len(lag_months)} lag periods")
        return pivoted

    def generate_industry_dummies(self, industry_df: pd.Series) -> pd.DataFrame:
        """行业虚拟变量

        Args:
            industry_df: 行业分类 Series（index=code）

        Returns:
            DataFrame of industry dummy variables（index=code）
        """
        dummies = pd.get_dummies(industry_df, prefix="ind")
        logger.info(f"Industry dummies: {dummies.shape[1]} industries")
        return dummies

    def build_features(self, factor_df: pd.DataFrame,
                       industry_df: pd.Series = None,
                       do_fill: bool = True,
                       do_winsorize: bool = True,
                       do_zscore: bool = True,
                       do_cross: bool = True,
                       do_dummies: bool = True) -> pd.DataFrame:
        """完整特征工程流水线

        Args:
            factor_df: 因子截面值宽表 [code, factor1, factor2, ...]
            industry_df: 行业分类 Series（index=code）

        Returns:
            处理后的特征 DataFrame（index=code）
        """
        # 设置code为index
        if "code" in factor_df.columns:
            feature_df = factor_df.set_index("code")
        else:
            feature_df = factor_df.copy()

        # 去掉非因子列（date等）
        non_factor_cols = ["date", "name"]
        feature_cols = [c for c in feature_df.columns if c not in non_factor_cols]
        feature_df = feature_df[feature_cols]

        logger.info(f"Raw features: {feature_df.shape[1]} columns, {feature_df.shape[0]} stocks")

        # 1. 缺失值填充
        if do_fill:
            feature_df = self.fill_missing(feature_df, industry_df)
            logger.info(f"Fill missing: done")

        # 2. 去极值
        if do_winsorize:
            feature_df = self.winsorize_mad(feature_df)
            logger.info(f"Winsorize MAD({self.n_mad}): done")

        # 3. Z-score标准化
        if do_zscore:
            feature_df = self.cross_section_zscore(feature_df)
            logger.info(f"Z-score: done")

        # 4. 因子交叉
        if do_cross:
            feature_df = self.generate_cross_features(feature_df)

        # 5. 行业虚拟变量
        if do_dummies and industry_df is not None:
            dummies = self.generate_industry_dummies(industry_df)
            # 对齐index
            common_idx = feature_df.index.intersection(dummies.index)
            feature_df = feature_df.loc[common_idx].join(dummies.loc[common_idx])

        logger.info(f"Final features: {feature_df.shape[1]} columns, {feature_df.shape[0]} stocks")
        return feature_df