"""loguru 统一日志。在 FastAPI lifespan 启动时调用 setup_logging()。"""

from __future__ import annotations

import sys

from loguru import logger

from .config import settings


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.debug else "INFO",
        format=(
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )
