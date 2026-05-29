"""IC热力图专用图表"""

import pandas as pd
import plotly.graph_objects as go
import numpy as np


def plot_ic_heatmap(ic_series: pd.DataFrame, factor_name: str = "All") -> go.Figure:
    """绘制IC热力图

    Args:
        ic_series: [date, factor_name, rank_ic] 或 [date, rank_ic]
        factor_name: 图表标题中的因子名

    Returns:
        plotly Figure
    """
    if "factor_name" in ic_series.columns:
        # 多因子IC矩阵
        pivot = ic_series.pivot_table(
            index="date", columns="factor_name", values="rank_ic"
        )
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="RdBu_r",
            zmin=-0.1, zmax=0.1,
            colorbar={"title": "Rank IC"},
        ))
        fig.update_layout(
            title=f"IC热力图 - {factor_name}",
            xaxis_title="因子",
            yaxis_title="日期",
            height=600,
        )
    else:
        # 单因子IC时间序列
        fig = go.Figure(data=go.Bar(
            x=ic_series["date"],
            y=ic_series["rank_ic"],
            marker_color=np.where(ic_series["rank_ic"] > 0, "green", "red"),
        ))
        fig.update_layout(
            title=f"Rank IC序列 - {factor_name}",
            xaxis_title="日期",
            yaxis_title="Rank IC",
            height=400,
        )

    return fig


def plot_layer_chart(layer_summary: dict, n_layers: int = 5) -> go.Figure:
    """绘制分层收益图

    Args:
        layer_summary: 分层回测汇总 dict
        n_layers: 分层数

    Returns:
        plotly Figure
    """
    layer_returns = layer_summary.get("layer_returns", {})
    if not layer_returns:
        fig = go.Figure()
        fig.update_layout(title="暂无分层回测数据")
        return fig

    layers = list(range(n_layers))
    returns = [layer_returns.get(f"layer_{i}", 0) for i in layers]

    fig = go.Figure(data=go.Bar(
        x=[f"Layer {i}" for i in layers],
        y=returns,
        marker_color=returns,
        colorscale="RdBu_r",
    ))

    fig.update_layout(
        title=f"分层收益图 (多空={layer_summary.get('avg_long_short', 0):.4f})",
        xaxis_title="分层",
        yaxis_title="平均收益",
        height=400,
    )

    return fig


def plot_decay_curve(decay_df: pd.DataFrame) -> go.Figure:
    """绘制衰减曲线

    Args:
        decay_df: [forward_period, ic_mean]

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=decay_df["forward_period"],
        y=decay_df["ic_mean"],
        mode="lines+markers",
        name="IC均值",
        line=dict(color="#3498db"),
    ))

    fig.add_trace(go.Scatter(
        x=decay_df["forward_period"],
        y=decay_df["icir"],
        mode="lines+markers",
        name="ICIR",
        line=dict(color="#e74c3c"),
        yaxis="y2",
    ))

    fig.update_layout(
        title="因子衰减曲线",
        xaxis_title="前瞻期（交易日）",
        yaxis_title="IC均值",
        yaxis2={"title": "ICIR", "overlaying": "y", "side": "right"},
        height=400,
    )

    return fig