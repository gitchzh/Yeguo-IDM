#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览管理器

管理视频预览功能，包括：
- 预览对话框管理
- 视频URL处理
- 预览缓存管理
- 错误处理和重试机制

作者: 椰果IDM开发团队
版本: 1.6.0
创建日期: 2025-09-10
"""

import os
import sys
import tempfile
import shutil
from typing import Optional, Dict, Any, List
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from ..ui.preview_dialog import PreviewDialog
from ..utils.logger import logger
from ..core.i18n_manager import tr


class PreviewManager(QObject):
    """预览管理器"""
    
    # 信号定义
    preview_opened = pyqtSignal(dict)  # 预览打开
    preview_closed = pyqtSignal(dict)  # 预览关闭
    preview_error = pyqtSignal(str)  # 预览错误
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_previews: List[PreviewDialog] = []
        self.preview_cache_dir = None
        self.max_previews = 3  # 最大同时预览数量
        
        self._init_cache_dir()
        logger.info("预览管理器初始化完成")
    
    def _init_cache_dir(self):
        """初始化缓存目录"""
        try:
            # 创建临时缓存目录
            self.preview_cache_dir = os.path.join(tempfile.gettempdir(), "ygmdm_preview_cache")
            os.makedirs(self.preview_cache_dir, exist_ok=True)
            logger.info(f"预览缓存目录: {self.preview_cache_dir}")
        except Exception as e:
            logger.error(f"创建预览缓存目录失败: {e}")
            self.preview_cache_dir = None
    
    def open_preview(self, video_info: Dict[str, Any], parent_widget=None) -> bool:
        """打开视频预览"""
        try:
            # 检查最大预览数量
            if len(self.active_previews) >= self.max_previews:
                QMessageBox.warning(
                    parent_widget,
                    tr("preview.max_previews_title"),
                    tr("preview.max_previews_message").format(max=self.max_previews)
                )
                return False
            
            # 验证视频信息
            if not self._validate_video_info(video_info):
                QMessageBox.warning(
                    parent_widget,
                    tr("preview.invalid_info_title"),
                    tr("preview.invalid_info_message")
                )
                return False
            
            # 创建预览对话框
            preview_dialog = PreviewDialog(parent_widget, video_info)
            
            # 连接信号
            preview_dialog.preview_closed.connect(lambda: self._on_preview_closed(preview_dialog))
            preview_dialog.preview_error.connect(self._on_preview_error)
            
            # 添加到活动预览列表
            self.active_previews.append(preview_dialog)
            
            # 显示预览对话框
            preview_dialog.show()
            preview_dialog.raise_()
            preview_dialog.activateWindow()
            
            # 发送信号
            self.preview_opened.emit(video_info)
            
            logger.info(f"视频预览已打开: {video_info.get('title', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"打开视频预览失败: {e}")
            self.preview_error.emit(str(e))
            return False
    
    def _validate_video_info(self, video_info: Dict[str, Any]) -> bool:
        """验证视频信息"""
        try:
            if not video_info:
                return False
            
            # 检查必要的字段
            required_fields = ['title']
            for field in required_fields:
                if field not in video_info or not video_info[field]:
                    logger.warning(f"视频信息缺少必要字段: {field}")
                    return False
            
            # 检查URL字段
            url_fields = ['url', 'download_url', 'webpage_url', 'original_url']
            has_url = any(video_info.get(field) for field in url_fields)
            
            if not has_url:
                logger.warning("视频信息中没有找到有效的URL")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证视频信息失败: {e}")
            return False
    
    def _on_preview_closed(self, preview_dialog: PreviewDialog):
        """预览关闭处理"""
        try:
            if preview_dialog in self.active_previews:
                self.active_previews.remove(preview_dialog)
                
                # 获取视频信息
                video_info = preview_dialog.get_video_info()
                
                # 发送信号
                self.preview_closed.emit(video_info)
                
                logger.info(f"视频预览已关闭: {video_info.get('title', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"处理预览关闭失败: {e}")
    
    def _on_preview_error(self, error_msg: str):
        """预览错误处理"""
        logger.error(f"预览错误: {error_msg}")
        self.preview_error.emit(error_msg)
    
    def close_all_previews(self):
        """关闭所有预览"""
        try:
            for preview_dialog in self.active_previews.copy():
                preview_dialog.close()
            
            self.active_previews.clear()
            logger.info("所有预览已关闭")
            
        except Exception as e:
            logger.error(f"关闭所有预览失败: {e}")
    
    def get_active_preview_count(self) -> int:
        """获取活动预览数量"""
        return len(self.active_previews)
    
    def get_active_previews_info(self) -> List[Dict[str, Any]]:
        """获取活动预览信息"""
        try:
            previews_info = []
            for preview_dialog in self.active_previews:
                if preview_dialog.isVisible():
                    previews_info.append(preview_dialog.get_video_info())
            return previews_info
        except Exception as e:
            logger.error(f"获取活动预览信息失败: {e}")
            return []
    
    def cleanup_cache(self):
        """清理预览缓存"""
        try:
            if self.preview_cache_dir and os.path.exists(self.preview_cache_dir):
                shutil.rmtree(self.preview_cache_dir)
                logger.info("预览缓存已清理")
        except Exception as e:
            logger.error(f"清理预览缓存失败: {e}")
    
    def get_cache_size(self) -> int:
        """获取缓存大小"""
        try:
            if not self.preview_cache_dir or not os.path.exists(self.preview_cache_dir):
                return 0
            
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(self.preview_cache_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            
            return total_size
            
        except Exception as e:
            logger.error(f"获取缓存大小失败: {e}")
            return 0
    
    def format_cache_size(self, size_bytes: int) -> str:
        """格式化缓存大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ("B", "KB", "MB", "GB")
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def cleanup(self):
        """清理资源"""
        try:
            self.close_all_previews()
            self.cleanup_cache()
            logger.info("预览管理器资源清理完成")
        except Exception as e:
            logger.error(f"预览管理器资源清理失败: {e}")


# 全局预览管理器实例
preview_manager = PreviewManager()
