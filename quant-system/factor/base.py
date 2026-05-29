"""因子基类 - 统一因子接口定义"""

import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class FactorInfo:
    """因子元信息"""
    name: str               # 因子名称，如 "EP", "ROE"
    category: str           # 分类：valuation/growth/quality/technical/scale
    description: str = ""   # 因子描述
    lookback: int = 0       # 回看期（交易日数），技术因子用
    freq: str = "daily"     # 频率：daily/quarterly/monthly
    depends: list = field(default_factory=list)  # 数据依赖表


class BaseFactor(ABC):
    """因子计算基类

    所有因子继承此基类，统一接口：
    - compute(): 计算因子值
    - info(): 返回因子元信息
    - neutralize(): 行业/市值中性化（可选）
    """

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算因子值

        Args:
            df: 截面数据 DataFrame，包含因子所需的所有列
               对于日频因子：df 包含单日全市场股票的行情/财务数据
               对于季频因子：df 包含单季度全市场股票的财务数据

        Returns:
            pd.Series: 因子值，index 为股票代码
        """
        raise NotImplementedError

    @abstractmethod
    def info(self) -> FactorInfo:
        """返回因子元信息"""
        raise NotImplementedError

    def neutralize(self, factor_df: pd.Series, industry_df: pd.Series,
                   market_cap_df: pd.Series = None,
                   method: str = "industry") -> pd.Series:
        """因子中性化

        Args:
            factor_df: 因子值 Series（index=code）
            industry_df: 行业分类 Series（index=code）
            market_cap_df: 市值 Series（index=code），市值中性化时需要
            method: "industry"（行业中性化）或 "market_cap"（市值中性化）或 "both"

        Returns:
            中性化后的因子值 Series
        """
        result = factor_df.copy()

        if method in ("industry", "both") and industry_df is not None:
            # 行业中性化：减去行业内均值
            aligned = pd.DataFrame({
                "factor": factor_df,
                "industry": industry_df,
            }).dropna()
            industry_mean = aligned.groupby("industry")["factor"].mean()
            result = aligned["factor"] - aligned["industry"].map(industry_mean)
            result = result.reindex(factor_df.index)

        if method in ("market_cap", "both") and market_cap_df is not None:
            # 市值中性化：对市值回归取残差
            aligned = pd.DataFrame({
                "factor": result,
                "mcap": market_cap_df,
            }).dropna()
            if len(aligned) > 10:  # 样本太少不做回归
                # 简单线性回归：factor = a + b * log(mcap) + residual
                import numpy as np
                log_mcap = np.log(aligned["mcap"].values)
                y = aligned["factor"].values
                # OLS: y = beta * x + alpha
                beta = np.cov(y, log_mcap)[0, 1] / np.var(log_mcap)
                alpha = np.mean(y) - beta * np.mean(log_mcap)
                residual = y - beta * log_mcap - alpha
                aligned["factor"] = residual
                result = aligned["factor"].reindex(factor_df.index)

        return result