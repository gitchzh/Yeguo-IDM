"""
Password Dialog Module

This module defines a password input dialog for:
- Encrypted file password input
- Other scenarios requiring password verification

Author: Yeguo IDM Development Team
Version: 1.0.0
"""

import os
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QIcon

from ..core.config import Config
from ..core.i18n_manager import tr
from ..utils.logger import logger


class PasswordDialog(QDialog):
    """密码输入对话框"""
    
    def __init__(self, title: str = None, message: str = None, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyCompany", "VideoDownloader")
        self.title = title or tr("password.title")
        self.message = message or tr("password.message")
        self.password = ""
        self.remember_password = False
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(self.title)
        self.setFixedSize(400, 200)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QLabel {
                color: #333333;
                font-size: 14px;
            }
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#cancelButton {
                background-color: #6c757d;
            }
            QPushButton#cancelButton:hover {
                background-color: #5a6268;
            }
            QCheckBox {
                font-size: 13px;
                color: #666666;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # 消息标签
        message_label = QLabel(self.message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)
        main_layout.addWidget(message_label)
        
        # 密码输入框
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(tr("password.placeholder"))
        self.password_edit.returnPressed.connect(self.accept_password)
        main_layout.addWidget(self.password_edit)
        
        # 记住密码选项
        self.remember_checkbox = QCheckBox(tr("password.remember"))
        self.remember_checkbox.setChecked(False)
        main_layout.addWidget(self.remember_checkbox)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # 确定按钮
        self.ok_button = QPushButton(tr("messages.ok"))
        self.ok_button.clicked.connect(self.accept_password)
        button_layout.addWidget(self.ok_button)
        
        # 取消按钮
        self.cancel_button = QPushButton(tr("messages.cancel"))
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
        # 设置焦点
        self.password_edit.setFocus()
    
    def load_settings(self):
        """加载设置"""
        try:
            # 加载记住密码设置
            remember = self.settings.value("password/remember", False, type=bool)
            self.remember_checkbox.setChecked(remember)
            
            # 如果记住密码，加载保存的密码
            if remember:
                saved_password = self.settings.value("password/saved", "", type=str)
                if saved_password:
                    self.password_edit.setText(saved_password)
        except Exception as e:
            logger.error(f"加载密码设置失败: {e}")
    
    def save_settings(self):
        """保存设置"""
        try:
            # 保存记住密码设置
            self.settings.setValue("password/remember", self.remember_checkbox.isChecked())
            
            # 如果选择记住密码，保存密码
            if self.remember_checkbox.isChecked():
                self.settings.setValue("password/saved", self.password)
            else:
                # 如果不记住密码，清除保存的密码
                self.settings.remove("password/saved")
            
            self.settings.sync()
        except Exception as e:
            logger.error(f"保存密码设置失败: {e}")
    
    def accept_password(self):
        """接受密码输入"""
        self.password = self.password_edit.text().strip()
        
        if not self.password:
            QMessageBox.warning(self, tr("messages.input_error"), tr("password.required"))
            self.password_edit.setFocus()
            return
        
        # 保存设置
        self.save_settings()
        
        # 关闭对话框
        self.accept()
    
    def get_password(self) -> str:
        """获取输入的密码"""
        return self.password
    
    def get_remember_password(self) -> bool:
        """获取是否记住密码"""
        return self.remember_checkbox.isChecked()
    
    def set_remember_password(self, remember: bool):
        """设置是否记住密码"""
        self.remember_checkbox.setChecked(remember)
    
    def set_message(self, message: str):
        """设置对话框消息"""
        self.message = message
        # 更新标签文本
        for child in self.children():
            if isinstance(child, QLabel):
                child.setText(message)
                break


def show_password_dialog(title: str = None, message: str = None, parent=None) -> Optional[str]:
    """
    显示密码输入对话框
    
    Args:
        title: 对话框标题
        message: 提示消息
        parent: 父窗口
        
    Returns:
        str: 输入的密码，如果取消则返回None
    """
    dialog = PasswordDialog(title, message, parent)
    if dialog.exec_() == QDialog.Accepted:
        return dialog.get_password()
    return None
