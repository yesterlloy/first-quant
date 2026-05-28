"""策略模块测试"""

import pandas as pd
import numpy as np
from strategy.ma_cross import MACrossStrategy
from strategy.momentum import MomentumStrategy
from strategy.mean_revert import MeanRevertStrategy


def _make_test_df(n: int = 100) -> pd.DataFrame:
    """生成测试行情数据"""
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    # 模拟股价：从10元开始，有涨有跌
    price = 10 + np.cumsum(np.random.randn(n) * 0.5)
    price = np.abs(price)  # 防负数

    return pd.DataFrame({
        "date": dates,
        "close": price,
        "open": price - np.random.rand(n) * 0.1,
        "high": price + np.random.rand(n) * 0.2,
        "low": price - np.random.rand(n) * 0.2,
        "volume": np.random.randint(1000, 100000, n),
    })


def test_ma_cross():
    """测试均线交叉策略"""
    df = _make_test_df()
    strategy = MACrossStrategy(short_window=5, long_window=20)

    signals = strategy.generate_signals(df)
    assert len(signals) == len(df), "信号长度应与数据长度一致"
    assert set(signals.unique()).issubset({0, 1, -1}), "信号值应为 0, 1, -1"

    params = strategy.get_params()
    assert params["short_window"] == 5
    assert params["long_window"] == 20
    print(f"✅ MA Cross: {len(signals[signals != 0])} signals generated")


def test_momentum():
    """测试动量策略"""
    df = _make_test_df()
    strategy = MomentumStrategy(lookback=20)

    signals = strategy.generate_signals(df)
    assert len(signals) == len(df)
    assert set(signals.unique()).issubset({0, 1, -1})

    params = strategy.get_params()
    assert params["lookback"] == 20
    print(f"✅ Momentum: {len(signals[signals != 0])} signals generated")


def test_mean_revert():
    """测试均值回归策略"""
    df = _make_test_df()
    strategy = MeanRevertStrategy(lookback=20, entry_z=2.0)

    signals = strategy.generate_signals(df)
    assert len(signals) == len(df)
    assert set(signals.unique()).issubset({0, 1, -1})

    params = strategy.get_params()
    assert params["entry_z"] == 2.0
    print(f"✅ Mean Revert: {len(signals[signals != 0])} signals generated")


if __name__ == "__main__":
    test_ma_cross()
    test_momentum()
    test_mean_revert()
    print("\n✅ All strategy tests passed!")