# Phase 1 开发计划 — 数据采集 + 存储 + 基础回测原型

> 目标：能拉数据、能存数据、能跑策略、能看结果。跑通了才算完成。

---

## 1. 项目结构

```
quant-system/
├── docker-compose.yml          # 统一部署
├── Dockerfile                   # Python运行环境
├── requirements.txt             # 依赖管理
├── config/
│   └── settings.yaml            # 全局配置（数据源、数据库连接等）
├── data/
│   ├── collector/               # 数据采集模块
│   │   ├── akshare_collector.py # A股行情采集
│   │   ├── fundamental.py       # 基础财务数据采集
│   │   └── scheduler.py         # 定时采集任务
│   │   └── cache/               # 本地缓存
│   └── db/
│       └── duckdb_manager.py    # DuckDB读写封装
├── strategy/
│   ├── base.py                  # 策略基类
│   ├── ma_cross.py              # 均线交叉策略
│   ├── momentum.py              # 动量策略
│   └── mean_revert.py           # 均值回归策略
├── backtest/
│   ├── engine.py                # 回测引擎（基于vectorbt）
│   ├── analyzer.py              # 回测分析（收益/夏普/最大回撤）
│   └── report.py                # 报告生成
├── visual/
│   ├── dashboard.py             # Dash/Plotly看板
│   └── charts.py                # 图表生成工具
├── scripts/
│   ├── run_collector.py         # 手动采集入口
│   ├── run_backtest.py          # 回测入口
│   └── run_dashboard.py         # 启动看板
└── tests/
    ├── test_collector.py
    ├── test_strategy.py
    └── test_backtest.py
```

---

## 2. 各模块详细设计

### 2.1 数据采集（data/collector）

| 功能 | 数据项 | 数据源 | 频率 |
|------|--------|--------|------|
| 日线行情 | 开高低收、成交量、换手率 | akshare `stock_zh_a_hist` | 每日收盘后 |
| 股票列表 | 代码、名称、行业、上市日期 | akshare `stock_zh_a_spot_em` | 每周 |
| 基础财务 | PE、PB、ROE、营收、净利润 | akshare `stock_financial_analysis_thi` | 每季 |
| 指数行情 | 沪深300、中证500等 | akshare `stock_zh_index_daily_em` | 每日 |

**采集策略**：
- 初次运行全量拉取（近5年日线 + 近3年财务）
- 后续增量更新，只拉缺失日期的数据
- 失败重试3次，记录异常日志
- 本地CSV缓存作为备份

### 2.2 数据存储（data/db）

- **存储引擎**：DuckDB（嵌入式，零运维，列存，时序查询快）
- **数据表设计**：
  - `daily_quote`：日线行情（code, date, open, high, low, close, volume, turnover）
  - `stock_info`：股票基本信息
  - `financial`：财务指标
  - `index_quote`：指数行情
- **索引**：(code, date) 复合主键，日期分区
- DuckDB文件存 Docker volume，持久化

### 2.3 策略模块（strategy）

策略基类统一接口：
```python
class BaseStrategy:
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """输入行情DataFrame，输出信号Series（1=买入，-1=卖出，0=持有）"""
        raise NotImplementedError

    def get_params(self) -> dict:
        """返回策略参数"""
        raise NotImplementedError
```

三个初始策略：
- **均线交叉**：MA5/MA20金叉死叉，经典趋势跟踪
- **动量策略**：过去N日涨幅排名，买前10%
- **均值回归**：偏离均值超过阈值时反向操作

### 2.4 回测引擎（backtest）

- 基于 vectorbt 实现（速度快，支持批量回测）
- 功能：
  - 单策略回测 + 参数网格搜索
  - 统计指标：年化收益、夏普比率、最大回撤、胜率、盈亏比
  - 输出报告（文本 + 图表）
- 初始资金100万，手续费0.1%，滑点0.05%

### 2.5 可视化看板（visual）

- Dash 搭建轻量 Web Dashboard
- 页面：
  - 数据概览：股票数量、数据覆盖日期范围
  - 回测结果：收益曲线、关键指标、信号分布图
  - 策略对比：多策略收益/风险对比表
- Docker内暴露端口，本机浏览器访问

---

## 3. Docker部署方案

```yaml
# docker-compose.yml
services:
  quant-app:
    build: .
    volumes:
      - ./data/db:/app/data/db      # DuckDB持久化
      - ./data/cache:/app/data/cache # CSV缓存
      - ./config:/app/config         # 配置文件
    ports:
      - "8050:8050"                   # Dashboard端口
    environment:
      - TZ=Asia/Shanghai
    command: python scripts/run_dashboard.py

  collector:
    build: .
    volumes: [同上]
    environment:
      - TZ=Asia/Shanghai
    # 每日18:00采集（cron或宿主机crontab触发）
```

---

## 4. 依赖清单

```
akshare>=1.12
duckdb>=0.9
pandas>=2.0
numpy>=1.24
vectorbt>=0.26
dash>=2.14
plotly>=5.18
pyyaml>=6.0
schedule>=1.2        # 定时任务
loguru>=0.7          # 日志
```

---

## 5. 开发顺序

| 步骤 | 内容 | 预估时间 | 产出 |
|------|------|----------|------|
| Step 1 | 项目骨架 + Dockerfile + 配置 | 1天 | 可运行的空项目 |
| Step 2 | 数据采集模块 + DuckDB存储 | 3天 | 能拉数据入库 |
| Step 3 | 策略基类 + 3个初始策略 | 2天 | 能生成信号 |
| Step 4 | 回测引擎 + 分析报告 | 2天 | 能跑回测看结果 |
| Step 5 | Dashboard可视化 | 2天 | 能在浏览器看图表 |
| Step 6 | 集成测试 + 文档 | 1天 | 完整可演示原型 |

**总预估：约10个工作日**

---

## 6. 验收标准

Phase 1 完成标志：
1. ✅ docker-compose up 一键启动
2. ✅ 手动触发数据采集，DuckDB中有5年A股日线数据
3. ✅ 三个策略都能跑回测，输出年化收益/夏普/最大回撤
4. ✅ Dashboard能展示回测结果图表
5. ✅ 有基本测试覆盖，代码能跑不报错

---

确认后我立刻开工。有要调整的现在说。