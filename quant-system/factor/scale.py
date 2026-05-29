"""规模因子 - 总市值/流通市值"""

import pandas as pd
import numpy as np
from factor.base import BaseFactor, FactorInfo


class MCAP(BaseFactor):
    """总市值因子"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="MCAP",
            category="scale",
            description="Total market capitalization (log)",
            freq="daily",
            depends=["daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 log(总市值)

        df 需包含: code, total_mv
        用 log 值，避免极端市值差异过大
        注意：小市值因子方向是 log(mcap) 的负值（小市值 = 高因子值 = 更好）
        但这里先返回原始 log(mcap)，检验时再看方向
        """
        total_mv = pd.to_numeric(df["total_mv"], errors="coerce")
        mcap = np.log(total_mv + 1e-10)
        mcap[(total_mv <= 0) | total_mv.isna()] = np.nan
        return mcap


class FCAP(BaseFactor):
    """流通市值因子"""

    def info(self) -> FactorInfo:
        return FactorInfo(
            name="FCAP",
            category="scale",
            description="Float market capitalization (log)",
            freq="daily",
            depends=["daily_quote"],
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算 log(流通市值)

        df 需包含: code, circ_mv
        """
        circ_mv = pd.to_numeric(df["circ_mv"], errors="coerce")
        fcap = np.log(circ_mv + 1e-10)
        fcap[(circ_mv <= 0) | circ_mv.isna()] = np.nan
        return fcap