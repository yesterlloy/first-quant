from typing import Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger


class APIException(Exception):
    """API 基础异常"""

    def __init__(
        self,
        code: int,
        message: str,
        details: Optional[dict[str, Any]] = None,
        status_code: int = 200,
    ):
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code


# 常用预定义异常
class NotFoundException(APIException):
    """资源不存在"""
    def __init__(self, resource: str = "Resource"):
        super().__init__(code=4004, message=f"{resource} not found", status_code=404)


class ValidationException(APIException):
    """参数验证失败"""
    def __init__(self, message: str = "Validation failed", details: Optional[dict] = None):
        super().__init__(code=4001, message=message, details=details, status_code=400)


class UnauthorizedException(APIException):
    """未授权"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(code=4004, message=message, status_code=401)


class ForbiddenException(APIException):
    """权限不足"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(code=4003, message=message, status_code=403)


class BusinessException(APIException):
    """业务逻辑异常"""
    def __init__(self, code: int = 5001, message: str = "Business error"):
        super().__init__(code=code, message=message, status_code=200)


def register_exception_handlers(app: FastAPI):
    """注册异常处理器"""

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """统一处理 API 异常"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": int(__import__("time").time()),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 5000,
                "message": "Internal server error",
                "details": str(exc) if app.state.config.DEBUG else None,
                "timestamp": int(__import__("time").time()),
            },
        )
