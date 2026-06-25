"""日志配置：基于 loguru，控制台 + 文件双输出."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.config import settings

_configured: bool = False


def setup_logging(log_level: Optional[str] = None) -> None:
    """初始化全局日志配置.

    - 控制台：彩色输出，便于开发调试
    - 文件：按日轮转，保留 30 天，自动压缩
    - 移除 loguru 默认 handler，避免重复输出
    """
    global _configured
    if _configured:
        return

    level = log_level or settings.LOG_LEVEL

    # 移除默认 handler
    logger.remove()

    # 控制台输出
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        colorize=True,
        backtrace=settings.DEBUG,
        diagnose=settings.DEBUG,
    )

    # 文件输出
    log_dir = Path(settings.LOG_DIR)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            level=level,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
                "{name}:{function}:{line} - {message}"
            ),
            rotation="00:00",  # 每天轮转
            retention="30 days",
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=settings.DEBUG,
        )
    except OSError:
        # 日志目录不可写时仅用控制台，不影响启动
        logger.warning(f"无法创建日志目录 {log_dir}，仅使用控制台输出")

    _configured = True
    logger.info(f"日志初始化完成，级别={level}")


# 导出单例 logger，便于其他模块直接 from app.utils.logger import logger
__all__ = ["logger", "setup_logging"]
