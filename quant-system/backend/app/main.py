"""FastAPI 应用入口.

启动顺序：
1. 初始化日志
2. 创建 FastAPI 实例，挂载 CORS / 异常处理
3. 注册 v1 路由
4. 启动时按配置初始化数据库表
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化日志与数据库."""
    setup_logging()
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION} (debug={settings.DEBUG})")

    # 将配置挂到 app.state，供异常处理器引用（exceptions.py 使用 app.state.config.DEBUG）
    app.state.config = settings

    try:
        init_db()
    except Exception as exc:  # noqa: BLE001 启动期 DB 失败不应静默
        logger.error(f"数据库初始化失败：{exc}")
        if settings.DEBUG:
            raise

    logger.info("应用启动完成")
    yield
    logger.info("应用关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="A股因子选股量化系统 - 后端 API",
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 异常处理
    register_exception_handlers(app)

    # 路由
    app.include_router(api_router, prefix="/api/v1")

    # 健康检查
    @app.get("/health", tags=["系统"])
    def health() -> dict:
        """健康检查端点."""
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    @app.get("/", tags=["系统"])
    def root() -> dict:
        """根路径."""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    return app


# uvicorn 入口：``uvicorn app.main:app``
app = create_app()
