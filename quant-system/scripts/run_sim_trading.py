"""模拟交易脚本 - 生成测试数据供Dashboard展示"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from data.db.duckdb_manager import DuckDBManager
from executor import (
    SignalLoader, PortfolioBuilder, PositionCalculator,
    OrderManager, TradeLogger, Rebalancer
)
from executor.broker import SimulatedBroker
from config import get_config


def generate_mock_signals(db: DuckDBManager, date: str = "2024-01-31"):
    """生成模拟信号数据"""
    signals = pd.DataFrame([
        {"code": "000001", "date": date, "model_name": "lgbm_v1", "predicted_return": 0.08, "signal": 1},
        {"code": "000002", "date": date, "model_name": "lgbm_v1", "predicted_return": 0.06, "signal": 1},
        {"code": "000063", "date": date, "model_name": "lgbm_v1", "predicted_return": 0.05, "signal": 1},
        {"code": "000100", "date": date, "model_name": "lgbm_v1", "predicted_return": 0.04, "signal": 1},
        {"code": "000333", "date": date, "model_name": "lgbm_v1", "predicted_return": 0.03, "signal": 1},
        {"code": "000651", "date": date, "model_name": "lgbm_v1", "predicted_return": 0.02, "signal": 1},
    ])
    signals["date"] = pd.to_datetime(signals["date"]).dt.date
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS ml_signal AS
        SELECT * FROM signals WHERE 1=0
    """)
    db.conn.execute("INSERT INTO ml_signal SELECT * FROM signals")
    print(f"Generated {len(signals)} mock signals")


def generate_mock_prices(db: DuckDBManager, date: str = "2024-01-31"):
    """生成模拟价格数据"""
    prices = pd.DataFrame([
        {"code": "000001", "date": date, "open": 10.5, "high": 10.8, "low": 10.3, "close": 10.6, "volume": 10000000, "turnover": 106000000, "change_pct": 0.01, "turnover_rate": 0.02},
        {"code": "000002", "date": date, "open": 25.0, "high": 25.5, "low": 24.8, "close": 25.2, "volume": 8000000, "turnover": 201600000, "change_pct": 0.008, "turnover_rate": 0.015},
        {"code": "000063", "date": date, "open": 35.0, "high": 35.8, "low": 34.5, "close": 35.5, "volume": 5000000, "turnover": 177500000, "change_pct": 0.015, "turnover_rate": 0.018},
        {"code": "000100", "date": date, "open": 5.2, "high": 5.3, "low": 5.1, "close": 5.25, "volume": 20000000, "turnover": 105000000, "change_pct": 0.005, "turnover_rate": 0.012},
        {"code": "000333", "date": date, "open": 68.0, "high": 69.0, "low": 67.5, "close": 68.5, "volume": 3000000, "turnover": 205500000, "change_pct": 0.007, "turnover_rate": 0.008},
        {"code": "000651", "date": date, "open": 42.0, "high": 42.5, "low": 41.5, "close": 42.2, "volume": 4000000, "turnover": 168800000, "change_pct": 0.006, "turnover_rate": 0.01},
    ])
    prices["date"] = pd.to_datetime(prices["date"]).dt.date
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_quote AS
        SELECT * FROM prices WHERE 1=0
    """)
    db.conn.execute("INSERT INTO daily_quote SELECT * FROM prices")
    print(f"Generated {len(prices)} mock prices")


def main():
    config = get_config()
    db = DuckDBManager(config["data"]["db_path"])
    db.connect()

    date = "2024-01-31"

    # 生成模拟数据
    generate_mock_prices(db, date)
    generate_mock_signals(db, date)

    broker = SimulatedBroker(db)

    # 初始建仓（买入一些亏损股票用于测试止损）
    print("Setting up initial positions...")
    broker.buy("000001", 1000, 12.0)  # 成本12元，现价10.6元（亏11.7%）
    broker.buy("000002", 2000, 24.0)  # 成本24元，现价25.2元（盈5%）

    # 运行调仓
    print("Running rebalance...")
    rebalancer = Rebalancer(db, broker, config={
        "top_n": 4,
        "max_single": 0.3,
        "stop_loss_ratio": -0.05,
        "enable_console_alert": True,
    })

    result = rebalancer.run(date, "lgbm_v1", total_capital=500000)
    print(f"\nRebalance result: {result}")

    # 生成多日持仓数据（模拟历史）
    print("\nGenerating historical position data...")
    trade_logger = TradeLogger(db)
    for i, d in enumerate(["2024-01-15", "2024-01-20", "2024-01-25", "2024-01-30", "2024-01-31"]):
        positions = pd.DataFrame([
            {"code": "000001", "shares": 1000 - i * 100, "weight": 0.4 - i * 0.05, "cost_price": 12.0, "current_price": 10.6, "market_value": (1000 - i * 100) * 10.6},
            {"code": "000002", "shares": 2000, "weight": 0.6 - i * 0.05, "cost_price": 24.0, "current_price": 25.2, "market_value": 2000 * 25.2},
        ])
        trade_logger.log_positions(positions, d)

    db.close()

    print("\n✅ 模拟交易完成！")
    print("  启动交易面板: python scripts/run_trading_dashboard.py")
    print("  端口: 8053")


if __name__ == "__main__":
    main()
