"""统一日志系统"""
import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[37m",  # White
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    ICONS = {
        "DEBUG": "🔍",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🚨",
    }

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        color = self.COLORS.get(record.levelname, "")
        icon = self.ICONS.get(record.levelname, "•")

        # 自定义级别支持（如 SUCCESS）
        if hasattr(record, "custom_level"):
            custom_level = record.custom_level
            if custom_level == "SUCCESS":
                color = "\033[32m"  # Green
                icon = "✅"
            elif custom_level == "STEP":
                color = "\033[34m"  # Blue
                icon = "🔹"

        record.levelname = f"{color}{icon} {record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str, level: int = logging.INFO, format_string: Optional[str] = None
) -> logging.Logger:
    """设置日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别
        format_string: 自定义格式字符串

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if format_string is None:
        format_string = "%(levelname)s %(message)s"

    formatter = ColoredFormatter(format_string)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger


def log_success(logger: logging.Logger, message: str) -> None:
    """记录成功消息"""
    record = logger.makeRecord(logger.name, logging.INFO, "", 0, message, (), None)
    record.custom_level = "SUCCESS"
    logger.handle(record)


def log_step(logger: logging.Logger, message: str) -> None:
    """记录步骤消息"""
    record = logger.makeRecord(logger.name, logging.INFO, "", 0, message, (), None)
    record.custom_level = "STEP"
    logger.handle(record)
