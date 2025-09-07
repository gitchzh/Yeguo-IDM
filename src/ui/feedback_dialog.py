"""
Feedback Dialog Module

Provides a user interface for feedback issues, supporting email feedback.
"""

import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QMessageBox, QLineEdit, QFormLayout,
    QGroupBox, QProgressBar, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

from src.core.config import Config
from src.utils.logger import logger
from src.core.i18n_manager import tr


class EmailSender(QThread):
    """邮件发送线程"""
    
    success = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, subject: str, content: str, user_email: str):
        super().__init__()
        self.subject = subject
        self.content = content
        self.user_email = user_email
        
    def run(self):
        """发送邮件"""
        try:
            # 邮件配置 - 从环境变量读取，如果没有设置则使用默认值
            sender_email = os.getenv("FEEDBACK_EMAIL", "yeguo.feedback@gmail.com")
            sender_password = os.getenv("FEEDBACK_PASSWORD", "your_app_password")
            receiver_email = os.getenv("RECEIVER_EMAIL", "gmrchzh@gmail.com")
            
            # 检查是否配置了正确的邮箱信息
            if sender_password == "your_app_password":
                raise Exception("邮件配置未完成，请按照 EMAIL_SETUP.md 文档配置邮箱信息")
            
            # 创建邮件
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = receiver_email
            message["Subject"] = f"[椰果下载器反馈] {self.subject}"
            
            # 邮件内容
            body = f"""
用户反馈信息：

反馈时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
用户邮箱：{self.user_email}
软件版本：{Config.APP_VERSION}

问题描述：
{self.content}

---
        此邮件由椰果IDM自动发送
            """
            
            message.attach(MIMEText(body, "plain", "utf-8"))
            
            # 发送邮件 - 支持QQ邮箱和Gmail
            if "@qq.com" in sender_email:
                # QQ邮箱配置
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context) as server:
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, receiver_email, message.as_string())
            else:
                # Gmail配置
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, receiver_email, message.as_string())
                
            self.success.emit()
            
        except Exception as e:
            logger.error(f"发送反馈邮件失败: {e}")
            self.error.emit(str(e))


class FeedbackDialog(QDialog):
    """反馈对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.email_sender = None
        
        # 应用与设置界面一致的样式表
        self.setStyleSheet("""
            /* 全局字体设置 - 统一微软雅黑 */
            * {
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                font-weight: 400;
            }
            
            QDialog {
                background-color: #ffffff;
                color: #1e1e1e;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
            }
            
            QGroupBox {
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                font-weight: 400;
                color: #1e1e1e;
                border: 1px solid #e1e1e1;
                border-radius: 3px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #f3f3f3;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
                color: #1e1e1e;
            }
            
            /* 按钮样式 - 与设置界面完全一致 */
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
                background-color: #f3f3f3;
                color: #a0a0a0;
                border: 1px solid #e1e1e1;
            }
            
            /* QDialogButtonBox按钮样式 - 与设置界面完全一致 */
            QDialogButtonBox QPushButton {
                background-color: #fdfdfd;
                color: #000000;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 4px 8px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                min-height: 20px;
                min-width: 50px;
                font-weight: normal;
            }
            
            QDialogButtonBox QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            
            QDialogButtonBox QPushButton:pressed {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            
            QLineEdit, QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e1e1e1;
                padding: 6px 0px 6px 8px;
                color: #1e1e1e;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                border-radius: 3px;
                selection-background-color: #0078d4;
            }
            
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #0078d4;
                outline: none;
                border-radius: 3px;
            }
            
            QLineEdit:hover, QTextEdit:hover {
                border: 1px solid #0078d4;
                border-radius: 3px;
            }
            
            QLabel {
                color: #1e1e1e;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
            }
            
            QProgressBar {
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                border: 1px solid #e1e1e1;
                border-radius: 3px;
                text-align: center;
                background-color: #f3f3f3;
                color: #1e1e1e;
            }
            
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 2px;
            }
        """)
        self.init_ui()
        
    def center_on_parent(self) -> None:
        """将对话框居中显示在父窗口上"""
        if self.parent():
            parent_rect = self.parent().geometry()
            dialog_rect = self.geometry()
            x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
            self.move(x, y)
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(tr("feedback.title"))
        self.setFixedSize(520, 450)  # 增加窗口尺寸确保完整显示
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 设置窗口居中显示
        self.center_on_parent()
        
        # 设置图标
        try:
            icon_path = "resources/LOGO.png"
            self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            logger.warning(f"设置窗口图标失败: {e}")
            
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(8)  # 适当增加组件间距
        layout.setContentsMargins(20, 20, 20, 20)  # 增加底部边距
        
        # 标题
        title_label = QLabel(tr("feedback.title"))
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))  # 减小标题字体
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 4px;")  # 减少底部边距
        layout.addWidget(title_label)
        
        # 说明文字
        desc_label = QLabel(tr("feedback.description"))
        desc_label.setFont(QFont("Microsoft YaHei", 9))  # 减小说明文字字体
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7f8c8d; margin: 4px 0;")  # 减少上下边距
        layout.addWidget(desc_label)
        
        # 表单组
        form_group = QGroupBox(tr("feedback.feedback_info"))
        form_layout = QFormLayout()
        form_layout.setSpacing(6)  # 减少表单项间距
        form_layout.setLabelAlignment(Qt.AlignRight)  # 标签右对齐
        
        # 用户邮箱
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText(tr("feedback.email_placeholder"))
        self.email_edit.setFont(QFont("Microsoft YaHei", 9))  # 减小输入框字体
        self.email_edit.setFixedHeight(28)  # 减小输入框高度
        form_layout.addRow(tr("feedback.contact_email"), self.email_edit)
        
        # 问题标题
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(tr("feedback.title_placeholder"))
        self.title_edit.setFont(QFont("Microsoft YaHei", 9))  # 减小输入框字体
        self.title_edit.setFixedHeight(28)  # 减小输入框高度
        form_layout.addRow(tr("feedback.problem_title"), self.title_edit)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 问题描述
        desc_group = QGroupBox(tr("feedback.problem_description"))
        desc_layout = QVBoxLayout()
        desc_layout.setContentsMargins(0, 0, 0, 0)
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText(tr("feedback.description_placeholder"))
        self.content_edit.setFont(QFont("Microsoft YaHei", 9))  # 减小文本编辑框字体
        self.content_edit.setMinimumHeight(120)  # 增加文本编辑框高度
        self.content_edit.setMaximumHeight(120)  # 限制最大高度
        desc_layout.addWidget(self.content_edit)
        
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(16)  # 进一步减小进度条高度
        layout.addWidget(self.progress_bar)
        
        # 按钮布局 - 与设置界面保持一致
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(0, 12, 0, 0)
        
        # 添加弹性空间
        button_layout.addStretch()
        
        # 使用QDialogButtonBox保持与设置界面一致
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.submit_feedback)
        self.button_box.rejected.connect(self.reject)
        
        # 设置按钮文本
        self.button_box.button(QDialogButtonBox.Ok).setText(tr("feedback.submit"))
        self.button_box.button(QDialogButtonBox.Cancel).setText(tr("feedback.cancel"))
        
        button_layout.addWidget(self.button_box)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        
    def submit_feedback(self):
        """提交反馈"""
        # 验证输入
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        user_email = self.email_edit.text().strip()
        
        if not title:
            QMessageBox.warning(self, tr("messages.info"), tr("feedback.title_required"))
            self.title_edit.setFocus()
            return
            
        if not content:
            QMessageBox.warning(self, tr("messages.info"), tr("feedback.description_required"))
            self.content_edit.setFocus()
            return
            
        # 显示确认对话框
        msg_box = QMessageBox()
        msg_box.setWindowTitle(tr("messages.confirm"))
        msg_box.setText(tr("feedback.confirm_submit"))
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.button(QMessageBox.Yes).setText(tr("messages.yes"))
        msg_box.button(QMessageBox.No).setText(tr("messages.no"))
        
        if msg_box.exec_() != QMessageBox.Yes:
            return
            
        # 开始发送
        self.start_sending(title, content, user_email)
        
    def start_sending(self, title: str, content: str, user_email: str):
        """开始发送反馈"""
        # 禁用界面
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        
        # 创建发送线程
        self.email_sender = EmailSender(title, content, user_email)
        self.email_sender.success.connect(self.on_send_success)
        self.email_sender.error.connect(self.on_send_error)
        self.email_sender.start()
        
    def on_send_success(self):
        """发送成功"""
        self.progress_bar.setVisible(False)
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle(tr("messages.operation_success"))
        msg_box.setText(tr("feedback.submit_success"))
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.button(QMessageBox.Ok).setText(tr("messages.ok"))
        msg_box.exec_()
        
        self.accept()
        
    def on_send_error(self, error_msg: str):
        """发送失败"""
        self.progress_bar.setVisible(False)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        self.button_box.button(QDialogButtonBox.Cancel).setEnabled(True)
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle(tr("messages.operation_failed"))
        msg_box.setText(tr("feedback.submit_error"))
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.button(QMessageBox.Ok).setText(tr("messages.ok"))
        msg_box.exec_()
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.email_sender and self.email_sender.isRunning():
            self.email_sender.terminate()
            self.email_sender.wait()
        event.accept()
