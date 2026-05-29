"""因子中性化处理模块"""

import pandas as pd
import numpy as np
from loguru import logger


def neutralize_industry(factor_df: pd.Series, industry_df: pd.Series) -> pd.Series:
    """行业中性化：减去行业内均值

    Args:
        factor_df: 因子值 Series（index=code）
        industry_df: 行业分类 Series（index=code）

    Returns:
        中性化后的因子值 Series
    """
    aligned = pd.DataFrame({
        "factor": factor_df,
        "industry": industry_df,
    }).dropna()

    if aligned.empty:
        logger.warning("No aligned data for industry neutralization")
        return factor_df

    industry_mean = aligned.groupby("industry")["factor"].mean()
    result = aligned["factor"] - aligned["industry"].map(industry_mean)
    return result.reindex(factor_df.index)


def neutralize_market_cap(factor_df: pd.Series, market_cap_df: pd.Series) -> pd.Series:
    """市值中性化：对 log(mcap) 回归取残差

    Args:
        factor_df: 因子值 Series（index=code）
        market_cap_df: 总市值 Series（index=code）

    Returns:
        中性化后的因子值 Series
    """
    aligned = pd.DataFrame({
        "factor": factor_df,
        "mcap": market_cap_df,
    }).dropna()

    if len(aligned) < 10:
        logger.warning(f"Too few samples ({len(aligned)}) for market cap neutralization")
        return factor_df

    log_mcap = np.log(aligned["mcap"].values)
    y = aligned["factor"].values

    # OLS: y = beta * log_mcap + alpha + residual
    beta = np.cov(y, log_mcap)[0, 1] / np.var(log_mcap)
    alpha = np.mean(y) - beta * np.mean(log_mcap)
    residual = y - beta * log_mcap - alpha

    aligned["factor"] = residual
    return aligned["factor"].reindex(factor_df.index)


def neutralize_both(factor_df: pd.Series, industry_df: pd.Series,
                    market_cap_df: pd.Series) -> pd.Series:
    """双重中性化：先行业，后市值"""
    step1 = neutralize_industry(factor_df, industry_df)
    return neutralize_market_cap(step1, market_cap_df)


def neutralize(factor_df: pd.Series, industry_df: pd.Series = None,
               market_cap_df: pd.Series = None,
               method: str = "industry") -> pd.Series:
    """统一中性化入口

    Args:
        method: "industry" | "market_cap" | "both"
    """
    if method == "industry":
        return neutralize_industry(factor_df, industry_df)
    elif method == "market_cap":
        return neutralize_market_cap(factor_df, market_cap_df)
    elif method == "both":
        return neutralize_both(factor_df, industry_df, market_cap_df)
    else:
        logger.warning(f"Unknown neutralization method: {method}")
        return factor_df