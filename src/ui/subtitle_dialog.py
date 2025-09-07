"""
Subtitle Download Dialog

This module provides subtitle download functionality, including:
- Subtitle list display
- Subtitle preview
- Subtitle download and format conversion
- Subtitle management

Author: Yeguo IDM Development Team
Version: 1.0.0
"""

import os
from typing import List, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QComboBox, QProgressBar,
    QGroupBox, QCheckBox, QMessageBox, QFileDialog, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from ..core.subtitle_manager import subtitle_manager, SubtitleInfo, SubtitleDownloader
from ..core.i18n_manager import tr


class SubtitleDownloadWorker(QThread):
    """字幕下载工作线程"""
    
    download_finished = pyqtSignal(str, str)  # language_code, subtitle_path
    download_failed = pyqtSignal(str, str)    # language_code, error_message
    progress_updated = pyqtSignal(int)        # progress percentage
    
    def __init__(self, url: str, subtitle_info: SubtitleInfo, save_path: str):
        super().__init__()
        self.url = url
        self.subtitle_info = subtitle_info
        self.save_path = save_path
    
    def run(self):
        try:
            self.progress_updated.emit(10)
            
            # 创建下载器
            downloader = subtitle_manager.download_subtitle(
                self.url, self.subtitle_info, self.save_path
            )
            
            self.progress_updated.emit(30)
            
            # 连接信号
            downloader.download_finished.connect(
                lambda lang, path: self.download_finished.emit(lang, path)
            )
            downloader.download_failed.connect(
                lambda lang, error: self.download_failed.emit(lang, error)
            )
            
            self.progress_updated.emit(50)
            
            # 开始下载
            downloader.start()
            downloader.wait()
            
            self.progress_updated.emit(100)
            
        except Exception as e:
            self.download_failed.emit(self.subtitle_info.language_code, str(e))


class SubtitleDialog(QDialog):
    """字幕下载对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.url = ""
        self.subtitles = []
        self.download_workers = []
        self.init_ui()
        
        # 设置窗口居中显示
        self.center_on_parent()
        
    def center_on_parent(self) -> None:
        """将对话框居中显示在父窗口上"""
        if self.parent():
            parent_rect = self.parent().geometry()
            dialog_rect = self.geometry()
            x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
            self.move(x, y)
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(tr("subtitle.title"))
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout()
        
        # URL输入区域
        url_group = QGroupBox("视频URL")
        url_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入视频URL")
        url_layout.addWidget(self.url_input)
        
        self.fetch_button = QPushButton(tr("subtitle.fetch"))
        self.fetch_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.fetch_button.setFixedSize(80, 24)  # 与反馈页面按钮保持一致
        self.fetch_button.clicked.connect(self.fetch_subtitles)
        url_layout.addWidget(self.fetch_button)
        
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # 主内容区域
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧字幕列表
        subtitle_group = QGroupBox(tr("subtitle.available"))
        subtitle_layout = QVBoxLayout()
        
        self.subtitle_list = QListWidget()
        self.subtitle_list.itemClicked.connect(self.on_subtitle_selected)
        # 应用滚动条样式
        from .scrollbar_styles import get_list_widget_style
        self.subtitle_list.setStyleSheet(get_list_widget_style())
        subtitle_layout.addWidget(self.subtitle_list)
        
        # 字幕操作按钮
        subtitle_button_layout = QHBoxLayout()
        
        self.download_button = QPushButton(tr("subtitle.download_selected"))
        self.download_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.download_button.setFixedSize(90, 24)  # 增加宽度以适应英文文本
        self.download_button.clicked.connect(self.download_selected_subtitle)
        self.download_button.setEnabled(False)
        subtitle_button_layout.addWidget(self.download_button)
        
        self.download_all_button = QPushButton(tr("subtitle.download_all"))
        self.download_all_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.download_all_button.setFixedSize(90, 24)  # 增加宽度以适应英文文本
        self.download_all_button.clicked.connect(self.download_all_subtitles)
        self.download_all_button.setEnabled(False)
        subtitle_button_layout.addWidget(self.download_all_button)
        
        subtitle_layout.addLayout(subtitle_button_layout)
        subtitle_group.setLayout(subtitle_layout)
        main_splitter.addWidget(subtitle_group)
        
        # 右侧预览区域
        preview_group = QGroupBox(tr("subtitle.preview"))
        preview_layout = QVBoxLayout()
        
        # 字幕信息
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("语言:"))
        self.language_label = QLabel("")
        info_layout.addWidget(self.language_label)
        
        info_layout.addWidget(QLabel("格式:"))
        self.format_label = QLabel("")
        info_layout.addWidget(self.format_label)
        
        info_layout.addWidget(QLabel("类型:"))
        self.type_label = QLabel("")
        info_layout.addWidget(self.type_label)
        
        info_layout.addStretch()
        preview_layout.addLayout(info_layout)
        
        # 预览文本
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        # 应用滚动条样式
        from .scrollbar_styles import get_text_edit_style
        self.preview_text.setStyleSheet(get_text_edit_style())
        preview_layout.addWidget(self.preview_text)
        
        # 下载选项
        download_options_group = QGroupBox(tr("subtitle.download_options"))
        options_layout = QVBoxLayout()
        
        # 保存路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存路径:"))
        self.save_path_input = QLineEdit()
        self.save_path_input.setText(os.getcwd())
        path_layout.addWidget(self.save_path_input)
        
        self.browse_button = QPushButton(tr("subtitle.browse"))
        self.browse_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.browse_button.setFixedSize(50, 24)  # 与反馈页面按钮保持一致
        self.browse_button.clicked.connect(self.browse_save_path)
        path_layout.addWidget(self.browse_button)
        options_layout.addLayout(path_layout)
        
        # 格式转换
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("转换格式:"))
        self.convert_format_combo = QComboBox()
        self.convert_format_combo.addItem(tr("subtitle.keep_original"), "")
        self.convert_format_combo.addItem("SRT", "srt")
        self.convert_format_combo.addItem("VTT", "vtt")
        format_layout.addWidget(self.convert_format_combo)
        options_layout.addLayout(format_layout)
        
        download_options_group.setLayout(options_layout)
        preview_layout.addWidget(download_options_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        preview_layout.addWidget(self.progress_bar)
        
        preview_group.setLayout(preview_layout)
        main_splitter.addWidget(preview_group)
        
        # 设置分割器比例
        main_splitter.setSizes([400, 400])
        layout.addWidget(main_splitter)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_button = QPushButton(tr("messages.close"))
        self.close_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.close_button.setFixedSize(50, 24)  # 与反馈页面按钮保持一致
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def fetch_subtitles(self):
        """获取字幕列表"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, tr("messages.info"), tr("subtitle.url_required"))
            return
        
        self.url = url
        self.fetch_button.setEnabled(False)
        self.fetch_button.setText(tr("subtitle.fetching"))
        
        try:
            # 获取字幕列表
            subtitles = subtitle_manager.get_available_subtitles(url)
            self.subtitles = subtitles
            
            # 更新字幕列表
            self.update_subtitle_list(subtitles)
            
            if subtitles:
                self.download_all_button.setEnabled(True)
                QMessageBox.information(self, tr("messages.operation_success"), tr("subtitle.found_count").format(count=len(subtitles)))
            else:
                QMessageBox.information(self, tr("messages.info"), tr("subtitle.not_found"))
                
        except Exception as e:
            QMessageBox.critical(self, tr("messages.operation_failed"), tr("subtitle.fetch_failed"))
        finally:
            self.fetch_button.setEnabled(True)
            self.fetch_button.setText(tr("subtitle.fetch"))
    
    def update_subtitle_list(self, subtitles: List[SubtitleInfo]):
        """更新字幕列表"""
        self.subtitle_list.clear()
        
        for subtitle in subtitles:
            # 创建列表项
            item_text = f"{subtitle.language} ({subtitle.format})"
            if subtitle.is_auto:
                item_text += " [自动]"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, subtitle)
            self.subtitle_list.addItem(item)
    
    def on_subtitle_selected(self, item: QListWidgetItem):
        """字幕选择事件"""
        subtitle = item.data(Qt.UserRole)
        if not subtitle:
            return
        
        # 更新信息显示
        self.language_label.setText(subtitle.language)
        self.format_label.setText(subtitle.format.upper())
        self.type_label.setText(tr("subtitle.auto_generated") if subtitle.is_auto else tr("subtitle.manual"))
        
        # 启用下载按钮
        self.download_button.setEnabled(True)
        
        # 清空预览
        self.preview_text.clear()
        self.preview_text.append(tr("subtitle.preview_not_implemented"))
    
    def download_selected_subtitle(self):
        """下载选中的字幕"""
        current_item = self.subtitle_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, tr("messages.info"), tr("subtitle.select_first"))
            return
        
        subtitle = current_item.data(Qt.UserRole)
        if not subtitle:
            return
        
        self.download_subtitle(subtitle)
    
    def download_all_subtitles(self):
        """下载所有字幕"""
        if not self.subtitles:
            QMessageBox.warning(self, tr("messages.info"), tr("subtitle.no_files"))
            return
        
        reply = QMessageBox.question(
            self, tr("messages.confirm"),
            tr("subtitle.confirm_download_all").format(count=len(self.subtitles)),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for subtitle in self.subtitles:
                self.download_subtitle(subtitle)
    
    def download_subtitle(self, subtitle: SubtitleInfo):
        """下载字幕"""
        save_path = self.save_path_input.text().strip()
        if not save_path or not os.path.exists(save_path):
            QMessageBox.warning(self, tr("messages.info"), tr("subtitle.select_save_path"))
            return
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.download_button.setEnabled(False)
        self.download_all_button.setEnabled(False)
        
        # 创建下载线程
        worker = SubtitleDownloadWorker(self.url, subtitle, save_path)
        worker.download_finished.connect(self.on_subtitle_downloaded)
        worker.download_failed.connect(self.on_subtitle_download_failed)
        worker.progress_updated.connect(self.progress_bar.setValue)
        
        self.download_workers.append(worker)
        worker.start()
    
    def on_subtitle_downloaded(self, language_code: str, subtitle_path: str):
        """字幕下载完成"""
        # 检查是否需要格式转换
        convert_format = self.convert_format_combo.currentData()
        if convert_format and subtitle_path:
            try:
                converted_path = subtitle_manager.convert_subtitle_format(subtitle_path, convert_format)
                if converted_path:
                    subtitle_path = converted_path
                    QMessageBox.information(self, tr("messages.operation_success"), tr("subtitle.converted_saved").format(path=converted_path))
                else:
                    QMessageBox.warning(self, tr("messages.operation_failed"), tr("subtitle.convert_failed"))
            except Exception as e:
                QMessageBox.warning(self, "转换失败", "格式转换失败，请稍后重试")
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        self.download_all_button.setEnabled(True)
        
        QMessageBox.information(self, tr("messages.operation_success"), tr("subtitle.download_completed").format(path=subtitle_path))
    
    def on_subtitle_download_failed(self, language_code: str, error: str):
        """字幕下载失败"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        self.download_all_button.setEnabled(True)
        
        QMessageBox.critical(self, tr("messages.operation_failed"), tr("subtitle.download_failed"))
    
    def browse_save_path(self):
        """浏览保存路径"""
        folder = QFileDialog.getExistingDirectory(self, tr("subtitle.select_save_path"), self.save_path_input.text())
        if folder:
            self.save_path_input.setText(folder)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止所有下载线程
        for worker in self.download_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        event.accept()
