"""统一量化门户 Dashboard - 所有功能模块的统一入口"""

import yaml
import dash
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd
import plotly.graph_objects as go
from loguru import logger
from datetime import datetime

from data.db import DBManager
from executor.pnl_calc import PnLCalculator


# Dashboard配置
DASHBOARDS = {
    "home": {"name": "首页概览", "port": None, "color": "#3498db"},
    "strategy": {"name": "策略回测", "port": 8050, "color": "#2ecc71"},
    "factor": {"name": "因子分析", "port": 8051, "color": "#e74c3c"},
    "ml": {"name": "ML模型", "port": 8052, "color": "#9b59b6"},
    "trading": {"name": "实盘监控", "port": 8053, "color": "#f39c12"},
}


def create_app(config_path: str = "config/settings.yaml") -> dash.Dash:
    """创建统一门户 Dash 应用"""

    with open(config_path) as f:
        config = yaml.safe_load(f)

    app = dash.Dash(
        __name__,
        title="量化投研平台",
        suppress_callback_exceptions=True,
    )

    # 导航栏
    nav_bar = html.Div([
        html.Div([
            html.H1("📈 量化投研平台", style={
                "margin": "0",
                "color": "white",
                "fontSize": "24px",
                "fontWeight": "bold",
            }),
        ], style={
            "display": "inline-block",
            "padding": "15px 30px",
        }),
        html.Div([
            html.Button(
                cfg["name"],
                id=f"nav-{name}-btn",
                n_clicks=0,
                style={
                    "backgroundColor": cfg["color"],
                    "color": "white",
                    "border": "none",
                    "padding": "10px 20px",
                    "margin": "0 5px",
                    "borderRadius": "5px",
                    "cursor": "pointer",
                    "fontSize": "14px",
                    "fontWeight": "bold",
                }
            )
            for name, cfg in DASHBOARDS.items()
        ], style={
            "display": "inline-block",
            "float": "right",
            "padding": "10px 20px",
        }),
    ], style={
        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "boxShadow": "0 4px 6px rgba(0,0,0,0.1)",
        "position": "sticky",
        "top": 0,
        "zIndex": 1000,
        "overflow": "hidden",
    })

    # 页面内容容器
    content = html.Div(id="page-content", style={
        "padding": "20px",
        "minHeight": "calc(100vh - 80px)",
        "backgroundColor": "#f5f7fa",
    })

    app.layout = html.Div([
        dcc.Store(id="current-page", data="home"),
        nav_bar,
        content,
    ])

    # 导航回调
    @app.callback(
        Output("page-content", "children"),
        Output("current-page", "data"),
        [Input(f"nav-{name}-btn", "n_clicks") for name in DASHBOARDS.keys()],
        State("current-page", "data"),
    )
    def navigate(*args):
        ctx = dash.callback_context
        current_page = args[-1]

        if not ctx.triggered:
            return _render_home_page(), "home"

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        page_name = button_id.replace("nav-", "").replace("-btn", "")

        if page_name == "home":
            return _render_home_page(), "home"
        else:
            return _render_dashboard_iframe(page_name), page_name

    return app


def _render_home_page() -> html.Div:
    """渲染首页概览页面"""
    try:
        with DBManager(read_only=True) as db:
            pnl_calc = PnLCalculator(db)
            # 获取系统状态数据
            system_status = _get_system_status(db, pnl_calc)
    except Exception as e:
        logger.error(f"Failed to load home page data: {e}")
        system_status = {}

    return html.Div([
        html.H2("🏠 系统概览", style={"color": "#2c3e50", "marginBottom": "30px"}),

        # 第一行：系统状态卡片
        html.Div([
            _render_status_card("📊 因子数量", system_status.get("factor_count", "-"), "#3498db"),
            _render_status_card("📈 ML模型数", system_status.get("model_count", "-"), "#9b59b6"),
            _render_status_card("📦 股票数量", system_status.get("stock_count", "-"), "#2ecc71"),
            _render_status_card("💼 持仓数量", system_status.get("position_count", "-"), "#f39c12"),
            _render_status_card("📝 交易次数", system_status.get("trade_count", "-"), "#e74c3c"),
            _render_status_card("🔔 告警数量", system_status.get("alert_count", "-"), "#e67e22"),
        ], style={
            "display": "flex",
            "gap": "20px",
            "flexWrap": "wrap",
            "justifyContent": "center",
            "marginBottom": "30px",
        }),

        # 第二行：组合概览
        html.Div([
            html.Div([
                html.H3("💼 组合概况", style={"color": "#2c3e50", "marginBottom": "15px"}),
                _render_portfolio_overview(system_status),
            ], style={
                "width": "48%",
                "display": "inline-block",
                "verticalAlign": "top",
                "padding": "20px",
                "backgroundColor": "white",
                "borderRadius": "10px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            }),

            html.Div([
                html.H3("🚀 快速入口", style={"color": "#2c3e50", "marginBottom": "15px"}),
                _render_quick_links(),
            ], style={
                "width": "48%",
                "display": "inline-block",
                "verticalAlign": "top",
                "marginLeft": "4%",
                "padding": "20px",
                "backgroundColor": "white",
                "borderRadius": "10px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            }),
        ], style={"marginBottom": "30px"}),

        # 第三行：最近任务状态
        html.Div([
            html.H3("⏰ 最近任务执行", style={"color": "#2c3e50", "marginBottom": "15px"}),
            _render_recent_tasks(system_status),
        ], style={
            "padding": "20px",
            "backgroundColor": "white",
            "borderRadius": "10px",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
        }),
    ])


def _render_status_card(title: str, value: str, color: str) -> html.Div:
    """渲染状态卡片"""
    return html.Div([
        html.H4(title, style={
            "margin": "0",
            "color": "#7f8c8d",
            "fontSize": "14px",
        }),
        html.H2(str(value), style={
            "margin": "10px 0 0 0",
            "color": color,
            "fontSize": "32px",
            "fontWeight": "bold",
        }),
    ], style={
        "padding": "20px",
        "backgroundColor": "white",
        "borderRadius": "10px",
        "minWidth": "150px",
        "textAlign": "center",
        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
        "flex": "1",
    })


def _render_portfolio_overview(status: dict) -> html.Div:
    """渲染组合概览"""
    pnl = status.get("portfolio_pnl", {})
    metrics = status.get("metrics", {})

    if not pnl or not metrics:
        return html.P("暂无组合数据，请先运行模拟交易", style={
            "textAlign": "center",
            "color": "#7f8c8d",
            "padding": "40px",
        })

    return html.Div([
        html.Div([
            html.Div([
                html.Strong("总市值:", style={"color": "#7f8c8d"}),
                html.Span(f" ¥{pnl.get('total_market_value', 0):,.0f}", style={
                    "color": "#2c3e50",
                    "fontWeight": "bold",
                    "fontSize": "18px",
                    "marginLeft": "10px",
                }),
            ], style={"padding": "10px 0", "borderBottom": "1px solid #eee"}),

            html.Div([
                html.Strong("浮动盈亏:", style={"color": "#7f8c8d"}),
                html.Span(f" ¥{pnl.get('total_unrealized_pnl', 0):+,.0f}", style={
                    "color": "#27ae60" if pnl.get('total_unrealized_pnl', 0) >= 0 else "#e74c3c",
                    "fontWeight": "bold",
                    "fontSize": "18px",
                    "marginLeft": "10px",
                }),
                html.Span(f" ({pnl.get('total_unrealized_pnl_pct', 0):+.2f}%)", style={
                    "color": "#27ae60" if pnl.get('total_unrealized_pnl', 0) >= 0 else "#e74c3c",
                    "fontSize": "14px",
                }),
            ], style={"padding": "10px 0", "borderBottom": "1px solid #eee"}),

            html.Div([
                html.Strong("累计收益:", style={"color": "#7f8c8d"}),
                html.Span(f" {metrics.get('total_return', 0)*100:+.2f}%", style={
                    "color": "#9b59b6",
                    "fontWeight": "bold",
                    "fontSize": "18px",
                    "marginLeft": "10px",
                }),
            ], style={"padding": "10px 0", "borderBottom": "1px solid #eee"}),

            html.Div([
                html.Strong("最大回撤:", style={"color": "#7f8c8d"}),
                html.Span(f" {metrics.get('max_drawdown', 0)*100:.2f}%", style={
                    "color": "#e67e22",
                    "fontWeight": "bold",
                    "fontSize": "18px",
                    "marginLeft": "10px",
                }),
            ], style={"padding": "10px 0", "borderBottom": "1px solid #eee"}),

            html.Div([
                html.Strong("夏普比率:", style={"color": "#7f8c8d"}),
                html.Span(f" {metrics.get('sharpe_ratio', 0):.2f}", style={
                    "color": "#1abc9c",
                    "fontWeight": "bold",
                    "fontSize": "18px",
                    "marginLeft": "10px",
                }),
            ], style={"padding": "10px 0"}),
        ]),
    ])


def _render_quick_links() -> html.Div:
    """渲染快速入口链接"""
    links = [
        {"name": "📊 因子分析", "desc": "查看因子IC、分层回测", "page": "factor", "color": "#e74c3c"},
        {"name": "🤖 ML模型", "desc": "模型训练与预测", "page": "ml", "color": "#9b59b6"},
        {"name": "📈 实盘监控", "desc": "实时监控持仓与风控", "page": "trading", "color": "#f39c12"},
        {"name": "⚡ 运行回测", "desc": "运行策略回测", "page": "strategy", "color": "#2ecc71"},
        {"name": "🔄 增量更新", "desc": "更新行情与因子数据", "page": "home", "color": "#3498db"},
        {"name": "⚙️ 系统设置", "desc": "配置参数管理", "page": "home", "color": "#95a5a6"},
    ]

    return html.Div([
        html.Div([
            html.Button(
                [
                    html.Div(link["name"], style={"fontWeight": "bold", "fontSize": "16px"}),
                    html.Div(link["desc"], style={"fontSize": "12px", "opacity": 0.8, "marginTop": "5px"}),
                ],
                style={
                    "width": "100%",
                    "padding": "15px",
                    "marginBottom": "10px",
                    "backgroundColor": link["color"],
                    "color": "white",
                    "border": "none",
                    "borderRadius": "8px",
                    "cursor": "pointer",
                    "textAlign": "left",
                },
            )
            for link in links
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px"}),
    ])


def _render_recent_tasks(status: dict) -> html.Div:
    """渲染最近任务状态"""
    recent_tasks = status.get("recent_tasks", [])

    if not recent_tasks:
        return html.P("暂无任务记录", style={
            "textAlign": "center",
            "color": "#7f8c8d",
            "padding": "40px",
        })

    data = []
    for task in recent_tasks:
        status_color = {
            "success": "#27ae60",
            "failed": "#e74c3c",
            "running": "#f39c12",
        }.get(task.get("status", "unknown"), "#95a5a6")

        data.append({
            "任务名称": task.get("name", "-"),
            "状态": task.get("status", "-"),
            "开始时间": str(task.get("start_time", "-")),
            "耗时(秒)": f"{task.get('duration', 0):.1f}",
        })

    columns = [
        {"name": "任务名称", "id": "任务名称"},
        {"name": "状态", "id": "状态"},
        {"name": "开始时间", "id": "开始时间"},
        {"name": "耗时(秒)", "id": "耗时(秒)"},
    ]

    return dash_table.DataTable(
        data=data,
        columns=columns,
        page_size=10,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#3498db", "color": "white", "fontWeight": "bold"},
        style_cell={"textAlign": "center", "padding": "10px"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        ],
    )


def _render_dashboard_iframe(page_name: str) -> html.Div:
    """使用iframe渲染子Dashboard"""
    cfg = DASHBOARDS.get(page_name, {"name": "未知", "port": 8050})
    port = cfg["port"]

    return html.Div([
        html.H2(f"📊 {cfg['name']}", style={
            "color": "#2c3e50",
            "marginBottom": "15px",
        }),
        html.Iframe(
            src=f"http://localhost:{port}",
            style={
                "width": "100%",
                "height": "calc(100vh - 150px)",
                "border": "none",
                "borderRadius": "10px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
            },
        ),
    ])


def _get_system_status(db, pnl_calc: PnLCalculator) -> dict:
    """获取系统状态数据"""
    status = {}

    try:
        # 因子数量
        status["factor_count"] = db.query(
            "SELECT COUNT(DISTINCT factor_name) as cnt FROM factor_value"
        ).iloc[0]["cnt"] if not db.query("SELECT * FROM factor_value LIMIT 1").empty else 0
    except:
        status["factor_count"] = 0

    try:
        # 股票数量
        status["stock_count"] = db.query(
            "SELECT COUNT(DISTINCT code) as cnt FROM stock_info"
        ).iloc[0]["cnt"] if not db.query("SELECT * FROM stock_info LIMIT 1").empty else 0
    except:
        status["stock_count"] = 0

    try:
        # 持仓数量
        status["position_count"] = db.query(
            "SELECT COUNT(DISTINCT code) as cnt FROM position_log"
        ).iloc[0]["cnt"] if not db.query("SELECT * FROM position_log LIMIT 1").empty else 0
    except:
        status["position_count"] = 0

    try:
        # 交易次数
        status["trade_count"] = db.query(
            "SELECT COUNT(*) as cnt FROM trade_log"
        ).iloc[0]["cnt"] if not db.query("SELECT * FROM trade_log LIMIT 1").empty else 0
    except:
        status["trade_count"] = 0

    try:
        # 告警数量
        status["alert_count"] = db.query(
            "SELECT COUNT(*) as cnt FROM risk_event_log"
        ).iloc[0]["cnt"] if not db.query("SELECT * FROM risk_event_log LIMIT 1").empty else 0
    except:
        status["alert_count"] = 0

    # ML模型数量
    status["model_count"] = 3  # lgbm, xgboost, ensemble

    # 组合PnL
    try:
        date_result = db.query("SELECT MAX(date) as max_date FROM position_log")
        if not date_result.empty and not pd.isna(date_result.iloc[0]["max_date"]):
            latest_date = str(date_result.iloc[0]["max_date"])
            status["portfolio_pnl"] = pnl_calc.calculate_portfolio_pnl(latest_date)
            status["metrics"] = pnl_calc.calculate_metrics("2020-01-01", latest_date)
        else:
            status["portfolio_pnl"] = {}
            status["metrics"] = {}
    except:
        status["portfolio_pnl"] = {}
        status["metrics"] = {}

    # 最近任务
    try:
        tasks_df = db.query("""
            SELECT task_name, status, start_time,
                   JULIANDAY(end_time) - JULIANDAY(start_time) as duration_days
            FROM scheduler_log
            ORDER BY start_time DESC
            LIMIT 10
        """)
        if not tasks_df.empty:
            status["recent_tasks"] = [
                {
                    "name": row["task_name"],
                    "status": row["status"],
                    "start_time": row["start_time"],
                    "duration": row.get("duration_days", 0) * 86400,
                }
                for _, row in tasks_df.iterrows()
            ]
        else:
            status["recent_tasks"] = []
    except:
        status["recent_tasks"] = []

    return status


def run_server(config_path: str = "config/settings.yaml"):
    """启动统一门户Dashboard"""
    dash_cfg = yaml.safe_load(open(config_path))["dashboard"]

    app = create_app(config_path)
    app.run(
        host=dash_cfg["host"],
        port=dash_cfg.get("portal_port", 8055),  # 使用新端口作为统一门户
        debug=dash_cfg["debug"],
    )


if __name__ == "__main__":
    run_server()
