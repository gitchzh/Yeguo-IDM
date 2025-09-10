"""
Main Window Module

This module defines the main window class for the VideoDownloader application, responsible for:
- User interface creation and layout management
- Window properties and style settings
- Menu bar and status bar creation
- UI component initialization and configuration
- Integration with business logic modules

Main Classes:
- VideoDownloader: Main window class, inherits from QMainWindow and VideoDownloaderMethods

Author: Yeguo IDM Development Team
Version: 1.0.0
"""

import os
import sys
import time
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict, deque

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QFileDialog, QProgressBar, QTextEdit, QMenu, QDialog,
    QSystemTrayIcon, QAction, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QSettings, QUrl
from PyQt5.QtGui import QIcon, QDesktopServices

from ..core.config import Config
from ..core.i18n_manager import i18n_manager, tr
from ..utils.logger import logger
from ..core.log_manager import log_manager
from ..utils.file_utils import sanitize_filename, format_size, get_ffmpeg_path, check_ffmpeg
from ..workers.parse_worker import ParseWorker
from ..workers.download_worker import DownloadWorker
from .main_window_methods import VideoDownloaderMethods


class VideoDownloader(QMainWindow, VideoDownloaderMethods):
    """
    视频下载器主窗口类
    
    负责管理整个应用程序的用户界面、状态管理和业务逻辑。
    包含视频解析、格式选择、下载管理、进度显示等功能。
    """
    
    def __init__(self):
        """
        初始化主窗口
        
        设置窗口属性、初始化成员变量、加载设置、创建用户界面。
        """
        QMainWindow.__init__(self)
        VideoDownloaderMethods.__init__(self)
        
        # 基础配置
        self.save_path: str = os.getcwd()                    # 文件保存路径
        self.parse_cache: OrderedDict = OrderedDict()        # 解析结果缓存
        self.formats: List[Dict] = []                        # 可用格式列表
        self.download_progress: Dict[str, Tuple[float, str]] = {}  # 下载进度信息
        self.is_downloading: bool = False                    # 下载状态标志
        
        # 工作线程管理
        self.download_workers: List[DownloadWorker] = []     # 下载工作线程列表
        self.parse_workers: List[ParseWorker] = []           # 解析工作线程列表

        self.netease_music_workers: List = []                # 网易云音乐解析工作线程列表
        self.download_queue: deque = deque()                 # 下载队列
        
        # 状态计数
        self.active_downloads: int = 0                       # 活动下载数量
        self.total_urls: int = 0                             # 总URL数量
        self.parsed_count: int = 0                           # 已解析数量
        self.is_parsing: bool = False                        # 解析状态标志
        
        # 外部依赖
        self.ffmpeg_path: Optional[str] = None  # FFmpeg路径，稍后初始化
        self.settings = QSettings("MyCompany", "VideoDownloader")  # 设置管理器
        
        # 系统托盘相关
        self.tray_icon: Optional[QSystemTrayIcon] = None  # 系统托盘图标
        self.is_minimized_to_tray: bool = False  # 是否最小化到托盘

        # 连接语言切换信号
        i18n_manager.language_changed.connect(self.on_language_changed)
        
        # 加载配置
        self.load_settings()
        
        # 在加载设置后初始化FFmpeg路径
        self.ffmpeg_path = get_ffmpeg_path(self.save_path)
        
        self.init_ui()

        # 设置应用图标
        icon_path = self.get_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            logger.info(f"应用图标已设置: {icon_path}")
        else:
            logger.warning(f"图标文件未找到: {icon_path}")
        
        # 设置更新源优先级（码云优先）
        from ..core.update_manager import update_manager
        update_manager.set_gitee_priority(True)
        
        # 启动时自动检查更新（延迟3秒，避免影响启动速度）
        QTimer.singleShot(3000, self.auto_check_updates)
    
    def get_icon_path(self) -> str:
        """获取图标文件路径"""
        if getattr(sys, "frozen", False):
            # 打包后的程序
            return os.path.join(sys._MEIPASS, "resources", "logo.ico")
        else:
            # 开发环境
            return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "logo.ico")

    def init_ui(self) -> None:
        """
        初始化用户界面
        
        创建和配置所有UI组件，包括菜单栏、输入区域、格式选择树、进度条、按钮等。
        设置布局、样式和事件连接。
        """
        # 设置窗口基本属性
        self.setWindowTitle(f"{tr('app.title')}-v{Config.APP_VERSION}")
        
        # 设置窗口在屏幕中心显示
        self._center_window()
        
        # 创建菜单栏
        self.create_menu_bar()

        # 创建中央部件和主布局
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()

        # ==================== 输入区域 ====================
        input_layout = QHBoxLayout()
        input_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中对齐
        input_layout.setSpacing(12)  # 设置组件间距
        input_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # URL输入框
        self.url_input = QTextEdit(self)
        self.url_input.setPlaceholderText(tr("main_window.url_placeholder"))
        self.url_input.setFixedHeight(32)  # 紧凑风格统一高度
        self.url_input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏垂直滚动条
        self.url_input.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        self.url_input.setContextMenuPolicy(Qt.CustomContextMenu)  # 自定义右键菜单
        self.url_input.customContextMenuRequested.connect(self.show_url_input_context_menu)
        input_layout.addWidget(QLabel(tr("main_window.video_link")))
        input_layout.addWidget(self.url_input)
        
        # 智能解析按钮（整合解析和暂停功能）
        self.smart_parse_button = QPushButton(tr("main_window.parse"), self)
        self.smart_parse_button.clicked.connect(self.smart_parse_action)
        self.smart_parse_button.setFixedSize(80, 32)  # 增加宽度以适应英文文本
        self.smart_parse_button.setMinimumSize(80, 32)
        self.smart_parse_button.setMaximumSize(80, 32)
        input_layout.addWidget(self.smart_parse_button)
        layout.addLayout(input_layout)

        # ==================== 配置区域 ====================
        
        # 按钮行布局（取消解析按钮和选择路径按钮左右对齐）
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中对齐
        button_layout.setSpacing(12)  # 设置组件间距
        button_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 取消解析按钮
        self.cancel_parse_button = QPushButton(tr("main_window.cancel_parse"), self)
        self.cancel_parse_button.clicked.connect(self.cancel_parse)
        self.cancel_parse_button.setFixedSize(125, 32)  # 与Choose Path按钮保持相同宽度
        self.cancel_parse_button.setMinimumSize(125, 32)
        self.cancel_parse_button.setMaximumSize(125, 32)
        self.cancel_parse_button.setEnabled(False)  # 初始禁用
        button_layout.addWidget(self.cancel_parse_button)
        
        # 添加弹性空间，实现左右对齐
        button_layout.addStretch()
        
        # 选择路径按钮
        self.path_button = QPushButton(tr("main_window.choose_path"), self)
        self.path_button.clicked.connect(self.choose_save_path)
        self.path_button.setFixedSize(125, 32)  # 稍微增加宽度以确保视觉一致性
        self.path_button.setMinimumSize(125, 32)
        self.path_button.setMaximumSize(125, 32)
        button_layout.addWidget(self.path_button)
        layout.addLayout(button_layout)
        
        # 保存路径显示
        path_layout = QHBoxLayout()
        path_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中对齐
        path_layout.setSpacing(12)  # 设置组件间距
        path_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        self.path_label = QLabel(f"{tr('main_window.save_path')} {self.save_path}")
        path_layout.addWidget(self.path_label)
        layout.addLayout(path_layout)

        # 下载速度限制设置
        speed_layout = QHBoxLayout()
        speed_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中对齐
        speed_layout.setSpacing(12)  # 设置组件间距
        speed_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        self.speed_limit_input = QLineEdit(self)
        self.speed_limit_input.setPlaceholderText(tr("main_window.speed_limit_placeholder"))
        self.speed_limit_input.setFixedHeight(32)  # 紧凑风格统一高度
        self.speed_limit_input.setFixedWidth(200)
        speed_layout.addWidget(QLabel(tr("main_window.speed_limit")))
        speed_layout.addWidget(self.speed_limit_input)
        layout.addLayout(speed_layout)

        # ==================== 格式选择区域 ====================
        
        # 选择控制按钮
        select_layout = QHBoxLayout()
        select_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中对齐
        select_layout.setSpacing(12)  # 设置组件间距
        select_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 智能选择按钮（整合全选、取消全选、反选功能）
        self.smart_select_button = QPushButton(tr("main_window.select_all"), self)
        self.smart_select_button.clicked.connect(self.smart_select_action)
        self.smart_select_button.setFixedSize(80, 32)  # 增加宽度以适应英文文本
        self.smart_select_button.setEnabled(False)  # 初始禁用
        select_layout.addWidget(self.smart_select_button)
        
        # 添加分隔符
        select_layout.addSpacing(20)
        
        # 智能下载按钮（整合下载和取消功能）
        self.smart_download_button = QPushButton(tr("main_window.download"), self)
        self.smart_download_button.clicked.connect(self.smart_download_action)
        self.smart_download_button.setEnabled(False)  # 初始禁用
        self.smart_download_button.setFixedSize(100, 32)  # 进一步增加宽度以适应"Download"/"Cancel Download"
        self.default_style = self.smart_download_button.styleSheet()  # 保存默认样式
        select_layout.addWidget(self.smart_download_button)
        
        # 智能暂停按钮（整合暂停和恢复功能）
        self.smart_pause_button = QPushButton(tr("main_window.pause"), self)
        self.smart_pause_button.clicked.connect(self.smart_pause_action)
        self.smart_pause_button.setEnabled(False)  # 初始禁用
        self.smart_pause_button.setFixedSize(80, 32)  # 增加宽度以适应英文文本
        select_layout.addWidget(self.smart_pause_button)
        
        # 添加弹性空间
        select_layout.addStretch()
        
        # 选择统计标签
        self.selection_count_label = QLabel(tr("main_window.selected_count").format(count=0), self)
        select_layout.addWidget(self.selection_count_label)
        
        layout.addLayout(select_layout)
        
        # 格式选择树形控件
        self.format_tree = QTreeWidget(self)
        self.format_tree.setHeaderLabels([tr("main_window.select_type"), tr("main_window.filename"), tr("main_window.file_type"), tr("main_window.file_size"), tr("main_window.status")])
        self.format_tree.itemDoubleClicked.connect(self.toggle_checkbox)  # 双击切换选择状态
        
        # 设置列宽，确保封面图片列有足够空间显示
        self.format_tree.setColumnWidth(0, 60)   # 封面图片列宽度
        self.format_tree.setColumnWidth(1, 300)  # 文件名称列宽度
        self.format_tree.setColumnWidth(2, 80)   # 文件类型列宽度
        self.format_tree.setColumnWidth(3, 120)  # 文件大小列宽度
        self.format_tree.setColumnWidth(4, 100)  # 状态列宽度
        
        # 设置封面图片列的最小宽度，防止被压缩
        self.format_tree.header().setMinimumSectionSize(60)
        self.format_tree.header().setStretchLastSection(True)  # 最后一列自动拉伸，确保没有空白
        self.format_tree.setAlternatingRowColors(True)  # 交替行颜色
        self.format_tree.setContextMenuPolicy(Qt.CustomContextMenu)  # 自定义右键菜单
        self.format_tree.customContextMenuRequested.connect(self.show_context_menu)  # 右键菜单事件
        self.format_tree.itemChanged.connect(self.on_item_changed)  # 项目状态变化事件
        
        # 隐藏水平滚动条
        self.format_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 设置格式树样式
        self.format_tree.setStyleSheet("""
             QTreeWidget {
                 border: 1px solid #e9ecef;
                 border-radius: 0px;
                 background-color: white;
                 padding: 0px;
                 font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                 font-size: 13px;
                 color: #000000;
             }
             
             QTreeWidget::item {
                 padding: 4px;
                 border: none;
                 background-color: transparent;
             }
             
             QTreeWidget::item:selected {
                 background-color: #cce4f7;
                 color: #000000;
             }
             
             QTreeWidget::item:hover {
                 background-color: #f0f0f0;
             }
             
             QHeaderView::section {
                 background-color: #f8f9fa;
                 color: #000000;
                 border: 1px solid #e9ecef;
                 padding: 6px;
                 font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                 font-size: 13px;
                 font-weight: bold;
             }
             
             QHeaderView::section:hover {
                 background-color: #e9ecef;
             }
        """)
        
        layout.addWidget(self.format_tree, stretch=3)  # 占据3倍空间

        # ==================== 进度显示区域 ====================
        
        self.progress_layout = QVBoxLayout()
        
        # 进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 初始隐藏
        self.progress_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel(tr("main_window.ready"), self)
        self.status_label.setVisible(False)  # 初始隐藏
        self.progress_layout.addWidget(self.status_label)
        layout.addLayout(self.progress_layout)

        # 设置布局
        widget.setLayout(layout)

        # ==================== 状态栏设置 ====================
        
        # 创建状态栏
        self.statusBar = self.statusBar()
        # 设置状态栏样式
        self.statusBar.setStyleSheet("""
             QStatusBar {
                 background-color: #007acc;
                 border: none;
                 color: #ffffff;
                 font-size: 13px;
                 font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                 padding: 0px;
                 margin: 0px;
                 min-height: 24px;
             }
             
             QStatusBar::item {
                 border: none;
                 background: transparent;
                 margin: 0px;
                 padding: 0px;
             }
             
             QStatusBar QLabel {
                 color: #ffffff;
                 font-size: 13px;
                 font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                 padding: 0px;
                 margin: 0px;
             }
        """)
        
        # 创建完整状态栏显示区域
        self.status_scroll_label = QLabel(tr("main_window.ready"))
        self.status_scroll_label.setWordWrap(False)  # 禁用自动换行，确保只显示一行
        self.status_scroll_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐，垂直居中
        self.status_scroll_label.setMaximumHeight(20)  # 限制最大高度为20像素
        self.status_scroll_label.setMinimumHeight(20)   # 设置最小高度为20像素
        # 设置文本格式，超出宽度时显示省略号
        self.status_scroll_label.setTextFormat(Qt.PlainText)
        # 设置状态标签样式
        self.status_scroll_label.setStyleSheet("""
             QLabel {
                 color: #ffffff;
                 font-weight: 400;
                 font-size: 11px;
                 font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                 padding: 2px 8px;
                 background-color: transparent;
                 border: none;
                 line-height: 1.0;
                 max-height: 20px;
                 margin: 0px;
             }
        """)
        
        # 状态显示相关变量
        self.current_status = tr("main_window.ready")
        self.latest_progress = ""
        
        # 添加到状态栏 - 占用整个状态栏
        self.statusBar.addWidget(self.status_scroll_label, 1)  # 1表示拉伸因子
        
        # 设置状态栏标签的最小宽度，确保有足够空间显示信息
        self.status_scroll_label.setMinimumWidth(800)
        
        # 初始化状态
        self.update_status_bar(tr("main_window.ready"), "", "")
        
        # 设置状态栏日志信号
        from ..utils.logger import set_status_bar_signal
        set_status_bar_signal(self.update_scroll_status)
        
        # 确保列宽设置生效
        self.ensure_column_widths()
        
        # 初始化系统托盘
        self.init_system_tray()

        # ==================== 样式设置 ====================
        
        # 应用浅色主题样式表
        self.setStyleSheet("""
            /* 全局字体设置 - 统一微软雅黑 */
            * {
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                font-weight: 400;
            }

            /* 主窗口样式 */
            QMainWindow {
                background-color: #ffffff;
                color: #000000;
            }

            /* 菜单栏样式 - Cursor风格浅色主题 */
            QMenuBar {
                background-color: #f8f9fa;
                color: #1e1e1e;
                border-bottom: 1px solid #e9ecef;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                font-weight: 400;
            }

            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
                border-radius: 6px;
                margin: 2px;
            }

            QMenuBar::item:selected {
                background-color: #007bff;
                color: #ffffff;
            }

            QMenuBar::item:pressed {
                background-color: #0056b3;
                color: #ffffff;
            }

            /* 菜单样式 - Cursor风格浅色主题 */
            QMenu {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 8px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
            }

            QMenu::item {
                padding: 10px 20px;
                border-radius: 6px;
                margin: 2px;
            }

            QMenu::item:selected {
                background-color: #007bff;
                color: #ffffff;
            }

            QMenu::separator {
                height: 1px;
                background-color: #e9ecef;
                margin: 6px 12px;
            }

                         /* 按钮样式 - 统一风格 */
             QPushButton {
                 background-color: #fdfdfd;
                 color: #000000;
                 border: 1px solid #d5d5d5;
                 border-radius: 3px;
                 padding: 4px 8px;
                 font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                 font-size: 13px;
                 min-height: 20px;
                 min-width: 50px;
                 margin: 0px;
                 font-weight: normal;
             }

            QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

            QPushButton:pressed {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

            QPushButton:disabled {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                color: #999999;
            }

            /* 智能下载按钮样式 */
            QPushButton#smart_download_button {
                background-color: #fdfdfd;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                color: #000000;
                padding: 4px 8px;
            }

            QPushButton#smart_download_button:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

            QPushButton#smart_pause_button {
                background-color: #fdfdfd;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                color: #000000;
                padding: 4px 8px;
            }

            QPushButton#smart_pause_button:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

            /* 全选按钮样式 */
            QPushButton#smart_select_button {
                background-color: #fdfdfd;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                color: #000000;
                padding: 4px 8px;
            }

            QPushButton#smart_select_button:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

            /* 智能解析按钮样式 */
            QPushButton#smart_parse_button {
                background-color: #fdfdfd;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                color: #000000;
                padding: 4px 8px;
                min-height: 20px;
                margin: 0px;
            }

            QPushButton#smart_parse_button:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

            QPushButton#smart_pause_button {
                background-color: #fdfdfd;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                color: #000000;
            }

            QPushButton#smart_pause_button:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

            /* 取消解析按钮样式 */
            QPushButton#cancel_parse_button {
                background-color: #fdfdfd;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                color: #000000;
                padding: 4px 8px;
                min-height: 20px;
                min-width: 80px;
                margin: 0px;
                text-align: center;
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }

            QPushButton#cancel_parse_button:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

            /* 选择路径按钮样式 */
            QPushButton#path_button {
                background-color: #fdfdfd;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                color: #000000;
                padding: 4px 8px;
                min-height: 20px;
                min-width: 80px;
                margin: 0px;
                text-align: center;
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }

            QPushButton#path_button:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }

                         /* 输入框样式 - Cursor风格浅色主题 */
             QTextEdit, QLineEdit {
                 font-size: 13px;
                 font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                 padding: 8px 12px;
                 border: 1px solid #e9ecef;
                 background-color: #ffffff;
                 border-radius: 8px;
                 color: #1e1e1e;
                 selection-background-color: #007bff;
                 margin: 0px;
             }
             
             /* 单行输入框样式 - Cursor风格 */
             QTextEdit {
                 background-color: #ffffff;
                 border: 1px solid #e9ecef;
                 padding: 1px 12px;
                 color: #1e1e1e;
                 font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                 font-size: 13px;
                 border-radius: 8px;
                 selection-background-color: #007bff;
                 margin: 0px;
                 line-height: 26px;
             }

            QTextEdit:focus, QLineEdit:focus {
                border: 1px solid #007bff;
                outline: none;
                border-radius: 8px;
            }

            QTextEdit:hover, QLineEdit:hover {
                border: 1px solid #007bff;
                border-radius: 8px;
            }

            /* 标签样式 - Cursor风格浅色主题 */
            QLabel {
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                color: #1e1e1e;
                font-weight: 400;
            }

            /* 进度条样式 - Cursor风格浅色主题 */
            QProgressBar {
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                text-align: center;
                background-color: #f8f9fa;
                color: #1e1e1e;
                height: 20px;
            }

            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 6px;
            }

            /* 树形控件样式 - Cursor风格浅色主题 */
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                gridline-color: #e9ecef;
                selection-background-color: #007bff;
                selection-color: #ffffff;
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                alternate-background-color: #f8f9fa;
            }

            QTreeWidget::item {
                padding: 8px;
                border: 1px solid transparent;
                border-radius: 6px;
                margin: 2px;
                font-size: 13px;
                color: #1e1e1e;
            }

            QTreeWidget::item:selected {
                background-color: #007bff;
                color: #ffffff;
            }

            QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }

            /* 表头样式 */
            QHeaderView::section {
                background-color: #f3f3f3;
                color: #1e1e1e;
                padding: 6px 8px;
                border: 1px solid #e1e1e1;
                border-radius: 2px;
                font-weight: 400;
                font-size: 13px;
                font-family: "Segoe UI", "Microsoft YaHei", "微软雅黑", sans-serif;
            }

            QHeaderView::section:hover {
                background-color: #e1e1e1;
            }

            /* 滚动条样式 - 完全贴右边，无右侧空间 */
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                border-radius: 0px;
                margin: 0px;
                position: absolute;
                right: 0px;
                top: 0px;
                bottom: 0px;
                border: none;
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

            QScrollBar:horizontal {
                background-color: transparent;
                height: 12px;
                border-radius: 0px;
                margin: 0px;
                position: absolute;
                bottom: 0px;
                left: 0px;
                right: 0px;
                border: none;
            }

            QScrollBar::handle:horizontal {
                background-color: #c1c1c1;
                min-width: 20px;
                border-radius: 0px;
                border: none;
                margin: 0px;
                height: 12px;
            }

            QScrollBar::handle:horizontal:hover {
                background-color: #a8a8a8;
            }

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background-color: transparent;
                border: none;
            }

            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background-color: transparent;
                border: none;
            }
            
            /* 确保水平滚动条完全贴底部 */
            QScrollBar::right-arrow:horizontal, QScrollBar::left-arrow:horizontal {
                width: 0px;
                height: 0px;
                background-color: transparent;
                border: none;
            }

            /* 复选框样式 - Visual Studio浅色主题 */
            QCheckBox {
                color: #1e1e1e;
                font-size: 13px;
                spacing: 6px;
                font-family: "Segoe UI", "Microsoft YaHei", "微软雅黑", sans-serif;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #e1e1e1;
                border-radius: 2px;
                background-color: #ffffff;
            }

            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }

            QCheckBox::indicator:hover {
                border: 1px solid #0078d4;
            }

            /* 状态栏样式 - Visual Studio浅色主题 */
            QStatusBar {
                background-color: #f3f3f3;
                color: #1e1e1e;
                border-top: 1px solid #e1e1e1;
                font-family: "Segoe UI", "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
            }

            QStatusBar::item {
                border: none;
                background-color: transparent;
            }

            /* 紧凑型图标设置 */
            QPushButton {
                icon-size: 16px 16px;
                padding: 4px 10px;
                margin: 1px;
            }

            QMenuBar::item {
                icon-size: 14px 14px;
                padding: 4px 8px;
            }

            QMenu::item {
                icon-size: 14px 14px;
                padding: 6px 16px 6px 8px;
            }

            QTreeWidget::item {
                icon-size: 14px 14px;
                padding: 2px 4px;
            }

            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }

        """)

        # ==================== 定时器设置 ====================
        
        # 创建定时器用于更新下载进度
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_download_progress)
        # 确保定时器在主线程中运行
        self.timer.start(500)  # 每500毫秒更新一次

    def update_status_bar(self, main_status: str, progress_info: str = "", file_info: str = "") -> None:
        """
        更新状态栏信息
        
        Args:
            main_status: 主要状态信息
            progress_info: 进度信息
            file_info: 文件信息
        """
        # 组合所有状态信息
        status_parts = []
        if main_status:
            status_parts.append(main_status)
        if progress_info:
            status_parts.append(progress_info)
        if file_info:
            status_parts.append(file_info)
        
        # 合并状态信息
        combined_status = " | ".join(status_parts) if status_parts else tr("main_window.ready")
        
        # 更新状态栏显示
        self.current_status = combined_status
        self.status_scroll_label.setText(combined_status)

    def update_scroll_status(self, status_text: str) -> None:
        """
        更新状态显示 - 每次只显示一行，显示所有后台信息
        
        Args:
            status_text: 状态文本
        """
        try:
            # 检查状态栏标签是否存在
            if not hasattr(self, 'status_scroll_label') or not self.status_scroll_label:
                return
            
            # 检查是否处于解析暂停状态，如果是则忽略状态更新
            # 修复逻辑：只有当按钮文本是"暂停"且is_parsing为True时，才是正常解析状态，应该显示状态
            # 当按钮文本是"解析"且is_parsing为True时，说明是暂停状态，应该忽略状态更新
            # 临时注释掉暂停检查，确保状态栏能正常显示
            # if hasattr(self, 'smart_parse_button') and self.smart_parse_button.text() == tr("main_window.parse") and hasattr(self, 'is_parsing') and self.is_parsing:
            #     # 处于解析暂停状态，忽略状态更新
            #     return
            
            # 检查是否处于下载暂停状态，如果是则忽略状态更新
            if hasattr(self, 'smart_pause_button') and self.smart_pause_button.text() == tr("main_window.resume_download"):
                # 处于下载暂停状态，忽略状态更新
                return
            
            # 不过滤任何消息，显示所有后台信息
            # 添加时间戳
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_text = f"[{timestamp}] {status_text}"
            
            # 检查文本长度，如果过长则截断
            max_length = 120  # 最大显示长度
            if len(formatted_text) > max_length:
                # 保留时间戳和开头部分，末尾添加省略号
                timestamp_part = f"[{timestamp}] "
                available_length = max_length - len(timestamp_part) - 3  # 3是省略号长度
                if available_length > 0:
                    truncated_text = f"{timestamp_part}{status_text[:available_length]}..."
                else:
                    truncated_text = f"{timestamp_part}..."
            else:
                truncated_text = formatted_text
            
            # 直接更新状态栏，每次只显示一行
            self.status_scroll_label.setText(truncated_text)
            
            # 记录最新状态
            self.latest_progress = status_text
                
        except Exception as e:
            # 记录错误但不影响程序运行
            logger.error(f"状态栏更新失败: {e}")
    
    def _should_filter_status_message(self, message: str) -> bool:
        """判断是否应该过滤掉状态消息"""
        # 过滤掉一些过于频繁或无用的消息
        filter_patterns = [
            tr("main_window.status_update_failed"),
            "QObject::startTimer",
            "QObject::killTimer",
            "QThread::start",
            "QThread::wait"
        ]
        
        for pattern in filter_patterns:
            if pattern in message:
                return True
        
        # 过滤掉过于频繁的进度信息
        if "progress" in message.lower() and "download" in message.lower():
            # 限制下载进度信息的频率
            current_time = time.time()
            if not hasattr(self, '_last_progress_time'):
                self._last_progress_time = 0
            
            if current_time - self._last_progress_time < 1:  # 1秒内只显示一次
                return True
            self._last_progress_time = current_time
        
        return False

    def create_menu_bar(self) -> None:
        """
        创建菜单栏
        
        包含文件、编辑、工具、帮助等传统菜单项。
        """
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu(tr('menu.file'))
        
        # 新建会话
        new_action = file_menu.addAction(tr('menu.new_session'))
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_session)
        
        file_menu.addSeparator()
        

        
        # 打开保存文件夹
        open_folder_action = file_menu.addAction(tr('menu.open_folder'))
        open_folder_action.setShortcut('Ctrl+Shift+O')
        open_folder_action.triggered.connect(self.open_save_path)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = file_menu.addAction(tr('menu.exit'))
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        
        # 编辑菜单
        edit_menu = menubar.addMenu(tr('menu.edit'))
        
        # 清空输入
        clear_input_action = edit_menu.addAction(tr('menu.clear_input'))
        clear_input_action.setShortcut('Ctrl+L')
        clear_input_action.triggered.connect(self.clear_input)
        
        # 清空列表
        clear_results_action = edit_menu.addAction(tr('menu.clear_list'))
        clear_results_action.setShortcut('Ctrl+Shift+R')
        clear_results_action.triggered.connect(self.clear_parse_results)
        
        # 工具菜单
        tools_menu = menubar.addMenu(tr('menu.tools'))
        
        tools_menu.addSeparator()
        
        # 设置
        settings_action = tools_menu.addAction(tr('menu.settings'))
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.show_settings_dialog)
        
        
        # 下载历史
        history_action = tools_menu.addAction(tr('menu.history'))
        history_action.setShortcut('Ctrl+H')
        history_action.triggered.connect(self.show_download_history)
        
        # 字幕下载
        subtitle_action = tools_menu.addAction(tr('menu.subtitle'))
        subtitle_action.setShortcut('Ctrl+T')
        subtitle_action.triggered.connect(self.show_subtitle_dialog)
        
        tools_menu.addSeparator()
        
        # 日志管理
        log_action = tools_menu.addAction(tr('menu.log'))
        log_action.setShortcut('Ctrl+Shift+L')
        log_action.triggered.connect(self.show_log_dialog)
        
        # 帮助菜单
        help_menu = menubar.addMenu(tr('menu.help'))
        
        # 使用说明
        help_action = help_menu.addAction(tr('menu.help_content'))
        help_action.setShortcut('F1')
        help_action.triggered.connect(self.show_help_dialog)
        
        help_menu.addSeparator()
        
        # 检查更新
        update_action = help_menu.addAction(tr('menu.check_update'))
        update_action.setShortcut('Ctrl+U')
        update_action.triggered.connect(self.check_for_updates)
        
        help_menu.addSeparator()
        
        # 问题反馈
        feedback_action = help_menu.addAction(tr('menu.feedback'))
        feedback_action.setShortcut('Ctrl+Shift+F')
        feedback_action.triggered.connect(self.show_feedback_dialog)
        
        help_menu.addSeparator()
        
        # 关于
        about_action = help_menu.addAction(tr('menu.about'))
        about_action.triggered.connect(self.show_about_dialog)
    
    def ensure_column_widths(self) -> None:
        """确保列宽设置正确，特别是选择列的宽度"""
        # 确保"选择"列有足够的宽度显示完整复选框
        self.format_tree.setColumnWidth(0, 172)
        
        # 设置最小列宽，防止被压缩
        header = self.format_tree.header()
        header.setMinimumSectionSize(172)
        
        # 确保其他列的合理宽度
        if self.format_tree.columnWidth(1) < 200:  # 文件名列
            self.format_tree.setColumnWidth(1, 250)
        if self.format_tree.columnWidth(4) < 100:  # 文件大小列
            self.format_tree.setColumnWidth(4, 120)
        if self.format_tree.columnWidth(5) < 80:   # 状态列（最后一列）
            self.format_tree.setColumnWidth(5, 100)
    
    def init_system_tray(self) -> None:
        """初始化系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("系统托盘不可用")
            return
        
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置图标
        icon_path = self.get_icon_path()
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 显示主窗口
        show_action = QAction(tr("tray.show_main_window"), self)
        show_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        # 设置
        settings_action = QAction(tr("menu.settings"), self)
        settings_action.triggered.connect(self.show_settings_dialog)
        tray_menu.addAction(settings_action)
        
        
        # 下载历史
        history_action = QAction(tr("menu.history"), self)
        history_action.triggered.connect(self.show_download_history)
        tray_menu.addAction(history_action)
        
        tray_menu.addSeparator()
        
        # 退出
        exit_action = QAction(tr("menu.exit"), self)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)
        
        # 连接托盘图标点击事件
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
        
        # 检查是否需要在启动时最小化
        if self.settings.value("start_minimized", False, type=bool):
            self.minimize_to_tray()
    
    def _center_window(self) -> None:
        """将窗口居中显示"""
        # 获取屏幕几何信息
        screen = QApplication.desktop().screenGeometry()
        
        # 设置窗口大小
        window_width = 1000
        window_height = 700
        
        # 计算居中位置
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        
        # 设置窗口位置和大小
        self.setGeometry(x, y, window_width, window_height)
    
    def show_main_window(self) -> None:
        """显示主窗口"""
        self.show()
        self.raise_()
        self.activateWindow()
        self.is_minimized_to_tray = False
    
    def minimize_to_tray(self) -> None:
        """最小化到系统托盘"""
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            self.is_minimized_to_tray = True
            self.tray_icon.showMessage(
                tr("app.title"),
                tr("tray.minimized_to_tray"),
                QSystemTrayIcon.Information,
                2000
            )
    
    def on_tray_icon_activated(self, reason) -> None:
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_main_window()
    
    def quit_application(self) -> None:
        """退出应用程序"""
        # 停止所有下载
        if self.is_downloading:
            reply = QMessageBox.question(
                self, tr("messages.confirm_exit"),
                tr("main_window.exit_with_downloads"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            self.cancel_downloads()
        
        # 退出应用程序
        QApplication.quit()
    
    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        # 检查是否启用了最小化到托盘
        if self.settings.value("minimize_to_tray", False, type=bool):
            self.minimize_to_tray()
            event.ignore()  # 阻止窗口关闭
        else:
            # 正常关闭
            self.quit_application()
            event.accept()
    
    def cleanup_workers(self) -> None:
        """清理所有工作线程，防止内存泄漏"""
        try:
            # 清理解析工作线程
            for worker in self.parse_workers[:]:  # 使用切片创建副本避免修改迭代中的列表
                if worker and worker.isRunning():
                    worker.cancel()
                    worker.wait(3000)  # 等待最多3秒
                    if worker.isRunning():
                        worker.terminate()  # 强制终止
                        worker.wait(1000)
                self.parse_workers.remove(worker)
            
            # 清理下载工作线程
            for worker in self.download_workers[:]:
                if worker and worker.isRunning():
                    worker.cancel()
                    worker.wait(3000)
                    if worker.isRunning():
                        worker.terminate()
                        worker.wait(1000)
                self.download_workers.remove(worker)
            
            # 清理网易云音乐工作线程
            for worker in self.netease_music_workers[:]:
                if worker and hasattr(worker, 'cancel') and callable(worker.cancel):
                    worker.cancel()
                    if hasattr(worker, 'wait') and callable(worker.wait):
                        worker.wait(3000)
                self.netease_music_workers.remove(worker)
            
            # 清空缓存和队列
            self.parse_cache.clear()
            self.formats.clear()
            self.download_progress.clear()
            self.download_queue.clear()
            
            logger.info("所有工作线程已清理完成")
            
        except Exception as e:
            logger.error(f"清理工作线程时发生错误: {e}")
    
    def quit_application(self) -> None:
        """退出应用程序"""
        try:
            # 停止所有下载
            if self.is_downloading:
                reply = QMessageBox.question(
                    self, tr("messages.confirm_exit"),
                    tr("main_window.exit_with_downloads"),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
                self.cancel_downloads()
            
            # 清理所有工作线程
            self.cleanup_workers()
            
            # 退出应用程序
            QApplication.quit()
            
        except Exception as e:
            logger.error(f"退出应用程序时发生错误: {e}")
            QApplication.quit()
