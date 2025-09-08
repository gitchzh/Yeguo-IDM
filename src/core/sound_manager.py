"""
声音通知管理模块

该模块负责管理应用程序的声音通知功能，包括：
- 下载完成声音通知
- 错误声音通知
- 系统声音播放
- 声音文件管理

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import sys
import platform
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtMultimedia import QSound, QSoundEffect
from PyQt5.QtWidgets import QApplication

from ..utils.logger import logger


class SoundManager(QObject):
    """
    声音管理器类
    
    负责管理应用程序的所有声音通知功能。
    """
    
    # 信号定义
    sound_played = pyqtSignal(str)  # 声音播放完成信号
    sound_error = pyqtSignal(str)   # 声音播放错误信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sound_enabled = True
        self.sound_effect = QSoundEffect()
        self._init_sounds()
    
    def _init_sounds(self) -> None:
        """初始化声音文件"""
        try:
            # 获取资源目录
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller打包后的路径
                resource_dir = os.path.join(sys._MEIPASS, 'resources', 'sounds')
            else:
                # 开发环境路径
                resource_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'sounds')
            
            # 确保声音目录存在
            if not os.path.exists(resource_dir):
                os.makedirs(resource_dir, exist_ok=True)
                logger.info(f"创建声音目录: {resource_dir}")
            
            # 定义声音文件路径
            self.sound_files = {
                'success': os.path.join(resource_dir, 'success.wav'),
                'error': os.path.join(resource_dir, 'error.wav'),
                'notification': os.path.join(resource_dir, 'notification.wav')
            }
            
            # 检查声音文件是否存在，如果不存在则创建默认声音
            self._create_default_sounds()
            
            logger.info("声音管理器初始化完成")
            
        except Exception as e:
            logger.error(f"声音管理器初始化失败: {e}")
            self.sound_enabled = False
    
    def _create_default_sounds(self) -> None:
        """创建默认声音文件"""
        try:
            for sound_name, sound_path in self.sound_files.items():
                if not os.path.exists(sound_path):
                    self._generate_default_sound(sound_name, sound_path)
                    
        except Exception as e:
            logger.error(f"创建默认声音文件失败: {e}")
    
    def _generate_default_sound(self, sound_name: str, sound_path: str) -> None:
        """生成默认声音文件"""
        try:
            # 使用系统默认声音
            if platform.system() == "Windows":
                if sound_name == 'success':
                    # Windows成功声音
                    self.sound_files[sound_name] = "SystemAsterisk"
                elif sound_name == 'error':
                    # Windows错误声音
                    self.sound_files[sound_name] = "SystemExclamation"
                else:
                    # Windows通知声音
                    self.sound_files[sound_name] = "SystemDefault"
            else:
                # 其他系统使用简单的提示音
                logger.info(f"为 {sound_name} 使用系统默认声音")
                
        except Exception as e:
            logger.error(f"生成默认声音失败: {e}")
    
    def set_sound_enabled(self, enabled: bool) -> None:
        """设置声音是否启用"""
        self.sound_enabled = enabled
        logger.info(f"声音通知{'启用' if enabled else '禁用'}")
    
    def play_success_sound(self) -> None:
        """播放成功声音"""
        if not self.sound_enabled:
            return
        
        try:
            self._play_sound('success')
            logger.info("播放下载完成声音")
        except Exception as e:
            logger.error(f"播放成功声音失败: {e}")
            self.sound_error.emit(str(e))
    
    def play_error_sound(self) -> None:
        """播放错误声音"""
        if not self.sound_enabled:
            return
        
        try:
            self._play_sound('error')
            logger.info("播放错误声音")
        except Exception as e:
            logger.error(f"播放错误声音失败: {e}")
            self.sound_error.emit(str(e))
    
    def play_notification_sound(self) -> None:
        """播放通知声音"""
        if not self.sound_enabled:
            return
        
        try:
            self._play_sound('notification')
            logger.info("播放通知声音")
        except Exception as e:
            logger.error(f"播放通知声音失败: {e}")
            self.sound_error.emit(str(e))
    
    def _play_sound(self, sound_name: str) -> None:
        """播放指定声音"""
        try:
            sound_path = self.sound_files.get(sound_name)
            if not sound_path:
                logger.warning(f"未找到声音文件: {sound_name}")
                return
            
            # 如果是系统声音
            if sound_path.startswith("System"):
                self._play_system_sound(sound_path)
            else:
                # 播放文件声音
                if os.path.exists(sound_path):
                    self.sound_effect.setSource(sound_path)
                    self.sound_effect.play()
                else:
                    logger.warning(f"声音文件不存在: {sound_path}")
                    
        except Exception as e:
            logger.error(f"播放声音失败: {e}")
            raise e
    
    def _play_system_sound(self, system_sound: str) -> None:
        """播放系统声音"""
        try:
            if platform.system() == "Windows":
                import winsound
                if system_sound == "SystemAsterisk":
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                elif system_sound == "SystemExclamation":
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                else:
                    winsound.MessageBeep(winsound.MB_OK)
            else:
                # 其他系统使用简单的beep
                # 使用系统默认提示音
                import sys
                if sys.platform == "win32":
                    import winsound
                    winsound.MessageBeep(winsound.MB_OK)
                else:
                    # 其他系统使用简单的beep
                    print('\a')  # ASCII bell character
                
        except Exception as e:
            logger.error(f"播放系统声音失败: {e}")
            raise e
    
    def test_sound(self) -> bool:
        """测试声音播放"""
        try:
            self.play_notification_sound()
            return True
        except Exception as e:
            logger.error(f"声音测试失败: {e}")
            return False


# 全局声音管理器实例
sound_manager = SoundManager()
