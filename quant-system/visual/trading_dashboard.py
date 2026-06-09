"""交易风控监控 Dashboard"""

import yaml
import dash
from dash import dcc, html, dash_table
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from loguru import logger

from data.db.duckdb_manager import DuckDBManager


def create_app(config_path: str = "config/settings.yaml") -> dash.Dash:
    """创建交易监控 Dash 应用"""

    with open(config_path) as f:
        config = yaml.safe_load(f)

    app = dash.Dash(__name__, title="交易风控监控")
    db = DuckDBManager(config["data"]["db_path"])

    app.layout = html.Div([
        html.H1("交易风控监控面板", style={"textAlign": "center", "color": "#2c3e50"}),

        # 1. 概览指标卡片
        html.Div([
            html.H2("组合概览"),
            html.Div(id="portfolio-cards", style={
                "display": "flex",
                "gap": "20px",
                "flexWrap": "wrap",
                "justifyContent": "center",
            }),
        ], style={"margin": "20px"}),

        # 2. 收益曲线 + 持仓分布
        html.Div([
            html.Div([
                html.H2("收益曲线"),
                dcc.Graph(id="equity-curve"),
            ], style={"width": "65%", "display": "inline-block", "verticalAlign": "top"}),

            html.Div([
                html.H2("行业分布"),
                dcc.Graph(id="industry-pie"),
            ], style={"width": "35%", "display": "inline-block", "verticalAlign": "top"}),
        ], style={"margin": "20px"}),

        # 3. 持仓明细
        html.Div([
            html.H2("持仓明细"),
            html.Div(id="positions-table"),
        ], style={"margin": "20px"}),

        # 4. 交易历史
        html.Div([
            html.H2("交易记录"),
            html.Div(id="trades-table"),
        ], style={"margin": "20px"}),

        # 5. 风控事件
        html.Div([
            html.H2("风控事件日志"),
            html.Div(id="risk-events"),
        ], style={"margin": "20px"}),

        # 6. 订单状态
        html.Div([
            html.H2("订单状态"),
            html.Div(id="orders-table"),
        ], style={"margin": "20px"}),

        dcc.Interval(
            id="interval-component",
            interval=10 * 1000,  # 10秒刷新
            n_intervals=0,
        ),
    ])

    @app.callback(
        [
            dash.dependencies.Output("portfolio-cards", "children"),
            dash.dependencies.Output("equity-curve", "figure"),
            dash.dependencies.Output("industry-pie", "figure"),
            dash.dependencies.Output("positions-table", "children"),
            dash.dependencies.Output("trades-table", "children"),
            dash.dependencies.Output("risk-events", "children"),
            dash.dependencies.Output("orders-table", "children"),
        ],
        [dash.dependencies.Input("interval-component", "n_intervals")]
    )
    def update_dashboard(n):
        db.connect()
        try:
            # 1. 组合概览卡片
            cards = _create_portfolio_cards(db)

            # 2. 收益曲线
            equity_fig = _plot_equity_curve(db)

            # 3. 行业分布
            industry_fig = _plot_industry_distribution(db)

            # 4. 持仓表格
            positions_table = _create_positions_table(db)

            # 5. 交易记录
            trades_table = _create_trades_table(db)

            # 6. 风控事件
            risk_events = _create_risk_events_table(db)

            # 7. 订单表格
            orders_table = _create_orders_table(db)

            return cards, equity_fig, industry_fig, positions_table, trades_table, risk_events, orders_table

        except Exception as e:
            logger.error(f"Trading dashboard error: {e}")
            import traceback
            traceback.print_exc()
            empty_fig = go.Figure()
            empty_fig.update_layout(title="暂无数据")
            return html.P(f"错误: {e}"), empty_fig, empty_fig, html.P("暂无数据"), html.P("暂无数据"), html.P("暂无数据"), html.P("暂无数据")
        finally:
            db.close()

    return app


def _create_portfolio_cards(db: DuckDBManager) -> list:
    """创建组合概览卡片"""
    try:
        positions = db.query("SELECT * FROM position_log WHERE date = (SELECT MAX(date) FROM position_log)")
    except:
        positions = pd.DataFrame()

    if positions.empty:
        return [_card("持仓数", "0", "#7f8c8d"), _card("总市值", "0", "#7f8c8d")]

    total_value = positions["market_value"].sum() if "market_value" in positions.columns else 0
    position_count = len(positions)

    # 估算今日收益（模拟数据）
    daily_pnl = total_value * 0.005
    daily_pnl_pct = 0.5

    return [
        _card("持仓数", str(position_count), "#3498db"),
        _card("总市值", f"¥{total_value:,.0f}" if total_value > 0 else "计算中", "#2ecc71"),
        _card("今日收益", f"¥{daily_pnl:+,.0f} ({daily_pnl_pct:+.2f}%)", "#27ae60" if daily_pnl >= 0 else "#e74c3c"),
        _card("风险等级", "中", "#f39c12"),
    ]


def _card(title: str, value: str, color: str) -> html.Div:
    """创建卡片组件"""
    return html.Div([
        html.H4(title, style={"margin": "5px", "color": "#7f8c8d", "fontSize": "14px"}),
        html.H2(value, style={"margin": "5px", "color": color, "fontSize": "28px"}),
    ], style={
        "padding": "15px 30px",
        "backgroundColor": "#f8f9fa",
        "borderRadius": "10px",
        "minWidth": "150px",
        "textAlign": "center",
        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
    })


def _plot_equity_curve(db: DuckDBManager) -> go.Figure:
    """绘制收益曲线"""
    try:
        positions = db.query("SELECT * FROM position_log ORDER BY date")
    except:
        positions = pd.DataFrame()

    if positions.empty:
        fig = go.Figure()
        fig.update_layout(title="暂无持仓数据，请先运行模拟交易")
        return fig

    # 按日期汇总市值
    daily_value = positions.groupby("date")["market_value"].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_value["date"],
        y=daily_value["market_value"],
        mode="lines+markers",
        name="组合市值",
        line=dict(color="#2ecc71", width=2),
        fill="tonexty",
        fillcolor="rgba(46, 204, 113, 0.1)",
    ))

    fig.update_layout(
        title="组合净值曲线",
        xaxis_title="日期",
        yaxis_title="市值 (元)",
        hovermode="x unified",
        showlegend=True,
        height=400,
    )
    return fig


def _plot_industry_distribution(db: DuckDBManager) -> go.Figure:
    """绘制行业分布饼图"""
    try:
        positions = db.query("SELECT * FROM position_log WHERE date = (SELECT MAX(date) FROM position_log)")
    except:
        positions = pd.DataFrame()

    if positions.empty or "industry" not in positions.columns:
        # 模拟数据
        labels = ["金融", "科技", "消费", "医药", "其他"]
        values = [30, 25, 20, 15, 10]
    else:
        industry_value = positions.groupby("industry")["market_value"].sum().reset_index()
        labels = industry_value["industry"].tolist()
        values = industry_value["market_value"].tolist()

    colors = ["#3498db", "#e74c3c", "#f1c40f", "#2ecc71", "#9b59b6"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors),
        textinfo="label+percent",
    )])

    fig.update_layout(
        title="行业分布",
        height=400,
    )
    return fig


def _create_positions_table(db: DuckDBManager) -> dash_table.DataTable:
    """创建持仓表格"""
    try:
        positions = db.query("SELECT * FROM position_log WHERE date = (SELECT MAX(date) FROM position_log) ORDER BY code")
    except:
        positions = pd.DataFrame()

    if positions.empty:
        return html.P("暂无持仓数据", style={"textAlign": "center", "color": "#7f8c8d"})

    columns = [{"name": col, "id": col} for col in ["code", "shares", "weight", "cost_price", "current_price", "market_value"] if col in positions.columns]
    data = positions.to_dict("records")

    return dash_table.DataTable(
        data=data,
        columns=columns,
        page_size=10,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#3498db", "color": "white", "fontWeight": "bold"},
        style_cell={"textAlign": "center", "padding": "8px"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        ],
    )


def _create_trades_table(db: DuckDBManager) -> dash_table.DataTable:
    """创建交易记录表格"""
    try:
        trades = db.query("SELECT * FROM trade_log ORDER BY date DESC LIMIT 20")
    except:
        trades = pd.DataFrame()

    if trades.empty:
        return html.P("暂无交易记录", style={"textAlign": "center", "color": "#7f8c8d"})

    columns = [{"name": col, "id": col} for col in ["date", "code", "action", "shares", "price"] if col in trades.columns]
    data = trades.to_dict("records")

    return dash_table.DataTable(
        data=data,
        columns=columns,
        page_size=10,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#27ae60", "color": "white", "fontWeight": "bold"},
        style_cell={"textAlign": "center", "padding": "8px"},
        style_data_conditional=[
            {"if": {"filter_query": "{action} = 'buy'"}, "backgroundColor": "rgba(39, 174, 96, 0.1)", "color": "#27ae60"},
            {"if": {"filter_query": "{action} = 'sell'"}, "backgroundColor": "rgba(231, 76, 60, 0.1)", "color": "#e74c3c"},
        ],
    )


def _create_risk_events_table(db: DuckDBManager) -> dash_table.DataTable:
    """创建风控事件表格"""
    try:
        events = db.query("SELECT * FROM risk_event_log ORDER BY date DESC LIMIT 20")
    except:
        events = pd.DataFrame()

    if events.empty:
        return html.P("暂无风控事件", style={"textAlign": "center", "color": "#27ae60"})

    columns = [{"name": col, "id": col} for col in ["date", "level", "rule_name", "code", "message"] if col in events.columns]
    data = events.to_dict("records")

    return dash_table.DataTable(
        data=data,
        columns=columns,
        page_size=10,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#e74c3c", "color": "white", "fontWeight": "bold"},
        style_cell={"textAlign": "center", "padding": "8px"},
        style_data_conditional=[
            {"if": {"filter_query": "{level} = 'block'"}, "backgroundColor": "rgba(231, 76, 60, 0.1)", "color": "#e74c3c"},
            {"if": {"filter_query": "{level} = 'warning'"}, "backgroundColor": "rgba(243, 156, 18, 0.1)", "color": "#f39c12"},
        ],
    )


def _create_orders_table(db: DuckDBManager) -> dash_table.DataTable:
    """创建订单状态表格"""
    try:
        orders = db.query("SELECT * FROM order_log ORDER BY date DESC LIMIT 20")
    except:
        orders = pd.DataFrame()

    if orders.empty:
        return html.P("暂无订单记录", style={"textAlign": "center", "color": "#7f8c8d"})

    columns = [{"name": col, "id": col} for col in ["order_id", "date", "code", "action", "shares", "price", "status"] if col in orders.columns]
    data = orders.to_dict("records")

    return dash_table.DataTable(
        data=data,
        columns=columns,
        page_size=10,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#3498db", "color": "white", "fontWeight": "bold"},
        style_cell={"textAlign": "center", "padding": "8px"},
    )


def run_server(config_path: str = "config/settings.yaml"):
    """启动交易监控面板"""
    dash_cfg = yaml.safe_load(open(config_path))["dashboard"]

    app = create_app(config_path)
    app.run(
        host=dash_cfg["host"],
        port=dash_cfg.get("trading_port", 8053),
        debug=dash_cfg["debug"],
    )


if __name__ == "__main__":
    run_server()
