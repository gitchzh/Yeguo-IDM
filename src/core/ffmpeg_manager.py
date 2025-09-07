#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg管理器 - 优先使用yt-dlp内置处理，系统FFmpeg作为备用
"""

import os
import subprocess
import shutil
from typing import Optional, Dict, Any
from ..utils.logger import logger

class FFmpegManager:
    """FFmpeg管理器 - 无需本地FFmpeg文件"""
    
    def __init__(self):
        self.ffmpeg_path = None
        self.ffmpeg_available = False
        self._detect_ffmpeg()
    
    def _detect_ffmpeg(self):
        """检测可用的FFmpeg"""
        # 方法1: 检测系统FFmpeg
        system_ffmpeg = self._find_system_ffmpeg()
        if system_ffmpeg:
            self.ffmpeg_path = system_ffmpeg
            self.ffmpeg_available = True
            logger.info(f"检测到系统FFmpeg: {system_ffmpeg}")
            return
        
        # 方法2: 检测PATH中的FFmpeg
        path_ffmpeg = shutil.which("ffmpeg")
        if path_ffmpeg:
            self.ffmpeg_path = path_ffmpeg
            self.ffmpeg_available = True
            logger.info(f"检测到PATH中的FFmpeg: {path_ffmpeg}")
            return
        
        # 方法3: 使用yt-dlp内置处理（推荐）
        logger.info("未检测到系统FFmpeg，将使用yt-dlp内置处理")
        self.ffmpeg_available = True  # yt-dlp内置处理可用
        self.ffmpeg_path = "yt-dlp-builtin"
    
    def _find_system_ffmpeg(self) -> Optional[str]:
        """查找系统安装的FFmpeg"""
        common_paths = [
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe",
            os.path.expanduser("~/ffmpeg/bin/ffmpeg"),
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def is_available(self) -> bool:
        """检查FFmpeg是否可用"""
        return self.ffmpeg_available
    
    def get_ffmpeg_location(self) -> str:
        """获取FFmpeg位置"""
        if self.ffmpeg_path == "yt-dlp-builtin":
            return "auto"  # yt-dlp会自动处理
        return self.ffmpeg_path or "auto"
    
    def get_method(self) -> str:
        """获取FFmpeg使用方法"""
        if self.ffmpeg_path == "yt-dlp-builtin":
            return "yt-dlp-builtin"
        elif self.ffmpeg_path:
            return "system"
        else:
            return "auto"
    
    def get_ffmpeg_path(self) -> Optional[str]:
        """获取FFmpeg路径"""
        if self.ffmpeg_path == "yt-dlp-builtin":
            return None  # yt-dlp内置处理
        return self.ffmpeg_path
    
    def get_ffmpeg_options(self) -> Dict[str, Any]:
        """获取FFmpeg配置选项"""
        if self.ffmpeg_path == "yt-dlp-builtin":
            # 使用yt-dlp内置处理
            return {
                "prefer_ffmpeg": True,
                "ffmpeg_location": "auto",
                "merge_output_format": "mp4",
                "postprocessors": [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            }
        else:
            # 使用系统FFmpeg
            return {
                "prefer_ffmpeg": True,
                "ffmpeg_location": self.ffmpeg_path,
                "merge_output_format": "mp4",
                "postprocessors": [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            }
    
    def test_ffmpeg(self) -> bool:
        """测试FFmpeg功能"""
        if self.ffmpeg_path == "yt-dlp-builtin":
            logger.info("使用yt-dlp内置FFmpeg处理")
            return True
        
        if not self.ffmpeg_path:
            return False
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("FFmpeg测试成功")
                return True
            else:
                logger.warning(f"FFmpeg测试失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"FFmpeg测试异常: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """获取FFmpeg信息"""
        info = {
            "available": self.ffmpeg_available,
            "type": "system" if self.ffmpeg_path != "yt-dlp-builtin" else "yt-dlp-builtin",
            "path": self.ffmpeg_path,
        }
        
        if self.ffmpeg_path and self.ffmpeg_path != "yt-dlp-builtin":
            try:
                result = subprocess.run(
                    [self.ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[0]
                    info["version"] = version_line
            except Exception as e:
                info["error"] = str(e)
        
        return info

# 全局FFmpeg管理器实例
ffmpeg_manager = FFmpegManager()

def get_ffmpeg_manager() -> FFmpegManager:
    """获取FFmpeg管理器实例"""
    return ffmpeg_manager

def is_ffmpeg_available() -> bool:
    """检查FFmpeg是否可用"""
    return ffmpeg_manager.is_available()

def get_ffmpeg_location() -> str:
    """获取FFmpeg位置"""
    return ffmpeg_manager.get_ffmpeg_location()

def get_ffmpeg_options() -> Dict[str, Any]:
    """获取FFmpeg配置选项"""
    return ffmpeg_manager.get_ffmpeg_options()
