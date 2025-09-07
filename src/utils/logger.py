"""
Logging Utilities Module

This module contains logging-related utility classes and functions, responsible for:
- Application logging system initialization and configuration
- Log file creation and management
- yt-dlp logging adapter implementation
- Log information formatting and output

Main Components:
- setup_logger: Setup logger
- logger: Global logger instance
- DebugLogger: yt-dlp logger adapter class

Author: Yeguo IDM Development Team
Version: 1.0.0
"""

import logging
import os
import time
import threading
from datetime import datetime
from PyQt5.QtCore import pyqtSignal, QObject, QTimer, QThread

# 全局状态栏更新信号
status_bar_signal = None
status_bar_signal_lock = threading.Lock()

def set_status_bar_signal(signal):
    """设置状态栏更新信号"""
    global status_bar_signal
    with status_bar_signal_lock:
        status_bar_signal = signal

def get_status_bar_signal():
    """获取状态栏更新信号"""
    global status_bar_signal
    with status_bar_signal_lock:
        return status_bar_signal

class StatusBarHandler(logging.Handler):
    """状态栏日志处理器 - 线程安全版本"""
    
    def __init__(self):
        super().__init__()
        self._last_error_time = 0
        self._error_count = 0
        self._max_errors = 10  # 最大错误次数
        self._error_reset_interval = 60  # 错误计数重置间隔（秒）
    
    def emit(self, record):
        """发送日志记录到状态栏"""
        try:
            # 检查是否在主线程中
            if QThread.currentThread() == QThread.currentThread().parent():
                # 在主线程中，直接发送
                self._send_to_status_bar(record)
            else:
                # 在子线程中，使用定时器延迟发送到主线程
                self._schedule_status_bar_update(record)
                
        except Exception as e:
            current_time = time.time()
            
            # 限制错误日志频率，避免刷屏
            if current_time - self._last_error_time > 5:  # 5秒内只记录一次
                self._last_error_time = current_time
                self._error_count += 1
                
                # 只在错误次数较少时记录，避免无限循环
                if self._error_count <= self._max_errors:
                    # 避免循环日志记录，静默处理状态栏更新失败
                    pass
                
                # 定期重置错误计数
                if current_time - self._last_error_time > self._error_reset_interval:
                    self._error_count = 0
    
    def _send_to_status_bar(self, record):
        """直接发送到状态栏"""
        signal = get_status_bar_signal()
        if signal and hasattr(signal, 'emit'):
            try:
                msg = record.getMessage()
                # 过滤掉过于频繁的日志
                if self._should_show_message(msg):
                    signal.emit(msg)
            except Exception as e:
                # 静默处理状态栏信号发送失败
                pass
    
    def _schedule_status_bar_update(self, record):
        """在子线程中调度状态栏更新"""
        try:
            # 在子线程中，直接使用信号发送到主线程
            # 避免在子线程中创建QTimer
            if hasattr(self, '_status_bar_signal') and self._status_bar_signal:
                self._status_bar_signal.emit(record.getMessage())
        except Exception:
            # 如果信号不可用，忽略这次更新
            pass
    
    def _should_show_message(self, msg):
        """判断是否应该显示消息（避免过于频繁的更新）"""
        # 过滤掉一些过于频繁的日志
        if "状态栏更新失败" in msg:
            return False
        if "download" in msg.lower() and "progress" in msg.lower():
            # 下载进度信息，限制频率
            return time.time() % 2 < 1  # 每2秒只显示一次
        return True

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
        # 静默处理日志文件设置失败，避免循环日志记录
        pass
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
        # 静默处理日志文件处理器创建失败
        pass
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
        try:
            if self.signal and hasattr(self.signal, 'emit'):
                self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        except Exception:
            # 忽略信号发送错误
            pass

    def warning(self, msg: str) -> None:
        """
        发送警告级别日志
        
        Args:
            msg: 警告信息内容
        """
        try:
            if self.signal and hasattr(self.signal, 'emit'):
                self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] [警告] {msg}")
        except Exception:
            # 忽略信号发送错误
            pass

    def error(self, msg: str) -> None:
        """
        发送错误级别日志
        
        Args:
            msg: 错误信息内容
        """
        try:
            if self.signal and hasattr(self.signal, 'emit'):
                self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] [错误] {msg}")
        except Exception:
            # 忽略信号发送错误
            pass

def get_logger(name: str = None) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称，默认为None
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    if name is None:
        return logging.getLogger("VideoDownloader")
    return logging.getLogger(name)

# 初始化日志系统
setup_logger()
logger = logging.getLogger("VideoDownloader")
