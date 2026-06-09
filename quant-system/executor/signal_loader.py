"""信号加载模块 - 从ml_signal表加载ML预测信号"""

import pandas as pd
from loguru import logger
from data.db.duckdb_manager import DuckDBManager


class SignalLoader:
    """从数据库加载ML信号"""

    def __init__(self, db: DuckDBManager):
        self.db = db

    def load_signals(self, date: str, model_name: str = "lgbm_v1") -> pd.DataFrame:
        """加载指定日期的ML信号

        Args:
            date: 调仓日期 (YYYY-MM-DD)
            model_name: 模型版本名

        Returns:
            DataFrame: [code, date, predicted_return, signal]
        """
        try:
            sql = f"""
                SELECT code, date, predicted_return, signal
                FROM ml_signal
                WHERE date = '{date}' AND model_name = '{model_name}'
                ORDER BY predicted_return DESC
            """
            result = self.db.query(sql)

            if result.empty:
                logger.warning(f"No signals for date={date}, model={model_name}")

            return result

        except Exception as e:
            logger.error(f"Failed to load signals: {e}")
            return pd.DataFrame()