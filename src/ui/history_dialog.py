"""
Download History Dialog

This module provides download history viewing and management functionality, including:
- History record list display
- Search and filter functionality
- Re-download functionality
- History record deletion and export

Author: Yeguo IDM Development Team
Version: 1.0.0
"""

import os
from datetime import datetime
from typing import List, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
    QDateEdit, QGroupBox, QCheckBox, QProgressBar, QTextEdit, QFileDialog,
    QMenu, QAction, QWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QIcon

from ..core.history import history_manager, DownloadRecord
from ..utils.file_utils import format_size
from ..core.i18n_manager import tr


class HistorySearchWorker(QThread):
    """历史记录搜索线程"""
    
    search_finished = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    
    def __init__(self, keyword: str = "", platform: str = "", status: str = "", 
                 start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        super().__init__()
        self.keyword = keyword
        self.platform = platform
        self.status = status
        self.start_date = start_date
        self.end_date = end_date
    
    def run(self):
        try:
            if self.keyword:
                records = history_manager.search_records(self.keyword)
            else:
                records = history_manager.get_all_records()
            
            # 过滤平台
            if self.platform:
                records = [r for r in records if r.platform == self.platform]
            
            # 过滤状态
            if self.status:
                records = [r for r in records if r.status == self.status]
            
            # 过滤日期
            if self.start_date or self.end_date:
                filtered_records = []
                for record in records:
                    if record.download_time:
                        # 确保日期比较的类型一致
                        record_date = record.download_time
                        if self.start_date and record_date < self.start_date:
                            continue
                        if self.end_date and record_date > self.end_date:
                            continue
                        filtered_records.append(record)
                records = filtered_records
            
            self.search_finished.emit(records)
            
        except Exception as e:
            self.search_failed.emit(str(e))


class HistoryDialog(QDialog):
    """下载历史对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_worker = None
        self.current_records = []
        self.init_ui()
        self.load_history()
        
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
        self.setWindowTitle(tr("menu.history"))
        self.setFixedSize(900, 600)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)  # 减少垂直间距
        layout.setContentsMargins(8, 8, 8, 8)  # 减少边距
        
        # 搜索区域
        search_group = QGroupBox(tr("history.search_filter"))
        search_layout = QVBoxLayout()
        search_layout.setSpacing(6)  # 减少搜索区域内部间距
        
        # 关键词搜索
        keyword_layout = QHBoxLayout()
        keyword_layout.addWidget(QLabel(tr("history.keyword") + ":"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText(tr("history.keyword_placeholder"))
        keyword_layout.addWidget(self.keyword_input)
        search_layout.addLayout(keyword_layout)
        
        # 过滤条件
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel(tr("history.platform") + ":"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItem(tr("history.all"), "")
        self.platform_combo.addItem("YouTube", "youtube")
        self.platform_combo.addItem("Bilibili", "bilibili")
        filter_layout.addWidget(self.platform_combo)
        
        filter_layout.addWidget(QLabel(tr("history.status") + ":"))
        self.status_combo = QComboBox()
        self.status_combo.addItem(tr("history.all"), "")
        self.status_combo.addItem(tr("history.completed"), "completed")
        self.status_combo.addItem(tr("history.failed"), "failed")
        self.status_combo.addItem(tr("history.cancelled"), "cancelled")
        filter_layout.addWidget(self.status_combo)
        
        filter_layout.addWidget(QLabel(tr("history.start_date") + ":"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        filter_layout.addWidget(self.start_date)
        
        filter_layout.addWidget(QLabel(tr("history.end_date") + ":"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        filter_layout.addWidget(self.end_date)
        
        search_layout.addLayout(filter_layout)
        
        # 搜索按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)  # 减少按钮间距
        
        self.search_button = QPushButton(tr("history.search"))
        self.search_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.search_button.setFixedSize(60, 24)  # 与反馈页面按钮保持一致
        self.search_button.clicked.connect(self.search_history)
        button_layout.addWidget(self.search_button)
        
        self.clear_button = QPushButton(tr("history.clear"))
        self.clear_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.clear_button.setFixedSize(50, 24)  # 与反馈页面按钮保持一致
        self.clear_button.clicked.connect(self.clear_filters)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        self.export_button = QPushButton(tr("history.export"))
        self.export_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.export_button.setFixedSize(60, 24)  # 增加宽度以适应英文文本"Export"
        self.export_button.clicked.connect(self.export_history)
        button_layout.addWidget(self.export_button)
        
        self.clear_history_button = QPushButton(tr("history.clear_history"))
        self.clear_history_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.clear_history_button.setFixedSize(110, 24)  # 增加宽度以适应英文文本"Clear History"
        self.clear_history_button.clicked.connect(self.clear_history)
        button_layout.addWidget(self.clear_history_button)
        
        search_layout.addLayout(button_layout)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            tr("history.title"), tr("history.filename"), tr("history.resolution"), 
            tr("history.file_size"), tr("history.platform"), tr("history.status"), 
            tr("history.download_time"), tr("history.actions")
        ])
        
        # 应用滚动条样式
        from .scrollbar_styles import get_tree_widget_style
        self.history_table.setStyleSheet(get_tree_widget_style())
        
        # 设置表格行高，使其更紧凑
        self.history_table.verticalHeader().setDefaultSectionSize(28)  # 减少行高
        
        # 设置表格属性
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 标题列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.history_table)
        
        # 状态栏
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 4, 0, 4)  # 减少状态栏边距
        self.status_label = QLabel(tr("history.total_records").format(count=0))
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(20)  # 设置进度条高度
        status_layout.addWidget(self.progress_bar)
        
        layout.addLayout(status_layout)
        
        self.setLayout(layout)
    
    def load_history(self):
        """加载历史记录"""
        self.search_history()
    
    def search_history(self):
        """搜索历史记录"""
        keyword = self.keyword_input.text().strip()
        platform = self.platform_combo.currentData()
        status = self.status_combo.currentData()
        
        # 将日期转换为datetime对象，确保类型一致
        start_date = datetime.combine(self.start_date.date().toPyDate(), datetime.min.time())
        end_date = datetime.combine(self.end_date.date().toPyDate(), datetime.max.time())
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.search_button.setEnabled(False)
        
        # 启动搜索线程
        self.search_worker = HistorySearchWorker(keyword, platform, status, start_date, end_date)
        self.search_worker.search_finished.connect(self.on_search_finished)
        self.search_worker.search_failed.connect(self.on_search_failed)
        self.search_worker.start()
    
    def on_search_finished(self, records: List[DownloadRecord]):
        """搜索完成"""
        self.current_records = records
        self.update_table(records)
        self.status_label.setText(tr("history.total_records").format(count=len(records)))
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        self.search_button.setEnabled(True)
    
    def on_search_failed(self, error: str):
        """搜索失败"""
        QMessageBox.critical(self, tr("messages.operation_failed"), tr("history.search_failed"))
        self.progress_bar.setVisible(False)
        self.search_button.setEnabled(True)
    
    def update_table(self, records: List[DownloadRecord]):
        """更新表格"""
        self.history_table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            # 标题
            title_item = QTableWidgetItem(record.title)
            title_item.setToolTip(record.title)
            self.history_table.setItem(row, 0, title_item)
            
            # 文件名
            filename_item = QTableWidgetItem(record.filename)
            filename_item.setToolTip(record.filename)
            self.history_table.setItem(row, 1, filename_item)
            
            # 分辨率
            resolution_item = QTableWidgetItem(record.resolution)
            self.history_table.setItem(row, 2, resolution_item)
            
            # 文件大小
            size_item = QTableWidgetItem(format_size(record.file_size))
            self.history_table.setItem(row, 3, size_item)
            
            # 平台
            platform_item = QTableWidgetItem(record.platform.upper())
            self.history_table.setItem(row, 4, platform_item)
            
            # 状态
            status_item = QTableWidgetItem(record.status)
            if record.status == "completed":
                status_item.setForeground(Qt.green)
            elif record.status == "failed":
                status_item.setForeground(Qt.red)
            else:
                status_item.setForeground(Qt.gray)
            self.history_table.setItem(row, 5, status_item)
            
            # 下载时间
            time_str = record.download_time.strftime("%Y-%m-%d %H:%M:%S") if record.download_time else ""
            time_item = QTableWidgetItem(time_str)
            self.history_table.setItem(row, 6, time_item)
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            
            # 重新下载按钮
            redownload_btn = QPushButton(tr("history.redownload"))
            redownload_btn.setFixedSize(60, 25)
            redownload_btn.clicked.connect(lambda checked, r=record: self.redownload_record(r))
            action_layout.addWidget(redownload_btn)
            
            # 删除按钮
            delete_btn = QPushButton(tr("history.delete"))
            delete_btn.setFixedSize(40, 25)
            delete_btn.clicked.connect(lambda checked, r=record: self.delete_record(r))
            action_layout.addWidget(delete_btn)
            
            action_layout.addStretch()
            self.history_table.setCellWidget(row, 7, action_widget)
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()
        
        # 获取选中的行
        row = self.history_table.rowAt(position.y())
        if row >= 0 and row < len(self.current_records):
            record = self.current_records[row]
            
            # 重新下载
            redownload_action = QAction(tr("history.redownload"), self)
            redownload_action.triggered.connect(lambda: self.redownload_record(record))
            menu.addAction(redownload_action)
            
            # 打开文件位置
            open_location_action = QAction(tr("history.open_location"), self)
            open_location_action.triggered.connect(lambda: self.open_file_location(record))
            menu.addAction(open_location_action)
            
            menu.addSeparator()
            
            # 删除记录
            delete_action = QAction(tr("history.delete_record"), self)
            delete_action.triggered.connect(lambda: self.delete_record(record))
            menu.addAction(delete_action)
        
        menu.exec_(self.history_table.mapToGlobal(position))
    
    def redownload_record(self, record: DownloadRecord):
        """重新下载记录"""
        reply = QMessageBox.question(
            self, tr("history.confirm_redownload"),
            f"{tr('history.redownload_confirm')}\n\n{tr('history.title')}: {record.title}\n{tr('history.resolution')}: {record.resolution}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 将URL添加到主窗口的输入框
            if hasattr(self.parent(), 'url_input'):
                current_text = self.parent().url_input.toPlainText()
                if current_text.strip():
                    current_text += "\n"
                current_text += record.url
                self.parent().url_input.setPlainText(current_text)
            
            QMessageBox.information(self, tr("messages.info"), tr("history.added_to_queue"))
    
    def open_file_location(self, record: DownloadRecord):
        """打开文件位置"""
        file_path = os.path.join(record.download_path, record.filename)
        if os.path.exists(file_path):
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                subprocess.run(["explorer", "/select,", file_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", "-R", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(file_path)])
        else:
            QMessageBox.warning(self, tr("messages.info"), tr("history.file_not_exists"))
    
    def delete_record(self, record: DownloadRecord):
        """删除记录"""
        reply = QMessageBox.question(
            self, tr("history.confirm_delete"),
            f"{tr('history.delete_confirm')}\n\n{tr('history.title')}: {record.title}\n{tr('history.filename')}: {record.filename}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if history_manager.delete_record(record.id):
                QMessageBox.information(self, tr("messages.operation_success"), tr("history.record_deleted"))
                self.search_history()  # 刷新列表
            else:
                QMessageBox.critical(self, tr("messages.operation_failed"), tr("history.export_failed"))
    
    def clear_filters(self):
        """清空过滤器"""
        self.keyword_input.clear()
        self.platform_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        self.search_history()
    
    def export_history(self):
        """导出历史记录"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("history.export_history"),
            f"download_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV文件 (*.csv);;JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    success = history_manager.export_history(file_path, 'csv')
                else:
                    success = history_manager.export_history(file_path, 'json')
                
                if success:
                    QMessageBox.information(self, tr("messages.operation_success"), f"{tr('history.export_success')}\n{file_path}")
                else:
                    QMessageBox.critical(self, tr("messages.operation_failed"), tr("history.export_failed"))
            except Exception as e:
                QMessageBox.critical(self, tr("messages.operation_failed"), tr("history.export_failed"))
    
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(
            self, tr("history.confirm_clear"),
            tr("history.clear_confirm"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 获取所有记录并删除
                all_records = history_manager.get_all_records()
                deleted_count = 0
                
                for record in all_records:
                    if history_manager.delete_record(record.id):
                        deleted_count += 1
                
                QMessageBox.information(self, tr("messages.operation_success"), tr("history.records_deleted").format(count=deleted_count))
                self.search_history()  # 刷新列表
                
            except Exception as e:
                QMessageBox.critical(self, tr("messages.operation_failed"), tr("history.clear_failed"))
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.quit()
            self.search_worker.wait()
        event.accept()
