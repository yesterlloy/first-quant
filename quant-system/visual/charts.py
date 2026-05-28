"""图表生成工具"""

import plotly.graph_objects as go
import plotly.figure_factory as ff
import pandas as pd


def plot_equity_curve(portfolio_values: pd.Series, title: str = "收益曲线") -> go.Figure:
    """绘制净值曲线"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio_values.index,
        y=portfolio_values.values,
        mode="lines",
        name="策略净值",
        line=dict(color="#2196F3", width=2),
    ))

    fig.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title="净值",
        template="plotly_white",
        hovermode="x unified",
    )
    return fig


def plot_drawdown(returns: pd.Series, title: str = "回撤曲线") -> go.Figure:
    """绘制回撤曲线"""
    cummax = (1 + returns).cumprod().cummax()
    drawdown = (1 + returns).cumprod() / cummax - 1

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdown.index,
        y=drawdown.values,
        mode="lines",
        name="回撤",
        line=dict(color="#F44336", width=2),
        fill="tozeroy",
        fillcolor="rgba(244, 67, 54, 0.2)",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title="回撤",
        template="plotly_white",
    )
    return fig


def plot_strategy_comparison(results: list) -> go.Figure:
    """多策略收益对比图"""
    fig = go.Figure()

    for result in results:
        pv = result["portfolio_value"]
        fig.add_trace(go.Scatter(
            x=pv.index,
            y=pv.values,
            mode="lines",
            name=result["strategy_name"],
        ))

    fig.update_layout(
        title="策略收益对比",
        xaxis_title="日期",
        yaxis_title="净值",
        template="plotly_white",
        hovermode="x unified",
    )
    return fig


def plot_metrics_table(results: list) -> go.Figure:
    """指标对比表格"""
    from backtest.analyzer import BacktestAnalyzer
    analyzer = BacktestAnalyzer()
    df = analyzer.compare(results)

    fig = ff.create_table(df)
    fig.update_layout(title="回测指标对比")
    return fig