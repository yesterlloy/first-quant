# A股因子选股量化系统

基于因子选股的A股量化分析系统，支持数据采集、因子计算、因子检验、策略回测、可视化展示。

## 开发进度

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 数据采集 + 存储 + 基础回测原型 | ✅ 完成 |
| Phase 2 | 因子系统 + 因子检验 | ✅ 完成 |
| Phase 3 | ML增强 + 因子合成 | 待开发 |
| Phase 4 | 实盘对接 + 风控监控 | 待开发 |

## 快速启动

```bash
# Phase 1: 数据采集
python scripts/run_collector.py

# Phase 2: 因子计算
python scripts/run_factor_compute.py --date 2026-05-29

# Phase 2: 因子检验
python scripts/run_factor_test.py --start 20200101 --end 20260529

# Phase 2: 因子Dashboard
python scripts/run_factor_dashboard.py

# Phase 1: 回测
python scripts/run_backtest.py

# Phase 1: 基础Dashboard
python scripts/run_dashboard.py
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

## 项目结构

```
quant-system/
├── config/              # 配置文件
├── data/
│   ├── collector/       # 数据采集模块（akshare/baostock/adata多源）
│   │   ├── akshare_collector.py
│   │   ├── multi_source.py        # 多数据源自动切换
│   │   ├── fundamental.py         # 基础财务
│   │   ├── financial_ext.py       # 扩展财务（Phase 2）
│   │   ├── dividend.py            # 分红数据（Phase 2）
│   │   ├── industry.py            # 行业分类（Phase 2）
│   │   └── scheduler.py           # 定时采集
│   └── db/              # DuckDB数据库管理
├── factor/              # 因子模块（Phase 2）
│   ├── base.py          # 因子基类
│   ├── registry.py      # 因子注册表
│   ├── valuation.py     # 估值因子
│   ├── quality.py       # 质量因子
│   ├── growth.py        # 成长因子
│   ├── technical.py     # 技术因子
│   ├── scale.py         # 规模因子
│   ├── processor.py     # 因子计算引擎
│   └── neutralize.py    # 中性化处理
├── factor_test/         # 因子检验模块（Phase 2）
│   ├── ic_test.py       # IC分析
│   ├── layer_test.py    # 分层回测
│   ├── regression_test.py # 截面回归
│   ├── decay_test.py    # 衰减分析
│   ├── screening.py     # 因子筛选
│   └── report.py        # 检验报告汇总
├── strategy/            # 策略模块
├── backtest/            # 回测引擎
├── visual/              # 可视化
│   ├── dashboard.py     # 基础看板
│   ├── factor_dashboard.py  # 因子看板（Phase 2）
│   └── ic_heatmap.py    # IC热力图（Phase 2）
├── scripts/             # 运行脚本
└── tests/               # 测试
```