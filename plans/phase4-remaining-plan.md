# Phase 4 剩余功能开发计划

> 开始日期: 2026-06-09
> 预计完成: 2026-06-15
> 总计任务: 6个模块
> 预估工作量: 5-6天

---

## 📋 开发顺序与优先级

```
Day 1: 告警推送增强（企业微信+邮件）
Day 2: PnL盈亏计算引擎
Day 3: 定时任务调度器
Day 4: 数据增量更新
Day 5: 统一门户Dashboard
Day 6: easytrader实盘接口（可选）
```

---

## 🔴 Task 1: 告警推送增强（0.5天）

### 目标
支持企业微信、邮件双通道告警推送

### 文件清单
- 修改: `risk/alert.py`
- 新增: `config/alarm.yaml`
- 修改: `config/settings.yaml`
- 新增: `tests/test_alert.py`

### 详细实现步骤

#### Step 1.1: 扩展 AlertChannel 基类
```python
class AlertChannel:
    def send(self, level: str, title: str, message: str, context: dict = None):
        """发送告警
        Args:
            level: info/warning/block/error
            title: 告警标题
            message: 告警详情
            context: 额外上下文信息（代码、仓位等）
        """
```

#### Step 1.2: 企业微信 Webhook 实现
```python
class WeChatWorkAlert(AlertChannel):
    """企业微信告警"""
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, level, title, message, context=None):
        # 调用企业微信机器人API
        # markdown格式消息
        # 不同级别用不同颜色
```

#### Step 1.3: 邮件 SMTP 实现
```python
class EmailAlert(AlertChannel):
    """邮件告警"""
    def __init__(self, smtp_config: dict):
        self.smtp_config = smtp_config
    
    def send(self, level, title, message, context=None):
        # smtplib发送邮件
        # HTML格式模板
```

#### Step 1.4: 告警配置文件 `config/alarm.yaml`
```yaml
alert:
  enabled: true
  channels:
    console:
      enabled: true
    wechat_work:
      enabled: false
      webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
    email:
      enabled: false
      smtp_host: "smtp.xxx.com"
      smtp_port: 587
      username: "xxx"
      password: "xxx"
      to: ["xxx@xxx.com"]
  
  rules:
    stop_loss: true          # 止损触发
    risk_block: true         # 风控拦截
    order_filled: false      # 订单成交（低噪点）
    daily_report: true       # 每日持仓报告
```

#### Step 1.5: 告警聚合与防骚扰
- 1分钟内相同告警只发1次
- 每日收盘后汇总发送持仓报告
- 交易时段才推送告警

### 验收标准
- [ ] 企业微信告警可正常推送
- [ ] 邮件告警可正常发送
- [ ] 告警级别颜色区分
- [ ] 告警防骚扰机制生效
- [ ] 5个单元测试通过

---

## 🔴 Task 2: PnL盈亏计算引擎（1天）

### 目标
计算真实盈亏、持仓浮盈、组合收益率、风险指标

### 文件清单
- 新增: `executor/pnl_calc.py`
- 修改: `executor/trade_log.py`
- 修改: `visual/trading_dashboard.py`
- 新增: `tests/test_pnl.py`

### 详细实现步骤

#### Step 2.1: PnLCalculator 类
```python
class PnLCalculator:
    def __init__(self, db: DuckDBManager):
        self.db = db
    
    def calculate_trade_pnl(self, trade_id: str) -> dict:
        """计算单笔交易盈亏"""
        # 买入总成本 vs 卖出总收入
    
    def calculate_position_pnl(self, code: str, date: str) -> dict:
        """计算单只持仓浮盈浮亏"""
        # 成本价 vs 现价
        # 绝对盈亏 + 百分比
    
    def calculate_portfolio_pnl(self, date: str) -> dict:
        """计算组合整体盈亏"""
        # 总市值 vs 总成本
        # 累计收益率
        # 当日盈亏
```

#### Step 2.2: 风险指标计算
```python
def calculate_metrics(self, start_date: str, end_date: str) -> dict:
    """计算组合风险指标"""
    return {
        "total_return": 0.0,      # 累计收益率
        "annual_return": 0.0,     # 年化收益率
        "max_drawdown": 0.0,      # 最大回撤
        "sharpe_ratio": 0.0,      # 夏普比率
        "win_rate": 0.0,          # 胜率
        "profit_loss_ratio": 0.0, # 盈亏比
    }
```

#### Step 2.3: 扩展 Dashboard PnL展示
- 新增"收益分析"Tab
- 累计收益曲线图
- 月度收益热力图
- 风险指标卡片

#### Step 2.4: 每日持仓报告
- 收盘后自动计算所有持仓PnL
- 生成markdown格式报告
- 通过告警通道推送

### 验收标准
- [ ] 单笔交易盈亏计算准确
- [ ] 持仓浮盈浮亏计算准确
- [ ] 组合收益率、夏普、最大回撤指标正确
- [ ] Dashboard新增PnL分析板块
- [ ] 8个单元测试通过

---

## 🔴 Task 3: 定时任务调度器（1天）

### 目标
APScheduler实现自动化任务调度

### 文件清单
- 新增: `scheduler/task_scheduler.py`
- 新增: `scheduler/tasks.py`
- 修改: `config/settings.yaml`
- 新增: `scripts/run_scheduler.py`
- 新增: `tests/test_scheduler.py`

### 详细实现步骤

#### Step 3.1: TaskScheduler 核心类
```python
class TaskScheduler:
    def __init__(self, config: dict):
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self.config = config
    
    def add_daily_task(self, func, hour: int, minute: int):
        """添加每日任务"""
    
    def add_monthly_task(self, func, day: int, hour: int):
        """添加月度任务（调仓日）"""
    
    def start(self):
        """启动调度器"""
    
    def shutdown(self):
        """关闭调度器"""
```

#### Step 3.2: 任务定义 `tasks.py`
```python
def daily_data_collection():
    """每日18:00 数据采集"""
    # 调用采集器获取最新日线数据

def daily_factor_calc():
    """每日19:00 因子重算"""
    # 计算当日所有因子

def daily_ml_predict():
    """每日20:00 ML预测"""
    # 生成最新信号

def monthly_rebalance():
    """每月最后一个交易日 调仓执行"""
    # 运行Rebalancer

def daily_report():
    """每日18:30 持仓报告推送"""
    # 计算PnL + 推送告警
```

#### Step 3.3: 调度配置
```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  
  tasks:
    data_collection:
      cron: "0 18 * * 1-5"  # 周一到周五18:00
      enabled: true
    
    factor_calc:
      cron: "0 19 * * 1-5"
      enabled: true
    
    ml_predict:
      cron: "0 20 * * 1-5"
      enabled: true
    
    rebalance:
      cron: "0 14 L * *"    # 每月最后一天14:00
      enabled: false
    
    daily_report:
      cron: "30 18 * * 1-5"
      enabled: true
```

#### Step 3.4: 任务执行日志
- 记录每次任务开始/结束时间
- 记录执行状态（成功/失败）
- 失败自动重试（最多3次）
- Dashboard展示任务执行状态

### 验收标准
- [ ] 定时任务可按cron执行
- [ ] 数据采集任务正常运行
- [ ] 因子计算任务正常运行
- [ ] 任务失败自动重试
- [ ] 任务执行日志可在Dashboard查看
- [ ] 6个单元测试通过

---

## 🟡 Task 4: 数据增量更新（0.5天）

### 目标
只采集和计算缺失日期的数据，避免全量重算

### 文件清单
- 修改: `data/collector/base_collector.py`
- 修改: `factor/processor.py`
- 新增: `data/db/data_status.py`
- 修改: `scripts/run_collector.py`

### 详细实现步骤

#### Step 4.1: 数据状态追踪表
```sql
CREATE TABLE data_collection_status (
    table_name VARCHAR PRIMARY KEY,
    last_date DATE,
    last_updated TIMESTAMP,
    record_count INTEGER,
    status VARCHAR  -- complete/incremental/failed
)
```

#### Step 4.2: 增量采集逻辑
```python
def get_missing_dates(self, start_date: str, end_date: str) -> List[str]:
    """获取缺失的交易日期列表"""
    # 查询数据库已有的日期范围
    # 返回需要补充的日期列表

def incremental_collect(self, code_list: List[str]):
    """增量采集"""
    # 只采集缺失日期的数据
    # 不覆盖已有数据
```

#### Step 4.3: 增量因子计算
- 只计算新增日期的因子
- 保留历史因子值不变

### 验收标准
- [ ] 自动识别缺失数据日期
- [ ] 增量采集不影响历史数据
- [ ] 增量因子计算正确
- [ ] 数据采集状态可查询
- [ ] 4个单元测试通过

---

## 🟡 Task 5: 统一门户Dashboard（1天）

### 目标
整合4个Dashboard，提供统一入口和导航

### 文件清单
- 新增: `visual/portal.py`
- 修改: `visual/dashboard.py`（重构为子app）
- 修改: `visual/factor_dashboard.py`
- 修改: `visual/ml_dashboard.py`
- 修改: `visual/trading_dashboard.py`

### 详细实现步骤

#### Step 5.1: Dash 多页面架构
```
/               # 首页概览
/strategy       # 策略回测
/factor         # 因子分析
/ml             # ML模型
/trading        # 交易风控
```

#### Step 5.2: 顶部导航栏
- Logo + 项目名称
- 4个模块导航按钮
- 当前页面高亮

#### Step 5.3: 首页概览
- 4个模块状态卡片
- 最新因子IC值
- 最新ML预测信号数
- 当前持仓数
- 快捷操作按钮

#### Step 5.4: 多端口合并
- 统一端口 8050
- 移除其他独立启动脚本
- 统一配置管理

### 验收标准
- [ ] 统一入口正常访问
- [ ] 页面切换不刷新
- [ ] 4个子功能全部正常
- [ ] 首页概览数据正确
- [ ] 响应式布局适配

---

## 🟡 Task 6: easytrader实盘接口（1天，可选）

### 目标
对接同花顺实现真实下单

### 文件清单
- 新增: `executor/broker/easytrader_broker.py`
- 修改: `config/settings.yaml`
- 新增: `scripts/run_real_trading.py`

### 详细实现步骤

#### Step 6.1: EasyTraderBroker 实现
```python
class EasyTraderBroker(BaseBroker):
    def __init__(self, config: dict):
        self.client = easytrader.use('ths')
        self.client.connect(config['client_path'])
    
    def buy(self, code: str, shares: int, price: float) -> str:
        """真实买入"""
        result = self.client.buy(code, price, shares)
        return result['entrust_no']
    
    def sell(self, code: str, shares: int, price: float) -> str:
        """真实卖出"""
    
    def query_positions(self) -> pd.DataFrame:
        """查询真实持仓"""
    
    def query_order_status(self, order_id: str) -> str:
        """查询订单状态"""
```

#### Step 6.2: 实盘安全开关
- 配置文件切换模拟/实盘
- 实盘模式下单前二次确认
- 最大单笔下单金额限制
- 每日最大亏损熔断

#### Step 6.3: 实盘与模拟盘对比
- 同时运行模拟盘和实盘
- Dashboard展示两者收益偏差
- 实盘vs模拟偏差分析

### 验收标准
- [ ] 同花顺客户端可正常连接
- [ ] 买入/卖出下单成功
- [ ] 持仓查询正确
- [ ] 实盘安全限制生效
- [ ] 模拟/实盘对比展示正常

---

## 📊 总体验收清单

| Task | 预估测试数 | 验收状态 |
|------|-----------|---------|
| Task 1: 告警推送 | 5 | ⏳ |
| Task 2: PnL计算 | 8 | ⏳ |
| Task 3: 定时调度 | 6 | ⏳ |
| Task 4: 增量更新 | 4 | ⏳ |
| Task 5: 统一门户 | 3 | ⏳ |
| Task 6: 实盘接口 | 5 | ⏳ |
| **总计** | **31** | |

---

## 🚀 开发顺序建议

### 第一优先级（必选）
1. Task 1 告警推送 → 实盘必备监控
2. Task 2 PnL计算 → 评估策略真实表现
3. Task 3 定时调度 → 实现完全自动化

### 第二优先级（推荐）
4. Task 4 增量更新 → 大幅提升运行效率
5. Task 5 统一门户 → 产品化体验

### 第三优先级（可选）
6. Task 6 实盘接口 → 需要Windows环境
