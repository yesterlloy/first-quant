"""Dash Dashboard — A股量化系统可视化看板"""

import yaml
import dash
from dash import dcc, html
import plotly.graph_objects as go
from loguru import logger

from data.db import DBManager
from strategy.ma_cross import MACrossStrategy
from strategy.momentum import MomentumStrategy
from strategy.mean_revert import MeanRevertStrategy
from backtest.engine import BacktestEngine
from backtest.analyzer import BacktestAnalyzer
from visual.charts import (
    plot_equity_curve, plot_drawdown, plot_strategy_comparison, plot_metrics_table,
)


def create_app(config_path: str = "config/settings.yaml") -> dash.Dash:
    """创建 Dash 应用"""

    with open(config_path) as f:
        config = yaml.safe_load(f)

    app = dash.Dash(__name__, title="A股量化系统")
    db_path = config["data"]["db_path"]
    bt_cfg = config["backtest"]

    # 布局
    app.layout = html.Div([
        html.H1("A股因子选股量化系统", style={"textAlign": "center"}),

        # 数据概览
        html.Div([
            html.H2("数据概览"),
            html.Div(id="data-overview"),
        ], style={"margin": "20px"}),

        # 回测指标
        html.Div([
            html.H2("回测指标对比"),
            dcc.Graph(id="metrics-table"),
        ], style={"margin": "20px"}),

        # 收益曲线
        html.Div([
            html.H2("策略收益对比"),
            dcc.Graph(id="equity-curves"),
        ], style={"margin": "20px"}),

        # 回撤曲线
        html.Div([
            html.H2("最大回撤"),
            dcc.Graph(id="drawdown-chart"),
        ], style={"margin": "20px"}),
    ])

    @app.callback(
        [
            dash.dependencies.Output("data-overview", "children"),
            dash.dependencies.Output("metrics-table", "figure"),
            dash.dependencies.Output("equity-curves", "figure"),
            dash.dependencies.Output("drawdown-chart", "figure"),
        ]
    )
    def update_dashboard():
        try:
            with DBManager(db_path, read_only=True) as db:
                # 数据概览
                coverage = db.get_data_coverage()
                overview = html.Div([
                    html.P(f"股票数量: {coverage['stocks']}"),
                    html.P(f"数据范围: {coverage['min_date']} ~ {coverage['max_date']}"),
                ])

                # 回测
                # 用沪深300成分示例（或全市场）
                # 先简单用一只股票演示
                sample_code = "000001"  # 平安银行
                df = db.get_daily_quote(code=sample_code)

                if df.empty:
                    empty_fig = go.Figure()
                    empty_fig.update_layout(title="暂无数据，请先运行数据采集")
                    return overview, empty_fig, empty_fig, empty_fig

                # 跑三个策略
                strategies = [
                    MACrossStrategy(short_window=5, long_window=20),
                    MomentumStrategy(lookback=20, buy_threshold=0.05),
                    MeanRevertStrategy(lookback=20, entry_z=2.0),
                ]

                engine = BacktestEngine(
                    initial_capital=bt_cfg["initial_capital"],
                    commission=bt_cfg["commission"],
                    slippage=bt_cfg["slippage"],
                )

                results = engine.run_multi(strategies, df)

                # 指标表格
                metrics_fig = plot_metrics_table(results)

                # 收益曲线
                equity_fig = plot_strategy_comparison(results)

                # 回撤（用第一个策略）
                dd_fig = plot_drawdown(results[0]["returns"], title=f"{results[0]['strategy_name']} 回撤")

                return overview, metrics_fig, equity_fig, dd_fig

        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            empty = go.Figure()
            empty.update_layout(title=f"错误: {e}")
            return html.P(f"错误: {e}"), empty, empty, empty

    return app


def run_server(config_path: str = "config/settings.yaml"):
    """启动 Dashboard"""
    dash_cfg = yaml.safe_load(open(config_path))["dashboard"]

    app = create_app(config_path)
    app.run(
        host=dash_cfg["host"],
        port=dash_cfg["port"],
        debug=dash_cfg["debug"],
    )


if __name__ == "__main__":
    run_server()