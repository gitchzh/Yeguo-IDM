"""
yt-dlp Logger Module

Provides unified yt-dlp logging functionality to avoid code duplication.

Author: Yeguo IDM Development Team
Version: 1.0.0
"""

from PyQt5.QtCore import QObject, pyqtSignal


class YTDlpLogger(QObject):
    """yt-dlp日志记录器，将输出重定向到我们的信号"""
    
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
    
    def debug(self, msg):
        """调试日志"""
        self.signal.emit(msg)
    
    def warning(self, msg):
        """警告日志"""
        self.signal.emit(f"[WARNING] {msg}")
    
    def error(self, msg):
        """错误日志"""
        self.signal.emit(f"[ERROR] {msg}")
    
    def info(self, msg):
        """信息日志"""
        self.signal.emit(f"[INFO] {msg}")
