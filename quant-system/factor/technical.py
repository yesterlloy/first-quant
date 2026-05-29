"""技术因子 - MOM/REV/VOL/TURN/LIQ"""

import pandas as pd
import numpy as np
from factor.base import BaseFactor, FactorInfo


class MOM(BaseFactor):
    """动量因子（过去N日累计收益）"""

    def __init__(self, lookback: int = 20):
        self._lookback = lookback

    def info(self) -> FactorInfo:
        return FactorInfo(
            name=f"MOM_{self._lookback}",
            category="technical",
            description=f"Momentum: past {self._lookback}-day cumulative return",
            lookback=self._lookback,
            freq="daily",
            depends=["daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算动量 = 过去N日收益率

        df 需包含: code, close（多日行情）
        每只股票取过去 lookback 日收盘价，算累计收益
        """
        lookback = self._lookback
        # df 是单日截面，需要多日行情来计算动量
        # 按 code 分组，取过去N日 close，算收益
        if "close_prev" in df.columns:
            # 已提供前N日收盘价
            close_now = pd.to_numeric(df["close"], errors="coerce")
            close_prev = pd.to_numeric(df["close_prev"], errors="coerce")
            return close_now / close_prev - 1.0
        else:
            # 直接用 change_pct 近似（简化：最近一日涨跌幅作为代理）
            return pd.to_numeric(df.get("change_pct", pd.Series(np.nan, index=df.index)), errors="coerce")


class REV(BaseFactor):
    """反转因子（短期收益反转）"""

    def __init__(self, lookback: int = 5):
        self._lookback = lookback

    def info(self) -> FactorInfo:
        return FactorInfo(
            name=f"REV_{self._lookback}",
            category="technical",
            description=f"Short-term reversal: negative of past {self._lookback}-day return",
            lookback=self._lookback,
            freq="daily",
            depends=["daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """反转因子 = -动量因子

        短期涨太多 → 反转看跌 → 因子值为负收益
        """
        mom = MOM(lookback=self._lookback).compute(df)
        return -mom


class VOL(BaseFactor):
    """波动率因子（日收益标准差）"""

    def __init__(self, lookback: int = 20):
        self._lookback = lookback

    def info(self) -> FactorInfo:
        return FactorInfo(
            name=f"VOL_{self._lookback}",
            category="technical",
            description=f"Volatility: past {self._lookback}-day return std",
            lookback=self._lookback,
            freq="daily",
            depends=["daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算波动率

        df 需包含: code, vol（预计算的波动率）或 change_pct 序列
        """
        if "vol" in df.columns:
            return pd.to_numeric(df["vol"], errors="coerce")
        else:
            # 简化：用 change_pct 的绝对值作为代理
            return pd.to_numeric(df.get("change_pct", pd.Series(np.nan, index=df.index)), errors="coerce").abs()


class TURN(BaseFactor):
    """换手率因子（日均换手率）"""

    def __init__(self, lookback: int = 20):
        self._lookback = lookback

    def info(self) -> FactorInfo:
        return FactorInfo(
            name=f"TURN_{self._lookback}",
            category="technical",
            description=f"Turnover rate: average daily turnover over {self._lookback} days",
            lookback=self._lookback,
            freq="daily",
            depends=["daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算换手率

        df 需包含: code, turnover_rate
        """
        return pd.to_numeric(df["turnover_rate"], errors="coerce")


class LIQ(BaseFactor):
    """Amihud非流动性因子（|收益|/成交额）"""

    def __init__(self, lookback: int = 20):
        self._lookback = lookback

    def info(self) -> FactorInfo:
        return FactorInfo(
            name=f"LIQ_{self._lookback}",
            category="technical",
            description=f"Amihud illiquidity: |return| / turnover over {self._lookback} days",
            lookback=self._lookback,
            freq="daily",
            depends=["daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算非流动性 = |涨跌幅| / 成交额

        df 需包含: code, change_pct, turnover
        值越大 → 流动性越差
        """
        change_pct = pd.to_numeric(df["change_pct"], errors="coerce").abs()
        turnover = pd.to_numeric(df["turnover"], errors="coerce")
        liq = change_pct / (turnover + 1e-10)  # 防除零
        liq[turnover <= 0] = np.nan
        return liq