# 交易执行子系统设计规范

> Phase 4 第一阶段：模拟盘引擎 + 订单管理 + 仓位计算

---

## 1. 概述

### 1.1 目标

开发交易执行子系统，实现从ML信号到虚拟/实盘下单的完整链路：

```
信号加载 → 组合构建 → 仓位计算 → 订单生成 → 执行 → 记录
```

### 1.2 关键决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 券商接口 | easytrader | 通用方案，免费，后续对接 |
| 调仓频率 | 月度调仓 | 符合ML滚动训练节奏 |
| 仓位方法 | 信号强度加权 | 简单实用，直接关联预测 |
| 持仓数量 | 10只左右 | 平衡分散度和管理成本 |
| 模拟盘 | 纯虚拟模拟 | 快速验证全链路 |

### 1.3 范围

**包含：**
- executor/ 模块（信号加载、组合构建、仓位计算、订单管理、模拟盘）
- broker/ 子模块（模拟Broker、easytrader接口）
- trade_log 模块（订单/成交/持仓记录入库）
- 配置文件（executor.yaml、broker.yaml）
- 单元测试（test_executor.py）

**不包含：**
- 风控体系（Phase 4 第二阶段）
- 监控报警（Phase 4 第三阶段）
- 运维体系（Phase 4 第四阶段）

---

## 2. 项目结构

```
quant-system/
├── executor/
│   ├── __init__.py
│   ├── signal_loader.py      # 从DB加载ML信号
│   ├── portfolio_builder.py  # 组合构建（筛选Top N）
│   ├── position_calc.py      # 仓位计算（信号强度加权）
│   ├── order_manager.py      # 订单管理（生成/跟踪/状态）
│   ├── simulator.py          # 模拟盘引擎（纯虚拟）
│   ├── broker/
│   │   ├── __init__.py
│   │   ├── base.py           # Broker基类
│   │   ├── easytrader.py     # easytrader接口
│   │   └── simulator.py      # 模拟Broker
│   ├── trade_log.py          # 交易记录（入库）
│   └── rebalance.py          # 调仓主流程编排
├── config/
│   ├── executor.yaml         # 执行参数配置
│   └── broker.yaml           # 券商接口配置（账号/路径）
├── scripts/
│   ├── run_simulator.py      # 启动模拟盘
│   └── run_rebalance.py      # 实盘调仓执行
└── tests/
    └── test_executor.py      # 执行模块测试
```

---

## 3. 模块设计

### 3.1 signal_loader.py

**职责：** 从 ml_signal 表加载最新预测信号

**核心接口：**

```python
class SignalLoader:
    def __init__(self, db: DuckDBManager):
        self.db = db

    def load_signals(self, date: str, model_name: str = "lgbm_v1") -> pd.DataFrame:
        """加载指定日期的ML信号

        Args:
            date: 调仓日期 (YYYY-MM-DD)
            model_name: 模型版本名

        Returns:
            DataFrame: [code, date, predicted_return, signal]
        """
```

**实现逻辑：**
1. 查询 ml_signal 表，筛选 date 和 model_name
2. 返回 code、predicted_return、signal 列
3. 空信号返回空DataFrame，不抛异常

---

### 3.2 portfolio_builder.py

**职责：** 筛选Top N股票构建组合

**核心接口：**

```python
class PortfolioBuilder:
    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    def build_portfolio(self, signals: pd.DataFrame) -> pd.DataFrame:
        """构建目标组合

        Args:
            signals: [code, predicted_return, signal]

        Returns:
            DataFrame: [code, predicted_return, rank]
        """
```

**实现逻辑：**
1. 按 predicted_return 降序排序
2. 选取 Top N（默认10）
3. 返回组合列表

---

### 3.3 position_calc.py

**职责：** 信号强度加权分配仓位

**核心接口：**

```python
class PositionCalculator:
    def __init__(self, total_ratio: float = 0.8, max_single: float = 0.1):
        self.total_ratio = total_ratio   # 总仓位80%
        self.max_single = max_single     # 单票上限10%

    def calc_weights(self, portfolio: pd.DataFrame, prices: pd.DataFrame,
                     total_capital: float) -> pd.DataFrame:
        """计算目标仓位

        Args:
            portfolio: [code, predicted_return]
            prices: [code, close_price]
            total_capital: 总资金

        Returns:
            DataFrame: [code, weight, shares, amount]
        """
```

**实现逻辑：**
1. 信号强度加权：`weight_i = abs(predicted_return_i) / sum(abs(predicted_return))`
2. 单票上限检查：若 weight > max_single，截断为 max_single，剩余分配给其他票
3. 计算股数：`shares = (total_capital * weight * total_ratio) / price`，向下取整100股
4. 返回目标持仓

---

### 3.4 order_manager.py

**职责：** 订单生成、跟踪状态、管理生命周期

**核心接口：**

```python
class OrderManager:
    def __init__(self, db: DuckDBManager, price_offset: float = 0.02):
        self.db = db
        self.price_offset = price_offset  # 限价偏移±2%

    def generate_orders(self, target_positions: pd.DataFrame,
                        current_positions: pd.DataFrame) -> pd.DataFrame:
        """生成调仓订单

        Args:
            target_positions: [code, shares, weight]
            current_positions: [code, shares] 或空DataFrame

        Returns:
            DataFrame: [order_id, code, action, shares, price, status]
        """

    def update_status(self, order_id: str, status: str):
        """更新订单状态"""

    def get_pending_orders(self) -> pd.DataFrame:
        """获取待执行订单"""
```

**订单生成逻辑：**

| 情况 | 动作 | 计算方式 |
|------|------|----------|
| 新票 | buy | shares = target_shares |
| 加仓 | buy | shares = target - current |
| 减仓 | sell | shares = current - target |
| 清仓 | sell | shares = current |

**限价计算：**
- buy: price = close_price * (1 + price_offset)
- sell: price = close_price * (1 - price_offset)

---

### 3.5 broker/base.py

**职责：** Broker抽象基类，定义统一接口

**核心接口：**

```python
class BaseBroker:
    def connect(self) -> bool:
        """连接券商/模拟系统"""

    def disconnect(self):
        """断开连接"""

    def buy(self, code: str, shares: int, price: float) -> str:
        """买入下单，返回order_id"""

    def sell(self, code: str, shares: int, price: float) -> str:
        """卖出下单，返回order_id"""

    def query_positions(self) -> pd.DataFrame:
        """查询当前持仓"""

    def query_order_status(self, order_id: str) -> str:
        """查询订单状态"""
```

---

### 3.6 broker/simulator.py

**职责：** 模拟Broker实现，虚拟成交

**实现逻辑：**
- connect/disconnect: 无实际操作
- buy/sell: 立即返回成功，生成虚拟order_id
- query_positions: 从 position_log 表查询
- query_order_status: 假设全部 filled

---

### 3.7 broker/easytrader.py

**职责：** easytrader实盘接口

**实现逻辑：**
- connect: 启动easytrader客户端
- buy/sell: 调用easytrader API下单
- query_positions: 获取真实持仓
- query_order_status: 查询券商订单状态

**依赖：**
- easytrader库
- 同花顺/通达信客户端

---

### 3.8 trade_log.py

**职责：** 记录订单、成交、持仓到DB

**核心接口：**

```python
class TradeLogger:
    def __init__(self, db: DuckDBManager):
        self.db = db

    def log_orders(self, orders: pd.DataFrame):
        """记录订单到 order_log 表"""

    def log_trades(self, trades: pd.DataFrame):
        """记录成交到 trade_log 表"""

    def log_positions(self, positions: pd.DataFrame, date: str):
        """记录持仓快照到 position_log 表"""

    def get_latest_positions(self) -> pd.DataFrame:
        """获取最新持仓"""
```

---

### 3.9 rebalance.py

**职责：** 编排调仓主流程

**核心接口：**

```python
class Rebalancer:
    def __init__(self, db: DuckDBManager, broker: BaseBroker, config: dict):
        self.db = db
        self.broker = broker
        self.config = config

    def run(self, date: str, model_name: str = "lgbm_v1"):
        """执行月度调仓全流程

        流程:
        1. 加载信号
        2. 构建组合
        3. 计算仓位
        4. 生成订单
        5. 执行订单
        6. 记录交易
        """
```

**流程编排：**
```python
def run(self, date, model_name):
    # 1. 加载信号
    signals = self.signal_loader.load_signals(date, model_name)
    if signals.empty:
        logger.warning("No signals, skip rebalance")
        return

    # 2. 构建组合
    portfolio = self.portfolio_builder.build_portfolio(signals)

    # 3. 获取价格
    prices = self.db.get_prices(date, portfolio["code"].tolist())

    # 4. 计算仓位
    positions = self.position_calc.calc_weights(portfolio, prices, self.total_capital)

    # 5. 获取当前持仓
    current = self.broker.query_positions()

    # 6. 生成订单
    orders = self.order_manager.generate_orders(positions, current)

    # 7. 执行订单
    trades = self.broker.execute_orders(orders)

    # 8. 记录交易
    self.trade_log.log_orders(orders)
    self.trade_log.log_trades(trades)
    self.trade_log.log_positions(positions, date)

    logger.info(f"Rebalance complete: {len(trades)} trades")
```

---

## 4. 数据库设计

新增3张表：

```sql
-- 订单记录
CREATE TABLE order_log (
    order_id VARCHAR PRIMARY KEY,
    date DATE,
    code VARCHAR,
    action VARCHAR,            -- buy/sell
    shares INTEGER,
    price DOUBLE,              -- 目标价格
    status VARCHAR,            -- pending/filled/cancelled
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 成交记录
CREATE TABLE trade_log (
    trade_id VARCHAR PRIMARY KEY,
    order_id VARCHAR,
    date DATE,
    code VARCHAR,
    action VARCHAR,
    shares INTEGER,
    price DOUBLE,              -- 实际成交价
    filled_at TIMESTAMP
);

-- 持仓快照（每日）
CREATE TABLE position_log (
    date DATE,
    code VARCHAR,
    shares INTEGER,
    weight DOUBLE,
    cost_price DOUBLE,
    current_price DOUBLE,
    market_value DOUBLE,
    PRIMARY KEY (date, code)
);
```

---

## 5. 配置设计

### executor.yaml

```yaml
rebalance:
  frequency: monthly
  top_n: 10
  total_position_ratio: 0.8
  max_single_position: 0.1

broker:
  type: simulator          # simulator / easytrader

order:
  price_offset: 0.02       # 限价偏移±2%
  timeout_seconds: 60      # 订单超时
```

### broker.yaml

```yaml
# 模拟盘时不需要配置
# easytrader配置（实盘时启用）
easytrader:
  client_path: /path/to/xiadan.exe
  account_type: ths       # ths/gj/yh
```

---

## 6. 测试策略

| 测试模块 | 测试内容 | 测试数 |
|----------|----------|--------|
| test_signal_loader | 加载信号、空信号处理 | 2 |
| test_portfolio_builder | Top N筛选、空输入 | 2 |
| test_position_calc | 信号强度加权、边界值 | 3 |
| test_order_manager | 订单生成、状态更新 | 4 |
| test_simulator | 模拟成交 | 2 |
| test_trade_log | 入库、查询 | 2 |
| test_rebalance | 全流程集成 | 1 |

**总测试数：14**

---

## 7. 验收标准

交易执行子系统完成标志：

1. ✅ executor/ 模块代码完成（约1500行）
2. ✅ 14个单元测试全部通过
3. ✅ 模拟盘全链路跑通：信号→组合→仓位→订单→成交→记录
4. ✅ order_log、trade_log、position_log 三张表数据正确
5. ✅ run_simulator.py 可一键启动模拟盘
6. ✅ 配置文件 executor.yaml、broker.yaml 可正确读取