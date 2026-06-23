"""ML训练/预测看板"""

import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.express as px
import pandas as pd
import yaml
from loguru import logger
from data.db import DBManager


class MLDashboard:
    """ML训练/预测看板

    页面：
    - 训练日志：各窗口训练结果
    - 模型对比：ML vs 传统基线
    - 预测信号分布
    - 特征重要性
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.db_path = self.config["data"]["db_path"]

        self.app = dash.Dash(__name__, external_stylesheets=[
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/css/bootstrap.min.css"
        ])
        self._build_layout()
        self._bind_callbacks()

    def _get_db(self):
        return DBManager(self.db_path, read_only=True)

    def _build_layout(self):
        self.app.layout = html.Div(className="container-fluid p-4", children=[
            html.H1("ML因子合成看板 🧠", className="mb-4",
                     style={"color": "#2c3e50", "fontWeight": "bold"}),

            dcc.Tabs(id="ml-tabs", value="training", children=[
                dcc.Tab(label="训练日志", value="training"),
                dcc.Tab(label="模型对比", value="compare"),
                dcc.Tab(label="预测信号", value="signal"),
                dcc.Tab(label="特征重要性", value="importance"),
            ]),

            html.Div(id="ml-content", className="mt-4"),
        ])

    def _bind_callbacks(self):
        @self.app.callback(
            Output("ml-content", "children"),
            Input("ml-tabs", "value"),
        )
        def render_tab(tab):
            db = self._get_db()
            db.connect()
            try:
                if tab == "training":
                    return self._render_training(db)
                elif tab == "compare":
                    return self._render_compare(db)
                elif tab == "signal":
                    return self._render_signal(db)
                elif tab == "importance":
                    return self._render_importance(db)
                return html.P("Unknown tab")
            except Exception as e:
                return html.P(f"Error: {e}", className="text-danger")
            finally:
                db.close()

    def _render_training(self, db):
        """训练日志表"""
        try:
            logs = db.query("SELECT * FROM model_log ORDER BY eval_date DESC")
            if logs.empty:
                return html.P("暂无训练日志，请先跑 run_train", className="text-muted")
            return dash_table.DataTable(
                data=logs.to_dict("records"),
                columns=[{"name": c, "id": c} for c in logs.columns],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center", "fontSize": "13px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#ecf0f1"},
                page_size=20,
            )
        except Exception as e:
            return html.P(f"查询失败: {e}")

    def _render_compare(self, db):
        """模型对比"""
        try:
            # 尝试读取对比结果CSV
            import os
            comp_file = "data/cache/ml/strategy_compare.csv"
            if os.path.exists(comp_file):
                df = pd.read_csv(comp_file)
                return dash_table.DataTable(
                    data=df.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in df.columns],
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "center", "fontSize": "14px"},
                    style_header={"fontWeight": "bold", "backgroundColor": "#ecf0f1"},
                )
            return html.P("暂无对比结果，请先跑 run_compare", className="text-muted")
        except Exception as e:
            return html.P(f"对比渲染失败: {e}")

    def _render_signal(self, db):
        """预测信号分布"""
        try:
            signals = db.query("""
                SELECT date, model_name,
                       COUNT(*) as n_stocks,
                       SUM(CASE WHEN signal=1 THEN 1 ELSE 0 END) as n_long,
                       SUM(CASE WHEN signal=-1 THEN 1 ELSE 0 END) as n_short,
                       AVG(predicted_return) as avg_pred
                FROM ml_signal
                GROUP BY date, model_name
                ORDER BY date DESC
            """)
            if signals.empty:
                return html.P("暂无预测信号", className="text-muted")

            fig = px.bar(signals, x="date", y="n_long", color="model_name",
                         title="做多信号数量")
            fig.update_layout(height=400)
            return dcc.Graph(figure=fig)
        except Exception as e:
            return html.P(f"信号渲染失败: {e}")

    def _render_importance(self, db):
        """特征重要性"""
        try:
            import os
            imp_file = "data/cache/ml/feature_importance.csv"
            if os.path.exists(imp_file):
                df = pd.read_csv(imp_file)
                fig = px.bar(df.head(20), x="feature", y="importance",
                             title="Top 20 Feature Importance")
                fig.update_layout(height=500)
                return dcc.Graph(figure=fig)
            return html.P("暂无特征重要性数据", className="text-muted")
        except Exception as e:
            return html.P(f"特征重要性渲染失败: {e}")

    def run(self, port=8052, host="0.0.0.0"):
        logger.info(f"ML Dashboard starting on {host}:{port}")
        self.app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    dashboard = MLDashboard()
    dashboard.run()