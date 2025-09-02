#!/usr/bin/env python3
"""
椰果IDM - 主程序入口

这是一个功能强大的视频下载器应用程序，支持从多个视频平台下载视频。
提供直观的图形用户界面，支持批量下载、格式选择、进度监控等功能。

主要特性：
- 支持YouTube、Bilibili等多个视频平台
- 多分辨率格式选择
- 批量下载和队列管理
- 实时进度监控
- 暂停/恢复/取消功能
- 日志记录和错误处理

作者: 椰果IDM开发团队
版本: 1.0.6
"""

import sys
import os

# 添加src目录到Python路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication
from src.ui.main_window import VideoDownloader
from src.utils.logger import logger
from src.core.log_manager import log_manager


def main() -> None:
    """
    主程序入口函数
    
    初始化Qt应用程序，创建主窗口并启动事件循环。
    """
    try:
        # 验证配置参数
        from src.core.config import Config
        if not Config.validate_config():
            logger.error("配置参数验证失败，程序无法启动")
            sys.exit(1)
        
        # 创建Qt应用程序实例
        app = QApplication(sys.argv)
        
        # 设置应用程序信息
        app.setApplicationName("椰果IDM")
        app.setApplicationVersion("1.0.6")
        app.setOrganizationName("椰果IDM开发团队")
        
        # 创建主窗口
        window = VideoDownloader()
        window.show()
        
        # 启动应用程序事件循环
        logger.info("应用程序启动成功")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
