# A股因子选股量化系统

基于因子选股的A股量化分析系统，支持数据采集、因子计算、因子检验、ML因子合成、策略回测、可视化展示。

## 开发进度

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 数据采集 + 存储 + 基础回测原型 | ✅ 完成 |
| Phase 2 | 因子系统 + 因子检验 | ✅ 完成 |
| Phase 3 | ML增强 + 因子合成 | ✅ 完成 |
| Phase 4 | 实盘对接 + 风控监控 | 待开发 |

## 快速启动

```bash
# Phase 1: 数据采集
python scripts/run_collector.py

# Phase 2: 因子计算 + 检验
python scripts/run_factor_compute.py
python scripts/run_factor_test.py

# Phase 3: ML训练
python scripts/run_feature_build.py          # 特征构建
python scripts/run_train.py --model lgbm_v1  # 模型训练
python scripts/run_compare.py                # 策略对比

# Dashboard
python scripts/run_dashboard.py       # 基础看板 (8050)
python scripts/run_factor_dashboard.py # 因子看板 (8051)
python scripts/run_ml_dashboard.py    # ML看板 (8052)
```

## Docker部署

```bash
docker compose up -d
```

## 因子库（17个因子）

| 分类 | 因子 | 说明 |
|------|------|------|
| **估值** | EP, BP, DP, SP | 盈利/价格、账面/价格、分红/价格、营收/市值 |
| **质量** | ROE, ROA, DebtRatio, CashFlowQuality | 净资产收益率、总资产净利率、资产负债率(翻转)、现金流质量 |
| **成长** | RevenueGrowth, ProfitGrowth, ROEChange | 营收增长率、净利润增长率、ROE变化率 |
| **技术** | MOM, REV, VOL, TURN, LIQ | 动量、反转、波动率、换手率、非流动性 |
| **规模** | MCAP, FCAP | 总市值(log)、流通市值(log) |

## 因子检验体系

| 检验方法 | 模块 | 输出 |
|----------|------|------|
| IC分析 | `ic_test.py` | IC均值、ICIR、正比例 |
| 分层回测 | `layer_test.py` | 5层分层、多空收益、单调性 |
| 截面回归 | `regression_test.py` | Fama-MacBeth β均值、t值 |
| 衰减分析 | `decay_test.py` | 半衰期、IC衰减曲线 |
| 因子筛选 | `screening.py` | 自动筛出 strong/moderate/weak |

## ML因子合成

| 模块 | 说明 |
|------|------|
| 特征工程 | 缺失值填充、MAD去极值、Z-score、因子交叉、行业dummy |
| 数据集 | 滚动窗口训练/验证/测试，防未来信息泄露 |
| LightGBM | 主力GBDT模型，滚动训练 |
| XGBoost | 对比模型 |
| Ridge/Lasso | 线性基线 |
| Ensemble | 多模型融合（等权/IC加权） |
| 传统基线 | 等权/IC加权/ICIR加权因子合成 |
| 超参搜索 | Optuna贝叶斯优化 |
| 评估 | IC/多空/过拟合检测 |

## 项目结构

```
quant-system/
├── config/              # 配置文件
├── data/
│   ├── collector/       # 数据采集（akshare/baostock/adata多源）
│   └── db/              # DuckDB数据库管理
├── factor/              # 因子模块
│   ├── base.py          # 因子基类
│   ├── registry.py      # 因子注册表
│   ├── valuation.py     # 估值因子
│   ├── quality.py       # 质量因子
│   ├── growth.py        # 成长因子
│   ├── technical.py     # 技术因子
│   ├── scale.py         # 规模因子
│   ├── processor.py     # 计算引擎
│   └── neutralize.py    # 中性化处理
├── factor_test/         # 因子检验
│   ├── ic_test.py       # IC分析
│   ├── layer_test.py    # 分层回测
│   ├── regression_test.py # 截面回归
│   ├── decay_test.py    # 衰减分析
│   ├── screening.py     # 因子筛选
│   └── report.py        # 检验报告
├── ml/                  # ML因子合成
│   ├── feature_engine.py # 特征工程
│   ├── dataset.py        # 数据集构建
│   ├── trainer.py        # 滚动训练引擎
│   ├── predictor.py      # 预测信号生成
│   ├── evaluator.py      # 模型评估
│   ├── hyperopt.py       # 超参搜索
│   └── models/
│       ├── lgbm.py       # LightGBM
│       ├── xgboost.py    # XGBoost
│       ├── linear.py     # Ridge/Lasso
│       └── ensemble.py   # 多模型融合
├── strategy/            # 策略模块
│   ├── ml_factor.py     # 传统因子合成策略
├── backtest/            # 回测引擎
│   ├── compare.py       # 多策略对比回测
├── visual/              # 可视化
│   ├── dashboard.py     # 基础看板
│   ├── factor_dashboard.py # 因子看板
│   ├── ml_dashboard.py  # ML看板
│   └── ic_heatmap.py    # IC图表
├── scripts/             # 运行脚本
└── tests/               # 测试