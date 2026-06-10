"""交易风控监控 Dashboard"""

import yaml
import dash
from dash import dcc, html, dash_table
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from loguru import logger
from datetime import datetime

from data.db.duckdb_manager import DuckDBManager
from executor.pnl_calc import PnLCalculator


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
    """创建组合概览卡片（使用真实PnL计算）"""
    pnl_calc = PnLCalculator(db)

    try:
        # 获取最新日期
        date_result = db.query("SELECT MAX(date) as max_date FROM position_log")
        if date_result.empty or pd.isna(date_result.iloc[0]["max_date"]):
            return [
                _card("持仓数", "0", "#7f8c8d"),
                _card("总市值", "0", "#7f8c8d"),
                _card("浮动盈亏", "0", "#7f8c8d"),
                _card("夏普比率", "-", "#7f8c8d"),
            ]

        latest_date = date_result.iloc[0]["max_date"]
        date_str = str(latest_date)

        # 使用PnL计算器获取真实数据
        portfolio_pnl = pnl_calc.calculate_portfolio_pnl(date_str)
        metrics = pnl_calc.calculate_metrics("2020-01-01", date_str)

        position_count = portfolio_pnl["position_count"]
        total_value = portfolio_pnl["total_market_value"]
        unrealized_pnl = portfolio_pnl["total_unrealized_pnl"]
        unrealized_pnl_pct = portfolio_pnl["total_unrealized_pnl_pct"]

        # 计算今日收益（需要前一天的数据）
        daily_pnl, daily_pnl_pct = _calculate_daily_return(db, pnl_calc, latest_date)

        cards = [
            _card("持仓数", str(position_count), "#3498db"),
            _card("总市值", f"¥{total_value:,.0f}" if total_value > 0 else "-", "#2ecc71"),
        ]

        # 今日收益卡片
        if daily_pnl is not None:
            color = "#27ae60" if daily_pnl >= 0 else "#e74c3c"
            cards.append(_card("今日收益", f"¥{daily_pnl:+,.0f}<br>({daily_pnl_pct:+.2f}%)", color))
        else:
            cards.append(_card("今日收益", "-", "#7f8c8d"))

        # 浮动盈亏卡片
        pnl_color = "#27ae60" if unrealized_pnl >= 0 else "#e74c3c"
        cards.append(_card("浮动盈亏", f"¥{unrealized_pnl:+,.0f}<br>({unrealized_pnl_pct:+.2f}%)", pnl_color))

        # 额外指标
        cards.append(_card("累计收益", f"{metrics.total_return*100:+.2f}%", "#9b59b6"))
        cards.append(_card("最大回撤", f"{metrics.max_drawdown*100:.2f}%", "#e67e22"))
        cards.append(_card("夏普比率", f"{metrics.sharpe_ratio:.2f}", "#1abc9c"))

        return cards

    except Exception as e:
        logger.warning(f"Failed to create portfolio cards: {e}")
        return [
            _card("持仓数", "0", "#7f8c8d"),
            _card("总市值", "-", "#7f8c8d"),
            _card("浮动盈亏", "-", "#7f8c8d"),
            _card("夏普比率", "-", "#7f8c8d"),
        ]


def _card(title: str, value: str, color: str) -> html.Div:
    """创建卡片组件"""
    return html.Div([
        html.H4(title, style={"margin": "5px", "color": "#7f8c8d", "fontSize": "14px"}),
        html.H2(value, style={"margin": "5px", "color": color, "fontSize": "24px"}),
    ], style={
        "padding": "15px 20px",
        "backgroundColor": "#f8f9fa",
        "borderRadius": "10px",
        "minWidth": "130px",
        "textAlign": "center",
        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
    })


def _calculate_daily_return(db: DuckDBManager, pnl_calc: PnLCalculator, current_date) -> tuple:
    """计算今日收益"""
    try:
        # 获取前一个交易日的市值
        prev_sql = """
            SELECT SUM(market_value) as prev_value
            FROM position_log
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 1
        """
        prev_result = db.query(prev_sql, [str(current_date)])

        if prev_result.empty or pd.isna(prev_result.iloc[0]["prev_value"]):
            return None, None

        prev_value = prev_result.iloc[0]["prev_value"]

        # 获取当前市值
        current_result = db.query(f"""
            SELECT SUM(market_value) as current_value
            FROM position_log
            WHERE date = '{str(current_date)}'
        """)

        if current_result.empty or pd.isna(current_result.iloc[0]["current_value"]):
            return None, None

        current_value = current_result.iloc[0]["current_value"]

        if prev_value > 0:
            daily_pnl = current_value - prev_value
            daily_pnl_pct = daily_pnl / prev_value * 100
            return daily_pnl, daily_pnl_pct

        return None, None
    except Exception as e:
        logger.debug(f"Failed to calculate daily return: {e}")
        return None, None


def _plot_equity_curve(db: DuckDBManager) -> go.Figure:
    """绘制收益曲线（带回撤）"""
    pnl_calc = PnLCalculator(db)

    try:
        # 获取净值曲线
        equity_df = pnl_calc.get_portfolio_equity_curve("2020-01-01", "2099-12-31")

        if equity_df.empty or len(equity_df) < 2:
            fig = go.Figure()
            fig.update_layout(title="暂无持仓数据，请先运行模拟交易")
            return fig

        # 计算回撤
        rolling_max = equity_df["equity"].expanding().max()
        drawdown = (equity_df["equity"] - rolling_max) / rolling_max * 100

        # 创建子图：净值 + 回撤
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            shared_xaxes=True,
            vertical_spacing=0.05,
        )

        # 净值曲线
        fig.add_trace(
            go.Scatter(
                x=equity_df["date"],
                y=equity_df["equity"],
                mode="lines",
                name="净值",
                line=dict(color="#2ecc71", width=2),
                fill="tonexty",
                fillcolor="rgba(46, 204, 113, 0.1)",
            ),
            row=1, col=1
        )

        # 回撤曲线
        fig.add_trace(
            go.Scatter(
                x=equity_df["date"],
                y=drawdown,
                mode="lines",
                name="回撤",
                line=dict(color="#e74c3c", width=1.5),
                fill="tonexty",
                fillcolor="rgba(231, 76, 60, 0.2)",
            ),
            row=2, col=1
        )

        # 标记最大回撤点
        max_dd_idx = drawdown.idxmin()
        if not pd.isna(max_dd_idx):
            max_dd_date = equity_df.loc[max_dd_idx, "date"]
            max_dd_value = drawdown.loc[max_dd_idx]
            fig.add_annotation(
                x=max_dd_date,
                y=max_dd_value - 2,
                text=f"最大回撤: {max_dd_value:.2f}%",
                showarrow=True,
                arrowhead=1,
                row=2, col=1
            )

        fig.update_layout(
            title="组合净值与回撤曲线",
            hovermode="x unified",
            showlegend=True,
            height=500,
        )
        fig.update_yaxes(title_text="净值 (元)", row=1, col=1)
        fig.update_yaxes(title_text="回撤 (%)", row=2, col=1, tickformat=".1f")

        return fig

    except Exception as e:
        logger.error(f"Failed to plot equity curve: {e}")
        fig = go.Figure()
        fig.update_layout(title=f"数据加载错误: {str(e)}")
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
    """创建持仓表格（含盈亏信息）"""
    pnl_calc = PnLCalculator(db)

    try:
        # 获取最新日期
        date_result = db.query("SELECT MAX(date) as max_date FROM position_log")
        if date_result.empty or pd.isna(date_result.iloc[0]["max_date"]):
            return html.P("暂无持仓数据", style={"textAlign": "center", "color": "#7f8c8d"})

        latest_date = str(date_result.iloc[0]["max_date"])

        # 获取持仓并计算每只股票的盈亏
        positions = db.query(f"SELECT * FROM position_log WHERE date = '{latest_date}' ORDER BY code")

        if positions.empty:
            return html.P("暂无持仓数据", style={"textAlign": "center", "color": "#7f8c8d"})

        # 计算每只股票的盈亏
        pnl_data = []
        for _, pos in positions.iterrows():
            pos_pnl = pnl_calc.calculate_position_pnl(pos["code"], latest_date)

            if pos_pnl:
                pnl_data.append({
                    "code": pos["code"],
                    "shares": pos_pnl.shares,
                    "cost_price": f"{pos_pnl.cost_price:.2f}",
                    "current_price": f"{pos_pnl.current_price:.2f}",
                    "market_value": f"{pos_pnl.market_value:.0f}",
                    "unrealized_pnl": f"{pos_pnl.unrealized_pnl:+.0f}",
                    "unrealized_pnl_pct": f"{pos_pnl.unrealized_pnl_pct:+.2f}%",
                })
            else:
                pnl_data.append({
                    "code": pos["code"],
                    "shares": pos.get("shares", 0),
                    "cost_price": "-",
                    "current_price": "-",
                    "market_value": "-",
                    "unrealized_pnl": "-",
                    "unrealized_pnl_pct": "-",
                })

        columns = [
            {"name": "代码", "id": "code"},
            {"name": "持仓数量", "id": "shares"},
            {"name": "成本价", "id": "cost_price"},
            {"name": "现价", "id": "current_price"},
            {"name": "市值", "id": "market_value"},
            {"name": "浮盈浮亏", "id": "unrealized_pnl"},
            {"name": "盈亏比例", "id": "unrealized_pnl_pct"},
        ]

        return dash_table.DataTable(
            data=pnl_data,
            columns=columns,
            page_size=15,
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": "#3498db", "color": "white", "fontWeight": "bold"},
            style_cell={"textAlign": "center", "padding": "8px"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
            ],
        )

    except Exception as e:
        logger.error(f"Failed to create positions table: {e}")
        return html.P(f"数据加载错误: {e}", style={"textAlign": "center", "color": "#e74c3c"})


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
