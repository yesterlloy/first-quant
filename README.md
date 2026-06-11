# 量化投研平台 A Quantitative Research Platform

一个功能完整的A股量化投研系统，包含数据采集、因子分析、机器学习、回测引擎、实盘交易全流程。

## ✨ 功能特性

| 模块 | 功能 | 状态 |
|------|------|------|
| 📊 **数据采集** | 多数据源(akshare/baostock/adata)、自动调度、增量更新 | ✅ |
| 🧪 **因子引擎** | 5大类20+因子、IC分析、分层回测、衰减分析 | ✅ |
| 🤖 **ML模型** | LightGBM/XGBoost、滚动训练、特征工程、模型融合 | ✅ |
| 📈 **回测引擎** | vectorbt高性能回测、多策略对比、指标分析 | ✅ |
| 💼 **交易执行** | 模拟券商、实盘对接(easytrader)、订单管理、仓位计算 | ✅ |
| 🛡️ **风控系统** | 事前检查、止损执行、实时监控、多级告警 | ✅ |
| 💰 **盈亏计算** | 实时PnL、净值曲线、回撤分析、夏普比率 | ✅ |
| ⏰ **定时调度** | APScheduler任务调度、自动备份、重试机制 | ✅ |
| 🖥️ **可视化看板** | 5个Dash应用、统一门户、图表交互 | ✅ |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        统一门户 Dashboard (8055)                      │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────────┤
│ 策略回测  │ 因子分析  │ ML模型   │ 实盘监控  │ 调度器   │   数据库    │
│ (8050)   │ (8051)   │ (8052)  │ (8053)  │          │  DuckDB    │
└──────────┴──────────┴──────────┴──────────┴──────────┴─────────────┘
```

---

## 🚀 快速开始

### 方式1：Docker一键启动（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd quant-system

# 启动所有服务
docker compose up -d

# 访问统一门户
open http://localhost:8055
```

### 方式2：本地开发启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动统一门户（包含所有看板）
python scripts/run_all_dashboards.py

# 3. 另开终端启动调度器
python scripts/run_scheduler.py start
```

---

## 📊 五大功能看板

| 看板 | 端口 | 功能 |
|------|------|------|
| **统一门户** | 8055 | 主入口，系统概览，快速导航 |
| 策略回测 | 8050 | MA交叉、动量、均值回归策略回测与分析 |
| 因子分析 | 8051 | 因子IC分析、分层回测、衰减分析、筛选 |
| ML模型 | 8052 | 模型训练、特征重要性、预测评估、参数优化 |
| 实盘监控 | 8053 | 持仓、盈亏、风控、交易记录、告警中心 |

---

## ⏰ 定时任务调度

系统已配置自动运行的任务：

| 任务 | 执行时间 | 说明 |
|------|---------|------|
| 数据采集 | 工作日 18:00 | 自动采集A股日线行情 |
| 因子计算 | 工作日 19:00 | 计算所有因子值 |
| 持仓日报 | 工作日 18:30 | 生成盈亏报告推送 |
| 数据库备份 | 每日 23:00 | 自动备份数据库（保留30天） |

### 常用命令

```bash
# 启动调度器
python scripts/run_scheduler.py start

# 手动触发任务
python scripts/run_scheduler.py trigger data_collection
python scripts/run_scheduler.py trigger factor_compute
python scripts/run_scheduler.py trigger db_backup

# 查看任务执行状态
python scripts/run_scheduler.py status
```

---

## 💹 模拟交易完整流程

### 步骤1：运行模拟交易

```bash
python scripts/run_sim_trading.py --date 20240611
```

**交易流程：**
```
1. ML模型预测信号
   ↓
2. 投资组合构建（风险平价/等权）
   ↓
3. 仓位计算（单票上限15%）
   ↓
4. 事前风控检查（止损/止盈/集中度）
   ↓
5. 订单生成与模拟撮合
   ↓
6. 交易日志记录
   ↓
7. 更新持仓与PnL计算
```

### 步骤2：查看交易结果

访问 **http://localhost:8053** 查看：
- 当前持仓列表与浮盈浮亏
- 历史成交记录
- 净值曲线与回撤分析
- 风控事件日志

---

## 🔧 配置说明

### 主要配置文件

| 文件 | 说明 |
|------|------|
| `config/settings.yaml` | 系统主配置（数据库路径、端口等） |
| `config/scheduler.yaml` | 调度器配置（任务cron、超时、重试） |
| `config/alarm.yaml` | 告警配置（企业微信、邮件、控制台） |
| `config/broker.yaml` | 券商配置（实盘/模拟切换） |

### 告警配置示例

```yaml
# config/alarm.yaml
channels:
  console:
    enabled: true  # 控制台输出
  
  wechat_work:
    enabled: false
    webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
  
  email:
    enabled: false
    smtp_host: "smtp.qq.com"
    smtp_port: 587
    username: "xxx@qq.com"
    password: "xxx"
    to_addrs: ["xxx@xxx.com"]
```

### 实盘交易配置

```yaml
# config/broker.yaml
broker:
  # 切换为easytrader即可开启实盘
  type: "simulator"  # 模拟模式 / easytrader 实盘模式
  broker_subtype: "ths"  # 东方财富 / ht华泰
  
  trading:
    max_order_amount: 100000      # 单笔最大金额
    max_positions: 20             # 最大持仓数
    max_position_ratio: 0.15      # 单只最大仓位15%
```

---

## 📈 内置因子库

| 类别 | 因子 |
|------|------|
| **估值因子** | PE、PB、PS、PCF、EV/EBITDA |
| **质量因子** | ROE、ROA、ROIC、毛利率、净利率、资产周转率 |
| **成长因子** | 营收增长率、净利润增长率、营收同比、净利润同比 |
| **技术因子** | 动量(MOM)、RSI、MACD、波动率、换手率、振幅 |
| **规模因子** | 市值、流通市值、对数市值 |

---

## 🤖 ML模型支持

| 模型 | 说明 | 推荐场景 |
|------|------|---------|
| **LightGBM** | 默认，速度快效果好 | 日常使用 |
| **XGBoost** | 精度略高，训练较慢 | 精度优先 |
| **Ridge/Lasso** | 线性基准模型 | 对比基线 |
| **Ensemble** | 多模型等权/IC加权融合 | 实盘使用 |

---

## 🐳 Docker运维命令

```bash
# 查看服务状态
docker compose ps

# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f dashboard
docker compose logs -f scheduler

# 进入容器
docker compose exec dashboard bash

# 重启服务
docker compose restart

# 停止所有服务
docker compose down

# 重新构建镜像
docker compose build --no-cache
```

---

## 💾 数据库备份管理

```bash
# 手动备份
python -m utils.db_backup backup

# 查看备份列表
python -m utils.db_backup list

# 恢复备份
python -m utils.db_backup restore backup_filename.duckdb.gz

# 清理旧备份（保留最近30天）
python -m utils.db_backup clean
```

---

## 🔍 常见问题排查

### Q1: Docker启动后访问不了
```bash
# 检查端口是否监听
lsof -i :8055

# 查看容器日志
docker compose logs dashboard
```

### Q2: Scheduler不执行任务
```bash
# 查看调度器日志
docker compose logs scheduler

# 检查时区
docker compose exec scheduler date
```

### Q3: 数据不更新
```python
from data.db.duckdb_manager import DuckDBManager
db = DuckDBManager()
db.connect()
print(db.query('SELECT MAX(date) FROM daily_quote'))
db.close()
```

### Q4: 告警不发送
```python
from risk import AlertManager
am = AlertManager.from_config('config/alarm.yaml')
am.info('测试', '这是一条测试消息')
```

---

## 📁 项目目录结构

```
quant-system/
├── data/                    # 数据模块
│   ├── collector/           # 数据采集器
│   └── db/                 # 数据库管理
├── factor/                  # 因子模块
│   ├── processor.py         # 因子计算
│   ├── valuation.py         # 估值因子
│   ├── quality.py           # 质量因子
│   └── ...
├── ml/                      # 机器学习模块
│   ├── feature_engine.py    # 特征工程
│   ├── trainer.py           # 模型训练
│   └── models/              # 模型定义
├── executor/                # 交易执行模块
│   ├── portfolio_builder.py # 组合构建
│   ├── position_calc.py     # 仓位计算
│   ├── order_manager.py     # 订单管理
│   ├── pnl_calc.py          # 盈亏计算
│   └── broker/              # 券商接口
├── risk/                    # 风控模块
│   ├── rules.py             # 风控规则
│   ├── checker.py           # 事前检查
│   ├── stop_loss.py         # 止损执行
│   └── alert.py             # 告警管理
├── scheduler/               # 定时调度模块
│   ├── engine.py            # 调度核心
│   ├── task_wrapper.py      # 任务包装
│   ├── tasks.py             # 具体任务
│   └── dependency.py        # 任务依赖
├── visual/                  # 可视化看板
│   ├── dashboard.py         # 基础策略看板
│   ├── factor_dashboard.py  # 因子分析看板
│   ├── ml_dashboard.py      # ML模型看板
│   ├── trading_dashboard.py # 实盘监控看板
│   └── portal_dashboard.py  # 统一门户
├── scripts/                 # 脚本目录
│   ├── run_all_dashboards.py # 启动所有看板
│   ├── run_scheduler.py     # 调度器脚本
│   ├── run_sim_trading.py   # 模拟交易脚本
│   └── ...
├── utils/                   # 工具类
│   └── db_backup.py         # 数据库备份工具
├── config/                  # 配置文件
│   ├── settings.yaml        # 系统配置
│   ├── scheduler.yaml       # 调度配置
│   ├── alarm.yaml           # 告警配置
│   └── broker.yaml.example  # 券商配置示例
├── tests/                   # 测试用例
├── requirements.txt         # Python依赖
├── Dockerfile              # Docker构建文件
├── docker-compose.yml      # Docker编排文件
└── README.md              # 本文档
```

---

## ⚠️ 风险提示

1. **先模拟后实盘**：实盘交易前请在模拟模式运行至少1个月验证策略有效性
2. **小资金测试**：实盘初期投入建议<总资金10%
3. **风控第一**：务必开启止损，设置单日最大亏损保护
4. **持续监控**：密切关注告警通知，异常情况及时处理
5. **历史不代表未来**：量化策略有风险，回测收益不代表实盘表现

---

## 🎯 使用建议

### 日常流程
1. **18:10** 系统自动采集当日数据
2. **18:30** 查看持仓日报推送
3. **19:00** 系统自动计算因子
4. **20:00** 查看Dashboard，检查模型信号

### 每周
1. 检查策略表现（收益、回撤、夏普比率）
2. 查看因子IC变化，因子有效性监控
3. 调整仓位（必要时）

### 每月
1. 月度调仓（如果启用月度任务）
2. 复盘当月交易
3. 重新训练ML模型
4. 检查备份完整性

---

## 📝 开发计划完成情况

- ✅ Phase 1: 数据采集 + 存储 + 基础回测
- ✅ Phase 2: 因子系统 + 因子检验
- ✅ Phase 3: ML增强 + 因子合成
- ✅ Phase 4: 实盘对接 + 风控监控 + 调度器

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

MIT License

---

**祝您投资顺利！ 📈💰**
