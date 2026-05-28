"""DuckDB 数据库管理模块"""

import duckdb
import pandas as pd
from loguru import logger


class DuckDBManager:
    """DuckDB 数据库封装，提供读写接口"""

    def __init__(self, db_path: str = "data/db/quant.duckdb"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """建立数据库连接"""
        self.conn = duckdb.connect(self.db_path)
        self._create_tables()
        logger.info(f"DuckDB connected: {self.db_path}")
        return self

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB closed")

    def _create_tables(self):
        """创建数据表"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_quote (
                code VARCHAR,
                date DATE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                turnover DOUBLE,
                change_pct DOUBLE,
                turnover_rate DOUBLE,
                PRIMARY KEY (code, date)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_info (
                code VARCHAR PRIMARY KEY,
                name VARCHAR,
                industry VARCHAR,
                list_date DATE,
                delist_date DATE
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS financial (
                code VARCHAR,
                date DATE,
                pe DOUBLE,
                pb DOUBLE,
                roe DOUBLE,
                revenue DOUBLE,
                net_profit DOUBLE,
                PRIMARY KEY (code, date)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS index_quote (
                code VARCHAR,
                date DATE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                turnover DOUBLE,
                PRIMARY KEY (code, date)
            )
        """)

        logger.info("Tables created/verified")

    def upsert_daily_quote(self, df: pd.DataFrame):
        """写入日线行情数据（增量更新）"""
        if df.empty:
            return

        # 删除已有数据再插入（避免重复）
        codes = df["code"].unique().tolist()
        dates = df["date"].unique().tolist()

        self.conn.execute("""
            DELETE FROM daily_quote
            WHERE code IN ({codes}) AND date IN ({dates})
        """.format(
            codes=", ".join([f"'{c}'" for c in codes]),
            dates=", ".join([f"'{d}'" for d in dates])
        ))

        self.conn.execute("INSERT INTO daily_quote SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into daily_quote")

    def upsert_stock_info(self, df: pd.DataFrame):
        """写入股票基本信息"""
        if df.empty:
            return

        self.conn.execute("DELETE FROM stock_info")
        self.conn.execute("INSERT INTO stock_info SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into stock_info")

    def upsert_financial(self, df: pd.DataFrame):
        """写入财务数据"""
        if df.empty:
            return

        codes = df["code"].unique().tolist()
        dates = df["date"].unique().tolist()

        self.conn.execute("""
            DELETE FROM financial
            WHERE code IN ({codes}) AND date IN ({dates})
        """.format(
            codes=", ".join([f"'{c}'" for c in codes]),
            dates=", ".join([f"'{d}'" for d in dates])
        ))

        self.conn.execute("INSERT INTO financial SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into financial")

    def upsert_index_quote(self, df: pd.DataFrame):
        """写入指数行情"""
        if df.empty:
            return

        codes = df["code"].unique().tolist()
        dates = df["date"].unique().tolist()

        self.conn.execute("""
            DELETE FROM index_quote
            WHERE code IN ({codes}) AND date IN ({dates})
        """.format(
            codes=", ".join([f"'{c}'" for c in codes]),
            dates=", ".join([f"'{d}'" for d in dates])
        ))

        self.conn.execute("INSERT INTO index_quote SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into index_quote")

    def query(self, sql: str) -> pd.DataFrame:
        """执行查询，返回DataFrame"""
        return self.conn.execute(sql).df()

    def get_daily_quote(self, code: str = None, start_date: str = None,
                        end_date: str = None) -> pd.DataFrame:
        """查询日线行情"""
        conditions = []
        if code:
            conditions.append(f"code = '{code}'")
        if start_date:
            conditions.append(f"date >= '{start_date}'")
        if end_date:
            conditions.append(f"date <= '{end_date}'")

        where = " AND " + " AND ".join(conditions) if conditions else ""
        return self.query(f"SELECT * FROM daily_quote{where} ORDER BY date")

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        return self.query("SELECT * FROM stock_info")

    def get_data_coverage(self) -> dict:
        """获取数据覆盖范围"""
        result = {}
        try:
            row = self.query("SELECT COUNT(DISTINCT code) as stocks, MIN(date) as min_date, MAX(date) as max_date FROM daily_quote")
            result["stocks"] = int(row["stocks"][0])
            result["min_date"] = str(row["min_date"][0])
            result["max_date"] = str(row["max_date"][0])
        except Exception:
            result = {"stocks": 0, "min_date": "N/A", "max_date": "N/A"}
        return result

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()