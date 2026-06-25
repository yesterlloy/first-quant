# 后端架构设计文档

> **版本**: v1.0
> **更新日期**: 2026-06-23
> **技术栈**: FastAPI + SQLAlchemy + SQLite/PostgreSQL + Redis + Celery

---

## 🎯 设计原则

1. **高性能**: 异步处理，数据库优化，缓存策略
2. **可扩展**: 模块化设计，易于新增功能
3. **可维护**: 清晰的分层架构，统一的错误处理
4. **兼容迁移**: 平滑过渡，兼容现有代码

---

## 📦 技术栈详情

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| Web框架 | FastAPI | 0.100+ | 高性能异步框架 |
| ORM | SQLAlchemy | 2.0+ | 类型安全 ORM |
| 数据库 | SQLite / PostgreSQL | 3.0+ / 15+ | 当前 SQLite，预留升级路径 |
| 缓存 | Redis | 7.0+ | API 缓存 + 会话存储 |
| 异步任务 | Celery | 5.3+ | 耗时任务异步执行 |
| 认证 | python-jose | - | JWT Token 认证 |
| 密码加密 | passlib | - | bcrypt 加密 |
| 数据验证 | Pydantic | 2.0+ | 类型安全的数据验证 |
| 日志 | Loguru | - | 结构化日志 |
| 测试 | pytest | - | 单元测试 + 集成测试 |

---

## 📁 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 应用入口
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py          # 配置管理
│   │   ├── security.py        # 安全相关（JWT、密码）
│   │   ├── database.py        # 数据库连接
│   │   ├── redis.py           # Redis 连接
│   │   ├── celery_app.py     # Celery 配置
│   │   └── exceptions.py     # 自定义异常
│   ├── api/                    # API 路由
│   │   ├── __init__.py
│   │   ├── deps.py            # 依赖注入
│   │   └── v1/               # v1 版本 API
│   │       ├── __init__.py
│   │       ├── auth.py        # 认证接口
│   │       ├── data.py        # 数据接口
│   │       ├── factor.py      # 因子接口
│   │       ├── backtest.py    # 回测接口
│   │       ├── ml.py          # ML 接口
│   │       ├── trading.py     # 交易接口
│   │       ├── risk.py        # 风控接口
│   │       └── scheduler.py   # 调度接口
│   ├── models/                  # 数据库模型
│   │   ├── __init__.py
│   │   ├── user.py            # 用户模型
│   │   ├── stock.py           # 股票模型
│   │   ├── factor.py          # 因子模型
│   │   ├── backtest.py        # 回测模型
│   │   ├── ml.py            # ML 模型
│   │   ├── trading.py         # 交易模型
│   │   └── scheduler.py       # 调度模型
│   ├── schemas/                 # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── common.py          # 通用响应
│   │   ├── user.py
│   │   ├── data.py
│   │   ├── factor.py
│   │   ├── backtest.py
│   │   ├── ml.py
│   │   ├── trading.py
│   │   └── scheduler.py
│   ├── services/                # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── data_service.py    # 数据服务
│   │   ├── factor_service.py  # 因子服务
│   │   ├── backtest_service.py # 回测服务
│   │   ├── ml_service.py     # ML 服务
│   │   ├── trading_service.py # 交易服务
│   │   ├── risk_service.py    # 风控服务
│   │   └── scheduler_service.py # 调度服务
│   ├── tasks/                   # Celery 任务
│   │   ├── __init__.py
│   │   ├── backtest_tasks.py
│   │   ├── ml_tasks.py
│   │   ├── data_tasks.py
│   │   └── base.py
│   ├── utils/                   # 工具函数
│   │   ├── __init__.py
│   │   ├── logger.py         # 日志配置
│   │   ├── cache.py          # 缓存工具
│   │   ├── datetime.py        # 日期工具
│   │   └── helpers.py       # 通用工具
│   └── tests/                   # 测试
│       ├── __init__.py
│       ├── conftest.py
│       ├── api/
│       └── services/
├── alembic/                    # 数据库迁移
│   ├── versions/
│   └── env.py
├── data/                       # 数据目录
│   ├── db/
│   └── cache/
├── requirements.txt            # Python 依赖
├── .env.example              # 环境变量示例
├── Dockerfile                # Docker 构建
└── README.md               # 项目说明
```

---

## 🏗️ 分层架构

```
┌─────────────────────────────────────────┐
│              API Layer (FastAPI Routes)          │
│    路由层：参数验证、响应格式化      │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│            Service Layer           │
│    业务逻辑层：核心计算、逻辑处理 │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│          Data Access Layer      │
│    ORM + 数据库操作            │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│            Database               │
│    SQLite / PostgreSQL           │
└─────────────────────────────────────┘
```

### 层间调用规则：
- API → Service → Data Access → Database

---

## 🔐 安全设计

### JWT 认证流程
```
1. 用户登录 → 验证密码 → 生成 Access Token + Refresh Token
2. 请求携带 Access Token → 验证 Token → 获取用户信息
3. Token 过期 → 使用 Refresh Token 刷新
```

### 密码加密
```python
# core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

### 权限控制
```python
# api/deps.py
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user
```

---

## 💾 数据库设计

### 核心表结构

#### 用户表 (users)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| username | String | 用户名（唯一） |
| email | String | 邮箱（唯一） |
| hashed_password | String | 加密密码 |
| is_active | Boolean | 是否激活 |
| is_superuser | Boolean | 是否管理员 |
| created_at | DateTime | 创建时间 |

#### 回测任务表 (backtest_tasks)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 任务ID |
| strategy_id | String | 策略ID |
| params | JSON | 策略参数 |
| stock_code | String | 股票代码 |
| status | String | 状态：pending/running/completed/failed |
| progress | Float | 进度 0-1 |
| result | JSON | 回测结果 |
| error_message | String | 错误信息 |
| created_by | Integer | 创建用户 |
| created_at | DateTime | 创建时间 |
| completed_at | DateTime | 完成时间 |

#### ML训练任务表 (ml_train_tasks)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 任务ID |
| model_name | String | 模型名称 |
| status | String | 状态 |
| progress | Float | 进度 |
| result | JSON | 训练结果 |
| created_by | Integer | 创建用户 |
| created_at | DateTime | 创建时间 |

---

## ⚡ 缓存策略

### Redis 缓存设计

| Key 前缀 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `user:{id}` | Hash | 24h | 用户信息 |
| `stock:{code}` | String | 1h | 股票信息 |
| `quote:{code}:{date}` | String | 1h | 行情数据 |
| `factor:{name}:{date}` | String | 1h | 因子值 |
| `backtest:{task_id}` | Hash | 7d | 回测结果 |

### 缓存装饰器
```python
# utils/cache.py
def cache(key_prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{hash(args + tuple(kwargs.items()))}"
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            await redis.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

---

## 📋 异步任务处理

### Celery 任务设计

```python
# core/celery_app.py
from celery import Celery

celery_app = Celery(
    "quant_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task(bind=True)
def run_backtest_task(self, task_id: str, params: dict):
    """运行回测任务"""
    # 更新任务状态为 running

    try:
        # 执行回测逻辑
        result = backtest_service.run_backtest(params)

        # 更新任务状态为 completed
        backtest_service.update_task_result(task_id, result)
        return result
    except Exception as e:
        # 更新任务状态为 failed
        backtest_service.update_task_error(task_id, str(e))
        raise
```

### 任务类型

| 任务 | 优先级 | 超时 | 说明 |
|------|--------|------|------|
| 回测任务 | 高 | 30min | 策略回测 |
| ML训练 | 中 | 1h | 模型训练 |
| 数据采集 | 中 | 10min | 每日数据采集 |
| 因子计算 | 中 | 10min | 每日因子计算 |

---

## 📊 API 响应统一格式

### 统一响应模型
```python
# schemas/common.py
from pydantic import BaseModel, Generic, TypeVar, Field

T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    code: int = Field(default=0, description="响应码，0表示成功")
    message: str = Field(default="success", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")
    timestamp: int = Field(default_factory=lambda: int(time.time()))

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
```

### 统一异常处理
```python
# core/exceptions.py
class APIException(Exception):
    code: int
    message: str
    details: dict | None

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=200,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": int(time.time()),
        }
    )
```

---

## 📝 日志设计

### 结构化日志
```python
# utils/logger.py
from loguru import logger
import sys
import json

def setup_logger():
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # 文件输出（JSON 格式）
    logger.add(
        "logs/app_{time}.log",
        rotation="100 MB",
        retention="30 days",
        level="DEBUG",
        serialize=True
    )
```

### 请求日志中间件
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000

    logger.info(
        f"{request.method} {request.url.path} "
        f"{response.status_code} {process_time:.2f}ms"
    )
    return response
```

---

## 🔄 数据库迁移

### Alembic 配置
```python
# alembic/env.py
from app.core.config import settings
from app.core.database import Base

target_metadata = Base.metadata

def run_migrations_online():
    connectable = create_engine(settings.DATABASE_URL)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()
```

### 迁移命令
```bash
# 生成迁移文件
alembic revision --autogenerate -m "create users table"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

## ✅ 测试策略

### 测试目录结构
```
tests/
├── conftest.py          # pytest 配置
├── api/                # API 测试
│   ├── test_auth.py
│   ├── test_data.py
│   └── test_backtest.py
└── services/            # 服务层测试
    ├── test_factor_service.py
    └── test_backtest_service.py
```

### 测试 Fixture
```python
# conftest.py
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    # 使用测试数据库
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
```

---

## 🚀 部署配置

### Gunicorn + Uvicorn
```python
# gunicorn.conf.py
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"
max_requests = 1000
max_requests_jitter = 50
```

### Docker Compose 生产配置
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/quant
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  celery_worker:
    build: ./backend
    command: celery -A app.core.celery_app worker --loglevel=info
    depends_on:
      - redis
```

---

## 🔮 扩展性设计

### 策略扩展机制
```python
# 策略注册机制
class StrategyRegistry:
    _strategies = {}

    @classmethod
    def register(cls, name: str):
        def decorator(strategy_class):
            cls._strategies[name] = strategy_class
            return strategy_class
        return decorator

    @classmethod
    def get(cls, name: str):
        return cls._strategies.get(name)

# 使用示例
@StrategyRegistry.register("ma_cross")
class MACrossStrategy:
    pass
```

### 因子扩展机制
类似策略注册机制，支持自定义因子

---

## 📈 性能优化

### 1. 数据库优化
- 索引优化：常用查询字段加索引
- 连接池：SQLAlchemy 连接池配置
- 查询优化：避免 N+1 查询，使用 selectinload

### 2. API 性能
- 分页：所有列表接口支持分页
- 缓存：热点数据 Redis 缓存
- 异步：IO 密集型操作异步化

### 3. 慢查询监控
- 自动记录超过 1s 的慢查询
- SQLAlchemy 事件监听慢查询
- 定期分析优化
