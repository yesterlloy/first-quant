# 风控子系统设计规范

> Phase 4 第二阶段：事前检查 + 实时监控 + 止损执行 + 告警

---

## 1. 概述

### 1.1 风控层级

```
事前风控 → 订单生成前检查 → 拦截不合规订单
事中风控 → 实时监控指标 → 触发告警/暂停交易
事后风控 → 每日收盘检查 → 止损执行/调仓建议
```

### 1.2 风控规则清单

| 层级 | 规则 | 说明 | 动作 |
|------|------|------|------|
| **个股** | 单票仓位上限 | 默认10% | 拦截 |
| | 单票最大亏损 | -5%硬止损 | 强制卖出 |
| | 停牌股过滤 | 自动剔除 | 拦截 |
| **组合** | 总仓位上限 | 默认80% | 调整仓位 |
| | 行业集中度 | 单行业≤30% | 分散/拦截 |
| | 最大回撤阈值 | -10%减仓 | 强制降仓 |
| | 日波动上限 | 单日回撤>3% | 告警 |
| **系统** | 信号有效性 | IC<0时暂停 | 暂停交易 |
| | 数据完整性 | 缺数据不下单 | 拦截 |
| | 下单异常 | 连续失败暂停 | 暂停+告警 |

---

## 2. 模块设计

### 2.1 risk_rules.py - 规则定义

```python
class RiskRule:
    def check(self, context: dict) -> RuleResult:
        pass

class SinglePositionLimit(RiskRule):
    """单票仓位上限"""

class IndustryConcentration(RiskRule):
    """行业集中度检查"""

class MaxDrawdownLimit(RiskRule):
    """最大回撤检查"""

class StopLossRule(RiskRule):
    """个股止损规则"""

class RuleResult:
    passed: bool
    level: str  # info / warning / block
    message: str
```

### 2.2 risk_checker.py - 事前风控

```python
class RiskChecker:
    def __init__(self, db, rules: list[RiskRule]):
        self.rules = rules
    
    def check_order(self, order: pd.Series, positions: pd.DataFrame) -> list[RuleResult]:
        """检查单个订单"""
    
    def check_portfolio(self, target_portfolio: pd.DataFrame) -> list[RuleResult]:
        """检查整个组合"""
    
    def filter_blocked_orders(self, orders: pd.DataFrame, positions: pd.DataFrame) -> tuple:
        """过滤被拦截的订单，返回(通过的, 被拦截的)"""
```

### 2.3 stop_loss.py - 止损执行

```python
class StopLossExecutor:
    def __init__(self, db, broker):
        self.db = db
        self.broker = broker
    
    def check_and_execute(self, date: str) -> list:
        """检查所有持仓，执行止损"""
    
    def calculate_pnl(self, code: str, cost_price: float, current_price: float) -> float:
        """计算单票盈亏率"""
```

### 2.4 alert.py - 告警推送

```python
class AlertChannel:
    def send(self, level: str, title: str, message: str):
        pass

class ConsoleAlert(AlertChannel):
    """控制台输出"""

class FileAlert(AlertChannel):
    """日志文件记录"""
```

---

## 3. 数据库设计

新增1张表：
```sql
-- 风控事件日志
CREATE TABLE risk_event_log (
    event_id VARCHAR PRIMARY KEY,
    date DATE,
    level VARCHAR,           -- info / warning / block
    rule_name VARCHAR,       -- 触发的规则名
    code VARCHAR,            -- 关联股票（可选）
    message VARCHAR,         -- 详细信息
    created_at TIMESTAMP
);
```

---

## 4. 测试策略

| 测试类 | 测试内容 |
|--------|----------|
| TestSinglePositionLimit | 单票仓位上限拦截 |
| TestIndustryConcentration | 行业集中度检查 |
| TestStopLoss | 止损触发与执行 |
| TestRiskChecker | 风控检查集成 |
| TestAlert | 告警推送 |

**预计测试数：10个**
