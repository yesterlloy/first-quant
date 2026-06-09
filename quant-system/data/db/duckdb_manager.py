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

        # Phase 2 新增表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_ext (
                code VARCHAR,
                date DATE,
                pe DOUBLE,
                pb DOUBLE,
                roe DOUBLE,
                roa DOUBLE,
                revenue DOUBLE,
                net_profit DOUBLE,
                total_assets DOUBLE,
                total_liability DOUBLE,
                debt_ratio DOUBLE,
                ocf DOUBLE,
                PRIMARY KEY (code, date)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dividend (
                code VARCHAR,
                year VARCHAR,
                dividend_per_share DOUBLE,
                ex_date DATE,
                PRIMARY KEY (code, year)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS industry_class (
                code VARCHAR PRIMARY KEY,
                name VARCHAR,
                industry_sw VARCHAR
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS factor_value (
                code VARCHAR,
                date DATE,
                factor_name VARCHAR,
                raw_value DOUBLE,
                neut_value DOUBLE,
                PRIMARY KEY (code, date, factor_name)
            )
        """)

        # Phase 4 新增表 - 交易记录
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS order_log (
                order_id VARCHAR PRIMARY KEY,
                date DATE,
                code VARCHAR,
                action VARCHAR,
                shares INTEGER,
                price DOUBLE,
                status VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_log (
                trade_id VARCHAR PRIMARY KEY,
                order_id VARCHAR,
                date DATE,
                code VARCHAR,
                action VARCHAR,
                shares INTEGER,
                price DOUBLE,
                filled_at TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS position_log (
                date DATE,
                code VARCHAR,
                shares INTEGER,
                weight DOUBLE,
                cost_price DOUBLE,
                current_price DOUBLE,
                market_value DOUBLE,
                PRIMARY KEY (date, code)
            )
        """)

        # Phase 4 新增表 - 调度器日志
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS scheduler_log_id_seq START 1")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_log (
                id INTEGER PRIMARY KEY DEFAULT nextval('scheduler_log_id_seq'),
                task_name VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_seconds FLOAT,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduler_log_task ON scheduler_log(task_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduler_log_time ON scheduler_log(start_time)")

        logger.info("Tables created/verified")

    def upsert_daily_quote(self, df: pd.DataFrame):
        """写入日线行情数据（增量更新）"""
        if df.empty:
            return
        df["code"] = df["code"].astype(str).str.zfill(6)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.drop_duplicates(subset=["code", "date"], keep="last")
        self.conn.execute("INSERT OR REPLACE INTO daily_quote SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into daily_quote")

    def upsert_stock_info(self, df: pd.DataFrame):
        """写入股票基本信息"""
        if df.empty:
            return
        df["code"] = df["code"].astype(str).str.zfill(6)
        self.conn.execute("INSERT OR REPLACE INTO stock_info SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into stock_info")

    def upsert_financial(self, df: pd.DataFrame):
        """写入财务数据"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO financial SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into financial")

    def upsert_index_quote(self, df: pd.DataFrame):
        """写入指数行情"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO index_quote SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into index_quote")

    def upsert_financial_ext(self, df: pd.DataFrame):
        """写入扩展财务数据"""
        if df.empty:
            return
        df["code"] = df["code"].astype(str).str.zfill(6)
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df = df.dropna(subset=["date"])
        df = df.drop_duplicates(subset=["code", "date"], keep="last")
        # 只写入表中定义的列
        cols = ["code", "date", "pe", "pb", "roe", "roa", "revenue",
                "net_profit", "total_assets", "total_liability", "debt_ratio", "ocf"]
        df = df[[c for c in cols if c in df.columns]]
        self.conn.execute("INSERT OR REPLACE INTO financial_ext SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into financial_ext")

    def upsert_dividend(self, df: pd.DataFrame):
        """写入分红数据"""
        if df.empty:
            return
        df["code"] = df["code"].astype(str).str.zfill(6)
        df = df.dropna(subset=["dividend_per_share"])
        df = df.drop_duplicates(subset=["code", "year"], keep="last")
        cols = ["code", "year", "dividend_per_share", "ex_date"]
        df = df[[c for c in cols if c in df.columns]]
        self.conn.execute("INSERT OR REPLACE INTO dividend SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into dividend")

    def upsert_industry_class(self, df: pd.DataFrame):
        """写入行业分类数据"""
        if df.empty:
            return
        df["code"] = df["code"].astype(str).str.zfill(6)
        df = df.drop_duplicates(subset=["code"], keep="last")
        cols = ["code", "name", "industry_sw"]
        df = df[[c for c in cols if c in df.columns]]
        self.conn.execute("INSERT OR REPLACE INTO industry_class SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into industry_class")

    def upsert_factor_value(self, df: pd.DataFrame):
        """写入因子值数据"""
        if df.empty:
            return
        df["code"] = df["code"].astype(str).str.zfill(6)
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df = df.dropna(subset=["raw_value"])
        df = df.drop_duplicates(subset=["code", "date", "factor_name"], keep="last")
        cols = ["code", "date", "factor_name", "raw_value", "neut_value"]
        df = df[[c for c in cols if c in df.columns]]
        self.conn.execute("INSERT OR REPLACE INTO factor_value SELECT * FROM df")
        logger.info(f"Upserted {len(df)} rows into factor_value")

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

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
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
            min_d = str(row["min_date"][0])[:10]
            max_d = str(row["max_date"][0])[:10]
            result["min_date"] = min_d if min_d not in ("NaT", "None", "Na") else "N/A"
            result["max_date"] = max_d if max_d not in ("NaT", "None", "Na") else "N/A"
        except Exception:
            result = {"stocks": 0, "min_date": "N/A", "max_date": "N/A"}
        return result

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()