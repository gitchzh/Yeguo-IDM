#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览对话框

提供视频预览的用户界面，包括：
- 视频播放器集成
- 视频信息显示
- 预览控制界面
- 错误处理和用户反馈

作者: 椰果IDM开发团队
版本: 1.6.0
创建日期: 2025-09-10
"""

import os
import sys
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QFrame, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont

from .video_player import VideoPlayer
from ..core.i18n_manager import tr
from ..utils.logger import logger


class PreviewDialog(QDialog):
    """视频预览对话框"""
    
    # 信号定义
    preview_closed = pyqtSignal()  # 预览关闭
    preview_error = pyqtSignal(str)  # 预览错误
    
    def __init__(self, parent=None, video_info: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.video_info = video_info or {}
        self.video_player = None
        self.is_loading = False
        
        self._init_ui()
        self._connect_signals()
        self._load_video()
        
        logger.info("预览对话框初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(tr("preview.title"))
        self.setWindowIcon(self._get_icon())
        self.setModal(False)  # 非模态对话框，允许同时操作主窗口
        
        # 设置窗口大小
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 标题栏
        self._create_title_bar(main_layout)
        
        # 视频信息栏
        self._create_info_bar(main_layout)
        
        # 视频播放区域
        self._create_video_area(main_layout)
        
        # 控制按钮栏
        self._create_control_bar(main_layout)
        
        # 状态栏
        self._create_status_bar(main_layout)
    
    def _create_title_bar(self, parent_layout):
        """创建标题栏"""
        title_frame = QFrame()
        title_frame.setFrameStyle(QFrame.StyledPanel)
        title_frame.setMaximumHeight(50)
        
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(10, 5, 10, 5)
        
        # 标题
        self.title_label = QLabel(tr("preview.title"))
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        # 关闭按钮
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setToolTip(tr("preview.close"))
        self.close_button.clicked.connect(self.accept)
        title_layout.addWidget(self.close_button)
        
        parent_layout.addWidget(title_frame)
    
    def _create_info_bar(self, parent_layout):
        """创建信息栏"""
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_frame.setMaximumHeight(80)
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 5, 10, 5)
        info_layout.setSpacing(5)
        
        # 视频标题
        self.video_title_label = QLabel()
        self.video_title_label.setWordWrap(True)
        self.video_title_label.setStyleSheet("font-weight: bold; color: #333;")
        info_layout.addWidget(self.video_title_label)
        
        # 视频信息
        info_row_layout = QHBoxLayout()
        
        self.format_label = QLabel()
        self.format_label.setStyleSheet("color: #666;")
        info_row_layout.addWidget(self.format_label)
        
        info_row_layout.addStretch()
        
        self.size_label = QLabel()
        self.size_label.setStyleSheet("color: #666;")
        info_row_layout.addWidget(self.size_label)
        
        info_layout.addLayout(info_row_layout)
        parent_layout.addWidget(info_frame)
    
    def _create_video_area(self, parent_layout):
        """创建视频播放区域"""
        video_frame = QFrame()
        video_frame.setFrameStyle(QFrame.StyledPanel)
        video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        video_layout = QVBoxLayout(video_frame)
        video_layout.setContentsMargins(5, 5, 5, 5)
        
        # 视频播放器
        self.video_player = VideoPlayer(self)
        video_layout.addWidget(self.video_player)
        
        parent_layout.addWidget(video_frame)
    
    def _create_control_bar(self, parent_layout):
        """创建控制按钮栏"""
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.StyledPanel)
        control_frame.setMaximumHeight(60)
        
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        # 重新加载按钮
        self.reload_button = QPushButton(tr("preview.reload"))
        self.reload_button.setToolTip(tr("preview.reload_tooltip"))
        self.reload_button.clicked.connect(self._reload_video)
        control_layout.addWidget(self.reload_button)
        
        control_layout.addStretch()
        
        # 下载按钮
        self.download_button = QPushButton(tr("preview.download"))
        self.download_button.setToolTip(tr("preview.download_tooltip"))
        self.download_button.clicked.connect(self._download_video)
        control_layout.addWidget(self.download_button)
        
        # 关闭按钮
        self.close_dialog_button = QPushButton(tr("preview.close"))
        self.close_dialog_button.clicked.connect(self.accept)
        control_layout.addWidget(self.close_dialog_button)
        
        parent_layout.addWidget(control_frame)
    
    def _create_status_bar(self, parent_layout):
        """创建状态栏"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_frame.setMaximumHeight(30)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 2, 10, 2)
        
        self.status_label = QLabel(tr("preview.ready"))
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.loading_label = QLabel()
        self.loading_label.setStyleSheet("color: #007bff; font-size: 10px;")
        self.loading_label.hide()
        status_layout.addWidget(self.loading_label)
        
        parent_layout.addWidget(status_frame)
    
    def _get_icon(self) -> QIcon:
        """获取图标"""
        try:
            if getattr(sys, "frozen", False):
                icon_path = os.path.join(sys._MEIPASS, "resources", "logo.ico")
            else:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "logo.ico")
            
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except Exception as e:
            logger.warning(f"获取图标失败: {e}")
        
        return QIcon()
    
    def _connect_signals(self):
        """连接信号"""
        if self.video_player:
            self.video_player.error_occurred.connect(self._on_video_error)
            self.video_player.state_changed.connect(self._on_video_state_changed)
    
    def _load_video(self):
        """加载视频"""
        if not self.video_info:
            self._show_error(tr("preview.no_video_info"))
            return
        
        try:
            self.is_loading = True
            self._update_status(tr("preview.loading"))
            self.loading_label.setText("⏳")
            self.loading_label.show()
            
            # 更新视频信息显示
            self._update_video_info()
            
            # 获取视频URL
            video_url = self._get_video_url()
            if not video_url:
                self._show_error(tr("preview.no_video_url"))
                return
            
            # 检查URL类型并处理
            if self._is_webpage_url(video_url):
                # 如果是网页URL，显示友好的提示信息
                self._show_webpage_url_info(video_url)
                return
            
            # 加载视频
            if self.video_player.load_video(video_url):
                self._update_status(tr("preview.loaded"))
                logger.info(f"视频预览加载成功: {video_url}")
            else:
                self._show_error(tr("preview.load_failed"))
            
        except Exception as e:
            logger.error(f"加载视频失败: {e}")
            self._show_error(f"{tr('preview.load_failed')}: {str(e)}")
        finally:
            self.is_loading = False
            self.loading_label.hide()
    
    def _update_video_info(self):
        """更新视频信息显示"""
        try:
            # 视频标题
            title = self.video_info.get('title', tr("preview.unknown_title"))
            self.video_title_label.setText(title)
            
            # 格式信息
            format_info = self.video_info.get('format', '')
            ext = self.video_info.get('ext', '')
            if format_info and ext:
                self.format_label.setText(f"{tr('preview.format')}: {format_info} ({ext})")
            else:
                self.format_label.setText(tr("preview.format_unknown"))
            
            # 文件大小
            filesize = self.video_info.get('filesize', 0)
            if filesize > 0:
                from ..utils.file_utils import format_size
                self.size_label.setText(f"{tr('preview.size')}: {format_size(filesize)}")
            else:
                self.size_label.setText(tr("preview.size_unknown"))
                
        except Exception as e:
            logger.error(f"更新视频信息失败: {e}")
    
    def _get_video_url(self) -> Optional[str]:
        """获取视频URL"""
        try:
            # 优先使用直接URL
            url = self.video_info.get('url')
            if url:
                return url
            
            # 尝试从其他字段获取
            for key in ['download_url', 'webpage_url', 'original_url']:
                url = self.video_info.get(key)
                if url:
                    return url
            
            return None
            
        except Exception as e:
            logger.error(f"获取视频URL失败: {e}")
            return None
    
    def _is_webpage_url(self, url: str) -> bool:
        """检查是否为网页URL"""
        if not url:
            return False
        
        # 检查是否为常见的视频网站URL
        webpage_indicators = [
            'bilibili.com/video/',
            'youtube.com/watch',
            'youtu.be/',
            'vimeo.com/',
            'dailymotion.com/video/',
            'twitch.tv/',
            'douyin.com/video/',
            'kuaishou.com/video/'
        ]
        
        return any(indicator in url.lower() for indicator in webpage_indicators)
    
    def _get_actual_video_url(self, webpage_url: str) -> Optional[str]:
        """获取实际视频流URL"""
        try:
            # 这里应该使用yt-dlp获取实际视频流URL
            # 但由于预览功能需要快速响应，我们暂时返回None
            # 在实际应用中，可以在这里集成yt-dlp来获取视频流URL
            
            logger.warning(f"无法获取视频流URL，网页URL: {webpage_url}")
            logger.info("提示：预览功能需要实际的视频流URL，当前使用网页URL可能无法播放")
            
            return None
            
        except Exception as e:
            logger.error(f"获取实际视频流URL失败: {e}")
            return None
    
    def _reload_video(self):
        """重新加载视频"""
        self._load_video()
    
    def _download_video(self):
        """下载视频"""
        try:
            # 发送下载信号到主窗口
            if hasattr(self.parent(), 'download_video_from_preview'):
                self.parent().download_video_from_preview(self.video_info)
            else:
                QMessageBox.information(self, tr("preview.download"), tr("preview.download_info"))
        except Exception as e:
            logger.error(f"下载视频失败: {e}")
            QMessageBox.warning(self, tr("preview.download"), f"{tr('preview.download_failed')}: {str(e)}")
    
    def _on_video_error(self, error_msg: str):
        """视频播放错误"""
        logger.error(f"视频播放错误: {error_msg}")
        self._show_error(error_msg)
        self.preview_error.emit(error_msg)
    
    def _on_video_state_changed(self, state):
        """视频状态改变"""
        try:
            from PyQt5.QtMultimedia import QMediaPlayer
            
            if state == QMediaPlayer.PlayingState:
                self._update_status(tr("preview.playing"))
            elif state == QMediaPlayer.PausedState:
                self._update_status(tr("preview.paused"))
            elif state == QMediaPlayer.StoppedState:
                self._update_status(tr("preview.stopped"))
            else:
                self._update_status(tr("preview.ready"))
                
        except Exception as e:
            logger.error(f"处理视频状态改变失败: {e}")
    
    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_label.setText(message)
        logger.debug(f"预览状态: {message}")
    
    def _show_error(self, error_msg: str):
        """显示错误信息"""
        self._update_status(f"❌ {error_msg}")
        QMessageBox.critical(self, tr("preview.error"), error_msg)
    
    def _show_webpage_url_info(self, url: str):
        """显示网页URL的友好提示信息"""
        try:
            self._update_status("ℹ️ 检测到网页URL，无法直接预览")
            
            # 创建友好的信息对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(tr("preview.webpage_url_title"))
            msg_box.setIcon(QMessageBox.Information)
            
            # 设置消息内容
            message = tr("preview.webpage_url_message").format(url=url)
            msg_box.setText(message)
            
            # 添加详细说明
            detailed_text = tr("preview.webpage_url_details")
            msg_box.setDetailedText(detailed_text)
            
            # 添加按钮
            msg_box.addButton(tr("preview.download_first"), QMessageBox.AcceptRole)
            msg_box.addButton(tr("preview.open_browser"), QMessageBox.ActionRole)
            msg_box.addButton(tr("preview.close"), QMessageBox.RejectRole)
            
            # 显示对话框
            result = msg_box.exec_()
            
            if result == 0:  # 下载后预览
                self._download_and_preview()
            elif result == 1:  # 浏览器打开
                self._open_in_browser(url)
            # result == 2 是关闭，不需要特殊处理
            
        except Exception as e:
            logger.error(f"显示网页URL信息失败: {e}")
            self._show_error(tr("preview.cannot_get_stream"))
    
    def _download_and_preview(self):
        """下载后预览"""
        try:
            # 发送下载信号到主窗口
            if hasattr(self.parent(), 'download_video_from_preview'):
                self.parent().download_video_from_preview(self.video_info)
                self._update_status("📥 已发送下载请求，请等待下载完成后使用本地文件预览")
            else:
                QMessageBox.information(self, tr("preview.download"), tr("preview.download_info"))
        except Exception as e:
            logger.error(f"下载视频失败: {e}")
            QMessageBox.warning(self, tr("preview.download"), f"{tr('preview.download_failed')}: {str(e)}")
    
    def _open_in_browser(self, url: str):
        """在浏览器中打开"""
        try:
            import webbrowser
            webbrowser.open(url)
            self._update_status("🌐 已在浏览器中打开视频")
            logger.info(f"在浏览器中打开视频: {url}")
        except Exception as e:
            logger.error(f"在浏览器中打开视频失败: {e}")
            QMessageBox.warning(self, tr("preview.error"), f"无法在浏览器中打开视频: {str(e)}")
    
    def get_video_info(self) -> Dict[str, Any]:
        """获取视频信息"""
        return self.video_info.copy()
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            if self.video_player:
                self.video_player.cleanup()
            self.preview_closed.emit()
            logger.info("预览对话框关闭")
        except Exception as e:
            logger.error(f"关闭预览对话框失败: {e}")
        finally:
            event.accept()
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)
