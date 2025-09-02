"""
日志管理模块

该模块整合了应用程序的所有日志管理功能，包括：
- 日志系统初始化和配置
- 日志文件管理
- 日志查看和导出
- 日志级别控制
- 日志轮转和清理

主要组件：
- LogManager: 日志管理器主类
- LogViewer: 日志查看器
- LogExporter: 日志导出器

作者: 椰果IDM开发团队
版本: 1.0.2
"""

import os
import logging
import shutil
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QProgressBar, QComboBox, QCheckBox, QSpinBox,
    QFileDialog, QMessageBox, QGroupBox, QFormLayout
)


class LogManager(QObject):
    """日志管理器主类"""
    
    # 信号定义
    log_updated = pyqtSignal(str)  # 日志更新信号
    log_cleared = pyqtSignal()     # 日志清空信号
    log_exported = pyqtSignal(str) # 日志导出完成信号
    
    def __init__(self, log_dir: str = None, max_file_size: int = 10 * 1024 * 1024):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志目录路径
            max_file_size: 单个日志文件最大大小（字节）
        """
        super().__init__()
        
        self.log_dir = log_dir or os.getcwd()
        self.max_file_size = max_file_size
        self.log_file = os.path.join(self.log_dir, "app.log")
        self.backup_dir = os.path.join(self.log_dir, "logs_backup")
        
        # 确保备份目录存在
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 初始化日志系统
        self._setup_logger()
        
        # 启动日志监控
        self._start_log_monitor()
    
    def _setup_logger(self) -> None:
        """设置日志记录器"""
        # 配置日志格式
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # 创建文件处理器
        try:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
        except (OSError, IOError) as e:
            print(f"无法创建日志文件处理器: {e}")
            file_handler = None
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 清除现有的处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 添加新的处理器
        if file_handler:
            root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # 创建应用专用日志记录器
        self.logger = logging.getLogger("VideoDownloader")
    
    def _start_log_monitor(self) -> None:
        """启动日志监控"""
        self.log_monitor_timer = QTimer()
        self.log_monitor_timer.timeout.connect(self._check_log_file)
        self.log_monitor_timer.start(60000)  # 每分钟检查一次
    
    def _check_log_file(self) -> None:
        """检查日志文件大小，必要时进行轮转"""
        try:
            if os.path.exists(self.log_file):
                file_size = os.path.getsize(self.log_file)
                if file_size > self.max_file_size:
                    self.logger.info(f"日志文件大小 ({file_size} bytes) 超过限制 ({self.max_file_size} bytes)，开始轮转")
                    self._rotate_log_file()
        except Exception as e:
            print(f"检查日志文件失败: {e}")
    
    def _rotate_log_file(self) -> None:
        """轮转日志文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"app_{timestamp}.log")
            
            # 复制当前日志文件而不是移动，避免文件占用问题
            if os.path.exists(self.log_file):
                shutil.copy2(self.log_file, backup_file)
                
                # 清空原文件并写入轮转标记
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write(f"日志文件轮转 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # 清理旧备份文件（保留最近10个）
            self._cleanup_old_backups()
            
            self.logger.info(f"日志文件已轮转到: {backup_file}")
            
        except Exception as e:
            self.logger.error(f"轮转日志文件失败: {e}")
    
    def _cleanup_old_backups(self, keep_count: int = 10) -> None:
        """清理旧的备份文件"""
        try:
            backup_files = []
            for file in os.listdir(self.backup_dir):
                if file.startswith("app_") and file.endswith(".log"):
                    file_path = os.path.join(self.backup_dir, file)
                    backup_files.append((file_path, os.path.getmtime(file_path)))
            
            # 按修改时间排序，保留最新的文件
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 删除多余的文件
            for file_path, _ in backup_files[keep_count:]:
                try:
                    os.remove(file_path)
                    self.logger.info(f"删除旧备份文件: {file_path}")
                except Exception as e:
                    self.logger.error(f"删除旧备份文件失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"清理旧备份文件失败: {e}")
    
    def get_log_content(self, max_lines: int = 1000) -> str:
        """
        获取日志内容
        
        Args:
            max_lines: 最大行数
            
        Returns:
            str: 日志内容
        """
        try:
            if not os.path.exists(self.log_file):
                return "日志文件不存在"
            
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
                content = f"[显示最后 {max_lines} 行]\n" + "".join(lines)
            else:
                content = "".join(lines)
                
            return content
            
        except Exception as e:
            return f"读取日志文件失败: {e}"
    
    def clear_log(self) -> bool:
        """
        清空日志文件
        
        Returns:
            bool: 是否成功
        """
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"日志已清空 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            self.log_cleared.emit()
            self.logger.info("日志文件已清空")
            return True
            
        except Exception as e:
            self.logger.error(f"清空日志文件失败: {e}")
            return False
    
    def export_log(self, target_path: str) -> bool:
        """
        导出日志文件
        
        Args:
            target_path: 目标文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            if not os.path.exists(self.log_file):
                return False
            
            shutil.copy2(self.log_file, target_path)
            self.log_exported.emit(target_path)
            self.logger.info(f"日志已导出到: {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出日志失败: {e}")
            return False
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            'file_exists': False,
            'file_size': 0,
            'line_count': 0,
            'last_modified': None,
            'backup_count': 0
        }
        
        try:
            if os.path.exists(self.log_file):
                stats['file_exists'] = True
                stats['file_size'] = os.path.getsize(self.log_file)
                stats['last_modified'] = datetime.fromtimestamp(
                    os.path.getmtime(self.log_file)
                )
                
                with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    stats['line_count'] = sum(1 for _ in f)
            
            # 统计备份文件数量
            if os.path.exists(self.backup_dir):
                backup_files = [f for f in os.listdir(self.backup_dir) 
                              if f.startswith("app_") and f.endswith(".log")]
                stats['backup_count'] = len(backup_files)
                
        except Exception as e:
            self.logger.error(f"获取日志统计信息失败: {e}")
        
        return stats


class LogViewer(QDialog):
    """日志查看器对话框"""
    
    def __init__(self, log_manager: LogManager, parent=None):
        """
        初始化日志查看器
        
        Args:
            log_manager: 日志管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.log_manager = log_manager
        self.setup_ui()
        self.setup_connections()
        self.load_log_content()
        
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
        
    def setup_ui(self) -> None:
        """设置用户界面"""
        self.setWindowTitle("日志查看器")
        self.setFixedSize(600, 500)
        self.setModal(False)
        
        layout = QVBoxLayout()
        
        # 标题和统计信息
        header_layout = QHBoxLayout()
        
        title_label = QLabel("应用程序日志")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 5px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 统计信息标签
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-size: 11px; color: #666;")
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        # 日志级别过滤
        level_label = QLabel("日志级别:")
        self.level_combo = QComboBox()
        self.level_combo.addItems(["全部", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.setCurrentText("全部")
        
        control_layout.addWidget(level_label)
        control_layout.addWidget(self.level_combo)
        
        # 自动刷新
        self.auto_refresh_check = QCheckBox("自动刷新")
        self.auto_refresh_check.setChecked(True)
        control_layout.addWidget(self.auto_refresh_check)
        
        # 刷新间隔
        interval_label = QLabel("间隔(秒):")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(5)
        self.interval_spin.setEnabled(False)
        
        control_layout.addWidget(interval_label)
        control_layout.addWidget(self.interval_spin)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                text-align: center;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 12px;
                padding: 8px;
                line-height: 1.4;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                border: none;
                border-radius: 0px;
                margin: 0px;
                position: absolute;
                right: 0px;
                top: 0px;
                bottom: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #c1c1c1;
                min-height: 20px;
                border-radius: 0px;
                border: none;
                margin: 0px;
                width: 12px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a8a8a8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background-color: transparent;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: transparent;
                border: none;
            }
            
            /* 确保滚动条完全贴右边 */
            QScrollBar::right-arrow:vertical, QScrollBar::left-arrow:vertical {
                width: 0px;
                height: 0px;
                background-color: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.log_text)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 刷新按钮
        self.refresh_button = QPushButton("刷新(&R)")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #fdfdfd;
                color: #000000;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: normal;
                min-height: 20px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            QPushButton:pressed {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
        """)
        button_layout.addWidget(self.refresh_button)
        
        # 导出按钮
        self.export_button = QPushButton("导出(&E)")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #fdfdfd;
                color: #000000;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: normal;
                min-height: 20px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            QPushButton:pressed {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
        """)
        button_layout.addWidget(self.export_button)
        
        # 清空按钮
        self.clear_button = QPushButton("清空(&C)")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #fdfdfd;
                color: #000000;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: normal;
                min-height: 20px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            QPushButton:pressed {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
        """)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        # 关闭按钮
        self.close_button = QPushButton("关闭(&X)")
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #fdfdfd;
                color: #000000;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: normal;
                min-height: 20px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            QPushButton:pressed {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
        """)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def setup_connections(self) -> None:
        """设置信号连接"""
        self.refresh_button.clicked.connect(self.load_log_content)
        self.export_button.clicked.connect(self.export_log)
        self.clear_button.clicked.connect(self.clear_log)
        
        # 自动刷新控制
        self.auto_refresh_check.toggled.connect(self.interval_spin.setEnabled)
        self.auto_refresh_check.toggled.connect(self._toggle_auto_refresh)
        
        # 日志级别过滤
        self.level_combo.currentTextChanged.connect(self.load_log_content)
    
    def _toggle_auto_refresh(self, enabled: bool) -> None:
        """切换自动刷新"""
        if hasattr(self, 'refresh_timer'):
            if enabled:
                interval = self.interval_spin.value() * 1000
                self.refresh_timer.start(interval)
            else:
                self.refresh_timer.stop()
        else:
            if enabled:
                self.refresh_timer = QTimer()
                self.refresh_timer.timeout.connect(self.load_log_content)
                interval = self.interval_spin.value() * 1000
                self.refresh_timer.start(interval)
    
    def load_log_content(self) -> None:
        """加载日志内容"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.refresh_button.setEnabled(False)
        
        # 使用异步加载
        self.log_loader = LogLoader(self.log_manager, self.level_combo.currentText())
        self.log_loader.content_loaded.connect(self._on_content_loaded)
        self.log_loader.error_occurred.connect(self._on_error_occurred)
        self.log_loader.start()
    
    def _on_content_loaded(self, content: str) -> None:
        """日志内容加载完成"""
        self.log_text.setText(content)
        self._scroll_to_bottom()
        self._update_stats()
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)
    
    def _on_error_occurred(self, error_msg: str) -> None:
        """日志加载出错"""
        self.log_text.setText(error_msg)
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)
    
    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)
    
    def _update_stats(self) -> None:
        """更新统计信息"""
        stats = self.log_manager.get_log_stats()
        if stats['file_exists']:
            size_mb = stats['file_size'] / (1024 * 1024)
            modified_str = stats['last_modified'].strftime("%Y-%m-%d %H:%M:%S") if stats['last_modified'] else "未知"
            stats_text = f"大小: {size_mb:.2f}MB | 行数: {stats['line_count']} | 修改: {modified_str} | 备份: {stats['backup_count']}"
        else:
            stats_text = "日志文件不存在"
        
        self.stats_label.setText(stats_text)
    
    def export_log(self) -> None:
        """导出日志"""
        try:
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "导出日志", 
                f"椰果IDM日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "文本文件 (*.txt);;所有文件 (*)"
            )
            
            if save_path:
                if self.log_manager.export_log(save_path):
                    QMessageBox.information(self, "成功", f"日志已导出到:\n{save_path}")
                else:
                    QMessageBox.critical(self, "错误", "导出日志失败")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出日志失败: {str(e)}")
    
    def clear_log(self) -> None:
        """清空日志"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认清空")
        msg_box.setText("确定要清空所有日志吗？此操作不可恢复！")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        
        reply = msg_box.exec_()
        
        if reply == QMessageBox.Yes:
            if self.log_manager.clear_log():
                self.load_log_content()
                QMessageBox.information(self, "成功", "日志已清空")
            else:
                QMessageBox.critical(self, "错误", "清空日志失败")
    
    def closeEvent(self, event) -> None:
        """关闭事件"""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        if hasattr(self, 'log_loader'):
            self.log_loader.quit()
        event.accept()


class LogLoader(QThread):
    """异步日志加载器"""
    
    content_loaded = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, log_manager: LogManager, level_filter: str = "全部"):
        """
        初始化日志加载器
        
        Args:
            log_manager: 日志管理器实例
            level_filter: 日志级别过滤
        """
        super().__init__()
        self.log_manager = log_manager
        self.level_filter = level_filter
    
    def run(self) -> None:
        """运行加载任务"""
        try:
            content = self.log_manager.get_log_content()
            
            # 应用级别过滤
            if self.level_filter != "全部":
                filtered_lines = []
                for line in content.split('\n'):
                    if f"[{self.level_filter}]" in line:
                        filtered_lines.append(line)
                content = '\n'.join(filtered_lines)
            
            self.content_loaded.emit(content)
            
        except Exception as e:
            self.error_occurred.emit(f"读取日志文件失败: {str(e)}")


# 全局日志管理器实例
log_manager = LogManager()
