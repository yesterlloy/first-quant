"""SQLite 数据库管理模块 - 解决多进程并发问题

与 DuckDBManager 接口完全兼容，可直接替换
SQLite WAL模式下支持：多进程读 + 单进程写
"""

import sqlite3
import pandas as pd
from pathlib import Path
from loguru import logger


class SQLiteManager:
    """SQLite 数据库封装，提供读写接口

    与 DuckDBManager 接口完全兼容，可直接替换
    """

    def __init__(self, db_path: str = "data/db/quant.sqlite.db", read_only: bool = False):
        self.db_path = db_path
        self.read_only = read_only
        self.conn = None

    def __enter__(self):
        """支持 with 语句"""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """with 语句退出时自动关闭"""
        self.close()

    def connect(self):
        """建立数据库连接

        SQLite WAL模式下：
        - 读操作：支持多进程并发
        - 写操作：同一时间只能有一个进程写入
        """
        # 确保目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        if self.read_only:
            # 只读模式：使用immutable避免锁竞争
            self.conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro",
                uri=True,
                timeout=30.0,
                isolation_level=None
            )
        else:
            # 读写模式：启用WAL以支持并发读
            self.conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                isolation_level=None
            )
            # 启用WAL模式 - 关键！支持并发读
            self.conn.execute("PRAGMA journal_mode=WAL")
            # 其他优化
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA cache_size=-100000")  # 100MB cache
            self.conn.execute("PRAGMA temp_store=MEMORY")
            self.conn.execute("PRAGMA mmap_size=30000000000")  # 30GB mmap

            self._create_tables()

        # 注册兼容DuckDB的SQL函数
        self._register_sql_functions()

        mode_info = " (READ_ONLY)" if self.read_only else ""
        logger.info(f"SQLite connected: {self.db_path}{mode_info}")
        return self

    def _register_sql_functions(self):
        """注册兼容DuckDB的SQL函数"""
        import math
        import statistics

        # STDDEV 聚合函数
        class StddevAgg:
            def __init__(self):
                self.vals = []

            def step(self, value):
                if value is not None:
                    self.vals.append(value)

            def finalize(self):
                if len(self.vals) < 2:
                    return None
                return statistics.stdev(self.vals)

        self.conn.create_aggregate("STDDEV", 1, StddevAgg)

        # VARIANCE 聚合函数
        class VarianceAgg:
            def __init__(self):
                self.vals = []

            def step(self, value):
                if value is not None:
                    self.vals.append(value)

            def finalize(self):
                if len(self.vals) < 2:
                    return None
                return statistics.variance(self.vals)

        self.conn.create_aggregate("VARIANCE", 1, VarianceAgg)

        # 其他常用统计函数
        import numpy as np

        def quantile_25(vals):
            vals = [v for v in vals if v is not None]
            return float(np.quantile(vals, 0.25)) if vals else None

        def quantile_75(vals):
            vals = [v for v in vals if v is not None]
            return float(np.quantile(vals, 0.75)) if vals else None

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            logger.info("SQLite closed")

    def _create_tables(self):
        """创建数据表 - SQLite语法"""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_quote (
                code TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                change_pct REAL,
                turnover_rate REAL,
                PRIMARY KEY (code, date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_info (
                code TEXT PRIMARY KEY,
                name TEXT,
                industry TEXT,
                list_date TEXT,
                delist_date TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial (
                code TEXT,
                date TEXT,
                pe REAL,
                pb REAL,
                roe REAL,
                revenue REAL,
                net_profit REAL,
                PRIMARY KEY (code, date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS index_quote (
                code TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                PRIMARY KEY (code, date)
            )
        """)

        # Phase 2 新增表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_ext (
                code TEXT,
                date TEXT,
                pe REAL,
                pb REAL,
                roe REAL,
                roa REAL,
                revenue REAL,
                net_profit REAL,
                total_assets REAL,
                total_liability REAL,
                debt_ratio REAL,
                ocf REAL,
                PRIMARY KEY (code, date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS industry_class (
                code TEXT PRIMARY KEY,
                industry_sw TEXT,
                industry_ths TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividend (
                code TEXT,
                year INTEGER,
                dividend_per_share REAL,
                ex_date TEXT,
                PRIMARY KEY (code, year)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factor_value (
                code TEXT,
                date TEXT,
                factor_name TEXT,
                raw_value REAL,
                neut_value REAL,
                PRIMARY KEY (code, date, factor_name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                strategy TEXT,
                code TEXT,
                side TEXT,
                quantity INTEGER,
                avg_price REAL,
                market_value REAL,
                pnl REAL,
                pnl_pct REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                strategy TEXT,
                code TEXT,
                side TEXT,
                quantity INTEGER,
                price REAL,
                amount REAL,
                commission REAL,
                pnl REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                strategy TEXT,
                code TEXT,
                side TEXT,
                quantity INTEGER,
                price REAL,
                status TEXT,
                reason TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                level TEXT,
                type TEXT,
                message TEXT,
                details TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                task TEXT,
                status TEXT,
                duration REAL,
                message TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_signal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                code TEXT,
                model_name TEXT,
                signal REAL,
                probability REAL,
                prediction TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                model_name TEXT,
                eval_date TEXT,
                train_start TEXT,
                train_end TEXT,
                val_start TEXT,
                val_end TEXT,
                train_samples INTEGER,
                val_samples INTEGER,
                train_auc REAL,
                val_auc REAL,
                top_return REAL,
                feature_count INTEGER
            )
        """)

        self.conn.commit()
        logger.info("Tables created/verified")

    def _translate_sql(self, sql: str) -> str:
        """SQL语法转换：DuckDB -> SQLite"""
        import re

        # STDDEV -> 兼容处理（已注册自定义函数）
        sql = re.sub(r'\bSTDDEV\s*\(', 'STDDEV(', sql, flags=re.IGNORECASE)

        # STRING_AGG -> GROUP_CONCAT
        sql = re.sub(r'\bSTRING_AGG\s*\(', 'GROUP_CONCAT(', sql, flags=re.IGNORECASE)

        # DATE_TRUNC -> SQLite strftime 兼容
        # DATE_TRUNC('month', date_col) -> strftime('%Y-%m-01', date_col)
        sql = re.sub(
            r"DATE_TRUNC\s*\(\s*['\"]month['\"]\s*,\s*([^)]+)\)",
            r"strftime('%Y-%m-01', \1)",
            sql,
            flags=re.IGNORECASE
        )
        sql = re.sub(
            r"DATE_TRUNC\s*\(\s*['\"]day['\"]\s*,\s*([^)]+)\)",
            r"strftime('%Y-%m-%d', \1)",
            sql,
            flags=re.IGNORECASE
        )

        # EXTRACT(EPOCH FROM ...) -> strftime('%s', ...)
        sql = re.sub(
            r"EXTRACT\s*\(\s*EPOCH\s+FROM\s+([^)]+)\)",
            r"strftime('%s', \1)",
            sql,
            flags=re.IGNORECASE
        )

        # || 字符串拼接（SQLite 原生支持，无需转换）
        # CAST(xxx AS VARCHAR) -> CAST(xxx AS TEXT)
        sql = re.sub(r"CAST\s*\(([^)]+)\s+AS\s+VARCHAR\s*\)", r"CAST(\1 AS TEXT)", sql, flags=re.IGNORECASE)

        return sql

    def query(self, sql: str) -> pd.DataFrame:
        """执行查询，返回DataFrame（自动做SQL语法兼容转换）"""
        sql = self._translate_sql(sql)
        return pd.read_sql(sql, self.conn)

    def execute(self, sql: str, params: tuple = None):
        """执行SQL语句"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor

    # ========== daily_quote 相关操作 ==========

    def upsert_daily_quote(self, df: pd.DataFrame):
        """增量更新日线行情数据"""
        cursor = self.conn.cursor()
        data = df.to_records(index=False).tolist()
        cursor.executemany("""
            INSERT OR REPLACE INTO daily_quote
            (code, date, open, high, low, close, volume, turnover, change_pct, turnover_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()
        logger.info(f"Upserted {len(df)} rows into daily_quote")

    # ========== stock_info 相关操作 ==========

    def upsert_stock_info(self, df: pd.DataFrame):
        """更新股票基本信息"""
        cursor = self.conn.cursor()
        data = df.to_records(index=False).tolist()
        cursor.executemany("""
            INSERT OR REPLACE INTO stock_info
            (code, name, industry, list_date, delist_date)
            VALUES (?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()
        logger.info(f"Upserted {len(df)} rows into stock_info")

    # ========== factor_value 相关操作 ==========

    def upsert_factor_value(self, df: pd.DataFrame):
        """增量更新因子数据"""
        cursor = self.conn.cursor()
        data = df[['code', 'date', 'factor_name', 'raw_value', 'neut_value']].to_records(index=False).tolist()
        cursor.executemany("""
            INSERT OR REPLACE INTO factor_value
            (code, date, factor_name, raw_value, neut_value)
            VALUES (?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()
        logger.info(f"Upserted {len(df)} rows into factor_value")

    # ========== 便捷查询方法 ==========

    def get_daily_quote(self, code: str = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取日线行情数据"""
        sql = "SELECT * FROM daily_quote WHERE 1=1"
        params = []

        if code:
            sql += " AND code = ?"
            params.append(code)
        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)

        sql += " ORDER BY date"
        return pd.read_sql(sql, self.conn, params=params)

    def get_data_coverage(self) -> dict:
        """获取数据覆盖情况统计"""
        result = {}

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT code) FROM daily_quote")
        result['stocks'] = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(date), MAX(date) FROM daily_quote")
        row = cursor.fetchone()
        result['min_date'] = row[0]
        result['max_date'] = row[1]

        return result
