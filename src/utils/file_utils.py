"""
文件工具模块

该模块包含文件操作相关的工具函数，负责：
- 文件名清理和合法性检查
- 文件大小格式化显示
- FFmpeg路径查找和验证
- 文件系统操作辅助功能

主要函数：
- sanitize_filename: 清理文件名，确保合法性
- format_size: 格式化文件大小显示
- get_ffmpeg_path: 获取FFmpeg可执行文件路径
- check_ffmpeg: 检查FFmpeg是否可用

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import re
import sys
import webbrowser
from typing import Optional
from PyQt5.QtWidgets import QMessageBox

from ..core.config import Config
from .logger import logger


def sanitize_filename(filename: str, save_path: str) -> str:
    """
    清理文件名，确保合法性
    
    移除文件名中的非法字符，限制长度，并处理重复文件名。
    
    Args:
        filename: 原始文件名
        save_path: 保存路径
        
    Returns:
        str: 清理后的合法文件名
    """
    # 验证保存路径的安全性
    if not os.path.isabs(save_path):
        save_path = os.path.abspath(save_path)
    
    # 检查路径遍历攻击
    if ".." in save_path or save_path.startswith("/"):
        logger.warning(f"检测到可疑路径: {save_path}")
        save_path = os.getcwd()
    
    # 移除Windows文件系统不允许的字符
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)
    
    # 移除路径分隔符，防止路径遍历
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # 限制文件名长度
    filename = filename[:Config.MAX_FILENAME_LENGTH]
    
    # 确保文件名不为空
    if not filename.strip():
        filename = "unnamed_file"
    
    # 处理重复文件名
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    max_attempts = 100  # 限制最大尝试次数
    
    # 如果文件已存在，添加数字后缀
    while os.path.exists(os.path.join(save_path, new_filename)):
        new_filename = f"{base}_{counter}{ext}"
        counter += 1
        
        # 防止无限循环
        if counter > max_attempts:
            logger.error(f"文件名冲突过多，达到最大尝试次数 ({max_attempts}): {filename}")
            # 使用时间戳作为后缀
            import time
            timestamp = int(time.time())
            new_filename = f"{base}_{timestamp}{ext}"
            break
        
        # 检查文件名长度是否超过限制
        if len(new_filename) > Config.MAX_FILENAME_LENGTH:
            # 截断基础名称
            max_base_length = Config.MAX_FILENAME_LENGTH - len(f"_{counter}{ext}")
            if max_base_length > 0:
                base = base[:max_base_length]
                new_filename = f"{base}_{counter}{ext}"
            else:
                # 如果仍然太长，使用时间戳
                import time
                timestamp = int(time.time())
                new_filename = f"file_{timestamp}{ext}"
                break
        
    return new_filename


def format_size(bytes_size: Optional[int]) -> str:
    """
    格式化文件大小显示
    
    将字节数转换为人类可读的文件大小格式（B、KB、MB、GB）。
    
    Args:
        bytes_size: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小字符串
    """
    if not bytes_size or bytes_size <= 0:
        return "未知"
        
    # 按1024进制转换单位
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
        
    return f"{bytes_size:.2f} GB"


def get_ffmpeg_path(save_path: str) -> Optional[str]:
    """
    获取 FFmpeg 可执行文件路径
    
    按优先级查找FFmpeg：
    1. 打包后的可执行文件
    2. resources目录中的FFmpeg
    3. 保存路径中的FFmpeg
    
    Args:
        save_path: 保存路径
        
    Returns:
        Optional[str]: FFmpeg路径，如果未找到则返回None
    """
    # 检查是否为打包后的可执行文件
    if getattr(sys, "frozen", False):
        ffmpeg_exe = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
    
    # 检查resources目录中是否有FFmpeg
    resources_ffmpeg = os.path.join("resources", "ffmpeg.exe")
    if os.path.exists(resources_ffmpeg):
        return resources_ffmpeg
            
    # 检查保存路径中是否有FFmpeg
    ffmpeg_path = os.path.join(save_path, "ffmpeg.exe")
    if os.path.exists(ffmpeg_path):
        return ffmpeg_path
        
    logger.warning("FFmpeg 未找到")
    return None


def check_ffmpeg(ffmpeg_path: Optional[str], parent_widget=None) -> bool:
    """
    检查 FFmpeg 是否可用
    
    如果FFmpeg未找到，提示用户并提供下载链接。
    
    Args:
        ffmpeg_path: FFmpeg路径
        parent_widget: 父窗口部件
        
    Returns:
        bool: FFmpeg是否可用
    """
    if not ffmpeg_path:
        msg_box = QMessageBox()
        msg_box.setWindowTitle("FFmpeg 未找到")
        msg_box.setText("FFmpeg 未找到，是否打开官网下载？\n请将 ffmpeg.exe 放入保存路径后重试。")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮中文文本
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        reply = msg_box.exec_()
        if reply == QMessageBox.Yes:
            webbrowser.open("https://ffmpeg.org/download.html")
        return False
    return True
