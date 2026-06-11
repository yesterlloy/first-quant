"""因子检验看板 - Dash可视化"""

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import yaml
from loguru import logger
from data.db.duckdb_manager import DuckDBManager
from factor.registry import FactorRegistry, auto_register


class FactorDashboard:
    """因子检验 Dashboard

    页面：
    - 因子概览：所有因子IC/ICIR汇总表
    - IC热力图：因子IC时间序列热力图
    - 分层收益图：因子分层回测收益曲线
    - 衰减曲线：因子预测力衰减
    - 筛选结果：有效因子清单
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.db_path = self.config["data"]["db_path"]

        # 注册因子
        auto_register()

        # Dash app
        self.app = dash.Dash(__name__, external_stylesheets=[
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/css/bootstrap.min.css"
        ])
        self._build_layout()
        self._bind_callbacks()

    def _get_db(self) -> DuckDBManager:
        """获取临时DB连接（只读模式）"""
        return DuckDBManager(self.db_path, read_only=True)

    def _build_layout(self):
        """构建页面布局"""
        self.app.layout = html.Div(className="container-fluid p-4", children=[
            # 标题
            html.H1("A股因子检验看板 🌙", className="mb-4",
                     style={"color": "#2c3e50", "fontWeight": "bold"}),

            # 因子选择
            html.Div(className="row mb-3", children=[
                html.Div(className="col-md-3", children=[
                    html.Label("选择因子:", className="form-label"),
                    dcc.Dropdown(
                        id="factor-dropdown",
                        options=[{"label": n, "value": n}
                                 for n in FactorRegistry.list_names()],
                        value="EP",
                        className="form-select",
                    ),
                ]),
                html.Div(className="col-md-3", children=[
                    html.Label("选择日期:", className="form-label"),
                    dcc.Input(id="date-input", type="text", value="2026-05-29",
                              className="form-control", placeholder="YYYY-MM-DD"),
                ]),
            ]),

            # Tabs
            dcc.Tabs(id="main-tabs", value="overview", children=[
                dcc.Tab(label="因子概览", value="overview"),
                dcc.Tab(label="IC热力图", value="ic_heatmap"),
                dcc.Tab(label="分层收益图", value="layer_chart"),
                dcc.Tab(label="衰减曲线", value="decay"),
                dcc.Tab(label="筛选结果", value="screening"),
            ]),

            # 内容区
            html.Div(id="tab-content", className="mt-4"),
        ])

    def _bind_callbacks(self):
        """绑定交互回调"""

        @self.app.callback(
            Output("tab-content", "children"),
            [Input("main-tabs", "value"),
             Input("factor-dropdown", "value"),
             Input("date-input", "value")]
        )
        def render_tab(tab, factor, date):
            db = self._get_db()
            db.connect()

            try:
                if tab == "overview":
                    return self._render_overview(db)
                elif tab == "ic_heatmap":
                    return self._render_ic_heatmap(db, factor)
                elif tab == "layer_chart":
                    return self._render_layer_chart(db, factor)
                elif tab == "decay":
                    return self._render_decay(db, factor)
                elif tab == "screening":
                    return self._render_screening(db)
                else:
                    return html.P("Unknown tab")
            except Exception as e:
                logger.error(f"Dashboard render error: {e}")
                return html.P(f"Error: {e}")
            finally:
                db.close()

    def _render_overview(self, db: DuckDBManager):
        """因子概览表"""
        try:
            # 尝试从 factor_value 表获取汇总
            factor_df = db.query("""
                SELECT factor_name, COUNT(DISTINCT code) as n_stocks,
                       COUNT(DISTINCT date) as n_dates,
                       AVG(raw_value) as avg_value,
                       STDDEV(raw_value) as std_value
                FROM factor_value
                GROUP BY factor_name
                ORDER BY factor_name
            """)

            if factor_df.empty:
                return html.P("暂无因子数据，请先计算因子值", className="text-muted")

            # 因子分类信息
            factor_infos = FactorRegistry.list_factors()
            info_map = {i.name: i for i in factor_infos}

            rows = []
            for _, row in factor_df.iterrows():
                name = row["factor_name"]
                info = info_map.get(name)
                rows.append({
                    "因子": name,
                    "分类": info.category if info else "-",
                    "描述": info.description if info else "-",
                    "股票数": int(row["n_stocks"]),
                    "日期数": int(row["n_dates"]),
                    "均值": f"{row['avg_value']:.4f}" if pd.notna(row["avg_value"]) else "-",
                    "标准差": f"{row['std_value']:.4f}" if pd.notna(row["std_value"]) else "-",
                })

            return dash_table.DataTable(
                data=rows,
                columns=[{"name": k, "id": k} for k in rows[0].keys()],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center", "fontSize": "14px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#ecf0f1"},
            )

        except Exception as e:
            return html.P(f"数据查询失败: {e}", className="text-danger")

    def _render_ic_heatmap(self, db: DuckDBManager, factor: str):
        """IC热力图"""
        try:
            ic_df = db.query(f"""
                SELECT date, factor_name, raw_value
                FROM factor_value
                WHERE factor_name = '{factor}'
                ORDER BY date
            """)

            if ic_df.empty:
                return html.P(f"暂无 {factor} 的IC数据", className="text-muted")

            # 简化：因子值随时间的变化折线图
            fig = px.line(ic_df, x="date", y="raw_value",
                          title=f"{factor} 因子值时间序列",
                          labels={"date": "日期", "raw_value": "因子值"})
            fig.update_layout(height=500)

            return dcc.Graph(figure=fig)

        except Exception as e:
            return html.P(f"IC热力图渲染失败: {e}", className="text-danger")

    def _render_layer_chart(self, db: DuckDBManager, factor: str):
        """分层收益图"""
        try:
            # 尝试读取分层回测结果
            layer_df = db.query(f"""
                SELECT code, date, raw_value
                FROM factor_value
                WHERE factor_name = '{factor}'
                ORDER BY date
            """)

            if layer_df.empty:
                return html.P(f"暂无 {factor} 数据", className="text-muted")

            # 因子值分布直方图
            fig = px.histogram(layer_df, x="raw_value",
                               title=f"{factor} 因子值分布",
                               nbins=50, labels={"raw_value": "因子值"})
            fig.update_layout(height=500)

            return dcc.Graph(figure=fig)

        except Exception as e:
            return html.P(f"分层收益图渲染失败: {e}", className="text-danger")

    def _render_decay(self, db: DuckDBManager, factor: str):
        """衰减曲线"""
        return html.P("衰减曲线需要跑完 decay_test 后显示", className="text-muted")

    def _render_screening(self, db: DuckDBManager):
        """筛选结果"""
        try:
            import os
            screening_file = "data/cache/factor/factor_screening.csv"
            if os.path.exists(screening_file):
                df = pd.read_csv(screening_file)
                return dash_table.DataTable(
                    data=df.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in df.columns],
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "center", "fontSize": "14px"},
                    style_header={"fontWeight": "bold", "backgroundColor": "#ecf0f1"},
                    style_data_conditional=[
                        {"if": {"filter_query": "{effectiveness} = 'strong'"},
                         "backgroundColor": "#d4edda"},
                        {"if": {"filter_query": "{effectiveness} = 'moderate'"},
                         "backgroundColor": "#fff3cd"},
                        {"if": {"filter_query": "{effectiveness} = 'weak'"},
                         "backgroundColor": "#f8d7da"},
                    ],
                )
            else:
                return html.P("暂无筛选结果，请先跑 run_factor_test", className="text-muted")
        except Exception as e:
            return html.P(f"筛选结果渲染失败: {e}", className="text-danger")

    def run(self, port: int = 8051, host: str = "0.0.0.0"):
        """启动 Dashboard"""
        logger.info(f"Factor Dashboard starting on {host}:{port}")
        self.app.run_server(host=host, port=port, debug=False)