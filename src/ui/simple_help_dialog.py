"""
Yeguo IDM - Simple Help Dialog

Provides simple and easy-to-use help functionality, including basic usage instructions, shortcuts, and about information.

Main Features:
- Usage Instructions: Quick start guide, platform support, advanced features, common questions
- Shortcuts: Common shortcut list and descriptions
- About Information: Version info, technical details, contact information

Technical Features:
- Simple tab design
- Modern UI styling
- Responsive layout
- Automatic window centering
- Complete help content

Author: Yeguo IDM Development Team
Contact Email: gmrchzh@gmail.com
Version: 1.6.0
Created: September 7, 2025
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QTabWidget, QWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ..core.config import Config
from ..utils.logger import logger
from ..core.i18n_manager import tr


class SimpleHelpDialog(QDialog):
    """简洁的帮助对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("help.title"))
        self.setModal(True)
        self.setFixedSize(600, 500)
        
        self.init_ui()
        self.center_on_parent()
    
    def center_on_parent(self) -> None:
        """将对话框居中显示在父窗口上"""
        if self.parent():
            parent_rect = self.parent().geometry()
            dialog_rect = self.geometry()
            x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
            self.move(x, y)
    
    def init_ui(self) -> None:
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel(tr("help.title"))
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1e1e1e;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 8px;
                margin-bottom: 10px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }
        """)
        layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e9ecef;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #1e1e1e;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #e9ecef;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 400;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #007bff;
                border-bottom: 2px solid #007bff;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)
        
        # 添加标签页
        self.create_help_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_button = QPushButton(tr("messages.close"))
        self.close_button.setStyleSheet("""
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
        """)
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_help_tab(self) -> None:
        """创建使用说明标签页"""
        help_widget = QWidget()
        layout = QVBoxLayout()
        
        # 帮助内容
        help_content = QTextEdit()
        help_content.setReadOnly(True)
        help_content.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.6;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                color: #1e1e1e;
            }
        """)
        
        help_text = f"""
<h2>{tr("help.quick_start")}</h2>
<p><b>1. {tr("help.step1")}</b><br>
{tr("help.step1_desc")}</p>

<p><b>2. {tr("help.step2")}</b><br>
{tr("help.step2_desc")}</p>

<p><b>3. {tr("help.step3")}</b><br>
{tr("help.step3_desc")}</p>

<p><b>4. {tr("help.step4")}</b><br>
{tr("help.step4_desc")}</p>

<h3>{tr("help.supported_platforms")}</h3>
<ul>
<li>YouTube - {tr("help.video_audio_subtitle")}</li>
<li>Bilibili - {tr("help.video_audio")}</li>
<li>{tr("help.netease_music")} - {tr("help.music_download")}</li>
<li>{tr("help.other_platforms")}</li>
</ul>

<h3>{tr("help.advanced_features")}</h3>
<ul>
<li><b>{tr("help.batch_download")}</b> - {tr("help.batch_download_desc")}</li>
<li><b>{tr("help.netease_music")}</b> - {tr("help.netease_music_desc")}</li>
<li><b>{tr("help.subtitle_download")}</b> - {tr("help.subtitle_download_desc")}</li>
<li><b>{tr("help.format_conversion")}</b> - {tr("help.format_conversion_desc")}</li>
<li><b>{tr("help.history_management")}</b> - {tr("help.history_management_desc")}</li>
</ul>

<h3>{tr("help.shortcuts")}</h3>
<table border="0" cellpadding="5" cellspacing="0">
<tr><td><b>F1</b></td><td>{tr("help.show_help")}</td></tr>
<tr><td><b>Ctrl+N</b></td><td>{tr("help.new_session")}</td></tr>
<tr><td><b>Ctrl+L</b></td><td>{tr("help.clear_input")}</td></tr>
<tr><td><b>Ctrl+Q</b></td><td>{tr("help.exit_program")}</td></tr>
<tr><td><b>Ctrl+Shift+O</b></td><td>{tr("help.open_folder")}</td></tr>
<tr><td><b>Ctrl+Shift+R</b></td><td>{tr("help.clear_list")}</td></tr>
<tr><td><b>Ctrl+,</b></td><td>{tr("help.settings")}</td></tr>
<tr><td><b>Ctrl+H</b></td><td>{tr("help.download_history")}</td></tr>
<tr><td><b>Ctrl+T</b></td><td>{tr("help.subtitle_download")}</td></tr>
<tr><td><b>Ctrl+Shift+L</b></td><td>{tr("help.log_management")}</td></tr>
<tr><td><b>Ctrl+Shift+F</b></td><td>{tr("help.feedback")}</td></tr>
</table>

<h3>{tr("help.common_questions")}</h3>
<p><b>{tr("help.download_failed")}</b><br>
{tr("help.check_network")}<br>
{tr("help.check_link")}<br>
{tr("help.try_other_format")}</p>

<p><b>{tr("help.format_selection")}</b><br>
{tr("help.mp4_best")}<br>
{tr("help.hd_quality")}<br>
{tr("help.mp3_audio")}</p>

<h3>{tr("help.get_help")}</h3>
<p>{tr("help.help_description")}</p>
<ul>
<li><b>{tr("help.email_contact")}</b>: gmrchzh@gmail.com</li>
<li><b>Gitee Issues</b>: <a href="https://gitee.com/mrchzh/ygmdm/issues">{tr("help.submit_issue")}</a></li>
<li><b>GitHub Issues</b>: <a href="https://github.com/gitchzh/Yeguo-IDM/issues">{tr("help.submit_issue")}</a></li>
</ul>

<h3>{tr("help.view_latest_code")}</h3>
<p>{tr("help.view_latest_code_desc")}</p>
<ul>
<li><b>{tr("help.gitee_repo")}</b>: <a href="https://gitee.com/mrchzh/ygmdm">https://gitee.com/mrchzh/ygmdm</a></li>
<li><b>{tr("help.github_repo")}</b>: <a href="https://github.com/gitchzh/Yeguo-IDM">https://github.com/gitchzh/Yeguo-IDM</a></li>
</ul>
<p><i>{tr("help.thanks")}</i></p>
        """
        
        help_content.setHtml(help_text)
        layout.addWidget(help_content)
        
        help_widget.setLayout(layout)
        self.tab_widget.addTab(help_widget, tr("help.quick_start"))


class QuickHelpDialog(QDialog):
    """快速帮助对话框"""
    
    def __init__(self, topic: str, parent=None):
        super().__init__(parent)
        self.topic = topic
        self.setWindowTitle(f"{tr('help.quick_help')} - {topic}")
        self.setModal(True)
        self.setFixedSize(450, 350)
        
        self.init_ui()
        self.center_on_parent()
    
    def center_on_parent(self) -> None:
        """将对话框居中显示在父窗口上"""
        if self.parent():
            parent_rect = self.parent().geometry()
            dialog_rect = self.geometry()
            x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
            self.move(x, y)
    
    def init_ui(self) -> None:
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel(f"快速帮助 - {self.topic}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #1e1e1e;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 8px;
                margin-bottom: 10px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }
        """)
        layout.addWidget(title_label)
        
        # 内容
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.6;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                color: #1e1e1e;
            }
        """)
        self.content.setHtml(self.get_quick_help_content())
        
        layout.addWidget(self.content)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_button = QPushButton(tr("messages.close"))
        self.close_button.setStyleSheet("""
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
        """)
        self.close_button.clicked.connect(self.accept)
        
        self.full_help_button = QPushButton(tr("help.show_help"))
        self.full_help_button.setStyleSheet("""
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
        """)
        self.full_help_button.clicked.connect(self.show_full_help)
        
        button_layout.addWidget(self.close_button)
        button_layout.addWidget(self.full_help_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_quick_help_content(self) -> str:
        """获取快速帮助内容"""
        content_map = {
            tr("help.download"): f"""
<h2>{tr("help.download_steps")}</h2>
<ol>
<li><b>{tr("help.paste_link")}</b> - {tr("help.paste_link_desc")}</li>
<li><b>{tr("help.click_parse")}</b> - {tr("help.click_parse_desc")}</li>
<li><b>{tr("help.select_format")}</b> - {tr("help.select_format_desc")}</li>
<li><b>{tr("help.start_download")}</b> - {tr("help.start_download_desc")}</li>
</ol>

<h3>{tr("help.supported_platforms")}</h3>
<ul>
<li>YouTube - {tr("help.video_audio_subtitle")}</li>
<li>Bilibili - {tr("help.video_audio")}</li>
<li>{tr("help.netease_music")} - {tr("help.music_download")}</li>
<li>{tr("help.other_platforms")}</li>
</ul>
            """,
            tr("help.format"): f"""
<h2>{tr("help.format_guide")}</h2>

<h3>{tr("help.video_formats")}</h3>
<ul>
<li><b>MP4</b> - {tr("help.mp4_desc")}</li>
<li><b>AVI</b> - {tr("help.avi_desc")}</li>
<li><b>MKV</b> - {tr("help.mkv_desc")}</li>
</ul>

<h3>{tr("help.resolution_selection")}</h3>
<ul>
<li><b>1080p</b> - {tr("help.1080p_desc")}</li>
<li><b>720p</b> - {tr("help.720p_desc")}</li>
<li><b>480p</b> - {tr("help.480p_desc")}</li>
</ul>

<h3>{tr("help.audio_formats")}</h3>
<ul>
<li><b>MP3</b> - {tr("help.mp3_desc")}</li>
<li><b>AAC</b> - {tr("help.aac_desc")}</li>
<li><b>FLAC</b> - {tr("help.flac_desc")}</li>
</ul>
            """,
            tr("help.shortcuts"): f"""
<h2>{tr("help.shortcuts")}</h2>

<h3>{tr("help.basic_operations")}</h3>
<ul>
<li><b>F1</b> - {tr("help.show_help")}</li>
<li><b>Ctrl+N</b> - {tr("help.new_session")}</li>
<li><b>Ctrl+L</b> - {tr("help.clear_input")}</li>
<li><b>Ctrl+Q</b> - {tr("help.exit_program")}</li>
</ul>

<h3>{tr("help.file_operations")}</h3>
<ul>
<li><b>Ctrl+Shift+O</b> - {tr("help.open_folder")}</li>
<li><b>Ctrl+Shift+R</b> - {tr("help.clear_list")}</li>
</ul>

<h3>{tr("help.tools_menu")}</h3>
<ul>
<li><b>Ctrl+,</b> - {tr("help.settings")}</li>
<li><b>Ctrl+H</b> - {tr("help.download_history")}</li>
<li><b>Ctrl+T</b> - {tr("help.subtitle_download")}</li>
</ul>
            """
        }
        
        return content_map.get(self.topic, f"<h2>{self.topic}</h2><p>相关内容正在完善中...</p>")
    
    def show_full_help(self) -> None:
        """显示完整帮助"""
        self.accept()
        help_dialog = SimpleHelpDialog(self.parent())
        help_dialog.exec_()
