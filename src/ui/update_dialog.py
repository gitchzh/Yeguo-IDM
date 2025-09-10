#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软件更新对话框

该模块提供软件更新的用户界面，包括：
- 更新检查对话框
- 更新下载进度显示
- 更新信息展示
- 用户交互控制

主要类：
- UpdateDialog: 更新对话框主类
- UpdateProgressDialog: 更新进度对话框

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import sys
import subprocess
from typing import Optional
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QProgressBar, QGroupBox, QFormLayout, QMessageBox,
    QCheckBox, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon

from ..core.update_manager import update_manager, VersionInfo
from ..core.i18n_manager import tr
from ..utils.logger import logger


class UpdateDialog(QDialog):
    """更新对话框"""
    
    def __init__(self, parent=None, version_info: Optional[VersionInfo] = None):
        super().__init__(parent)
        self.version_info = version_info
        self.download_path = ""
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(tr("update.title"))
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel(tr("update.title"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        if self.version_info:
            # 显示更新信息
            self.setup_update_info(layout)
        else:
            # 显示检查更新界面
            self.setup_check_interface(layout)
        
        # 按钮布局
        self.setup_buttons(layout)
        
        self.setLayout(layout)
    
    def setup_update_info(self, layout):
        """设置更新信息显示"""
        # 版本信息组
        version_group = QGroupBox(tr("update.version_info"))
        version_layout = QFormLayout()
        
        # 当前版本
        current_version_label = QLabel(tr("update.current_version"))
        current_version_value = QLabel(f"v{update_manager.checker.current_version if update_manager.checker else '1.6.0'}")
        current_version_value.setStyleSheet("color: #666;")
        version_layout.addRow(current_version_label, current_version_value)
        
        # 最新版本
        latest_version_label = QLabel(tr("update.latest_version"))
        latest_version_value = QLabel(f"v{self.version_info.version}")
        latest_version_value.setStyleSheet("color: #007bff; font-weight: bold;")
        version_layout.addRow(latest_version_label, latest_version_value)
        
        # 发布日期
        release_date_label = QLabel(tr("update.release_date"))
        release_date_value = QLabel(self.version_info.release_date)
        release_date_value.setStyleSheet("color: #666;")
        version_layout.addRow(release_date_label, release_date_value)
        
        # 文件大小
        if self.version_info.file_size > 0:
            file_size_label = QLabel(tr("update.file_size"))
            file_size_mb = self.version_info.file_size / (1024 * 1024)
            file_size_value = QLabel(f"{file_size_mb:.1f} MB")
            file_size_value.setStyleSheet("color: #666;")
            version_layout.addRow(file_size_label, file_size_value)
        
        # 更新源
        source_label = QLabel(tr("update.source"))
        source_text = self.version_info.source.upper()
        if self.version_info.source == "gitee":
            source_text = "码云 (Gitee)"
        elif self.version_info.source == "github":
            source_text = "GitHub"
        source_value = QLabel(source_text)
        source_value.setStyleSheet("color: #28a745; font-weight: bold;")
        version_layout.addRow(source_label, source_value)
        
        version_group.setLayout(version_layout)
        layout.addWidget(version_group)
        
        # 更新说明
        if self.version_info.release_notes:
            notes_group = QGroupBox(tr("update.release_notes"))
            notes_layout = QVBoxLayout()
            
            notes_text = QTextEdit()
            notes_text.setPlainText(self.version_info.release_notes)
            notes_text.setMaximumHeight(120)
            notes_text.setReadOnly(True)
            notes_layout.addWidget(notes_text)
            
            notes_group.setLayout(notes_layout)
            layout.addWidget(notes_group)
    
    def setup_check_interface(self, layout):
        """设置检查更新界面"""
        # 检查状态
        self.status_label = QLabel(tr("update.checking"))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #007bff; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        layout.addWidget(self.progress_bar)
        
        # 自动检查选项
        self.auto_check_checkbox = QCheckBox(tr("update.auto_check"))
        self.auto_check_checkbox.setChecked(True)
        layout.addWidget(self.auto_check_checkbox)
    
    def setup_buttons(self, layout):
        """设置按钮"""
        button_layout = QHBoxLayout()
        
        if self.version_info:
            # 有更新时的按钮
            self.download_button = QPushButton(tr("update.download"))
            self.download_button.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """)
            self.download_button.clicked.connect(self.start_download)
            button_layout.addWidget(self.download_button)
            
            self.later_button = QPushButton(tr("update.later"))
            self.later_button.clicked.connect(self.reject)
            button_layout.addWidget(self.later_button)
            
        else:
            # 检查更新时的按钮
            self.check_button = QPushButton(tr("update.check_now"))
            self.check_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
            """)
            self.check_button.clicked.connect(self.check_updates)
            button_layout.addWidget(self.check_button)
            
            self.cancel_button = QPushButton(tr("update.cancel"))
            self.cancel_button.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_button)
        
        # 添加弹性空间
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """设置信号连接"""
        if not self.version_info:
            # 连接更新检查信号
            update_manager.update_available.connect(self.on_update_available)
            update_manager.no_update_available.connect(self.on_no_update)
            update_manager.update_check_failed.connect(self.on_check_failed)
    
    def check_updates(self):
        """检查更新"""
        self.status_label.setText(tr("update.checking"))
        self.progress_bar.setRange(0, 0)
        self.check_button.setEnabled(False)
        
        update_manager.check_for_updates(force=True)
    
    def on_update_available(self, version_info: VersionInfo):
        """发现新版本"""
        self.accept()
        # 显示更新对话框
        dialog = UpdateDialog(self.parent(), version_info)
        dialog.exec_()
    
    def on_no_update(self):
        """无更新"""
        self.status_label.setText(tr("update.no_update"))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.check_button.setEnabled(True)
        
        # 3秒后自动关闭
        QTimer.singleShot(3000, self.accept)
    
    def on_check_failed(self, error_msg: str):
        """检查失败"""
        self.status_label.setText(tr("update.check_failed"))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.check_button.setEnabled(True)
        
        logger.error(f"更新检查失败: {error_msg}")
    
    def start_download(self):
        """开始下载"""
        if not self.version_info:
            return
        
        # 获取下载目录
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "椰果IDM更新")
        
        # 显示下载进度对话框
        progress_dialog = UpdateProgressDialog(self, self.version_info, download_dir)
        if progress_dialog.exec_() == QDialog.Accepted:
            self.accept()
        else:
            # 下载被取消或失败
            pass


class UpdateProgressDialog(QDialog):
    """更新下载进度对话框"""
    
    def __init__(self, parent=None, version_info: VersionInfo = None, download_dir: str = ""):
        super().__init__(parent)
        self.version_info = version_info
        self.download_dir = download_dir
        self.download_path = ""
        self.setup_ui()
        self.setup_connections()
        self.start_download()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(tr("update.downloading"))
        self.setFixedSize(450, 200)
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel(tr("update.downloading_title"))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 版本信息
        version_label = QLabel(f"v{self.version_info.version}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #007bff; font-size: 12px;")
        layout.addWidget(version_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel(tr("update.preparing_download"))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton(tr("update.cancel_download"))
        self.cancel_button.clicked.connect(self.cancel_download)
        button_layout.addWidget(self.cancel_button)
        
        self.open_folder_button = QPushButton(tr("update.open_folder"))
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.open_download_folder)
        button_layout.addWidget(self.open_folder_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def setup_connections(self):
        """设置信号连接"""
        # 连接下载管理器信号
        if update_manager.downloader:
            update_manager.downloader.download_progress.connect(self.progress_bar.setValue)
            update_manager.downloader.download_status.connect(self.status_label.setText)
            update_manager.downloader.download_completed.connect(self.on_download_completed)
            update_manager.downloader.download_failed.connect(self.on_download_failed)
    
    def start_download(self):
        """开始下载"""
        update_manager.download_update(self.version_info, self.download_dir)
    
    def cancel_download(self):
        """取消下载"""
        update_manager.stop_download()
        self.reject()
    
    def on_download_completed(self, file_path: str):
        """下载完成"""
        self.download_path = file_path
        self.progress_bar.setValue(100)
        self.status_label.setText(tr("update.download_completed"))
        self.cancel_button.setText(tr("update.close"))
        self.open_folder_button.setEnabled(True)
        
        # 询问是否立即安装
        reply = QMessageBox.question(
            self,
            tr("update.install_now"),
            tr("update.install_now_message"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.install_update()
        else:
            self.accept()
    
    def on_download_failed(self, error_msg: str):
        """下载失败"""
        self.status_label.setText(tr("update.download_failed"))
        self.cancel_button.setText(tr("update.close"))
        
        QMessageBox.critical(
            self,
            tr("update.download_failed"),
            tr("update.download_failed_message").format(error=error_msg)
        )
    
    def install_update(self):
        """安装更新"""
        try:
            if sys.platform == "win32":
                # Windows: 直接运行安装程序
                subprocess.Popen([self.download_path], shell=True)
            else:
                # 其他平台: 打开文件管理器
                import subprocess
                subprocess.Popen(['xdg-open', self.download_path])
            
            # 退出当前程序
            QApplication.quit()
            
        except Exception as e:
            logger.error(f"启动安装程序失败: {e}")
            QMessageBox.critical(
                self,
                tr("update.install_failed"),
                tr("update.install_failed_message").format(error=str(e))
            )
    
    def open_download_folder(self):
        """打开下载文件夹"""
        try:
            if sys.platform == "win32":
                os.startfile(self.download_dir)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', self.download_dir])
        except Exception as e:
            logger.error(f"打开文件夹失败: {e}")


def show_update_dialog(parent=None, version_info: Optional[VersionInfo] = None):
    """显示更新对话框的便捷函数"""
    dialog = UpdateDialog(parent, version_info)
    return dialog.exec_()


def check_for_updates(parent=None):
    """检查更新的便捷函数"""
    dialog = UpdateDialog(parent)
    return dialog.exec_()
