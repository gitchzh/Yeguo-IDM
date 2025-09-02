"""
日志工具模块

该模块包含日志记录相关的工具类和函数，负责：
- 应用程序日志系统的初始化和配置
- 日志文件的创建和管理
- yt-dlp日志适配器的实现
- 日志信息的格式化和输出

主要组件：
- setup_logger: 设置日志记录器
- logger: 全局日志记录器实例
- DebugLogger: yt-dlp日志记录器适配器类

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import logging
import os
from datetime import datetime
from PyQt5.QtCore import pyqtSignal

# 全局状态栏更新信号
status_bar_signal = None

def set_status_bar_signal(signal):
    """设置状态栏更新信号"""
    global status_bar_signal
    status_bar_signal = signal

class StatusBarHandler(logging.Handler):
    """状态栏日志处理器"""
    
    def emit(self, record):
        """发送日志记录到状态栏"""
        try:
            if status_bar_signal:
                # 显示所有日志信息，不过滤
                msg = record.getMessage()
                # 发送到状态栏
                status_bar_signal.emit(msg)
        except Exception:
            # 忽略状态栏更新错误，避免影响日志系统
            pass

def setup_logger():
    """设置日志记录器"""
    # 创建日志目录
    log_dir = os.getcwd()
    log_file = os.path.join(log_dir, "app.log")
    
    # 检查日志文件权限
    try:
        # 尝试创建或写入日志文件
        if os.path.exists(log_file):
            # 检查文件是否可写
            if not os.access(log_file, os.W_OK):
                # 如果不可写，尝试创建新的日志文件
                log_file = os.path.join(log_dir, f"app_{int(time.time())}.log")
        else:
            # 尝试创建日志文件
            try:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("")
            except (OSError, IOError):
                # 如果创建失败，使用临时目录
                import tempfile
                temp_dir = tempfile.gettempdir()
                log_file = os.path.join(temp_dir, "app.log")
                logger.warning(f"无法在程序目录创建日志文件，使用临时目录: {log_file}")
    except Exception as e:
        print(f"日志文件设置失败: {e}")
        return None
    
    # 配置日志格式
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 创建文件处理器
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
    except (OSError, IOError) as e:
        print(f"无法创建日志文件处理器: {e}")
        file_handler = None
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加新的处理器
    if file_handler:
        root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 添加状态栏处理器
    status_bar_handler = StatusBarHandler()
    status_bar_handler.setLevel(logging.INFO)
    status_bar_handler.setFormatter(formatter)
    root_logger.addHandler(status_bar_handler)
    
    return root_logger

class DebugLogger:
    """
    yt-dlp 日志记录器适配器
    
    将 yt-dlp 的日志输出转换为 PyQt5 信号，实现日志信息在界面上的实时显示。
    支持 debug、warning、error 三种日志级别。
    """
    
    def __init__(self, signal: pyqtSignal):
        """
        初始化日志记录器
        
        Args:
            signal: PyQt5 信号对象，用于向界面发送日志信息
        """
        self.signal = signal

    def debug(self, msg: str) -> None:
        """
        发送调试级别日志
        
        Args:
            msg: 调试信息内容
        """
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def warning(self, msg: str) -> None:
        """
        发送警告级别日志
        
        Args:
            msg: 警告信息内容
        """
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] [警告] {msg}")

    def error(self, msg: str) -> None:
        """
        发送错误级别日志
        
        Args:
            msg: 错误信息内容
        """
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] [错误] {msg}")

# 初始化日志系统
setup_logger()
logger = logging.getLogger("VideoDownloader")
