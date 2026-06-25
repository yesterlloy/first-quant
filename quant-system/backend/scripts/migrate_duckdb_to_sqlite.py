#!/usr/bin/env python3
"""DuckDB → SQLite 数据迁移脚本

迁移数据：
- stock_info (股票基本信息)
- daily_quote (日线行情，约 670 万行)
- factor_value (因子值)
- index_quote (指数行情)
"""

import sys
import os
from pathlib import Path
from typing import Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import duckdb
import sqlite3
import pandas as pd
from loguru import logger


class DuckDBToSQLiteMigrator:
    """DuckDB 到 SQLite 数据迁移器"""

    def __init__(
        self,
        duckdb_path: str = "../data/db/quant.duckdb",
        sqlite_path: str = "../data/db/quant.sqlite.db",
        batch_size: int = 50000,
    ):
        self.duckdb_path = duckdb_path
        self.sqlite_path = sqlite_path
        self.batch_size = batch_size

    def migrate_table(
        self,
        table_name: str,
        duck_conn: duckdb.DuckDBPyConnection,
        sqlite_conn: sqlite3.Connection,
        date_filter: Optional[str] = None,
    ) -> int:
        """迁移单张表

        Args:
            table_name: 表名
            duck_conn: DuckDB 连接
            sqlite_conn: SQLite 连接
            date_filter: 日期筛选条件 (可选)

        Returns:
            迁移行数
        """
        # 获取行数
        count_sql = f"SELECT COUNT(*) as cnt FROM {table_name}"
        if date_filter:
            count_sql += f" WHERE {date_filter}"
        total = duck_conn.execute(count_sql).fetchone()[0]

        if total == 0:
            logger.info(f"⏭️  {table_name}: 0 行，跳过")
            return 0

        logger.info(f"🔄 迁移 {table_name}: {total:,} 行...")

        # 分批迁移
        migrated = 0
        batches = (total + self.batch_size - 1) // self.batch_size

        for batch_idx, offset in enumerate(range(0, total, self.batch_size), 1):
            # 从 DuckDB 读取
            sql = f"SELECT * FROM {table_name}"
            if date_filter:
                sql += f" WHERE {date_filter}"
            sql += f" LIMIT {self.batch_size} OFFSET {offset}"

            df = duck_conn.execute(sql).df()

            # 日期列标准化（DuckDB DATE → SQLite TEXT ISO 格式）
            for col in df.columns:
                if df[col].dtype.name == "date" or "date" in col.lower():
                    df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")

            # 写入 SQLite
            df.to_sql(
                table_name,
                sqlite_conn,
                if_exists="append" if migrated > 0 else "replace",
                index=False,
                chunksize=self.batch_size,
            )

            migrated += len(df)

            # 每 10 批打印一次进度
            if batch_idx % max(1, batches // 10) == 0 or batch_idx == batches:
                logger.info(f"  {table_name}: {migrated:,}/{total:,} 行 ({migrated/total*100:.1f}%)")
        logger.info(f"✅ {table_name}: {migrated:,} 行迁移完成")
        return migrated

    def create_indexes(self, sqlite_conn: sqlite3.Connection):
        """创建索引"""
        logger.info("🔨 创建索引...")

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_daily_quote_code ON daily_quote(code)",
            "CREATE INDEX IF NOT EXISTS idx_daily_quote_date ON daily_quote(date)",
            "CREATE INDEX IF NOT EXISTS idx_daily_quote_code_date ON daily_quote(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_stock_info_code ON stock_info(code)",
            "CREATE INDEX IF NOT EXISTS idx_factor_value_code ON factor_value(code)",
            "CREATE INDEX IF NOT EXISTS idx_factor_value_date ON factor_value(date)",
            "CREATE INDEX IF NOT EXISTS idx_factor_value_factor ON factor_value(factor_name)",
            "CREATE INDEX IF NOT EXISTS idx_factor_value_code_date ON factor_value(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_index_quote_code ON index_quote(code)",
            "CREATE INDEX IF NOT EXISTS idx_index_quote_date ON index_quote(date)",
        ]

        for idx_sql in indexes:
            try:
                sqlite_conn.execute(idx_sql)
            except Exception as e:
                logger.warning(f"索引创建失败（可能已存在）: {e}")

        logger.info("✅ 索引创建完成")

    def run(self):
        """执行完整迁移"""
        logger.info("=" * 60)
        logger.info("🚀 开始 DuckDB → SQLite 数据迁移")
        logger.info("=" * 60)

        # 验证源文件
        if not os.path.exists(self.duckdb_path):
            logger.error(f"❌ DuckDB 文件不存在: {self.duckdb_path}")
            return False

        logger.info(f"📂 源文件: {self.duckdb_path}")
        logger.info(f"📂 目标文件: {self.sqlite_path}")
        logger.info(f"📦 批次大小: {self.batch_size:,}")

        # 连接数据库
        duck_conn = duckdb.connect(self.duckdb_path, read_only=True)
        sqlite_conn = sqlite3.connect(self.sqlite_path)

        # 开启 WAL 模式加速写入
        sqlite_conn.execute("PRAGMA journal_mode = WAL")
        sqlite_conn.execute("PRAGMA synchronous = OFF")
        sqlite_conn.execute("PRAGMA cache_size = -1000000")  # 1GB 缓存
        sqlite_conn.execute("PRAGMA temp_store = MEMORY")

        try:
            total_rows = 0

            # 1. 股票信息 (小表，全量)
            total_rows += self.migrate_table("stock_info", duck_conn, sqlite_conn)

            # 2. 日线行情 (大表，670 万行)
            total_rows += self.migrate_table("daily_quote", duck_conn, sqlite_conn)

            # 3. 因子值
            total_rows += self.migrate_table("factor_value", duck_conn, sqlite_conn)

            # 4. 指数行情
            total_rows += self.migrate_table("index_quote", duck_conn, sqlite_conn)

            # 5. 其他表（如存在）
            other_tables = [
                "financial",
                "financial_ext",
                "dividend",
                "industry_class",
            ]

            # 获取 DuckDB 中存在的表
            existing_tables = duck_conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).df()["table_name"].tolist()

            for table in other_tables:
                if table in existing_tables:
                    total_rows += self.migrate_table(table, duck_conn, sqlite_conn)

            # 创建索引
            self.create_indexes(sqlite_conn)

            # 提交事务
            sqlite_conn.commit()

            logger.info("=" * 60)
            logger.info(f"🎉 迁移完成！总计: {total_rows:,} 行")
            logger.info("=" * 60)

            # 验证
            self.verify(sqlite_conn)
            return True

        except Exception as e:
            logger.exception(f"❌ 迁移失败: {e}")
            sqlite_conn.rollback()
            return False

        finally:
            duck_conn.close()
            sqlite_conn.close()

    def verify(self, sqlite_conn: sqlite3.Connection):
        """验证迁移结果"""
        logger.info("\n📊 迁移结果验证:")
        logger.info("-" * 60)

        tables = ["stock_info", "daily_quote", "factor_value", "index_quote"]

        for table in tables:
            try:
                cursor = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]

                # 获取数据日期范围
                cursor = sqlite_conn.execute(
                    f"SELECT MIN(date), MAX(date), COUNT(DISTINCT date) FROM {table}"
                )
                min_date, max_date, days = cursor.fetchone()

                logger.info(
                    f"{table:15s}: {count:>10,} 行, {days:>5} 天, {min_date} → {max_date}"
                )

            except Exception as e:
                logger.warning(f"{table}: 验证失败 - {e}")

        # 验证数据库文件大小
        size_mb = os.path.getsize(self.sqlite_path) / (1024 * 1024)
        logger.info(f"\n💾 SQLite 数据库大小: {size_mb:.1f} MB")


if __name__ == "__main__":
    # 设置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    migrator = DuckDBToSQLiteMigrator(
        duckdb_path="../data/db/quant.duckdb",
        sqlite_path="../data/db/quant.sqlite.db",
        batch_size=50000,
    )

    success = migrator.run()
    sys.exit(0 if success else 1)
