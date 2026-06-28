"""API v1 路由聚合. """

from fastapi import APIRouter

from app.api.v1 import auth, data, factor, backtest, ml, trading

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(data.router, prefix="/data", tags=["数据"])
api_router.include_router(factor.router, prefix="/factor", tags=["因子"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["回测"])
api_router.include_router(ml.router)  # 已包含 /ml 前缀
api_router.include_router(trading.router)  # 已包含 /trading 前缀

__all__ = ["api_router"]
