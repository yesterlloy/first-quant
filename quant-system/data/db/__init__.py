"""数据库模块

支持 DuckDB 和 SQLite 两种后端，通过环境变量切换

设置环境变量 DB_BACKEND=sqlite 即可使用 SQLite
默认使用 sqlite（解决多进程并发问题）
"""

import os

DB_BACKEND = os.getenv('DB_BACKEND', 'sqlite').lower()

if DB_BACKEND == 'sqlite':
    from .sqlite_manager import SQLiteManager as DBManager
else:
    from .duckdb_manager import DuckDBManager as DBManager

__all__ = ['DBManager']
