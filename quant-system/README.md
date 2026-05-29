# A股因子选股量化系统

基于因子选股的A股量化分析系统，支持数据采集、策略回测、可视化展示。

## 快速启动

```bash
# 1. 数据采集
python scripts/run_collector.py

# 2. 运行回测
python scripts/run_backtest.py

# 3. 启动Dashboard
python scripts/run_dashboard.py
```

## Docker部署

```bash
docker compose up -d
```

## 项目结构

```
quant-system/
├── config/          # 配置文件
├── data/
│   ├── collector/   # 数据采集模块
│   └── db/          # 数据库管理
├── strategy/        # 策略模块
├── backtest/        # 回测引擎
├── visual/          # 可视化
├── scripts/         # 运行脚本
└── tests/           # 测试
```