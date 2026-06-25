# API 接口详细设计文档

> **版本**: v1.0
> **更新日期**: 2026-06-23
> **Base URL**: `/api/v1`

---

## 📋 统一响应格式

### 成功响应
```json
{
  "code": 0,
  "message": "success",
  "data": {
    // 具体数据
  },
  "timestamp": 1719123456
}
```

### 分页响应
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "pages": 5
  },
  "timestamp": 1719123456
}
```

### 错误响应
```json
{
  "code": 4001,
  "message": "参数验证失败",
  "details": {
    "code": "股票代码不能为空"
  },
  "timestamp": 1719123456
}
```

---

## 🔐 认证接口

### 登录
```http
POST /api/v1/auth/login
Content-Type: application/json

Request:
{
  "username": "admin",
  "password": "password"
}

Response:
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbG...",
    "refresh_token": "eyJhbG...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

### 获取当前用户信息
```http
GET /api/v1/auth/me
Authorization: Bearer {token}
```

### 刷新 Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbG..."
}
```

---

## 📊 数据模块 API

### 1. 股票列表
```http
GET /api/v1/data/stocks?page=1&page_size=20&keyword=平安

Response:
{
  "code": 0,
  "data": {
    "items": [
      {
        "code": "000001",
        "name": "平安银行",
        "industry": "银行",
        "list_date": "1991-04-03"
      }
    ],
    "total": 5000,
    "page": 1,
    "page_size": 20
  }
}
```

### 2. 股票详情
```http
GET /api/v1/data/stocks/{code}

Response:
{
  "code": 0,
  "data": {
    "code": "000001",
    "name": "平安银行",
    "industry": "银行",
    "list_date": "1991-04-03",
    "market_cap": 250000000000,
    "pe_ttm": 8.5,
    "pb": 0.85
  }
}
```

### 3. 日线行情
```http
GET /api/v1/data/stocks/{code}/quote?start_date=2024-01-01&end_date=2024-12-31

Response:
{
  "code": 0,
  "data": {
    "code": "000001",
    "name": "平安银行",
    "quotes": [
      {
        "date": "2024-01-02",
        "open": 10.5,
        "high": 10.8,
        "low": 10.4,
        "close": 10.7,
        "volume": 123456789,
        "turnover": 1345678900,
        "change_pct": 0.025,
        "turnover_rate": 0.0065
      }
    ]
  }
}
```

### 4. 数据概览统计
```http
GET /api/v1/data/overview

Response:
{
  "code": 0,
  "data": {
    "total_stocks": 4958,
    "total_days": 1549,
    "min_date": "2020-01-02",
    "max_date": "2026-05-28",
    "total_quotes": 6706664,
    "last_update": "2026-05-28 15:30:00"
  }
}
```

### 5. 指数列表
```http
GET /api/v1/data/indices
```

### 6. 指数行情
```http
GET /api/v1/data/indices/{code}/quote
```

---

## 🧮 因子模块 API

### 1. 因子列表
```http
GET /api/v1/factors

Response:
{
  "code": 0,
  "data": {
    "items": [
      {
        "name": "EP",
        "display_name": "盈利收益率",
        "category": "valuation",
        "description": "盈利收益率因子",
        "formula": "1/PE",
        "direction": 1
      }
    ],
    "total": 18
  }
}
```

### 2. 因子详情
```http
GET /api/v1/factors/{name}
```

### 3. 因子值查询
```http
GET /api/v1/factors/{name}/values?date=2024-01-01

Response:
{
  "code": 0,
  "data": {
    "factor_name": "EP",
    "date": "2024-01-01",
    "values": [
      {
        "code": "000001",
        "name": "平安银行",
        "raw_value": 0.125,
        "neut_value": 0.0023
      }
    ],
    "total": 4958
  }
}
```

### 4. IC 分析结果
```http
GET /api/v1/factors/{name}/ic?start_date=2024-01-01&end_date=2024-12-31

Response:
{
  "code": 0,
  "data": {
    "factor_name": "EP",
    "ic_mean": 0.052,
    "ic_std": 0.12,
    "ir": 0.43,
    "ic_win_rate": 0.58,
    "ic_series": [
      {"date": "2024-01-01", "ic": 0.065},
      {"date": "2024-01-02", "ic": 0.042}
    ]
  }
}
```

### 5. 分层回测结果
```http
GET /api/v1/factors/{name}/layer-test
```

---

## 💹 回测模块 API

### 1. 策略列表
```http
GET /api/v1/backtest/strategies

Response:
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "ma_cross",
        "name": "双均线策略",
        "description": "短均线上穿长均线买入，下穿卖出",
        "params": [
          {"name": "short_window", "type": "int", "default": 5, "min": 1, "max": 60},
          {"name": "long_window", "type": "int", "default": 20, "min": 5, "max": 250}
        ]
      },
      {
        "id": "momentum",
        "name": "动量策略",
        "description": "过去N天涨幅超过阈值买入",
        "params": [...]
      },
      {
        "id": "mean_revert",
        "name": "均值回归策略",
        "description": "价格偏离均值N倍标准差时反向操作",
        "params": [...]
      }
    ]
  }
}
```

### 2. 运行回测（异步）
```http
POST /api/v1/backtest/run
Content-Type: application/json

Request:
{
  "strategy_id": "ma_cross",
  "params": {
    "short_window": 5,
    "long_window": 20
  },
  "stock_code": "000001",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 1000000,
  "commission": 0.001,
  "slippage": 0.0005
}

Response:
{
  "code": 0,
  "data": {
    "task_id": "bt_abc123",
    "status": "running",
    "message": "回测任务已提交"
  }
}
```

### 3. 回测状态查询
```http
GET /api/v1/backtest/tasks/{task_id}

Response (进行中):
{
  "code": 0,
  "data": {
    "task_id": "bt_abc123",
    "status": "running",
    "progress": 0.65,
    "message": "正在计算第 156 天..."
  }
}

Response (完成):
{
  "code": 0,
  "data": {
    "task_id": "bt_abc123",
    "status": "completed",
    "progress": 1.0,
    "result": {
      "strategy_name": "双均线策略(5,20)",
      "stock_code": "000001",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "metrics": {
        "total_return": 0.3256,
        "annual_return": 0.352,
        "sharpe_ratio": 1.85,
        "max_drawdown": -0.1235,
        "win_rate": 0.523,
        "profit_loss_ratio": 1.45,
        "total_trades": 42
      },
      "equity_curve": [
        {"date": "2024-01-01", "value": 1000000},
        {"date": "2024-01-02", "value": 1005200}
      ],
      "drawdown_curve": [...],
      "trades": [...]
    }
  }
}
```

### 4. 回测历史
```http
GET /api/v1/backtest/history?page=1&page_size=20
```

---

## 🤖 ML 模块 API

### 1. 模型列表
```http
GET /api/v1/ml/models
```

### 2. 提交训练任务
```http
POST /api/v1/ml/train
Content-Type: application/json

{
  "model_name": "lightgbm_v1",
  "start_date": "2020-01-01",
  "end_date": "2023-12-31",
  "factors": ["EP", "BP", "ROE", "MOM_20"],
  "params": {
    "n_estimators": 100,
    "learning_rate": 0.05
  }
}
```

### 3. 训练状态查询
```http
GET /api/v1/ml/train/{task_id}
```

### 4. 预测信号
```http
GET /api/v1/ml/signals?date=2024-01-01&model_name=lightgbm_v1
```

---

## 📈 实盘模块 API

### 1. 持仓查询
```http
GET /api/v1/trading/positions

Response:
{
  "code": 0,
  "data": {
    "total_asset": 1256800,
    "cash": 256800,
    "market_value": 1000000,
    "positions": [
      {
        "code": "000001",
        "name": "平安银行",
        "quantity": 10000,
        "avg_cost": 9.8,
        "current_price": 10.5,
        "market_value": 105000,
        "profit": 7000,
        "profit_pct": 0.0714
      }
    ]
  }
}
```

### 2. 订单列表
```http
GET /api/v1/trading/orders?status=all&page=1&page_size=20
```

### 3. 交易记录
```http
GET /api/v1/trading/trades?start_date=2024-01-01&end_date=2024-12-31
```

### 4. 账户统计
```http
GET /api/v1/trading/account

Response:
{
  "code": 0,
  "data": {
    "total_asset": 1256800,
    "initial_capital": 1000000,
    "total_profit": 256800,
    "total_profit_pct": 0.2568,
    "annual_return": 0.285,
    "max_drawdown": -0.085,
    "win_rate": 0.56,
    "profit_loss_ratio": 1.65
  }
}
```

---

## ⚠️ 风控模块 API

### 1. 风险事件列表
```http
GET /api/v1/risk/events?level=warning&page=1&page_size=20
```

### 2. 风控规则列表
```http
GET /api/v1/risk/rules
```

### 3. 更新风控规则
```http
PUT /api/v1/risk/rules/{id}
```

---

## ⏰ 任务调度 API

### 1. 任务列表
```http
GET /api/v1/scheduler/tasks

Response:
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "data_collection",
        "name": "数据采集",
        "cron": "0 18 * * 1-5",
        "next_run": "2024-06-24 18:00:00",
        "last_run": "2024-06-23 18:00:00",
        "last_status": "success",
        "enabled": true
      }
    ]
  }
}
```

### 2. 手动触发任务
```http
POST /api/v1/scheduler/tasks/{task_id}/trigger
```

### 3. 任务日志
```http
GET /api/v1/scheduler/logs?task_id=data_collection&page=1&page_size=20
```

---

## 🔄 WebSocket API

### 连接地址
```
ws://localhost:8000/ws
```

### 消息格式

#### 订阅回测进度
```json
{
  "type": "subscribe",
  "topic": "backtest:{task_id}"
}
```

#### 进度推送
```json
{
  "type": "progress",
  "topic": "backtest:bt_abc123",
  "data": {
    "task_id": "bt_abc123",
    "progress": 0.65,
    "message": "正在计算第 156 天..."
  }
}
```

---

## 📝 错误码说明

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|------------|
| 0 | 成功 | 200 |
| 4001 | 参数验证失败 | 400 |
| 4002 | 资源不存在 | 404 |
| 4003 | 权限不足 | 403 |
| 4004 | 未授权 | 401 |
| 5001 | 服务器内部错误 | 500 |
| 5002 | 数据库操作失败 | 500 |
| 5003 | 外部服务调用失败 | 500 |
| 6001 | 回测任务失败 | 422 |
| 6002 | 训练任务失败 | 422 |
