"""回测引擎测试"""

import pandas as pd
import numpy as np
from strategy.ma_cross import MACrossStrategy
from strategy.momentum import MomentumStrategy
from backtest.engine import BacktestEngine


def _make_test_df(n: int = 200) -> pd.DataFrame:
    """生成较长测试数据"""
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    # 模拟趋势+噪声
    trend = np.linspace(10, 15, n)
    noise = np.random.randn(n) * 0.3
    price = trend + noise

    return pd.DataFrame({
        "date": dates,
        "close": price,
        "open": price - 0.1,
        "high": price + 0.2,
        "low": price - 0.2,
        "volume": np.random.randint(1000, 100000, n).astype(float),
        "turnover": price * np.random.randint(1000, 100000, n).astype(float),
        "change_pct": np.random.randn(n) * 2,
        "turnover_rate": np.random.rand(n) * 3,
    })


def test_backtest_single():
    """测试单策略回测"""
    df = _make_test_df()
    strategy = MACrossStrategy()
    engine = BacktestEngine()

    result = engine.run(strategy, df)

    assert "strategy_name" in result
    assert "total_return" in result
    assert "sharpe_ratio" in result
    assert "max_drawdown" in result
    assert "portfolio_value" in result

    print(f"✅ Single backtest: {result['strategy_name']}")
    print(f"   Total return: {result['total_return']:.2%}")
    print(f"   Sharpe: {result['sharpe_ratio']:.2f}")


def test_backtest_multi():
    """测试多策略回测"""
    df = _make_test_df()
    strategies = [
        MACrossStrategy(),
        MomentumStrategy(),
    ]
    engine = BacktestEngine()

    results = engine.run_multi(strategies, df)

    assert len(results) == 2
    for r in results:
        assert "strategy_name" in r
        assert "total_return" in r

    print(f"✅ Multi backtest: {len(results)} strategies")


if __name__ == "__main__":
    test_backtest_single()
    test_backtest_multi()
    print("\n✅ All backtest tests passed!")