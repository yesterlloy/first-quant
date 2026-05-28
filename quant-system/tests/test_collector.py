"""DuckDB 数据库管理测试"""

import pandas as pd
import tempfile
import os
from data.db.duckdb_manager import DuckDBManager


def test_duckdb_basic():
    """测试 DuckDB 基本读写"""
    # 使用临时数据库
    db_path = os.path.join(tempfile.mkdtemp(), "test.duckdb")
    db = DuckDBManager(db_path)

    db.connect()

    # 写入日线数据
    test_df = pd.DataFrame({
        "code": ["000001", "000001", "600000"],
        "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-01"]),
        "open": [10.0, 10.5, 8.0],
        "high": [10.5, 11.0, 8.5],
        "low": [9.8, 10.2, 7.8],
        "close": [10.2, 10.8, 8.2],
        "volume": [100000, 120000, 80000],
        "turnover": [1000000, 1200000, 800000],
        "change_pct": [2.0, 5.88, 2.5],
        "turnover_rate": [1.0, 1.2, 0.8],
    })

    db.upsert_daily_quote(test_df)

    # 查询
    result = db.get_daily_quote(code="000001")
    assert len(result) == 2, f"Expected 2 rows, got {len(result)}"

    result_all = db.get_daily_quote()
    assert len(result_all) == 3, f"Expected 3 rows, got {len(result_all)}"

    # 数据覆盖范围
    coverage = db.get_data_coverage()
    assert coverage["stocks"] == 2
    assert coverage["min_date"] == "2020-01-01"

    db.close()

    # 清理
    os.unlink(db_path)

    print("✅ DuckDB basic test passed!")


def test_duckdb_upsert():
    """测试增量更新（重复数据不报错）"""
    db_path = os.path.join(tempfile.mkdtemp(), "test.duckdb")
    db = DuckDBManager(db_path)
    db.connect()

    # 第一次写入
    df1 = pd.DataFrame({
        "code": ["000001"],
        "date": pd.to_datetime(["2020-01-01"]),
        "open": [10.0],
        "high": [10.5],
        "low": [9.8],
        "close": [10.2],
        "volume": [100000],
        "turnover": [1000000],
        "change_pct": [2.0],
        "turnover_rate": [1.0],
    })
    db.upsert_daily_quote(df1)

    # 第二次写入（同一天数据更新）
    df2 = pd.DataFrame({
        "code": ["000001"],
        "date": pd.to_datetime(["2020-01-01"]),
        "open": [10.1],
        "high": [10.6],
        "low": [9.9],
        "close": [10.3],
        "volume": [110000],
        "turnover": [1100000],
        "change_pct": [2.5],
        "turnover_rate": [1.1],
    })
    db.upsert_daily_quote(df2)

    result = db.get_daily_quote(code="000001")
    assert len(result) == 1, "重复数据应被替换，只有1行"
    assert result["close"].iloc[0] == 10.3, "数据应被更新"

    db.close()
    os.unlink(db_path)

    print("✅ DuckDB upsert test passed!")


if __name__ == "__main__":
    test_duckdb_basic()
    test_duckdb_upsert()
    print("\n✅ All DuckDB tests passed!")