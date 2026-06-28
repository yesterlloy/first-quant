"""API v1 路由聚合. """

from fastapi import APIRouter

from app.api.v1 import auth, data, factor, backtest

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(data.router, prefix="/data", tags=["数据"])
api_router.include_router(factor.router, prefix="/factor", tags=["因子"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["回测"])

__all__ = ["api_router"]
