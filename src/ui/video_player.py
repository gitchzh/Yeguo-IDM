#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频播放器组件

提供视频预览功能的核心播放器组件，包括：
- 视频播放控制
- 进度条和音量控制
- 全屏播放支持
- 键盘快捷键支持

作者: 椰果IDM开发团队
版本: 1.6.0
创建日期: 2025-09-10
"""

import os
import sys
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QFrame, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QUrl, QSize
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

from ..core.i18n_manager import tr
from ..utils.logger import logger


class VideoPlayer(QWidget):
    """视频播放器组件"""
    
    # 信号定义
    position_changed = pyqtSignal(int)  # 播放位置改变
    duration_changed = pyqtSignal(int)  # 视频时长改变
    state_changed = pyqtSignal(QMediaPlayer.State)  # 播放状态改变
    error_occurred = pyqtSignal(str)  # 播放错误
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.is_fullscreen = False
        
        self._init_ui()
        self._connect_signals()
        self._setup_shortcuts()
        
        logger.info("视频播放器组件初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 视频显示区域
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setMinimumSize(640, 360)
        layout.addWidget(self.video_widget)
        
        # 控制面板
        self._create_control_panel(layout)
        
        # 设置媒体播放器
        self.media_player.setVideoOutput(self.video_widget)
    
    def _create_control_panel(self, parent_layout):
        """创建控制面板"""
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.StyledPanel)
        control_frame.setMaximumHeight(80)
        
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 5, 10, 5)
        control_layout.setSpacing(5)
        
        # 进度条
        progress_layout = QHBoxLayout()
        
        self.position_label = QLabel("00:00")
        self.position_label.setMinimumWidth(50)
        self.position_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.position_label)
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        progress_layout.addWidget(self.progress_slider)
        
        self.duration_label = QLabel("00:00")
        self.duration_label.setMinimumWidth(50)
        self.duration_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.duration_label)
        
        control_layout.addLayout(progress_layout)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        
        # 播放/暂停按钮
        self.play_button = QPushButton()
        self.play_button.setIcon(self._get_icon("play"))
        self.play_button.setToolTip(tr("preview.play"))
        self.play_button.clicked.connect(self._toggle_play_pause)
        self.play_button.setFixedSize(40, 30)
        button_layout.addWidget(self.play_button)
        
        # 停止按钮
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self._get_icon("stop"))
        self.stop_button.setToolTip(tr("preview.stop"))
        self.stop_button.clicked.connect(self._stop)
        self.stop_button.setFixedSize(40, 30)
        button_layout.addWidget(self.stop_button)
        
        # 音量控制
        button_layout.addWidget(QLabel(tr("preview.volume")))
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        button_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("80%")
        self.volume_label.setMinimumWidth(30)
        button_layout.addWidget(self.volume_label)
        
        # 全屏按钮
        self.fullscreen_button = QPushButton()
        self.fullscreen_button.setIcon(self._get_icon("fullscreen"))
        self.fullscreen_button.setToolTip(tr("preview.fullscreen"))
        self.fullscreen_button.clicked.connect(self._toggle_fullscreen)
        self.fullscreen_button.setFixedSize(40, 30)
        button_layout.addWidget(self.fullscreen_button)
        
        control_layout.addLayout(button_layout)
        parent_layout.addWidget(control_frame)
    
    def _get_icon(self, icon_name: str) -> QIcon:
        """获取图标"""
        # 使用系统默认图标或文本
        icon_map = {
            "play": "▶",
            "pause": "⏸",
            "stop": "⏹",
            "fullscreen": "⛶"
        }
        
        # 这里可以替换为实际的图标文件
        return QIcon()
    
    def _connect_signals(self):
        """连接信号"""
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.stateChanged.connect(self._on_state_changed)
        self.media_player.error.connect(self._on_error)
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        # 空格键：播放/暂停
        self.play_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.play_shortcut.activated.connect(self._toggle_play_pause)
        
        # ESC键：退出全屏
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.escape_shortcut.activated.connect(self._exit_fullscreen)
        
        # F键：全屏切换
        self.fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F), self)
        self.fullscreen_shortcut.activated.connect(self._toggle_fullscreen)
    
    def load_video(self, url: str) -> bool:
        """加载视频"""
        try:
            # 检查URL类型
            if url.startswith(('http://', 'https://')):
                # 网络URL
                if self._is_webpage_url(url):
                    logger.warning(f"检测到网页URL，可能无法直接播放: {url}")
                    logger.info("提示：QMediaPlayer无法直接播放网页URL，需要实际的视频流URL")
                    # 不直接返回错误，让预览对话框处理
                    return False
                
                media_content = QMediaContent(QUrl(url))
            else:
                # 本地文件
                media_content = QMediaContent(QUrl.fromLocalFile(url))
            
            # 设置媒体内容
            self.media_player.setMedia(media_content)
            
            # 设置播放器属性以提高兼容性
            self.media_player.setVolume(80)  # 设置默认音量
            
            logger.info(f"视频加载成功: {url}")
            return True
            
        except Exception as e:
            logger.error(f"视频加载失败: {e}")
            self.error_occurred.emit(str(e))
            return False
    
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
    
    def _toggle_play_pause(self):
        """切换播放/暂停"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def _stop(self):
        """停止播放"""
        self.media_player.stop()
    
    def _on_slider_moved(self, position: int):
        """进度条拖动"""
        self.media_player.setPosition(position)
    
    def _on_volume_changed(self, volume: int):
        """音量改变"""
        self.media_player.setVolume(volume)
        self.volume_label.setText(f"{volume}%")
    
    def _on_position_changed(self, position: int):
        """播放位置改变"""
        self.progress_slider.setValue(position)
        self.position_label.setText(self._format_time(position))
        self.position_changed.emit(position)
    
    def _on_duration_changed(self, duration: int):
        """视频时长改变"""
        self.progress_slider.setRange(0, duration)
        self.duration_label.setText(self._format_time(duration))
        self.duration_changed.emit(duration)
    
    def _on_state_changed(self, state: QMediaPlayer.State):
        """播放状态改变"""
        if state == QMediaPlayer.PlayingState:
            self.play_button.setIcon(self._get_icon("pause"))
            self.play_button.setToolTip(tr("preview.pause"))
        else:
            self.play_button.setIcon(self._get_icon("play"))
            self.play_button.setToolTip(tr("preview.play"))
        
        self.state_changed.emit(state)
    
    def _on_error(self, error: QMediaPlayer.Error):
        """播放错误"""
        # 获取详细的错误信息
        error_string = self.media_player.errorString()
        
        # 根据错误类型提供更友好的错误信息
        if error == QMediaPlayer.ResourceError:
            if "0x80040218" in error_string or "DirectShowPlayerService" in error_string:
                error_msg = "DirectShow播放器错误：无法播放此视频格式。请尝试下载视频后本地播放。"
            else:
                error_msg = f"资源错误: {error_string}"
        elif error == QMediaPlayer.FormatError:
            error_msg = f"格式错误: 不支持的视频格式。{error_string}"
        elif error == QMediaPlayer.NetworkError:
            error_msg = f"网络错误: 无法访问视频资源。{error_string}"
        elif error == QMediaPlayer.AccessDeniedError:
            error_msg = f"访问被拒绝: {error_string}"
        else:
            error_msg = f"播放错误 ({error}): {error_string}"
        
        logger.error(f"视频播放错误: {error_msg}")
        self.error_occurred.emit(error_msg)
    
    def _toggle_fullscreen(self):
        """切换全屏"""
        if self.is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()
    
    def _enter_fullscreen(self):
        """进入全屏"""
        self.is_fullscreen = True
        self.video_widget.setFullScreen(True)
        self.fullscreen_button.setIcon(self._get_icon("exit_fullscreen"))
        self.fullscreen_button.setToolTip(tr("preview.exit_fullscreen"))
    
    def _exit_fullscreen(self):
        """退出全屏"""
        self.is_fullscreen = False
        self.video_widget.setFullScreen(False)
        self.fullscreen_button.setIcon(self._get_icon("fullscreen"))
        self.fullscreen_button.setToolTip(tr("preview.fullscreen"))
    
    def _format_time(self, milliseconds: int) -> str:
        """格式化时间"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_video_info(self) -> Dict[str, Any]:
        """获取视频信息"""
        return {
            "duration": self.media_player.duration(),
            "position": self.media_player.position(),
            "volume": self.media_player.volume(),
            "state": self.media_player.state(),
            "is_fullscreen": self.is_fullscreen
        }
    
    def set_volume(self, volume: int):
        """设置音量"""
        self.volume_slider.setValue(volume)
        self.media_player.setVolume(volume)
    
    def seek(self, position: int):
        """跳转到指定位置"""
        self.media_player.setPosition(position)
    
    def cleanup(self):
        """清理资源"""
        try:
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())
            logger.info("视频播放器资源清理完成")
        except Exception as e:
            logger.error(f"视频播放器资源清理失败: {e}")
