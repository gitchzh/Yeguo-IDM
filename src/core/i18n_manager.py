"""
国际化管理器

提供多语言支持功能，包括语言切换、文本翻译等。
"""

import os
import json
import locale
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QSettings
from PyQt5.QtWidgets import QApplication

from ..utils.logger import logger


class I18nManager(QObject):
    """国际化管理器"""
    
    # 语言切换信号
    language_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_language = "zh_CN"  # 默认中文
        self.translations = {}
        self.supported_languages = {
            "zh_CN": "简体中文",
            "en_US": "English"
        }
        
        # 加载设置
        self.settings = QSettings("MyCompany", "VideoDownloader")
        self.load_language_setting()
        
        # 加载翻译文件
        self.load_translations()
        
    def load_language_setting(self):
        """加载语言设置"""
        saved_language = self.settings.value("language", "")
        if saved_language and saved_language in self.supported_languages:
            self.current_language = saved_language
        else:
            # 尝试检测系统语言
            system_language = self.detect_system_language()
            if system_language in self.supported_languages:
                self.current_language = system_language
            else:
                self.current_language = "zh_CN"  # 默认中文
                
        logger.info(f"当前语言: {self.current_language}")
        
    def detect_system_language(self) -> str:
        """检测系统语言"""
        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                # 映射系统语言到支持的语言
                language_map = {
                    "zh_CN": "zh_CN",
                    "zh_TW": "zh_CN",  # 繁体中文映射到简体中文
                    "en_US": "en_US",
                    "en_GB": "en_US"   # 英式英语映射到美式英语
                }
                return language_map.get(system_locale, "zh_CN")
        except Exception as e:
            logger.warning(f"检测系统语言失败: {e}")
        return "zh_CN"
        
    def load_translations(self):
        """加载翻译文件"""
        try:
            # 获取翻译文件目录
            i18n_dir = os.path.join(os.path.dirname(__file__), "..", "i18n")
            
            for lang_code in self.supported_languages.keys():
                lang_file = os.path.join(i18n_dir, f"{lang_code}.json")
                if os.path.exists(lang_file):
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                        logger.info(f"加载语言文件: {lang_file}")
                else:
                    logger.warning(f"语言文件不存在: {lang_file}")
                    
        except Exception as e:
            logger.error(f"加载翻译文件失败: {e}")
            
    def get_text(self, key: str, default: str = None) -> str:
        """获取翻译文本"""
        try:
            if self.current_language in self.translations:
                # 支持嵌套键，如 "app.title"
                keys = key.split('.')
                value = self.translations[self.current_language]
                
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default or key
                
                return value if isinstance(value, str) else (default or key)
            else:
                return default or key
        except Exception as e:
            logger.error(f"获取翻译文本失败: {e}")
            return default or key
            
    def set_language(self, language: str):
        """设置语言"""
        if language in self.supported_languages:
            self.current_language = language
            self.settings.setValue("language", language)
            self.language_changed.emit(language)
            logger.info(f"语言已切换为: {language}")
        else:
            logger.warning(f"不支持的语言: {language}")
            
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.supported_languages.copy()
        
    def get_current_language(self) -> str:
        """获取当前语言"""
        return self.current_language
        
    def get_current_language_name(self) -> str:
        """获取当前语言名称"""
        return self.supported_languages.get(self.current_language, "简体中文")


# 全局国际化管理器实例
i18n_manager = I18nManager()


def tr(key: str, default: str = None) -> str:
    """翻译函数 - 全局快捷方式"""
    return i18n_manager.get_text(key, default)
