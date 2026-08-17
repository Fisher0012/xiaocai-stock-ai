"""FinMCP 日志配置

MCP server 的 stdout 是协议通道，日志必须输出到 stderr。
"""

import logging
import os
import sys


def get_logger(name: str) -> logging.Logger:
    """获取配置好的 logger

    Args:
        name: logger 名称，通常传 __name__

    Returns:
        配置好的 Logger 实例，输出到 stderr
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        level_str = os.getenv("FINMCP_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
        handler.setLevel(level)
        logger.setLevel(level)

        formatter = logging.Formatter(
            "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
