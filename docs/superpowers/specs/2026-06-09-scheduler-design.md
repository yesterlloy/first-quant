# 定时任务调度器设计规范

> 设计日期: 2026-06-09
> 所属阶段: Phase 4 实盘对接与风控监控
> 技术方案: APScheduler 轻量级调度器

---

## 1. 概述

### 1.1 目标

为量化系统提供自动化任务调度能力，支持每日数据采集、因子计算、月度调仓、日报推送等定时任务。

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **单层架构** | 不需要独立worker进程，所有任务在同一进程内执行 |
| **内存存储** | 任务状态保存在内存，重启后重新注册 |
| **幂等设计** | 每个任务可重复执行，不产生副作用 |
| **优雅停机** | 接收 SIGINT/SIGTERM 后等待当前任务完成再退出 |
| **YAGNI** | 只实现必要功能，避免过度设计 |

---

## 2. 系统架构

### 2.1 核心模块

```
┌─────────────────────────────────────────────────────────────┐
│                    Task Scheduler 核心模块                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Scheduler  │ →  │ Task Runner │ →  │ Exec Log   │      │
│  │   Engine    │    │   (Worker)  │    │   Store    │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│         ↓                  ↓                   ↓             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Job Store  │    │ Retry Logic │ →  │  Alert Mgr │      │
│  │ (Memory)    │    │ (Exponential)│    │  告警推送   │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌───────────┬───────────┬───────────┬───────────┐
        │  数据采集  │  因子计算  │  月度调仓  │  日报推送  │
        │  (每日18点) │  (每日19点) │  (月末14点) │  (每日18:30)│
        └───────────┴───────────┴───────────┴───────────┘
```

### 2.2 模块职责

| 模块 | 职责 |
|------|------|
| **SchedulerEngine** | 初始化 APScheduler，注册任务，启动/停止调度 |
| **TaskWrapper** | 任务包装器，统一处理重试、日志、异常、告警 |
| **TaskDefinitions** | 具体任务实现（采集/因子/调仓/报告） |
| **SchedulerLogStore** | 执行日志入库与查询 |

---

## 3. 数据库设计

### 3.1 调度日志表

```sql
CREATE TABLE IF NOT EXISTS scheduler_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name VARCHAR(100) NOT NULL,        -- 任务名称
    status VARCHAR(20) NOT NULL,            -- running / success / failed / skipped
    start_time TIMESTAMP NOT NULL,           -- 开始时间
    end_time TIMESTAMP,                      -- 结束时间
    duration_seconds FLOAT,                  -- 耗时
    retry_count INTEGER DEFAULT 0,           -- 重试次数
    error_message TEXT,                      -- 异常信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scheduler_log_task ON scheduler_log(task_name);
CREATE INDEX idx_scheduler_log_time ON scheduler_log(start_time);
```

---

## 4. 配置设计

### 4.1 配置文件路径

`config/scheduler.yaml`

### 4.2 配置格式

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  
  # 错过任务处理策略
  misfire_grace_time: 3600  # 1小时内的错过才补执行
  misfire_policy: "skip"    # skip / run_once

  # 全局重试配置
  retry:
    max_attempts: 3
    initial_delay: 1.0      # 初始等待 1 秒
    max_delay: 8.0          # 最大等待 8 秒
    backoff_multiplier: 2.0 # 指数因子

  # 告警配置
  alert_on_failure: true
  alert_on_success: false

tasks:
  # 每日数据采集
  data_collection:
    enabled: true
    cron: "0 18 * * 1-5"    # 周一到周五 18:00
    timeout: 300             # 5分钟超时
    retry: true
    
  # 每日因子计算
  factor_compute:
    enabled: true
    cron: "0 19 * * 1-5"    # 周一到周五 19:00
    timeout: 600             # 10分钟超时
    retry: true
    depends_on: ["data_collection"]  # 依赖数据采集完成
    
  # 月度调仓
  monthly_rebalance:
    enabled: false           # 默认关闭，手动开启
    cron: "0 14 L * *"      # 每月最后一天 14:00
    timeout: 1200            # 20分钟超时
    retry: false
    
  # 每日持仓报告
  daily_report:
    enabled: true
    cron: "30 18 * * 1-5"   # 周一到周五 18:30
    timeout: 60
    retry: false
```

---

## 5. 核心功能清单

### 5.1 调度核心 (P0)

| 功能 | 说明 |
|------|------|
| Cron 表达式调度 | 支持标准 cron 格式（分 时 日 月 周） |
| 并发控制 | 同一时间同一任务只运行一个实例 |
| 错过任务处理 | 超过 grace_time 的任务跳过，否则立即执行 |
| 优雅停机 | 接收到退出信号后等待当前任务完成 |

### 5.2 任务定义 (P0)

| 任务 | 触发时间 | 说明 |
|------|---------|------|
| 数据采集 | 每日 18:00 | 调用采集器获取日线数据 |
| 因子计算 | 每日 19:00 | 计算所有因子值 |
| 月度调仓 | 每月最后一天 14:00 | 执行 Rebalancer 调仓 |
| 日报推送 | 每日 18:30 | 计算 PnL 并推送告警 |

### 5.3 执行保障 (P0)

| 功能 | 说明 |
|------|------|
| 指数退避重试 | 1s → 2s → 4s → 8s，最多 3 次 |
| 当日截止时间 | 超过 18:00 不再重试，避免跨日数据 |
| 超时控制 | 每个任务有最大执行时间限制 |

### 5.4 日志与告警 (P0)

| 功能 | 说明 |
|------|------|
| 执行日志入库 | 每个任务的开始/结束/耗时/错误都入库 |
| 失败自动告警 | 任务失败推送到 AlertManager |
| 任务状态查询 | 查询最近 N 次执行结果 |

### 5.5 进阶功能 (P1/P2)

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 交易日历过滤 | P1 | A股节假日不执行任务 |
| 热重载配置 | P2 | 修改配置无需重启 |
| 手动触发接口 | P1 | 命令行手动触发任务 |

---

## 6. 重试策略详解

### 6.1 指数退避算法

```
重试间隔 = min(initial_delay * (backoff_multiplier ^ retry_count), max_delay)
```

| 第 N 次重试 | 等待时间 |
|-----------|---------|
| 1 | 1s |
| 2 | 2s |
| 3 | 4s |

### 6.2 截止时间逻辑

```python
current_hour = datetime.now().hour
if current_hour >= 18:  # 下午6点后不再重试
    logger.warning("Skip retry: past daily cutoff time")
    break
```

---

## 7. API 接口设计

### 7.1 Scheduler 类

```python
class QuantScheduler:
    def __init__(self, config_path: str = "config/scheduler.yaml"):
        pass
    
    def start(self):
        """启动调度器，阻塞运行"""
        pass
    
    def shutdown(self, wait: bool = True):
        """停止调度器"""
        pass
    
    def trigger_task(self, task_name: str) -> bool:
        """手动触发任务"""
        pass
    
    def get_task_status(self, task_name: str, limit: int = 10) -> list:
        """获取任务最近执行状态"""
        pass
```

### 7.2 启动脚本

```bash
# 启动调度器
python scripts/run_scheduler.py

# 手动触发任务
python scripts/run_scheduler.py --trigger data_collection

# 查看任务状态
python scripts/run_scheduler.py --status data_collection
```

---

## 8. 测试用例设计

| 测试分类 | 用例数 | 测试内容 |
|---------|--------|---------|
| 调度器核心 | 3 | 启动/停止、任务注册、错过任务处理 |
| 任务包装器 | 4 | 正常执行、异常捕获、重试机制、超时控制 |
| 日志存储 | 2 | 日志写入、状态查询 |
| 任务集成 | 2 | 采集任务、因子任务 |
| **总计** | **11** | |

---

## 9. 实现计划

### 9.1 开发顺序

| Step | 模块 | 预估代码量 | 测试数 |
|------|------|-----------|--------|
| 1 | 数据库表扩展 | 20行 | 0 |
| 2 | SchedulerLogStore | 80行 | 2 |
| 3 | TaskWrapper 重试包装器 | 100行 | 4 |
| 4 | QuantScheduler 核心 | 150行 | 3 |
| 5 | 具体任务实现 | 80行 | 2 |
| 6 | 启动脚本 + CLI | 50行 | 0 |
| **总计** | | **~480行** | **11个测试** |

### 9.2 预估时间

**开发 + 测试：约 0.5 ~ 1 天**

---

## 10. 潜在风险与应对

| 风险 | 影响 | 应对方案 |
|------|------|---------|
| 调度进程意外退出 | 高 | 1. Supervisor 托管 2. 启动时检查错过任务 3. 告警推送 |
| 任务执行时间超长 | 中 | 每个任务加超时控制，超时自动终止 |
| 任务依赖顺序 | 中 | 简单依赖在配置中声明，复杂依赖用 DAG（P2） |
| 时区问题 | 高 | 强制使用 Asia/Shanghai，所有时间带时区 |
