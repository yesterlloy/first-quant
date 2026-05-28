"""回测运行入口"""

import sys
import os
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db.duckdb_manager import DuckDBManager
from strategy.ma_cross import MACrossStrategy
from strategy.momentum import MomentumStrategy
from strategy.mean_revert import MeanRevertStrategy
from backtest.engine import BacktestEngine
from backtest.analyzer import BacktestAnalyzer
from backtest.report import BacktestReport


def main():
    config_path = "config/settings.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    bt_cfg = config["backtest"]
    db = DuckDBManager(config["data"]["db_path"])
    db.connect()

    # 获取数据
    code = sys.argv[1] if len(sys.argv) > 1 else "000001"
    df = db.get_daily_quote(code=code)

    if df.empty:
        print(f"无数据: {code}，请先运行数据采集")
        db.close()
        return

    # 策略列表
    strategies = [
        MACrossStrategy(short_window=5, long_window=20),
        MomentumStrategy(lookback=20, buy_threshold=0.05),
        MeanRevertStrategy(lookback=20, entry_z=2.0),
    ]

    # 回测
    engine = BacktestEngine(
        initial_capital=bt_cfg["initial_capital"],
        commission=bt_cfg["commission"],
        slippage=bt_cfg["slippage"],
    )
    results = engine.run_multi(strategies, df)

    # 分析报告
    report = BacktestReport()
    report_text = report.generate(results)
    print(report_text)

    db.close()


if __name__ == "__main__":
    main()