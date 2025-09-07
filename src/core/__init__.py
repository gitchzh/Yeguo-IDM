"""
核心模块

包含应用程序的核心配置和基础功能。
"""

from .config import Config
from .log_manager import log_manager, LogManager, LogViewer

__all__ = ["Config", "log_manager", "LogManager", "LogViewer"]
