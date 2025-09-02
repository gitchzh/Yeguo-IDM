"""主窗口方法模块

该模块包含VideoDownloader主窗口的所有业务逻辑方法，包括：
- 视频解析和格式过滤
- 下载管理和状态更新
- UI交互和事件处理
- 设置和配置管理
- 日志查看和导出
- 帮助和反馈功能

主要类：
- VideoDownloaderMethods: 主窗口方法类，包含所有业务逻辑

作者: 椰果IDM开发团队
版本: 1.0.0"""

import os
import re
import time
import threading
import gc
import psutil
import shutil
from typing import Dict, List, Optional, Tuple, Any
from collections import OrderedDict

from PyQt5.QtWidgets import (
    QMessageBox, QFileDialog, QTreeWidgetItem, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QApplication
)
from PyQt5.QtCore import Qt, QUrl, QPoint, QTimer
from PyQt5.QtGui import QCloseEvent, QDesktopServices, QPixmap

from ..core.config import Config
from ..core.queue_manager import queue_manager, DownloadStatus
from ..core.history import history_manager, DownloadRecord
from ..core.playlist_manager import playlist_manager

from ..core.subtitle_manager import subtitle_manager

from ..core.netease_music_manager import NetEaseMusicManager
from ..utils.logger import logger
from ..utils.file_utils import sanitize_filename, format_size, check_ffmpeg
from ..core.log_manager import log_manager, LogViewer
from ..workers.parse_worker import ParseWorker
from ..workers.download_worker import DownloadWorker

from ..workers.netease_music_worker import NetEaseMusicParseWorker



def is_standard_resolution(resolution: str) -> bool:
    """
    判断是否为标准分辨率
    
    Args:
        resolution: 分辨率字符串，如 "1920x1080", "1280x720" 等
        
    Returns:
        bool: 是否为标准分辨率
    """
    # 标准分辨率列表 - 扩展支持更多常见分辨率
    standard_resolutions = {
        # 4K
        "3840x2160", "4096x2160",
        # 2K
        "2560x1440", "2048x1080",
        # 1080P
        "1920x1080", "1920x1088", "1440x1080",  # 添加1440x1080（4:3比例1080P）
        # 720P
        "1280x720", "1280x736", "960x720",  # 添加960x720（4:3比例720P）
        # 480P - 添加更多变体
        "854x480", "848x480", "832x480", "852x480", "850x480", "856x480", "858x480", "860x480", "862x480", "864x480", "866x480", "868x480", "870x480", "872x480", "874x480", "876x480", "878x480", "880x480",
        # 360P
        "640x360", "640x368", "640x480",  # 添加640x480（4:3比例480P）
        # 240P
        "426x240", "424x240", "480x360",  # 添加480x360（4:3比例360P）
        # 144P
        "256x144", "256x160"
    }
    
    # 清理分辨率字符串，移除空格和特殊字符
    clean_resolution = resolution.strip().lower()
    
    # 检查是否在标准分辨率列表中
    if clean_resolution in standard_resolutions:
        return True
    
    # 检查是否为音频格式（没有分辨率）
    if clean_resolution in ["audio only", "audio_only", "audio"]:
        return True
    
    # 检查是否为标准P格式（如1080p, 720p等）
    if re.match(r"^\d+p$", clean_resolution):
        p_value = int(clean_resolution[:-1])
        if p_value in [144, 240, 360, 480, 720, 1080, 1440, 2160]:
            return True
    
    # 检查是否为接近标准分辨率的格式（允许±1像素的误差）
    if "x" in clean_resolution:
        try:
            width, height = clean_resolution.split("x")
            width, height = int(width), int(height)
            
            # 检查是否接近标准分辨率
            for std_res in standard_resolutions:
                if "x" in std_res:
                    std_width, std_height = std_res.split("x")
                    std_width, std_height = int(std_width), int(std_height)
                    
                    # 允许±4像素的误差，以包含更多变体
                    if abs(width - std_width) <= 4 and abs(height - std_height) <= 4:
                        return True
        except (ValueError, IndexError):
            pass
    
    return False


def filter_formats(formats: List[Dict], strict_filter: bool = False) -> List[Dict]:
    """
    过滤格式列表，只保留标准分辨率的格式
    
    Args:
        formats: 原始格式列表
        strict_filter: 是否使用严格过滤模式，False时保留更多格式
        
    Returns:
        List[Dict]: 过滤后的格式列表
    """
    filtered_formats = []
    
    for format_info in formats:
        # 获取分辨率信息
        resolution = format_info.get("resolution", "")
        format_note = format_info.get("format_note", "")
        width = format_info.get("width")
        height = format_info.get("height")
        
        # 构建完整的分辨率字符串
        resolution_str = resolution
        if not resolution_str and width and height:
            resolution_str = f"{width}x{height}"
        elif not resolution_str and format_note:
            resolution_str = format_note
        
        # 检查是否为音频格式
        acodec = format_info.get("acodec", "none")
        vcodec = format_info.get("vcodec", "none")
        if acodec != "none" and vcodec == "none":
            # 音频格式，保留
            filtered_formats.append(format_info)
            continue
        
        # 检查是否为视频格式
        if vcodec == "none":
            # 跳过纯音频格式（非视频）
            continue
        
        # 如果不使用严格过滤，保留所有视频格式
        if not strict_filter:
            filtered_formats.append(format_info)
            continue
        
        # 严格过滤模式：只保留标准分辨率的格式
        if is_standard_resolution(resolution_str):
            filtered_formats.append(format_info)
        else:
            logger.info(f"过滤掉非标准分辨率: {resolution_str} (原始: {resolution}, 说明: {format_note}, 宽高: {width}x{height})")
    
    return filtered_formats


class VideoDownloaderMethods:
    """主窗口类的方法实现"""
    
    def __init__(self):
        """初始化主窗口方法"""
        # 线程安全锁
        self._parse_lock = threading.RLock()  # 使用可重入锁
        self._download_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._memory_lock = threading.Lock()  # 内存检查锁
        
        # 内存监控
        self._last_memory_check = time.time()
        self._memory_check_interval = 30  # 30秒检查一次内存
    
    def load_settings(self) -> None:
        """加载保存的设置"""
        self.save_path = self.settings.value("save_path", os.getcwd())
        # 如果 path_label 已存在，则更新其文本
        if hasattr(self, 'path_label'):
            self.path_label.setText(f"保存路径: {self.save_path}")

    def choose_save_path(self) -> None:
        """选择保存路径"""
        folder = QFileDialog.getExistingDirectory(self, "选择保存路径", self.save_path)
        if folder:
            self.save_path = folder
            # 如果 path_label 已存在，则更新其文本
            if hasattr(self, 'path_label'):
                self.path_label.setText(f"保存路径: {self.save_path}")

    def validate_url(self, url: str) -> bool:
        """验证 URL 是否有效"""

        
        # 检查是否为网易云音乐链接
        if NetEaseMusicManager().is_netease_music_url(url):
            return True
        
        # 检查是否为标准HTTP/HTTPS链接
        return bool(re.match(r"^https?://.*", url))

    def toggle_checkbox(self, item: QTreeWidgetItem, column: int) -> None:
        """双击切换复选框状态"""
        if item and column == 0:  # 只处理第0列的复选框
            current_state = item.checkState(column)
            new_state = Qt.Checked if current_state == Qt.Unchecked else Qt.Unchecked
            item.setCheckState(column, new_state)
            self.on_item_changed(item, column)

    def select_all_formats(self) -> None:
        """全选所有格式"""
        # 临时禁用信号以避免触发 on_item_changed
        self.format_tree.blockSignals(True)
        try:
            for i in range(self.format_tree.topLevelItemCount()):
                root_item = self.format_tree.topLevelItem(i)
                if root_item.childCount() > 0:
                    # 有子项的项目（视频等）
                    for j in range(root_item.childCount()):
                        child_item = root_item.child(j)
                        child_item.setCheckState(0, Qt.Checked)  # 子项复选框在第0列
                    # 设置父项状态
                    root_item.setCheckState(0, Qt.Checked)
                else:
                    # 没有子项的项目（网易云音乐等）
                    root_item.setCheckState(0, Qt.Checked)
        finally:
            self.format_tree.blockSignals(False)
        self.update_selection_count()
        self.update_smart_select_button_text()

    def deselect_all_formats(self) -> None:
        """取消全选所有格式"""
        # 临时禁用信号以避免触发 on_item_changed
        self.format_tree.blockSignals(True)
        try:
            for i in range(self.format_tree.topLevelItemCount()):
                root_item = self.format_tree.topLevelItem(i)
                if root_item.childCount() > 0:
                    # 有子项的项目（视频等）
                    for j in range(root_item.childCount()):
                        child_item = root_item.child(j)
                        child_item.setCheckState(0, Qt.Unchecked)  # 子项复选框在第0列
                    # 设置父项状态
                    root_item.setCheckState(0, Qt.Unchecked)
                else:
                    # 没有子项的项目（网易云音乐等）
                    root_item.setCheckState(0, Qt.Unchecked)
        finally:
            self.format_tree.blockSignals(False)
        self.update_selection_count()
        self.update_smart_select_button_text()

    def invert_selection(self) -> None:
        """反选所有格式"""
        # 临时禁用信号以避免触发 on_item_changed
        self.format_tree.blockSignals(True)
        try:
            for i in range(self.format_tree.topLevelItemCount()):
                root_item = self.format_tree.topLevelItem(i)
                if root_item.childCount() > 0:
                    # 有子项的项目（视频等）
                    for j in range(root_item.childCount()):
                        child_item = root_item.child(j)
                        current_state = child_item.checkState(0)
                        new_state = Qt.Checked if current_state == Qt.Unchecked else Qt.Unchecked
                        child_item.setCheckState(0, new_state)
                    # 检查是否所有子项都被选中，更新父项状态
                    all_checked = all(root_item.child(k).checkState(0) == Qt.Checked for k in range(root_item.childCount()))
                    root_item.setCheckState(0, Qt.Checked if all_checked else Qt.Unchecked)
                else:
                    # 没有子项的项目（网易云音乐等）
                    current_state = root_item.checkState(0)
                    new_state = Qt.Checked if current_state == Qt.Unchecked else Qt.Unchecked
                    root_item.setCheckState(0, new_state)
        finally:
            self.format_tree.blockSignals(False)
        self.update_selection_count()
        self.update_smart_select_button_text()

    def update_selection_count(self) -> None:
        """更新选择计数"""
        selected_count = 0
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            if root_item.childCount() > 0:
                # 统计子项的选择状态（复选框在第0列）
                for j in range(root_item.childCount()):
                    if root_item.child(j).checkState(0) == Qt.Checked:
                        selected_count += 1
            else:
                # 统计没有子项的项目（网易云音乐等）
                if root_item.checkState(0) == Qt.Checked:
                    selected_count += 1
        self.selection_count_label.setText(f"已选择: {selected_count} 项")
        
        # 根据选择状态启用/禁用下载按钮
        self.smart_download_button.setEnabled(selected_count > 0)
        
        # 更新状态栏文件信息
        if self.formats:
            self.update_status_bar(
                "就绪",
                "",
                f"已选择: {selected_count} / {len(self.formats)} 项"
            )

    def smart_parse_action(self) -> None:
        """智能解析按钮动作"""
        if self.smart_parse_button.text() == "解析":
            # 检查是否正在解析中
            if self.is_parsing:
                # 恢复解析
                self.resume_parse()
            else:
                # 开始解析
                self.parse_video()
        else:
            # 暂停解析
            self.pause_parse()
    
    def parse_video(self) -> None:
        """解析视频链接"""
        urls = [url.strip() for url in self.url_input.toPlainText().split("\n") if url.strip()]
        if not urls:
            QMessageBox.warning(self, "提示", "请先输入要下载的视频或音乐链接")
            return

        # 分类URL
        playlist_urls = []
        single_video_urls = []
        netease_music_urls = []
        
        for url in urls:
            if NetEaseMusicManager().is_netease_music_url(url):
                netease_music_urls.append(url)
            elif playlist_manager.is_playlist_url(url):
                playlist_urls.append(url)
            else:
                if not self.validate_url(url):
                    QMessageBox.warning(self, "提示", f"链接格式不正确，请检查后重新输入")
                    return
                single_video_urls.append(url)
        
        # 处理网易云音乐链接
        if netease_music_urls:
            self._handle_netease_music_parsing(netease_music_urls)
        
        # 处理播放列表
        if playlist_urls:
            self._handle_playlist_parsing(playlist_urls)
        
        # 处理单个视频
        if single_video_urls:
            self._handle_single_video_parsing(single_video_urls)
    
    def _handle_playlist_parsing(self, playlist_urls: List[str]) -> None:
        """处理播放列表解析"""
        for url in playlist_urls:
            # 获取播放列表信息
            playlist_info = playlist_manager.get_playlist_info(url)
            if not playlist_info:
                logger.error(f"无法获取播放列表信息: {url}")
                continue
            
            # 显示播放列表信息对话框
            reply = self._show_playlist_info_dialog(playlist_info)
            if reply == QMessageBox.Yes:
                # 获取播放列表中的视频URL
                video_urls = playlist_manager.get_playlist_video_urls(url)
                if video_urls:
                    self._parse_video_urls(video_urls)
    
    def _show_playlist_info_dialog(self, playlist_info) -> int:
        """显示播放列表信息对话框"""
        msg = QMessageBox()
        msg.setWindowTitle("播放列表检测")
        msg.setText(f"检测到播放列表：{playlist_info.title}")
        msg.setInformativeText(f"包含 {playlist_info.video_count} 个视频\n上传者：{playlist_info.uploader}")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.button(QMessageBox.Yes).setText("解析播放列表")
        msg.button(QMessageBox.No).setText("跳过")
        return msg.exec_()
    

    
    def _handle_netease_music_parsing(self, netease_music_urls: List[str]) -> None:
        """处理网易云音乐链接解析"""
        # 清空之前的结果
        self.format_tree.clear()
        self.formats = []
        self.smart_download_button.setEnabled(False)
        self.smart_select_button.setEnabled(False)
        self.selection_count_label.setText("已选择: 0 项")
        
        logger.info("开始解析网易云音乐...")
        self.update_status_bar("正在解析网易云音乐...", "", "")
        self.status_scroll_label.setText("")  # 清空滚动状态

        # 更新按钮状态
        self.smart_parse_button.setText("暂停")
        self.smart_parse_button.setEnabled(True)
        self.cancel_parse_button.setEnabled(True)
        
        self.netease_music_workers = []
        self.total_urls = len(netease_music_urls)
        self.parsed_count = 0
        self.is_parsing = True  # 设置解析状态标志
        
        for url in netease_music_urls:
            # 创建网易云音乐解析工作线程
            worker = NetEaseMusicParseWorker(url)
            worker.progress_signal.connect(self.update_scroll_status)
            worker.log_signal.connect(self.update_scroll_status)
            worker.music_parsed_signal.connect(self.on_netease_music_parse_finished)
            worker.error_signal.connect(self.on_netease_music_parse_failed)
            worker.finished_signal.connect(self.on_netease_music_parse_completed)
            
            # 保存工作线程到列表中，防止被垃圾回收
            self.netease_music_workers.append(worker)
            
            # 添加超时保护
            def start_worker_with_timeout(w=worker):
                w.start()
            
            # 延迟启动，避免同时启动多个线程
            QTimer.singleShot(100 * len(self.netease_music_workers), start_worker_with_timeout)
    
    def on_netease_music_parse_finished(self, music_info: dict) -> None:
        """网易云音乐解析完成处理"""
        try:
            # 根据类型处理不同的数据结构
            if music_info.get('type') == 'netease_music_song':
                # 单个歌曲
                self._add_netease_music_song_to_ui(music_info)
                status_msg = f"网易云音乐解析完成: {music_info['title']} - {music_info['artist']}"
            elif music_info.get('type') == 'netease_music_playlist':
                # 歌单
                self._add_netease_music_playlist_to_ui(music_info)
                status_msg = f"网易云音乐解析完成: {music_info['playlist_name']} (共{music_info['track_count']}首歌曲)"
            else:
                # 兼容旧格式，尝试作为单个歌曲处理
                self._add_netease_music_song_to_ui(music_info)
                status_msg = f"网易云音乐解析完成: {music_info.get('title', '未知')} - {music_info.get('artist', '未知')}"
            
            # 更新状态
            self.update_status_bar(status_msg, "", "")
            self.smart_select_button.setEnabled(True)
            
            # 增加解析计数
            self.parsed_count += 1
            
            # 检查是否所有解析都完成
            if self.parsed_count >= self.total_urls:
                self.finalize_netease_music_parse()
            
        except Exception as e:
            logger.error(f"处理网易云音乐解析结果失败: {str(e)}")
            self.update_status_bar(f"处理网易云音乐失败: {str(e)}", "", "")
            # 增加解析计数并检查完成状态
            self.parsed_count += 1
            if self.parsed_count >= self.total_urls:
                self.finalize_netease_music_parse()
    
    def on_netease_music_parse_failed(self, error_msg: str) -> None:
        """网易云音乐解析失败处理"""
        logger.error(f"网易云音乐解析失败: {error_msg}")
        self.update_status_bar(f"网易云音乐解析失败: {error_msg}", "", "")
        QMessageBox.warning(self, "解析失败", f"网易云音乐解析失败，请检查链接或稍后重试")
        # 增加解析计数并检查完成状态
        self.parsed_count += 1
        if self.parsed_count >= self.total_urls:
            self.finalize_netease_music_parse()
    
    def on_netease_music_parse_completed(self) -> None:
        """网易云音乐解析完成（线程结束）"""
        self._cleanup_netease_music_workers()
    
    def finalize_netease_music_parse(self) -> None:
        """完成网易云音乐解析"""
        try:
            # 检查是否所有工作线程都已完成
            if all(not w.isRunning() for w in self.netease_music_workers):
                # 重置解析状态
                self.is_parsing = False
                self.smart_parse_button.setText("解析")
                self.smart_parse_button.setEnabled(True)
                self.cancel_parse_button.setEnabled(False)
                
                # 清理工作线程
                self._cleanup_netease_music_workers()
                
                # 更新状态
                self.update_status_bar("网易云音乐解析完成", "", "")
                logger.info("网易云音乐解析完成")
                
        except Exception as e:
            logger.error(f"完成网易云音乐解析失败: {str(e)}")
            self.update_status_bar(f"完成解析失败: {str(e)}", "", "")
            self.reset_parse_state()
    
    def _add_netease_music_song_to_ui(self, music_info: dict) -> None:
        """添加网易云音乐单个歌曲到UI"""
        try:
            # 添加格式选项
            for format_info in music_info['formats']:
                # 创建歌曲项（直接显示在树形控件中）
                song_item = QTreeWidgetItem(self.format_tree)
                
                # 设置显示信息：名称、时长、歌手、大小、文件类型、状态
                song_item.setCheckState(0, Qt.Unchecked)  # 复选框在第0列
                # 加载音乐封面图片
                cover_url = music_info.get('cover_url', '')
                if cover_url:
                    self._load_thumbnail_sync(song_item, cover_url)
                else:
                    song_item.setIcon(0, self.style().standardIcon(self.style().SP_MediaVolume))
                song_item.setText(1, f"{music_info['title']} - {music_info['artist']}")  # 文件名称（显示歌曲名称+歌手）
                song_item.setText(2, format_info['ext'].upper())  # 文件类型
                
                # 处理文件大小显示
                filesize = format_info.get('filesize')
                if filesize and filesize > 0:
                    size_str = self._format_size(filesize)
                else:
                    size_str = "未知大小"
                song_item.setText(3, size_str)  # 文件大小
                
                song_item.setText(4, "未下载")  # 状态
                song_item.setCheckState(0, Qt.Unchecked)
                
                # 保存格式信息
                format_data = {
                    'type': 'netease_music',
                    'format_id': format_info['format_id'],
                    'ext': format_info['ext'],
                    'format': format_info['format'],
                    'filesize': format_info.get('filesize'),
                    'url': format_info['url'],
                    'title': music_info['title'],
                    'artist': music_info['artist'],
                    'album': music_info['album'],
                    'duration': music_info['duration'],
                    'cover_url': music_info.get('cover_url', ''),
                    'original_url': music_info['original_url'],
                    'song_id': music_info['song_id'],
                    'item': song_item
                }
                
                self.formats.append(format_data)
                logger.info(f"添加网易云音乐格式到UI: {music_info['title']} - {format_info['ext'].upper()}")
            
        except Exception as e:
            logger.error(f"添加网易云音乐到UI失败: {str(e)}")
    
    def _add_netease_music_playlist_to_ui(self, music_info: dict) -> None:
        """添加网易云音乐歌单到UI"""
        try:
            # 添加格式选项
            for format_info in music_info['formats']:
                # 创建歌曲项（直接显示在树形控件中）
                song_item = QTreeWidgetItem(self.format_tree)
                
                # 设置显示信息：名称、时长、歌手、大小、文件类型、状态
                song_item.setCheckState(0, Qt.Unchecked)  # 复选框在第0列
                # 加载音乐封面图片
                cover_url = format_info.get('cover_url', '')
                if cover_url:
                    self._load_thumbnail_sync(song_item, cover_url)
                else:
                    song_item.setIcon(0, self.style().standardIcon(self.style().SP_MediaVolume))
                song_item.setText(1, f"{format_info['song_title']} - {format_info['song_artist']}")  # 文件名称（显示歌曲名称+歌手）
                song_item.setText(2, format_info['ext'].upper())  # 文件类型
                
                # 处理文件大小显示
                filesize = format_info.get('filesize')
                if filesize and filesize > 0:
                    size_str = self._format_size(filesize)
                else:
                    size_str = "未知大小"
                song_item.setText(3, size_str)  # 文件大小
                
                song_item.setText(4, "未下载")  # 状态
                song_item.setCheckState(0, Qt.Unchecked)
                
                # 保存格式信息
                format_data = {
                    'type': 'netease_music',
                    'format_id': format_info['format_id'],
                    'ext': format_info['ext'],
                    'format': format_info['format'],
                    'filesize': format_info.get('filesize'),
                    'url': format_info['url'],
                    'title': format_info['song_title'],
                    'artist': format_info['song_artist'],
                    'album': format_info['song_album'],
                    'duration': format_info['song_duration'],
                    'cover_url': music_info.get('cover_url', ''),
                    'original_url': music_info['original_url'],
                    'song_id': format_info['song_id'],
                    'playlist_name': format_info['playlist_name'],
                    'playlist_creator': format_info['playlist_creator'],
                    'item': song_item
                }
                
                self.formats.append(format_data)
                logger.info(f"添加网易云音乐格式到UI: {format_info['song_title']} - {format_info['ext'].upper()}")
            
        except Exception as e:
            logger.error(f"添加网易云音乐歌单到UI失败: {str(e)}")
    
    def _add_netease_music_to_ui(self, music_info: dict) -> None:
        """添加网易云音乐到UI（兼容方法）"""
        # 根据类型调用相应的方法
        if music_info.get('type') == 'netease_music_playlist':
            self._add_netease_music_playlist_to_ui(music_info)
        else:
            self._add_netease_music_song_to_ui(music_info)
    
    def _format_duration(self, duration_ms: int) -> str:
        """格式化时长（毫秒转分:秒）"""
        if not duration_ms:
            return "未知"
        
        seconds = duration_ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小（字节转可读格式）"""
        if not size_bytes or size_bytes <= 0:
            return "未知大小"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    def _cleanup_netease_music_workers(self) -> None:
        """清理网易云音乐工作线程"""
        try:
            # 移除已完成的工作线程
            self.netease_music_workers = [worker for worker in self.netease_music_workers if worker.isRunning()]
            
            # 如果没有正在运行的工作线程，重置解析状态
            if not self.netease_music_workers and self.is_parsing:
                self.is_parsing = False
                self.smart_parse_button.setText("解析")
                self.smart_parse_button.setEnabled(True)
                self.cancel_parse_button.setEnabled(False)
                
        except Exception as e:
            logger.error(f"清理网易云音乐工作线程失败: {str(e)}")
    

    

    

    

            

    
    def _handle_single_video_parsing(self, video_urls: List[str]) -> None:
        """处理单个视频解析"""
        self._parse_video_urls(video_urls)
    
    def _parse_video_urls(self, urls: List[str]) -> None:
        """解析视频URL列表"""
        # 清空之前的结果
        self.format_tree.clear()
        self.formats = []
        self.parse_cache.clear()  # 清空解析缓存
        self.smart_download_button.setEnabled(False)
        
        # 禁用选择按钮
        self.smart_select_button.setEnabled(False)
        
        # 重置选择计数
        self.selection_count_label.setText("已选择: 0 项")
        
        logger.info("开始解析视频...")
        self.update_status_bar("正在解析视频...", "", "")
        self.status_scroll_label.setText("")  # 清空滚动状态

        # 更新按钮状态
        self.smart_parse_button.setText("暂停")
        self.smart_parse_button.setEnabled(True)
        self.cancel_parse_button.setEnabled(True)
        
        self.parse_workers = []
        self.total_urls = len(urls)
        self.parsed_count = 0
        self.is_parsing = True  # 添加解析状态标志
        
        for url in urls:
            worker = ParseWorker(url)
            worker.status_signal.connect(self.update_scroll_status)  # 连接状态信号
            worker.log_signal.connect(self.update_scroll_status)  # 连接日志信号到状态栏
            worker.progress_signal.connect(self.on_parse_progress)  # 连接进度信号
            worker.video_parsed_signal.connect(self.on_video_parsed)  # 连接视频解析信号
            worker.finished.connect(self.on_parse_completed)  # 连接完成信号
            worker.error.connect(self.on_parse_error)
            
            # 添加超时保护
            def start_worker_with_timeout(w=worker):
                w.start()
            
            # 延迟启动，避免同时启动多个线程
            QTimer.singleShot(100 * len(self.parse_workers), start_worker_with_timeout)
            self.parse_workers.append(worker)

    def on_parse_progress(self, current_progress: int, total_count: int) -> None:
        """处理解析进度更新"""
        try:
            progress_text = f"解析进度: {current_progress}/{total_count}"
            self.update_status_bar(progress_text, "", "")
            logger.debug(f"解析进度更新: {current_progress}/{total_count}")
        except Exception as e:
            logger.error(f"处理解析进度失败: {str(e)}")

    def on_video_parsed(self, info: Dict, url: str) -> None:
        """处理单个视频解析完成"""
        try:
            # 检查内存使用
            self._check_memory_usage()
            
            # 检查是否已经处理过这个视频
            video_id = info.get("id", "")
            webpage_url = info.get("webpage_url", url)
            
            # 检查是否已经缓存过这个视频
            if webpage_url in self.parse_cache:
                logger.info(f"视频已存在，跳过重复处理: {video_id}")
                return
            
            with self._cache_lock:
                self.parse_cache[webpage_url] = info
                if len(self.parse_cache) > Config.CACHE_LIMIT:
                    self.parse_cache.popitem()

            # 立即处理并显示当前视频的解析结果
            self.on_parse_finished(info)
            
            logger.info(f"视频解析完成: {info.get('title', '未知标题')}")
            
        except Exception as e:
            logger.error(f"处理视频解析结果失败: {str(e)}")
            self.update_status_bar(f"解析失败: {str(e)}", "", "")

    def on_parse_completed(self, info: Dict) -> None:
        """处理解析完成"""
        try:
            self.parsed_count += 1
            
            # 实时更新状态栏显示解析进度
            progress_text = f"解析进度: {self.parsed_count}/{self.total_urls}"
            self.update_status_bar(progress_text, "", "")
            
            # 如果所有视频都解析完成，执行最终处理
            if self.parsed_count == self.total_urls and all(not w.isRunning() for w in self.parse_workers) and all(not w.isRunning() for w in self.netease_music_workers):
                try:
                    self.finalize_parse()
                except Exception as e:
                    logger.error(f"最终解析处理失败: {str(e)}")
                    self.update_status_bar(f"最终处理失败: {str(e)}", "", "")
                if hasattr(self, "video_root"):
                    del self.video_root
                    
        except Exception as e:
            logger.error(f"处理解析完成失败: {str(e)}")
            self.update_status_bar(f"解析完成处理失败: {str(e)}", "", "")
            self.reset_parse_state()

    def cache_and_finish(self, info: Dict, url: str) -> None:
        """缓存解析结果并完成解析"""
        try:
            # 检查内存使用
            self._check_memory_usage()
            
            # 检查是否已经处理过这个视频
            video_id = info.get("id", "")
            webpage_url = info.get("webpage_url", url)
            
            # 检查是否已经缓存过这个视频
            if webpage_url in self.parse_cache:
                logger.info(f"视频已存在，跳过重复处理: {video_id}")
                self.parsed_count += 1
                return
            
            with self._cache_lock:
                self.parse_cache[webpage_url] = info
                if len(self.parse_cache) > Config.CACHE_LIMIT:
                    self.parse_cache.popitem()

            # 立即处理并显示当前视频的解析结果
            self.on_parse_finished(info)

            self.parsed_count += 1
            
            # 实时更新状态栏显示解析进度
            progress_text = f"解析进度: {self.parsed_count}/{self.total_urls}"
            self.update_status_bar(progress_text, "", "")
            
            # 如果所有视频都解析完成，执行最终处理
            if self.parsed_count == self.total_urls and all(not w.isRunning() for w in self.parse_workers) and all(not w.isRunning() for w in self.netease_music_workers):
                try:
                    self.finalize_parse()
                except Exception as e:
                    logger.error(f"最终解析处理失败: {str(e)}")
                    self.update_status_bar(f"最终处理失败: {str(e)}", "", "")
                if hasattr(self, "video_root"):
                    del self.video_root
        except Exception as e:
            logger.error(f"缓存解析结果失败: {str(e)}")
            self.update_status_bar(f"解析失败: {str(e)}", "", "")
            self.reset_parse_state()

    def finalize_parse(self) -> None:
        """完成解析并更新 UI"""
        if self.formats:
            # 启用选择按钮
            self.smart_select_button.setEnabled(True)
            
            # 更新选择计数
            self.update_selection_count()
            
            # 刷新下载状态显示
            self.refresh_download_status()
            
            logger.info("所有视频和音乐解析完成")
            
            # 统计解析结果 - 确保在所有视频都添加完成后统计
            # 等待一小段时间确保UI更新完成
            QApplication.processEvents()
            
            # 再次等待确保所有视频项都已添加到树形控件
            time.sleep(0.3)  # 进一步增加等待时间
            QApplication.processEvents()
            
            # 强制刷新树形控件
            self.format_tree.update()
            QApplication.processEvents()
            
            # 再次等待确保刷新完成
            time.sleep(0.1)
            QApplication.processEvents()
            
            # 直接统计树形控件中的项目
            total_video_items = 0
            resolution_groups = self.format_tree.topLevelItemCount()
            
            for i in range(resolution_groups):
                root_item = self.format_tree.topLevelItem(i)
                total_video_items += root_item.childCount()
            
            # 统计唯一视频和音乐文件数量
            unique_video_count = 0
            unique_music_count = 0
            unique_filenames = set()
            unique_music_names = set()
            
            for i in range(resolution_groups):
                root_item = self.format_tree.topLevelItem(i)
                for j in range(root_item.childCount()):
                    child_item = root_item.child(j)
                    filename = child_item.text(1)  # 文件名在第1列
                    
                    # 检查是否为音乐文件
                    if "🎵" in root_item.text(0):  # 音乐文件在根节点有🎵标识
                        unique_music_names.add(filename)
                    else:
                        base_filename = re.sub(r"_\d+$", "", filename)
                        unique_filenames.add(base_filename)
            
            unique_video_count = len(unique_filenames)
            unique_music_count = len(unique_music_names)
            total_formats = len(self.formats)
            
            # 添加详细的调试日志
            logger.info(f"=== 解析完成统计信息 ===")
            logger.info(f"分辨率分类数量: {resolution_groups}")
            logger.info(f"实际视频文件数量: {unique_video_count}")
            logger.info(f"音乐文件数量: {unique_music_count}")
            logger.info(f"视频项总数: {total_video_items}")
            logger.info(f"可用格式数量: {total_formats}")
            logger.info(f"self.formats 长度: {len(self.formats)}")
            logger.info(f"=== 统计信息结束 ===")
            
            # 更新状态栏
            status_text = f"共找到 {total_formats} 个格式"
            if unique_video_count > 0:
                status_text += f"，{unique_video_count} 个视频"
            if unique_music_count > 0:
                status_text += f"，{unique_music_count} 个音乐"
            self.update_status_bar("解析完成，请选择下载格式", "", status_text)
            self.status_scroll_label.setText("解析完成 ✓")  # 清空滚动状态
            
            # 确保列宽设置正确
            self.ensure_column_widths()
            
            # 显示详细的解析完成提示
            message = f"解析完成！\n\n"
            message += f"• 分类数量：{resolution_groups} 个\n"
            if unique_video_count > 0:
                message += f"• 视频文件：{unique_video_count} 个\n"
            if unique_music_count > 0:
                message += f"• 音乐文件：{unique_music_count} 个\n"
            message += f"• 项目总数：{total_video_items} 个\n"
            message += f"• 可用格式：{total_formats} 个\n\n"
            message += "请选择需要下载的格式。"
            
            QMessageBox.information(self, "解析完成", message)
        else:
            logger.warning("未找到任何可用格式")
            self.update_status_bar("未找到可用格式", "", "")
            self.status_scroll_label.setText("解析失败 ✗")  # 清空滚动状态
            QMessageBox.warning(self, "提示", "未找到可下载的格式，请检查链接或稍后重试")
        self.reset_parse_state()



    def get_resolution(self, f: Dict) -> str:
        """从格式信息中提取分辨率并标准化"""
        # 首先检查 resolution 字段
        resolution = f.get("resolution", "")
        if resolution and resolution != "audio only" and "x" in resolution:
            return self.standardize_resolution(resolution)
            
        # 检查 width 和 height 字段
        width = f.get("width")
        height = f.get("height")
        if width and height:
            return self.standardize_resolution(f"{width}x{height}")
        elif height:
            return f"{height}p"
            
        # 检查 format_note 字段
        format_note = f.get("format_note", "")
        if format_note and format_note != "unknown":
            # 尝试从 format_note 中提取分辨率
            if "x" in format_note:
                return self.standardize_resolution(format_note)
            elif format_note.isdigit():
                return f"{format_note}p"
                
        # 检查 format 字段
        format_str = f.get("format", "")
        if "x" in format_str:
            match = re.search(r"(\d+)x(\d+)", format_str)
            if match:
                return self.standardize_resolution(f"{match.group(1)}x{match.group(2)}")
                
        # 检查是否为音频格式
        if f.get("acodec", "none") != "none" and f.get("vcodec", "none") == "none":
            return "audio only"
            
        # 如果都找不到，返回未知
        return "未知"

    def standardize_resolution(self, resolution: str) -> str:
        """标准化分辨率到主流分辨率"""
        if not resolution or "x" not in resolution:
            return resolution
            
        try:
            width, height = resolution.split("x")
            width, height = int(width), int(height)
            
            # 1080P 变体 → 1920x1080 或 1440x1080
            if abs(height - 1080) <= 4:
                if abs(width - 1920) <= 4:
                    return "1920x1080"
                elif abs(width - 1440) <= 4:
                    return "1440x1080"
            # 720P 变体 → 1280x720 或 960x720
            elif abs(height - 720) <= 4:
                if abs(width - 1280) <= 4:
                    return "1280x720"
                elif abs(width - 960) <= 4:
                    return "960x720"
            # 480P 变体 → 852x480 或 640x480
            elif abs(height - 480) <= 4:
                if abs(width - 852) <= 4:
                    return "852x480"
                elif abs(width - 640) <= 4:
                    return "640x480"
            # 360P 变体 → 640x360 或 480x360
            elif abs(height - 360) <= 4:
                if abs(width - 640) <= 4:
                    return "640x360"
                elif abs(width - 480) <= 4:
                    return "480x360"
            # 240P 变体 → 426x240
            elif abs(height - 240) <= 4:
                if abs(width - 426) <= 4:
                    return "426x240"
            else:
                return resolution
        except (ValueError, IndexError):
            return resolution

    def on_parse_finished(
        self,
        info: Dict
    ) -> None:
        """处理解析完成的数据"""
        video_title = info.get("title", "未知标题")
        video_id = info.get("id", "unknown")
        
        # 检查是否已经添加过这个视频
        if self._is_video_already_added(video_id, video_title):
            logger.info(f"视频已存在，跳过重复添加: {video_title} (ID: {video_id})")
            return
            
        audio_format = None
        audio_filesize = 0
        video_formats: Dict[str, Dict] = {}

        # 处理视频标题格式 - 优化合集视频处理
        # 检查是否为合集视频的一部分
        if "p" in video_title.lower() and re.search(r"p\d+", video_title):
            # 合集视频，提取部分标题
            match = re.search(r"p\d+\s*(.+?)(?:_\w+)?$", video_title)
            if match:
                part_title = match.group(1).strip()
                formatted_title = part_title
            else:
                # 如果无法提取部分标题，使用完整标题
                formatted_title = video_title
        else:
            # 单个视频，使用完整标题
            formatted_title = video_title
            if f"_{video_id}" in formatted_title:
                formatted_title = formatted_title.replace(f"_{video_id}", "")
        
        # 确保标题不为空
        if not formatted_title.strip():
            formatted_title = f"视频_{video_id}"
        
        # 不再添加方括号包装
        # if not formatted_title.startswith("["):
        #     formatted_title = f"[{formatted_title}]"

        # 不再创建视频根节点，直接使用分辨率分组
        video_root = None

        formats = info.get("formats", [])
        logger.info(f"解析条目 '{video_title}'，共有 {len(formats)} 个格式")

        # 过滤格式，保留所有视频格式（非严格过滤）
        filtered_formats = filter_formats(formats, strict_filter=False)
        logger.info(f"过滤后剩余 {len(filtered_formats)} 个格式")

        # 处理格式信息
        for f in filtered_formats:
            format_id = f.get("format_id")
            resolution = self.get_resolution(f)
            ext = f.get("ext", "")
            acodec = f.get("acodec", "none")
            filesize = f.get("filesize") or f.get("filesize_approx")
            vbr = f.get("vbr", 0)
            
            # 调试信息：记录每个格式的详细信息
            logger.info(f"格式 {format_id}: resolution={resolution}, ext={ext}, acodec={acodec}, vbr={vbr}, filesize={filesize}, width={f.get('width')}, height={f.get('height')}, format_note={f.get('format_note')}")

            # 计算文件大小
            if not filesize:
                duration = info.get("duration", 0)
                abr = f.get("abr", 0)
                total_br = (abr or 0) + (vbr or 0)
                if duration and total_br:
                    filesize = (total_br * duration * 1000) / 8

            # 查找最佳音频格式
            if "audio only" in f.get("format", "") and ext in ["m4a", "mp3"] and not audio_format:
                audio_format = format_id
                audio_filesize = filesize if filesize else 0
                
            # 收集视频格式 - 每个分辨率只保留最优格式
            elif resolution != "未知" and f.get("vcodec", "none") != "none":
                # 跳过Premium格式和其他可能不可用的格式
                format_note = f.get("format_note", "").lower()
                if "premium" in format_note or "membership" in format_note or "paid" in format_note:
                    logger.info(f"跳过Premium格式 {format_id}: {format_note}")
                    continue
                
                # 为每个分辨率只保留最优格式（按文件大小排序）
                if resolution not in video_formats or filesize > video_formats[resolution].get("filesize", 0):
                    video_formats[resolution] = {
                        "format_id": format_id,
                        "ext": ext,
                        "filesize": filesize if filesize else 0,
                        "vcodec": f.get("vcodec", "none")
                    }
                    logger.info(f"更新最优视频格式: {resolution} -> {format_id} (大小: {filesize})")
            else:
                logger.info(f"跳过格式 {format_id}: resolution={resolution}, vbr={vbr}, vcodec={f.get('vcodec', 'none')}")

        # 创建分辨率分组和视频项
        logger.info(f"视频 '{formatted_title}' 将被添加到以下分辨率: {list(video_formats.keys())}")
        
        # 统计每个分辨率分类下的视频数量
        resolution_counts = {}
        for i in range(self.format_tree.topLevelItemCount()):
            item = self.format_tree.topLevelItem(i)
            res_name = item.text(0)  # 分辨率名称在第0列
            resolution_counts[res_name] = item.childCount()
        
        logger.info(f"现有分辨率分组: {list(resolution_counts.keys())}")
        

        
        for res, v_format in sorted(video_formats.items(), key=lambda x: x[0], reverse=True):
            # 查找或创建分辨率分组（直接作为根节点）
            res_group = None
            for i in range(self.format_tree.topLevelItemCount()):
                if self.format_tree.topLevelItem(i).text(0) == res:  # 分辨率名称在第0列
                    res_group = self.format_tree.topLevelItem(i)
                    logger.info(f"找到现有分辨率分组: {res}")
                    break
            if not res_group:
                res_group = QTreeWidgetItem(self.format_tree)
                res_group.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)  # 分辨率节点可选择
                res_group.setCheckState(0, Qt.Unchecked)  # 复选框在第0列
                res_group.setText(0, res)  # 分辨率名称在第0列
                res_group.setIcon(0, self.style().standardIcon(self.style().SP_DirIcon))  # 添加文件夹图标
                res_group.setExpanded(True)
                logger.info(f"创建新的分辨率分组: {res}")

            # 为每个分辨率创建最优视频项
            # 在文件名中添加分辨率和编码信息
            base_filename = sanitize_filename(formatted_title, self.save_path)
            vcodec_short = v_format.get("vcodec", "unknown").split(".")[0]  # 提取编码类型
            filename = f"{base_filename}_{res}_{vcodec_short}"
            
            # 确保在同一分辨率分组内文件名唯一
            filename = self.ensure_unique_filename(res_group, filename)
            
            video_item = QTreeWidgetItem(res_group)
            
            # 计算总大小（视频+音频）
            total_size = v_format["filesize"]
            if audio_format:
                total_size += audio_filesize
                
            # 添加视频项到树形控件
            thumbnail_url = info.get("thumbnail", "")
            self._add_tree_item(video_item, filename, "mp4", res, total_size, thumbnail_url)
            
            logger.info(f"添加最优视频项到分辨率 {res} ({vcodec_short}): {filename}")
            
            # 添加到格式列表
            format_id = v_format["format_id"]
            if audio_format:
                format_id = f"{format_id}+{audio_format}"
                
            self.formats.append({
                "video_id": video_id,
                "format_id": format_id,
                "description": f"{filename}.mp4",
                "type": "video_audio",
                "ext": "mp4",
                "filesize": total_size,
                "url": info.get("webpage_url", ""),
                "item": video_item
            })
        
        # 记录当前分辨率分类的统计信息
        current_counts = {}
        for i in range(self.format_tree.topLevelItemCount()):
            item = self.format_tree.topLevelItem(i)
            res_name = item.text(0)  # 分辨率名称在第0列
            current_counts[res_name] = item.childCount()
        
        logger.info(f"当前分辨率分类统计: {current_counts}")
        
        # 实时更新UI - 每个视频解析完成后立即启用选择按钮
        if self.formats:
            self.smart_select_button.setEnabled(True)
            self.update_selection_count()
            
        # 更新分辨率分组的显示顺序（按分辨率从高到低）
        self.sort_resolution_groups()

    def count_total_video_items(self) -> int:
        """统计树形控件中总的视频项数量"""
        total_count = 0
        resolution_details = {}
        
        logger.info(f"开始统计总视频项数量，树形控件顶级项目数量: {self.format_tree.topLevelItemCount()}")
        
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            resolution = root_item.text(0)
            child_count = root_item.childCount()
            total_count += child_count
            resolution_details[resolution] = child_count
            logger.info(f"分辨率分组 {i}: {resolution} -> {child_count} 个子项")
            
        # 记录详细的统计信息
        logger.info(f"视频项统计详情: {resolution_details}")
        logger.info(f"总视频项数量: {total_count}")
        
        return total_count

    def count_unique_videos(self) -> int:
        """统计实际的视频文件数量（去重）"""
        unique_videos = set()
        all_filenames = []
        
        logger.info(f"开始统计唯一视频文件，树形控件顶级项目数量: {self.format_tree.topLevelItemCount()}")
        
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            resolution = root_item.text(0)
            child_count = root_item.childCount()
            logger.info(f"检查分辨率分组: {resolution}, 子项数量: {child_count}")
            
            for j in range(child_count):
                child_item = root_item.child(j)
                # 获取文件名（去掉可能的数字后缀）
                filename = child_item.text(1)  # 文件名在第1列
                all_filenames.append(filename)
                # 移除数字后缀以获取原始文件名
                base_filename = re.sub(r"_\d+$", "", filename)
                unique_videos.add(base_filename)
                logger.info(f"  子项 {j}: {filename} -> {base_filename}")
        
        logger.info(f"所有文件名: {all_filenames}")
        logger.info(f"去重后的文件名: {sorted(list(unique_videos))}")
        logger.info(f"实际视频文件数量（去重）: {len(unique_videos)}")
        return len(unique_videos)

    def sort_resolution_groups(self) -> None:
        """按分辨率从高到低排序分辨率分组"""
        try:
            # 获取所有分辨率分组
            groups = []
            for i in range(self.format_tree.topLevelItemCount()):
                item = self.format_tree.topLevelItem(i)
                resolution = item.text(0)
                groups.append((resolution, item))
            
            # 按分辨率排序（从高到低）
            def resolution_sort_key(res_text):
                if "x" in res_text:
                    try:
                        width, height = res_text.split("x")
                        return int(height)  # 按高度排序
                    except:
                        return 0
                return 0
            
            groups.sort(key=lambda x: resolution_sort_key(x[0]), reverse=True)
            
            # 重新排列树形控件项
            for i, (resolution, item) in enumerate(groups):
                # 将项目移动到正确的位置
                self.format_tree.takeTopLevelItem(self.format_tree.indexOfTopLevelItem(item))
                self.format_tree.insertTopLevelItem(i, item)
                
            logger.info(f"分辨率分组已排序: {[g[0] for g in groups]}")
        except Exception as e:
            logger.error(f"排序分辨率分组失败: {str(e)}")

    def ensure_unique_filename(self, parent_item: QTreeWidgetItem, base_filename: str) -> str:
        """确保在同一分辨率分组内文件名唯一"""
        try:
            # 获取同一分组下所有现有文件名
            existing_filenames = set()
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                existing_filename = child.text(1)  # 文件名在第1列
                existing_filenames.add(existing_filename)
            
            # 如果文件名已存在，添加数字后缀
            filename = base_filename
            counter = 1
            while filename in existing_filenames:
                # 移除可能的现有后缀
                if re.search(r"_\d+$", filename):
                    filename = re.sub(r"_\d+$", "", filename)
                filename = f"{filename}_{counter}"
                counter += 1
            
            return filename
        except Exception as e:
            logger.error(f"确保文件名唯一失败: {str(e)}")
            return base_filename

    def _add_tree_item(
        self,
        item: QTreeWidgetItem,
        filename: str,
        file_type: str,
        resolution: str,
        filesize: Optional[int],
        thumbnail_url: str = None
    ) -> None:
        """添加树形控件项"""
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        # 第0列设置复选框和图标，第1列显示文件名
        item.setCheckState(0, Qt.Unchecked)  # 复选框在第0列
        
        # 如果有封面URL，同步加载封面图片
        if thumbnail_url:
            self._load_thumbnail_sync(item, thumbnail_url)
        else:
            # 设置默认视频图标
            item.setIcon(0, self.style().standardIcon(self.style().SP_MediaPlay))
            
        item.setText(1, filename)
        item.setText(2, file_type)
        item.setText(3, format_size(filesize))
        
        # 检查文件是否已下载，设置状态列
        file_path = os.path.join(self.save_path, f"{filename}.{file_type}")
        if os.path.exists(file_path):
            # 文件已下载，显示"已下载"
            item.setText(4, "已下载")
            item.setForeground(4, Qt.green)
            # 禁用已下载文件的复选框，防止重复下载
            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
        else:
            # 文件未下载，显示"未下载"
            item.setText(4, "未下载")
            item.setForeground(4, Qt.black)
            # 确保未下载文件的复选框可用
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

    def _load_thumbnail_sync(self, item: QTreeWidgetItem, thumbnail_url: str) -> None:
        """同步加载封面图片"""
        try:
            import requests
            from PyQt5.QtGui import QPixmap, QIcon
            
            # 获取表格行高度，封面图片高度为行高减1
            tree_widget = item.treeWidget()
            if tree_widget:
                # 获取第一行的实际高度
                first_item = tree_widget.topLevelItem(0)
                if first_item:
                    row_height = tree_widget.visualItemRect(first_item).height()
                else:
                    # 如果没有项目，使用默认高度
                    row_height = 20
            else:
                row_height = 20
            
            # 封面图片高度为行高减1
            icon_height = max(1, row_height - 1)
            icon_width = icon_height  # 保持正方形
            
            # 同步下载封面图片
            response = requests.get(thumbnail_url, timeout=5)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    # 缩放图片到合适大小
                    scaled_pixmap = pixmap.scaled(icon_width, icon_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon = QIcon(scaled_pixmap)
                    item.setIcon(0, icon)
                    
                    # 设置工具提示用于悬停放大
                    self._set_thumbnail_tooltip(item, pixmap)
                    return
            
            # 如果加载失败，设置默认图标
            item.setIcon(0, self.style().standardIcon(self.style().SP_MediaPlay))
            
        except Exception as e:
            logger.warning(f"加载封面图片失败: {e}")
            # 设置默认图标
            item.setIcon(0, self.style().standardIcon(self.style().SP_MediaPlay))

    def _set_thumbnail_tooltip(self, item: QTreeWidgetItem, original_pixmap: QPixmap) -> None:
        """设置封面图片的工具提示（悬停放大）"""
        try:
            # 创建放大版本的图片
            enlarged_pixmap = original_pixmap.scaled(
                200, 200,  # 放大到200x200
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 创建HTML格式的工具提示
            tooltip_html = f"""
            <div style="background-color: white; border: 2px solid #ccc; padding: 5px;">
                <img src="data:image/png;base64,{self._pixmap_to_base64(enlarged_pixmap)}" 
                     width="{enlarged_pixmap.width()}" 
                     height="{enlarged_pixmap.height()}" />
            </div>
            """
            
            # 设置工具提示
            item.setToolTip(0, tooltip_html)
            
        except Exception as e:
            logger.warning(f"设置封面工具提示失败: {e}")

    def _pixmap_to_base64(self, pixmap: QPixmap) -> str:
        """将QPixmap转换为base64字符串"""
        try:
            from PyQt5.QtCore import QBuffer
            from PyQt5.QtGui import QImage
            import base64
            
            # 转换为QImage
            image = pixmap.toImage()
            
            # 创建缓冲区
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite)
            
            # 保存为PNG格式
            image.save(buffer, "PNG")
            
            # 获取数据并转换为base64
            data = buffer.data()
            base64_data = base64.b64encode(data.data()).decode('utf-8')
            
            return base64_data
            
        except Exception as e:
            logger.warning(f"转换图片到base64失败: {e}")
            return ""

    def on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """处理树形控件项状态变化"""
        # 处理分辨率节点的复选框变化（第0列）
        if column == 0 and item.parent() is None:
            # 临时禁用信号以避免循环触发
            self.format_tree.blockSignals(True)
            try:
                # 直接设置所有子项的状态，不使用递归
                checked = item.checkState(0) == Qt.Checked
                for i in range(item.childCount()):
                    child = item.child(i)
                    child.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            finally:
                self.format_tree.blockSignals(False)
        
        # 处理视频文件节点的复选框变化（第0列）
        elif column == 0 and item.parent() is not None:
            parent = item.parent()
            if parent:
                # 临时禁用信号以避免循环触发
                self.format_tree.blockSignals(True)
                try:
                    all_checked = all(parent.child(i).checkState(0) == Qt.Checked for i in range(parent.childCount()))
                    parent.setCheckState(0, Qt.Checked if all_checked else Qt.Unchecked)
                finally:
                    self.format_tree.blockSignals(False)
        
        # 更新选择计数
        self.update_selection_count()

    def pause_parse(self) -> None:
        """暂停解析"""
        for worker in self.parse_workers:
            if worker.isRunning():
                worker.pause()
        # 暂停网易云音乐解析工作线程
        for worker in self.netease_music_workers:
            if worker.isRunning():
                worker.pause()

        self.smart_parse_button.setText("解析")
        # 保持 is_parsing 状态为 True，表示解析任务仍在进行中
        self.update_status_bar("解析已暂停", "", "")
        logger.info("解析已暂停")
        
        # 清空状态栏滚动显示，停止显示解析进度
        self.status_scroll_label.setText("")
    
    def resume_parse(self) -> None:
        """恢复解析"""
        for worker in self.parse_workers:
            if worker.isRunning():
                worker.resume()
        # 恢复网易云音乐解析工作线程
        for worker in self.netease_music_workers:
            if worker.isRunning():
                worker.resume()

        self.smart_parse_button.setText("暂停")
        self.update_status_bar("解析已恢复", "", "")
        logger.info("解析已恢复")
    
    def cancel_parse(self) -> None:
        """取消解析"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认")
        msg_box.setText("确定要取消所有解析任务吗？")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮中文文本
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        reply = msg_box.exec_()
        
        if reply == QMessageBox.Yes:
            for worker in self.parse_workers:
                if worker.isRunning():
                    worker.cancel()
            # 取消网易云音乐解析工作线程
            for worker in self.netease_music_workers:
                if worker.isRunning():
                    worker.cancel()

            self.reset_parse_state()
            logger.info("解析已取消")
            self.update_status_bar("解析已取消", "", "")
    
    def reset_parse_state(self) -> None:
        """重置解析状态"""
        self.is_parsing = False
        self.parse_workers.clear()
        # 清理网易云音乐解析工作线程
        self.netease_music_workers.clear()

        self.smart_parse_button.setText("解析")
        self.smart_parse_button.setEnabled(True)
        self.cancel_parse_button.setEnabled(False)
        self.status_scroll_label.setText("")

    def on_parse_error(self, error_msg: str) -> None:
        """处理解析错误"""
        # 检查是否为超时错误
        if "timeout" in error_msg.lower() or "超时" in error_msg:
            detailed_error = f"解析超时: {error_msg}\n\n建议:\n1. 检查网络连接\n2. 尝试重新解析\n3. 检查视频链接是否有效"
            QMessageBox.warning(self, "解析超时", detailed_error)
        else:
            QMessageBox.critical(self, "解析错误", error_msg)
        
        logger.error(f"解析错误: {error_msg}")
        self.update_status_bar(f"解析错误: {error_msg}", "", "")
        self.reset_parse_state()

    def download_progress_hook(self, d: Dict) -> None:
        """下载进度回调"""
        try:
            if isinstance(d, dict) and d.get("status") == "downloading":
                filename = d.get("filename", "")
                percent_str = d.get("_percent_str", "0%").strip("%")
                speed = d.get("_speed_str", "未知速率")
                try:
                    percent = float(percent_str)
                except ValueError:
                    percent = 0
                self.download_progress[filename] = (percent, speed)
            elif isinstance(d, dict) and d.get("status") == "finished":
                filename = d.get("filename", "")
                # 标记为已完成，但不立即删除，让 on_download_finished 处理
                self.download_progress[filename] = (100, "已完成")
                logger.info(f"文件下载完成: {filename}")
        except Exception as e:
            logger.error(f"进度回调处理错误: {e}")
            # 如果参数不是预期的字典格式，尝试处理字符串或其他格式
            if isinstance(d, str):
                logger.info(f"收到字符串进度信息: {d}")
            else:
                logger.info(f"收到未知格式进度信息: {type(d)} - {d}")

    def update_download_progress(self) -> None:
        """更新下载进度"""
        # 检查是否所有下载都已完成
        if not self.is_downloading or (not self.download_progress and not self.download_workers):
            self.smart_download_button.setText("下载")
            self.smart_download_button.setStyleSheet(self.default_style)
            self.setWindowTitle(f"椰果IDM-v{Config.APP_VERSION}")
            self.update_status_bar("就绪", "", "")
            return

        # 检查是否所有下载都已完成（没有活动下载且没有队列）
        if self.active_downloads <= 0 and not self.download_queue:
            # 所有下载完成，显示100%进度
            self.setWindowTitle(f"椰果IDM-v{Config.APP_VERSION} - 下载中 (100.0%)")
            self.update_status_bar("下载中 (100.0%)", "已完成", "")
            return

        # 计算总体进度：已完成文件 + 当前下载进度
        total_files = len(self.download_progress) + len([w for w in self.download_workers if not w.isRunning()])
        if total_files == 0:
            return
            
        # 当前下载进度总和
        current_percent = sum(percent for percent, _ in self.download_progress.values())
        # 已完成文件数（每个算100%）
        completed_files = len([w for w in self.download_workers if not w.isRunning()])
        completed_percent = completed_files * 100
        
        # 总进度 = (已完成进度 + 当前进度) / 总文件数
        total_percent = completed_percent + current_percent
        avg_percent = total_percent / total_files
        
        # 确保进度不超过100%
        avg_percent = min(avg_percent, 100.0)
        
        total_speed = [speed for _, speed in self.download_progress.values()]
        speed_text = ", ".join(total_speed) if total_speed else "已完成"
        active_count = len([w for w in self.download_workers if w.isRunning()])
        
        # 更新窗口标题
        self.setWindowTitle(f"椰果IDM-v{Config.APP_VERSION} - 下载中 ({avg_percent:.1f}%)")
        
        # 更新状态栏
        self.update_status_bar(
            f"下载中 ({avg_percent:.1f}%)", 
            f"{speed_text} | 活动: {active_count}/{Config.MAX_CONCURRENT_DOWNLOADS}",
            f"文件: {total_files}"
        )

        while self.active_downloads < Config.MAX_CONCURRENT_DOWNLOADS and self.download_queue:
            url, fmt = self.download_queue.popleft()
            self.start_download(url, fmt)

    def download_selected(self, item: Optional[QTreeWidgetItem] = None, column: Optional[int] = None) -> None:
        """下载选中的格式"""
        selected_formats = []

        try:
            def collect_checked_items(tree_item: QTreeWidgetItem) -> List[Dict]:
                checked_items = []
                # 检查当前项目本身（用于网易云音乐等直接添加的项目）
                if tree_item.checkState(0) == Qt.Checked and tree_item.childCount() == 0:
                    for fmt in self.formats:
                        if fmt["item"] == tree_item:
                            checked_items.append(fmt)
                            break
                # 检查子项目（用于视频等有层次结构的项目）
                for i in range(tree_item.childCount()):
                    child = tree_item.child(i)
                    if child.checkState(0) == Qt.Checked and child.childCount() == 0:  # 复选框在第0列
                        for fmt in self.formats:
                            if fmt["item"] == child:
                                checked_items.append(fmt)
                                break
                    elif child.childCount() > 0:
                        checked_items.extend(collect_checked_items(child))
                return checked_items

            for i in range(self.format_tree.topLevelItemCount()):
                top_item = self.format_tree.topLevelItem(i)
                selected_formats.extend(collect_checked_items(top_item))

            if not selected_formats:
                QMessageBox.warning(self, "提示", "请选择要下载的格式")
                return

            if not check_ffmpeg(self.ffmpeg_path, self):
                self.update_status_bar("错误: 请安装 FFmpeg 并放入保存路径", "", "")
                self.reset_download_state()
                return
            
            # 检查磁盘空间
            if not self._check_disk_space():
                QMessageBox.warning(self, "磁盘空间不足", "磁盘空间不足，请清理磁盘或选择其他保存位置")
                self.update_status_bar("错误: 磁盘空间不足", "", "")
                self.reset_download_state()
                return

            self.is_downloading = True
            self.download_progress.clear()
            self.smart_download_button.setEnabled(True)  # 保持启用状态，允许取消下载
            self.smart_parse_button.setEnabled(False)
            self.smart_pause_button.setEnabled(True)
            # 隐藏进度条和状态标签，只在状态栏显示
            self.progress_bar.setVisible(False)
            self.status_label.setVisible(False)
            self.smart_download_button.setText("取消下载")
            logger.info("开始下载...")
            self.update_status_bar("开始下载...", "准备中", f"选中: {len(selected_formats)} 个文件")

            for fmt in selected_formats:
                if self.active_downloads < Config.MAX_CONCURRENT_DOWNLOADS:
                    # 对于网易云音乐，使用原始URL而不是fmt["url"]
                    download_url = fmt.get("original_url", fmt["url"]) if fmt.get("type") == "netease_music" else fmt["url"]
                    self.start_download(download_url, fmt)
                else:
                    download_url = fmt.get("original_url", fmt["url"]) if fmt.get("type") == "netease_music" else fmt["url"]
                    self.download_queue.append((download_url, fmt))

        except Exception as e:
            logger.error(f"下载失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "下载失败", "下载过程中发生错误，请稍后重试")
            self.update_status_bar(f"下载失败: {str(e)}", "", "")
            self.reset_download_state()

    def start_download(self, url: str, selected_format: Dict) -> None:
        """启动下载任务"""
        try:
            # 检查是否为网易云音乐
            if selected_format.get("type") == "netease_music":
                self._start_netease_music_download(url, selected_format)
                return
            
            # 原有的视频下载逻辑
            output_file = os.path.join(self.save_path, selected_format["description"])
            self.download_progress[output_file] = (0, "未知速率")
            logger.info(f"开始下载: {output_file}")

            ydl_opts = {
                "outtmpl": os.path.join(self.save_path, selected_format["description"]),
                "quiet": False,
                "ffmpeg_location": self.ffmpeg_path,
                
                # 增强下载稳定性配置
                "retries": 10,  # 增加重试次数
                "fragment_retries": 10,  # 增加片段重试次数
                "extractor_retries": 5,  # 增加提取器重试次数
                "socket_timeout": 60,  # 增加socket超时时间
                "http_chunk_size": 10485760,  # 10MB块大小，平衡速度和稳定性
                "buffersize": 4096,  # 增大缓冲区
                
                # 下载恢复和断点续传
                "continuedl": True,  # 启用断点续传
                "noprogress": False,  # 显示进度
                
                # 错误处理
                "ignoreerrors": False,  # 不忽略错误，确保错误被正确处理
                "no_warnings": False,  # 显示警告信息
                
                # 网络配置
                "prefer_insecure": True,  # 优先使用不安全的连接
                "no_check_certificate": True,  # 不检查证书
                
                # 请求头配置
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                },
            }

            speed_limit = self.speed_limit_input.text().strip()
            if speed_limit.isdigit():
                ydl_opts["ratelimit"] = int(speed_limit) * 1024

            # 使用解析时确定的特定格式ID
            format_id = selected_format.get("format_id", "")
            height = selected_format.get("height", 0)
            
            # 如果有特定的格式ID，使用它；否则使用best
            if format_id and format_id != "unknown":
                format_spec = format_id
                logger.info(f"使用特定格式ID: {format_spec} (高度: {height})")
            else:
                # 根据高度选择最佳格式
                if height >= 1080:
                    format_spec = "best[height>=1080]/best"
                elif height >= 720:
                    format_spec = "best[height>=720]/best"
                elif height >= 480:
                    format_spec = "best[height>=480]/best"
                elif height >= 360:
                    format_spec = "best[height>=360]/best"
                else:
                    format_spec = "best"
                logger.info(f"使用高度匹配格式: {format_spec} (高度: {height})")
            
            ydl_opts.update({
                "format": format_spec,
                "merge_output_format": "mp4",
            })

            worker = DownloadWorker(url, ydl_opts, format_id)
            worker.progress_signal.connect(self.download_progress_hook)
            worker.log_signal.connect(self.update_scroll_status)  # 连接日志信号到状态栏
            worker.finished.connect(lambda filename: self.on_download_finished(filename, url, selected_format))
            worker.error.connect(self.on_download_error)
            worker.start()
            self.download_workers.append(worker)
            self.active_downloads += 1
        except Exception as e:
            logger.error(f"启动下载失败: {str(e)}", exc_info=True)
            self.update_status_bar(f"下载失败: {selected_format['description']} - {str(e)}", "", "")
            self.reset_download_state()
    
    def _start_netease_music_download(self, url: str, selected_format: Dict) -> None:
        """启动网易云音乐下载"""
        try:
            # 生成文件名
            title = selected_format["title"]
            artist = selected_format["artist"]
            ext = selected_format["ext"]
            
            # 清理文件名中的非法字符
            safe_title = sanitize_filename(title, self.save_path)
            safe_artist = sanitize_filename(artist, self.save_path)
            filename = f"{safe_artist} - {safe_title}.{ext}"
            output_file = os.path.join(self.save_path, filename)
            
            self.download_progress[output_file] = (0, "未知速率")
            logger.info(f"开始下载网易云音乐: {filename}")
            
            # 创建增强的下载选项，专门针对网易云音乐的反爬虫机制
            ydl_opts = {
                "outtmpl": output_file,
                "quiet": False,
                "ffmpeg_location": self.ffmpeg_path,
                
                # 增强下载稳定性配置
                "retries": 15,
                "fragment_retries": 15,
                "extractor_retries": 10,
                "socket_timeout": 120,
                "http_chunk_size": 10485760,
                "buffersize": 8192,
                
                # 下载恢复和断点续传
                "continuedl": True,
                "noprogress": False,
                
                # 错误处理
                "ignoreerrors": False,
                "no_warnings": False,
                
                # 网络配置
                "prefer_insecure": True,
                "no_check_certificate": True,
                "nocheckcertificate": True,
                
                # 地理绕过
                "geo_bypass": True,
                "geo_bypass_country": "CN",
                
                # 请求头配置 - 模拟真实浏览器
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0",
                    "Referer": "https://music.163.com/",
                    "Origin": "https://music.163.com",
                    "DNT": "1",
                },
                
                # 额外的HTTP头部
                "http_headers": {
                    "Referer": "https://music.163.com/",
                    "Origin": "https://music.163.com",
                    "X-Requested-With": "XMLHttpRequest",
                },
                
                # 下载策略
                "concurrent_fragment_downloads": 5,
                "max_sleep_interval": 5,
                "sleep_interval": 1,
                
                # 格式选择策略
                "format": "best[ext=mp3]/best",
                "format_sort": ["ext:mp3:m4a", "quality", "filesize"],
                
                # 重试策略
                "retry_sleep": "exponential",
                "max_retries": 15,
                "fragment_retries": 15,
                "extractor_retries": 10,
                
                # 进度回调
                "progress_hooks": [],
            }
            
            # 设置速度限制
            speed_limit = self.speed_limit_input.text().strip()
            if speed_limit.isdigit():
                ydl_opts["ratelimit"] = int(speed_limit) * 1024
            
            # 使用网易云音乐的下载链接
            download_url = selected_format["url"]
            
            # 检查下载链接是否有效
            if not download_url:
                error_msg = f"无法获取歌曲下载链接，可能是付费歌曲或版权受限: {title} - {artist}"
                logger.warning(error_msg)
                self.update_status_bar(error_msg, "", "")
                self.reset_download_state()
                return
            
            # 创建专门的网易云音乐下载工作线程
            worker = DownloadWorker(download_url, ydl_opts)
            worker.progress_signal.connect(self.download_progress_hook)
            worker.log_signal.connect(self.update_scroll_status)  # 连接日志信号到状态栏
            worker.finished.connect(lambda filename: self.on_download_finished(filename, url, selected_format))
            worker.error.connect(self.on_download_error)
            worker.start()
            self.download_workers.append(worker)
            self.active_downloads += 1
            
        except Exception as e:
            logger.error(f"启动网易云音乐下载失败: {str(e)}", exc_info=True)
            self.update_status_bar(f"网易云音乐下载失败: {selected_format.get('title', '未知')} - {str(e)}", "", "")
            self.reset_download_state()
    

            
            # 创建下载选项
            ydl_opts = {
                "outtmpl": output_file,
                "quiet": False,
                "ffmpeg_location": self.ffmpeg_path,
                
                # 增强下载稳定性配置
                "retries": 10,  # 增加重试次数
                "fragment_retries": 10,  # 增加片段重试次数
                "extractor_retries": 5,  # 增加提取器重试次数
                "socket_timeout": 60,  # 增加socket超时时间
                "http_chunk_size": 10485760,  # 10MB块大小，平衡速度和稳定性
                "buffersize": 4096,  # 增大缓冲区
                
                # 下载恢复和断点续传
                "continuedl": True,  # 启用断点续传
                "noprogress": False,  # 显示进度
                
                # 错误处理
                "ignoreerrors": False,  # 不忽略错误，确保错误被正确处理
                "no_warnings": False,  # 显示警告信息
                
                # 网络配置
                "prefer_insecure": True,  # 优先使用不安全的连接
                "no_check_certificate": True,  # 不检查证书
                
                # 请求头配置
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                },
            }
            
            speed_limit = self.speed_limit_input.text().strip()
            if speed_limit.isdigit():
                ydl_opts["ratelimit"] = int(speed_limit) * 1024
            


    def on_download_finished(self, filename: str, url: str, selected_format: Optional[Dict] = None) -> None:
        """处理下载完成"""
        # 防止active_downloads变为负数
        if self.active_downloads > 0:
            self.active_downloads -= 1
        
        # 从下载进度中移除已完成的文件
        if filename and filename in self.download_progress:
            del self.download_progress[filename]
        
        logger.info(f"下载完成: {filename}")
        
        # 添加到下载历史记录
        if filename and selected_format:
            self._add_to_download_history(url, filename, selected_format)
        
        # 强制更新UI，确保状态更新
        QApplication.processEvents()
        
        # 使用QTimer延迟处理，避免UI阻塞
        def cleanup_after_delay():
            # 更新下载状态显示 - 刷新所有文件状态
            self.refresh_download_status()
            
            # 再次强制更新UI
            QApplication.processEvents()
            
            # 清理已完成的下载工作线程
            with self._download_lock:
                self.download_workers = [w for w in self.download_workers if w.isRunning()]
                # 强制清理已完成线程的内存
                for worker in self.download_workers:
                    if not worker.isRunning():
                        worker.deleteLater()
            
            # 检查是否所有下载都完成了
            if self.active_downloads <= 0 and not self.download_queue:
                # 所有下载完成，显示100%进度
                self.setWindowTitle(f"椰果IDM-v{Config.APP_VERSION} - 下载中 (100.0%)")
                self.update_status_bar("下载中 (100.0%)", "已完成", "")
                # 强制更新状态栏显示
                self.update_status_bar("下载中 (100.0%)", "已完成", "")
                logger.info("所有下载已完成，显示完成对话框")
                
                # 最终刷新一次状态
                self.refresh_download_status()
                QApplication.processEvents()
                
                self.show_completion_dialog()
            else:
                # 还有文件在下载，更新状态
                self.update_status_bar(f"下载完成: {os.path.basename(filename) if filename else '未知文件'}", "", "")
        
        QTimer.singleShot(100, cleanup_after_delay)
    
    def _add_to_download_history(self, url: str, filename: str, format_info: Dict) -> None:
        """添加到下载历史记录"""
        try:
            # 获取文件大小
            file_path = os.path.join(self.save_path, filename)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            # 对于网易云音乐，使用原始URL
            record_url = format_info.get('original_url', url) if format_info.get('type') == 'netease_music' else url
            
            # 创建下载记录
            record = DownloadRecord(
                url=record_url,
                title=format_info.get('title', ''),
                filename=filename,
                format_id=format_info.get('format_id', ''),
                resolution=format_info.get('resolution', ''),
                file_size=file_size,
                download_path=self.save_path,
                platform=self._detect_platform(record_url)
            )
            
            # 添加到历史记录
            history_manager.add_record(record)
            logger.info(f"已添加到下载历史: {filename}")
            
        except Exception as e:
            logger.error(f"添加下载历史失败: {e}")
    
    def _detect_platform(self, url: str) -> str:
        """检测视频平台"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'bilibili.com' in url:
            return 'bilibili'
        elif 'music.163.com' in url:
            return 'netease_music'
        else:
            return 'unknown'

    def show_completion_dialog(self) -> None:
        """显示下载完成对话框"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("下载完成")
            dialog.setFixedSize(500, 280)
            dialog.setModal(True)
            dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            
            # 设置对话框样式
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """)
            
            layout = QVBoxLayout()
            layout.setSpacing(20)
            layout.setContentsMargins(25, 25, 25, 25)
            
            # 成功图标和标题
            title_label = QLabel("🎉 下载完成")
            title_label.setStyleSheet("""
                font-size: 20px; 
                font-weight: bold; 
                color: #28a745; 
                margin: 0;
                padding: 10px 0;
            """)
            title_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_label)
            
            # 分隔线
            line = QLabel()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #e0e0e0; margin: 0;")
            layout.addWidget(line)
            
            # 成功信息
            success_label = QLabel("所有文件已成功下载完成！")
            success_label.setStyleSheet("""
                font-size: 14px; 
                color: #495057; 
                margin: 15px 0 10px 0;
                padding: 8px 0;
                line-height: 1.4;
                min-height: 20px;
            """)
            success_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(success_label)
            
            # 路径信息容器
            path_container = QLabel()
            path_container.setStyleSheet("""
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 15px;
                margin: 10px 0;
                font-family: "Microsoft YaHei", sans-serif;
            """)
            
            # 路径标题
            path_title = QLabel("📁 保存位置：")
            path_title.setStyleSheet("""
                font-size: 13px; 
                font-weight: bold; 
                color: #495057; 
                margin: 0 0 8px 0;
            """)
            
            # 路径内容
            path_content = QLabel(self.save_path)
            path_content.setStyleSheet("""
                font-size: 12px; 
                color: #6c757d; 
                margin: 0;
                word-wrap: break-word;
                line-height: 1.4;
            """)
            path_content.setWordWrap(True)
            
            # 路径布局
            path_layout = QVBoxLayout()
            path_layout.setSpacing(5)
            path_layout.setContentsMargins(0, 0, 0, 0)
            path_layout.addWidget(path_title)
            path_layout.addWidget(path_content)
            path_container.setLayout(path_layout)
            layout.addWidget(path_container)
            
            # 添加弹性空间
            layout.addStretch(1)
            
            # 按钮布局
            button_layout = QHBoxLayout()
            button_layout.setSpacing(12)
            button_layout.addStretch(1)
            
            # 确定按钮
            ok_button = QPushButton("确定")
            ok_button.setFixedSize(90, 36)
            ok_button.clicked.connect(dialog.accept)
            ok_button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: #ffffff;
                    border: 1px solid #6c757d;
                    border-radius: 6px;
                    padding: 1px 8px;
                    font-family: "Microsoft YaHei", sans-serif;
                    font-size: 13px;
                    font-weight: 400;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                    border: 1px solid #5a6268;
                }
                QPushButton:pressed {
                    background-color: #545b62;
                    border: 1px solid #545b62;
                }
            """)
            button_layout.addWidget(ok_button)
            
            # 打开文件夹按钮
            open_button = QPushButton("📂 打开文件夹")
            open_button.setFixedSize(120, 36)
            open_button.clicked.connect(lambda: self.open_save_path_and_close(dialog))
            open_button.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: #ffffff;
                    border: 1px solid #007bff;
                    border-radius: 6px;
                    padding: 1px 8px;
                    font-family: "Microsoft YaHei", sans-serif;
                    font-size: 13px;
                    font-weight: 400;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                    border: 1px solid #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                    border: 1px solid #004085;
                }
            """)
            button_layout.addWidget(open_button)
            
            button_layout.addStretch(1)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            # 设置默认按钮
            ok_button.setDefault(True)
            ok_button.setFocus()
            
            # 显示对话框
            logger.info("显示下载完成对话框")
            dialog.exec_()
            
            # 重置下载状态
            self.reset_download_state()
            
            # 刷新下载状态显示
            self.refresh_download_status()
            
        except Exception as e:
            logger.error(f"显示完成对话框失败: {str(e)}")
            # 如果对话框显示失败，至少重置状态
            self.reset_download_state()

    def open_save_path_and_close(self, dialog: QDialog) -> None:
        """打开保存路径并关闭对话框"""
        self.open_save_path()
        dialog.accept()

    def open_save_path(self) -> None:
        """打开保存路径"""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.save_path))
        except Exception as e:
            logger.error(f"打开文件夹失败: {str(e)}")
            QMessageBox.warning(self, "提示", "无法打开文件夹，请检查路径是否正确")

    def on_download_error(self, error_msg: str) -> None:
        """处理下载错误"""
        # 防止active_downloads变为负数
        if self.active_downloads > 0:
            self.active_downloads -= 1
        
        # 分析错误类型并提供相应的处理建议
        error_lower = error_msg.lower()
        
        if any(keyword in error_lower for keyword in ["bytes read", "more expected"]):
            # 不完整下载错误
            detailed_error = f"下载不完整: {error_msg}\n\n建议:\n1. 检查网络连接\n2. 尝试重新下载\n3. 降低下载速度限制"
            logger.error(f"下载不完整错误: {error_msg}")
            QMessageBox.warning(self, "下载不完整", "文件下载不完整，请重新下载")
        elif any(keyword in error_lower for keyword in ["timeout", "connection"]):
            # 网络超时错误
            detailed_error = f"网络连接超时: {error_msg}\n\n建议:\n1. 检查网络连接\n2. 增加超时时间\n3. 尝试重新下载"
            logger.error(f"网络超时错误: {error_msg}")
            QMessageBox.warning(self, "网络超时", "网络连接超时，请检查网络后重试")
        elif any(keyword in error_lower for keyword in ["format", "codec"]):
            # 格式或编解码器错误
            detailed_error = f"格式不支持: {error_msg}\n\n建议:\n1. 选择其他格式\n2. 更新FFmpeg\n3. 检查视频源"
            logger.error(f"格式错误: {error_msg}")
            QMessageBox.warning(self, "格式不支持", "文件格式不支持，请选择其他格式")
        else:
            # 其他错误
            detailed_error = f"下载失败: {error_msg}\n\n建议:\n1. 检查网络连接\n2. 尝试重新下载\n3. 联系技术支持"
            logger.error(f"下载错误: {error_msg}")
            QMessageBox.critical(self, "下载失败", "下载失败，请稍后重试")
        
        self.update_status_bar(f"下载错误: {error_msg[:50]}...", "", "")
        
        # 检查是否所有下载都失败了
        if self.active_downloads <= 0 and not self.download_queue:
            self.reset_download_state()
        else:
            # 还有下载在进行，继续处理队列
            self._process_download_queue()
    
    def _process_download_queue(self) -> None:
        """处理下载队列中的任务"""
        try:
            while len(self.download_queue) > 0 and self.active_downloads < Config.MAX_CONCURRENT_DOWNLOADS:
                url, fmt = self.download_queue.pop(0)
                # 对于网易云音乐，使用原始URL而不是队列中的URL
                download_url = fmt.get("original_url", url) if fmt.get("type") == "netease_music" else url
                self.start_download(download_url, fmt)
        except Exception as e:
            logger.error(f"处理下载队列失败: {str(e)}")

    def pause_downloads(self) -> None:
        """暂停下载"""
        for worker in self.download_workers:
            if worker.isRunning():
                worker.pause()
        self.smart_pause_button.setText("恢复下载")
        self.update_status_bar("下载已暂停", "", "")
        logger.info("下载已暂停")
        
        # 清空状态栏滚动显示，停止显示下载进度
        if hasattr(self, 'status_scroll_label'):
            self.status_scroll_label.setText("")

    def cancel_downloads(self) -> None:
        """取消所有下载"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认")
        msg_box.setText("是否要停止所有正在进行的下载？")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮中文文本
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        reply = msg_box.exec_()
        if reply == QMessageBox.Yes:
            for worker in self.download_workers:
                if worker.isRunning():
                    worker.cancel()
            # 取消网易云音乐解析工作线程
            for worker in self.netease_music_workers:
                if worker.isRunning():
                    worker.cancel()
            self.download_queue.clear()
            self.reset_download_state()
            logger.info("下载已取消")
            self.update_status_bar("下载已取消", "", "")

    def reset_download_state(self) -> None:
        """重置下载状态"""
        self.download_progress.clear()
        self.is_downloading = False
        self.active_downloads = 0
        self.download_workers.clear()
        # 清理网易云音乐工作线程
        self.netease_music_workers.clear()
        self.smart_download_button.setEnabled(True)
        self.smart_parse_button.setEnabled(True)
        self.smart_pause_button.setEnabled(False)
        # 确保进度条和状态标签保持隐藏
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.smart_download_button.setText("下载")
        self.smart_download_button.setStyleSheet(self.default_style)
        self.smart_pause_button.setText("暂停")

    def show_context_menu(self, pos: "QPoint") -> None:
        """显示右键菜单"""
        from PyQt5.QtWidgets import QApplication
        menu = QMenu(self)
        copy_action = menu.addAction("复制文件名")
        action = menu.exec_(self.format_tree.mapToGlobal(pos))
        if action == copy_action:
            item = self.format_tree.currentItem()
            if item and item.childCount() == 0:
                filename = item.text(1)
                QApplication.clipboard().setText(filename)

    def show_url_input_context_menu(self, pos: "QPoint") -> None:
        """显示输入框右键菜单（中文）"""
        from PyQt5.QtWidgets import QApplication
        menu = QMenu(self)
        
        # 获取当前选中的文本
        cursor = self.url_input.textCursor()
        has_selection = cursor.hasSelection()
        has_text = not self.url_input.toPlainText().strip() == ""
        
        # 撤销
        undo_action = menu.addAction("撤销")
        undo_action.setEnabled(self.url_input.document().isUndoAvailable())
        undo_action.triggered.connect(self.url_input.undo)
        
        # 重做
        redo_action = menu.addAction("重做")
        redo_action.setEnabled(self.url_input.document().isRedoAvailable())
        redo_action.triggered.connect(self.url_input.redo)
        
        menu.addSeparator()
        
        # 剪切
        cut_action = menu.addAction("剪切")
        cut_action.setEnabled(has_selection)
        cut_action.triggered.connect(self.url_input.cut)
        
        # 复制
        copy_action = menu.addAction("复制")
        copy_action.setEnabled(has_selection)
        copy_action.triggered.connect(self.url_input.copy)
        
        # 粘贴
        paste_action = menu.addAction("粘贴")
        paste_action.triggered.connect(self.url_input.paste)
        
        # 删除
        delete_action = menu.addAction("删除")
        delete_action.setEnabled(has_selection)
        delete_action.triggered.connect(lambda: self.url_input.textCursor().removeSelectedText())
        
        menu.addSeparator()
        
        # 全选
        select_all_action = menu.addAction("全选")
        select_all_action.setEnabled(has_text)
        select_all_action.triggered.connect(self.url_input.selectAll)
        
        # 清空
        clear_action = menu.addAction("清空")
        clear_action.setEnabled(has_text)
        clear_action.triggered.connect(self.url_input.clear)
        
        # 显示菜单
        menu.exec_(self.url_input.mapToGlobal(pos))

    def smart_select_action(self) -> None:
        """智能选择按钮动作"""
        if not self.formats:
            return
            
        # 统计当前选择状态
        selected_count = 0
        total_count = 0
        
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            if root_item.childCount() > 0:
                # 有子项的项目（视频等）
                for j in range(root_item.childCount()):
                    total_count += 1
                    if root_item.child(j).checkState(0) == Qt.Checked:
                        selected_count += 1
            else:
                # 没有子项的项目（网易云音乐等）
                total_count += 1
                if root_item.checkState(0) == Qt.Checked:
                    selected_count += 1
        
        # 根据当前状态决定动作
        if selected_count == 0:
            # 没有选中任何项，执行全选
            self.select_all_formats()
            self.smart_select_button.setText("取消全选")
        elif selected_count == total_count:
            # 全部选中，执行取消全选
            self.deselect_all_formats()
            self.smart_select_button.setText("全选")
        else:
            # 部分选中，执行反选
            self.invert_selection()
            # 反选后重新判断状态
            self.update_smart_select_button_text()
    
    def update_smart_select_button_text(self) -> None:
        """更新智能选择按钮文本"""
        if not self.formats:
            return
            
        selected_count = 0
        total_count = 0
        
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            if root_item.childCount() > 0:
                # 有子项的项目（视频等）
                for j in range(root_item.childCount()):
                    total_count += 1
                    if root_item.child(j).checkState(0) == Qt.Checked:
                        selected_count += 1
            else:
                # 没有子项的项目（网易云音乐等）
                total_count += 1
                if root_item.checkState(0) == Qt.Checked:
                    selected_count += 1
        
        if selected_count == 0:
            self.smart_select_button.setText("全选")
        elif selected_count == total_count:
            self.smart_select_button.setText("取消全选")
        else:
            self.smart_select_button.setText("反选")
    

    def refresh_download_status(self) -> None:
        """刷新所有文件的下载状态"""
        try:
            logger.info("开始刷新下载状态...")
            updated_count = 0
            
            # 遍历所有树形项目，更新状态
            for i in range(self.format_tree.topLevelItemCount()):
                root_item = self.format_tree.topLevelItem(i)
                for j in range(root_item.childCount()):
                    child_item = root_item.child(j)
                    item_filename = child_item.text(1)  # 文件名在第1列
                    item_type = child_item.text(2)      # 文件类型在第2列
                    
                    # 构建完整的文件路径
                    file_path = os.path.join(self.save_path, f"{item_filename}.{item_type}")
                    
                    # 检查文件是否存在
                    if os.path.exists(file_path):
                        # 文件已下载，显示"已下载"
                        old_status = child_item.text(4)
                        child_item.setText(4, "已下载")
                        child_item.setForeground(4, Qt.green)
                        # 禁用已下载文件的复选框，防止重复下载
                        child_item.setFlags(child_item.flags() & ~Qt.ItemIsUserCheckable)
                        
                        if old_status != "已下载":
                            logger.info(f"文件状态更新为已下载: {item_filename}.{item_type}")
                            updated_count += 1
                    else:
                        # 文件未下载，显示"未下载"
                        old_status = child_item.text(4)
                        child_item.setText(4, "未下载")
                        child_item.setForeground(4, Qt.black)
                        # 启用未下载文件的复选框
                        child_item.setFlags(child_item.flags() | Qt.ItemIsUserCheckable)
                        
                        if old_status != "未下载":
                            logger.info(f"文件状态更新为未下载: {item_filename}.{item_type}")
                            updated_count += 1
            
            logger.info(f"下载状态刷新完成，更新了 {updated_count} 个文件的状态")
                        
        except Exception as e:
            logger.error(f"刷新下载状态失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def smart_download_action(self) -> None:
        """智能下载按钮动作"""
        if self.is_downloading:
            # 如果正在下载，执行取消操作
            self.cancel_downloads()
        else:
            # 如果未下载，执行下载操作
            self.download_selected()
    
    def smart_pause_action(self) -> None:
        """智能暂停按钮动作"""
        if self.smart_pause_button.text() == "暂停":
            # 当前是暂停状态，执行暂停操作
            self.pause_downloads()
        else:
            # 当前是恢复状态，执行恢复操作
            self.resume_downloads()
    
    def resume_downloads(self) -> None:
        """恢复下载"""
        for worker in self.download_workers:
            if worker.isRunning():
                worker.resume()
        self.smart_pause_button.setText("暂停")
        self.update_status_bar("下载已恢复", "", "")
        logger.info("下载已恢复")
    
    def clear_input(self) -> None:
        """清空输入框"""
        self.url_input.clear()
        
    def clear_parse_results(self) -> None:
        """清空列表"""
        try:
            # 确认对话框
            reply = QMessageBox.question(
                self, 
                "确认清空", 
                "确定要清空所有列表吗？\n此操作将清除所有已解析的视频格式信息。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 清空格式树
                self.format_tree.clear()
                
                # 清空相关数据
                self.formats = []
                self.parse_cache.clear()
                
                # 重置按钮状态
                self.smart_download_button.setEnabled(False)
                self.smart_select_button.setEnabled(False)
                
                # 重置选择计数
                self.selection_count_label.setText("已选择: 0 项")
                
                # 更新状态栏
                self.update_status_bar("列表已清空", "", "")
                self.status_scroll_label.setText("列表已清空")
                
                # 记录日志
                logger.info("用户清空了列表")
                
        except Exception as e:
            logger.error(f"清空列表失败: {str(e)}")
            QMessageBox.critical(self, "操作失败", "清空列表失败，请稍后重试")
        
    def new_session(self) -> None:
        """新建会话"""
        self.url_input.clear()
        self.format_tree.clear()
        self.formats = []
        self.smart_download_button.setEnabled(False)
        self.smart_select_button.setEnabled(False)
        self.selection_count_label.setText("已选择: 0 项")
        self.update_status_bar("就绪", "", "")
        self.status_scroll_label.setText("")
        
    
        
    def show_settings_dialog(self) -> None:
        """显示设置对话框"""
        from .settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 应用设置到主窗口
            self.apply_settings_from_dialog(dialog.get_settings_dict())
            
    def apply_settings_from_dialog(self, settings_dict: Dict[str, Any]) -> None:
        """从设置对话框应用设置到主窗口"""
        try:
            # 应用基本设置
            if settings_dict.get("save_path"):
                self.save_path = settings_dict["save_path"]
                # 如果 path_label 已存在，则更新其文本
                if hasattr(self, 'path_label'):
                    self.path_label.setText(f"保存路径: {self.save_path}")
                
            # 应用下载设置
            if "max_concurrent" in settings_dict:
                Config.MAX_CONCURRENT_DOWNLOADS = settings_dict["max_concurrent"]
                
            if "speed_limit" in settings_dict:
                speed_limit = settings_dict["speed_limit"]
                if speed_limit > 0:
                    self.speed_limit_input.setText(str(speed_limit))
                else:
                    self.speed_limit_input.clear()
                    
            # 应用界面设置
            if "font_size" in settings_dict:
                font_size = settings_dict["font_size"]
                # 更新全局字体大小
                self.update_font_size(font_size)
                
            # 应用高级设置
            if settings_dict.get("ffmpeg_path"):
                self.ffmpeg_path = settings_dict["ffmpeg_path"]
                
            logger.info("设置已应用到主窗口")
            
        except Exception as e:
            logger.error(f"应用设置失败: {str(e)}")
            
    def update_font_size(self, font_size: int) -> None:
        """更新全局字体大小"""
        try:
            # 更新样式表中的字体大小
            current_style = self.styleSheet()
            # 这里可以添加动态更新字体大小的逻辑
            logger.info(f"字体大小已更新为: {font_size}px")
        except Exception as e:
            logger.error(f"更新字体大小失败: {str(e)}")
        
    
        
    def show_log_dialog(self) -> None:
        """显示日志查看对话框"""
        try:
            # 使用新的日志查看器
            log_viewer = LogViewer(log_manager, self)
            log_viewer.show()
            logger.info("日志查看器已打开")
        except Exception as e:
            logger.error(f"打开日志查看器失败: {str(e)}")
            QMessageBox.critical(self, "操作失败", "打开日志查看器失败，请稍后重试")
        


            

        
    def show_help_dialog(self) -> None:
        """显示使用说明对话框"""
        help_text = """
        <div style="font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6;">
            <h2 style="color: #007bff; margin-bottom: 20px;">🎯 椰果IDM 使用指南</h2>
            
            <h3 style="color: #495057; margin-top: 25px; margin-bottom: 15px;">📋 快速开始</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <ol style="margin: 0; padding-left: 20px;">
                    <li><strong>粘贴链接：</strong>将视频或音乐链接粘贴到输入框中（支持多个链接，每行一个）</li>
                    <li><strong>获取格式：</strong>点击"解析"按钮，系统会自动获取可用的下载格式</li>
                    <li><strong>选择内容：</strong>在格式列表中选择您需要的分辨率和音质（可多选）</li>
                    <li><strong>开始下载：</strong>点击"下载"按钮，选择保存位置后开始下载</li>
                </ol>
            </div>
            
            <h3 style="color: #495057; margin-top: 25px; margin-bottom: 15px;">✨ 主要功能</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div style="background: #e3f2fd; padding: 12px; border-radius: 6px; border-left: 4px solid #2196f3;">
                    <h4 style="margin: 0 0 8px 0; color: #1976d2;">🎬 多平台支持</h4>
                    <ul style="margin: 0; padding-left: 15px; font-size: 13px;">
                        <li>YouTube 视频下载</li>
                        <li>Bilibili（B站）视频</li>
                        <li>网易云音乐下载</li>
                        <li>支持多种媒体格式</li>
                    </ul>
                </div>
                <div style="background: #e8f5e8; padding: 12px; border-radius: 6px; border-left: 4px solid #4caf50;">
                    <h4 style="margin: 0 0 8px 0; color: #388e3c;">⚡ 高效下载</h4>
                    <ul style="margin: 0; padding-left: 15px; font-size: 13px;">
                        <li>批量下载支持</li>
                        <li>多线程并发下载</li>
                        <li>断点续传功能</li>
                    </ul>
                </div>
                <div style="background: #fff3e0; padding: 12px; border-radius: 6px; border-left: 4px solid #ff9800;">
                    <h4 style="margin: 0 0 8px 0; color: #f57c00;">🎛️ 智能控制</h4>
                    <ul style="margin: 0; padding-left: 15px; font-size: 13px;">
                        <li>下载速度调节</li>
                        <li>暂停/恢复/取消</li>
                        <li>实时进度显示</li>
                    </ul>
                </div>
                <div style="background: #f3e5f5; padding: 12px; border-radius: 6px; border-left: 4px solid #9c27b0;">
                    <h4 style="margin: 0 0 8px 0; color: #7b1fa2;">🔧 格式管理</h4>
                    <ul style="margin: 0; padding-left: 15px; font-size: 13px;">
                        <li>多种分辨率选择</li>
                        <li>智能格式推荐</li>
                        <li>自动格式转换</li>
                    </ul>
                </div>
            </div>
            
            <h3 style="color: #495057; margin-top: 25px; margin-bottom: 15px;">🚀 YouTube 下载优化</h3>
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; border-left: 4px solid #4caf50;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>快速解析：</strong>优化的解析参数，15秒超时保护，大幅提升解析速度</li>
                    <li><strong>智能选择：</strong>每种分辨率自动选择最优编码格式，避免选择困难</li>
                    <li><strong>全面支持：</strong>支持从144P到4K的所有常见分辨率</li>
                    <li><strong>编码识别：</strong>自动识别AVC、VP9、AV1等编码格式</li>
                    <li><strong>质量优化：</strong>按文件大小选择最优格式，确保最佳质量</li>
                </ul>
            </div>
            
            <h3 style="color: #495057; margin-top: 25px; margin-bottom: 15px;">🎵 网易云音乐下载</h3>
            <div style="background: #f3e5f5; padding: 15px; border-radius: 8px; border-left: 4px solid #9c27b0;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>单曲下载：</strong>支持网易云音乐单曲链接解析和下载</li>
                    <li><strong>歌单批量：</strong>支持歌单链接解析，可批量下载所有歌曲</li>
                    <li><strong>智能解析：</strong>使用yt-dlp引擎，支持付费歌曲解析</li>
                    <li><strong>信息完整：</strong>显示歌曲名称、歌手、时长、文件大小等</li>
                    <li><strong>灵活控制：</strong>支持解析过程中的暂停、恢复和取消操作</li>
                    <li><strong>实时反馈：</strong>状态栏实时显示解析进度和状态信息</li>
                </ul>
            </div>
            
            <h3 style="color: #495057; margin-top: 25px; margin-bottom: 15px;">💡 实用技巧</h3>
            <div style="background: #fff8e1; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>批量处理：</strong>在输入框中每行粘贴一个链接，可同时处理多个内容</li>
                    <li><strong>格式建议：</strong>建议优先选择1080P或720P分辨率，平衡质量和文件大小</li>
                    <li><strong>下载控制：</strong>使用"暂停"按钮可暂停下载，使用"取消"按钮可停止下载</li>
                    <li><strong>路径设置：</strong>在设置中可自定义下载保存位置</li>
                    <li><strong>链接支持：</strong>支持标准YouTube链接和短链接（youtu.be）</li>
                    <li><strong>音乐下载：</strong>支持单曲链接和歌单链接，歌单会自动解析所有歌曲</li>
                    <li><strong>操作控制：</strong>解析过程中可随时暂停、恢复或取消操作</li>
                    <li><strong>右键功能：</strong>输入框支持中文右键菜单，包含撤销、复制、粘贴等功能</li>
                </ul>
            </div>
            
            <h3 style="color: #495057; margin-top: 25px; margin-bottom: 15px;">⚠️ 温馨提示</h3>
            <div style="background: #ffebee; padding: 15px; border-radius: 8px; border-left: 4px solid #f44336;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li>请确保网络连接稳定，下载大文件时建议使用有线网络</li>
                    <li>某些视频可能因版权限制无法下载，这是正常现象</li>
                    <li>下载速度受网络环境和服务器限制，请耐心等待</li>
                    <li>建议定期清理下载文件夹，避免占用过多磁盘空间</li>
                    <li>如遇到问题，可使用"问题反馈"功能联系我们</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding: 15px; background: #e8f5e8; border-radius: 8px;">
                <p style="margin: 0; color: #2e7d32; font-weight: bold;">🎉 现在开始您的下载之旅吧！</p>
            </div>
        </div>
        """
        
        # 创建自定义对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
        from PyQt5.QtCore import Qt
        
        dialog = QDialog(self)
        dialog.setWindowTitle("使用说明")
        dialog.setFixedSize(800, 600)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        
        # 创建文本浏览器
        text_browser = QTextBrowser()
        text_browser.setHtml(help_text)
        text_browser.setOpenExternalLinks(True)
        text_browser.setContentsMargins(0, 0, 0, 0)
        text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px 0px 15px 15px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
                line-height: 1.6;
                margin-right: 0px;
                padding-right: 0px;
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
        """)
        layout.addWidget(text_browser)
        
        dialog.setLayout(layout)
        
        dialog.exec_()
        
    def show_shortcuts_dialog(self) -> None:
        """显示快捷键帮助对话框"""
        shortcuts_text = """
        <div style="font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6;">
            <h2 style="color: #007bff; margin-bottom: 20px;">⌨️ 快捷键参考</h2>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h3 style="color: #495057; margin-bottom: 15px; border-bottom: 2px solid #e9ecef; padding-bottom: 8px;">📁 文件管理</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+O</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">选择下载保存位置</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+Shift+O</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">打开下载文件夹</td>
                        </tr>
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+Q</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">退出程序</td>
                        </tr>
                    </table>
                    
                    <h3 style="color: #495057; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #e9ecef; padding-bottom: 8px;">✏️ 格式选择</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+A</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">选择所有格式</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+D</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">取消所有选择</td>
                        </tr>
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+I</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">反选格式</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+L</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">清空链接输入</td>
                        </tr>
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+Z</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">撤销操作</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+Y</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">重做操作</td>
                        </tr>
                    </table>
                </div>
                
                <div>
                    <h3 style="color: #495057; margin-bottom: 15px; border-bottom: 2px solid #e9ecef; padding-bottom: 8px;">🛠️ 下载控制</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">F5</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">开始解析链接</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">F6</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">开始下载</td>
                        </tr>
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">F7</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">暂停下载</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">F8</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">取消下载</td>
                        </tr>
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+,</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">打开设置</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+Shift+L</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">查看日志</td>
                        </tr>
                    </table>
                    
                    <h3 style="color: #495057; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #e9ecef; padding-bottom: 8px;">❓ 帮助支持</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">F1</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">查看使用说明</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+F1</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">查看快捷键</td>
                        </tr>
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 8px; border: 1px solid #e9ecef; font-weight: bold; color: #007bff;">Ctrl+Shift+F</td>
                            <td style="padding: 8px; border: 1px solid #e9ecef;">提交问题反馈</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #2196f3;">
                <h4 style="margin: 0 0 10px 0; color: #1976d2;">💡 使用提示</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    <li>快捷键可以大大提高操作效率，建议熟练掌握常用快捷键</li>
                    <li>在格式列表中双击项目可以快速切换选择状态</li>
                    <li>使用Tab键可以在不同控件间快速切换焦点</li>
                    <li>在输入框中按Enter键可以快速解析视频/音乐</li>
                    <li>输入框支持中文右键菜单，包含撤销、复制、粘贴等功能</li>
                    <li>网易云音乐解析过程中可随时暂停、恢复或取消</li>
                </ul>
            </div>
        </div>
        """
        
        # 创建自定义对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
        from PyQt5.QtCore import Qt
        
        dialog = QDialog(self)
        dialog.setWindowTitle("快捷键帮助")
        dialog.setFixedSize(700, 500)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        
        # 创建文本浏览器
        text_browser = QTextBrowser()
        text_browser.setHtml(shortcuts_text)
        text_browser.setOpenExternalLinks(True)
        text_browser.setContentsMargins(0, 0, 0, 0)
        text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px 0px 15px 15px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
                line-height: 1.6;
                margin-right: 0px;
                padding-right: 0px;
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
        """)
        layout.addWidget(text_browser)
        
        dialog.setLayout(layout)
        
        dialog.exec_()
        
    def show_feedback_dialog(self) -> None:
        """显示问题反馈对话框"""
        try:
            from .feedback_dialog import FeedbackDialog
            dialog = FeedbackDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "操作失败", "打开反馈对话框失败，请稍后重试")
            logger.error(f"打开反馈对话框失败: {str(e)}")
    
    def show_download_history(self) -> None:
        """显示下载历史对话框"""
        try:
            from .history_dialog import HistoryDialog
            dialog = HistoryDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "操作失败", "打开下载历史对话框失败，请稍后重试")
            logger.error(f"打开下载历史对话框失败: {str(e)}")
    
    def show_subtitle_dialog(self) -> None:
        """显示字幕下载对话框"""
        try:
            from .subtitle_dialog import SubtitleDialog
            dialog = SubtitleDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "操作失败", "打开字幕下载对话框失败，请稍后重试")
            logger.error(f"打开字幕下载对话框失败: {str(e)}")
        
    def show_about_dialog(self) -> None:
        """显示关于对话框"""
        about_text = f"""
        <div style="font-family: 'Microsoft YaHei', sans-serif; text-align: left; line-height: 1.6;">
            <div style="margin-bottom: 30px; text-align: center;">
                <h1 style="color: #007bff; margin-bottom: 10px; font-size: 28px;">🥥 椰果IDM</h1>
                <p style="color: #6c757d; font-size: 16px; margin: 0;">版本 {Config.APP_VERSION}</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 12px; margin-bottom: 25px;">
                <p style="margin: 0 0 15px 0; font-size: 16px; color: #495057;">
                    <strong>一个简单、免费、无套路的视频和音乐下载工具</strong>
                </p>
                <p style="margin: 0; color: #6c757d;">
                    支持从 YouTube、Bilibili（B站）下载视频，从网易云音乐下载音乐
                </p>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px;">
                <div style="background: #e8f5e8; padding: 15px; border-radius: 8px;">
                    <h3 style="margin: 0 0 10px 0; color: #2e7d32;">🎯 主要特色</h3>
                    <ul style="margin: 0; padding-left: 15px; color: #495057;">
                        <li>多平台视频/音乐下载</li>
                        <li>批量下载支持</li>
                        <li>智能格式选择</li>
                        <li>现代化界面设计</li>
                        <li>实时状态反馈</li>
                    </ul>
                </div>
                <div style="background: #e3f2fd; padding: 15px; border-radius: 8px;">
                    <h3 style="margin: 0 0 10px 0; color: #1976d2;">🔧 技术优势</h3>
                    <ul style="margin: 0; padding-left: 15px; color: #495057;">
                        <li>多线程并发下载</li>
                        <li>断点续传支持</li>
                        <li>实时进度显示</li>
                        <li>完整的日志系统</li>
                    </ul>
                </div>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin-bottom: 25px;">
                <h3 style="margin: 0 0 10px 0; color: #f57c00;">👨‍💻 开发者信息</h3>
                <p style="margin: 0; color: #495057;">
                    <strong>作者：</strong>mrchzh<br>
                    <strong>邮箱：</strong>gmrchzh@gmail.com<br>
                    <strong>创建日期：</strong>2025年8月25日
                </p>
            </div>
            
            <div style="background: #f3e5f5; padding: 15px; border-radius: 8px; margin-bottom: 25px;">
                <h3 style="margin: 0 0 10px 0; color: #7b1fa2;">📄 开源信息</h3>
                <p style="margin: 0; color: #495057;">
                    本项目采用 <strong>MIT 许可证</strong><br>
                    基于开源项目构建，感谢所有贡献者
                </p>
            </div>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px;">
                <h3 style="margin: 0 0 10px 0; color: #2e7d32;">🙏 致谢</h3>
                <p style="margin: 0; color: #495057;">
                    感谢以下开源项目的支持：<br>
                    <strong>yt-dlp</strong> - 强大的视频下载库<br>
                    <strong>PyQt5</strong> - 现代化GUI框架<br>
                    <strong>FFmpeg</strong> - 多媒体处理工具
                </p>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; text-align: center;">
                <p style="margin: 0; color: #ffffff; font-weight: bold; font-size: 16px;">
                    🎉 感谢您使用椰果IDM！
                </p>
            </div>
        </div>
        """
        
        # 创建自定义对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
        from PyQt5.QtCore import Qt
        
        dialog = QDialog(self)
        dialog.setWindowTitle("关于椰果IDM")
        dialog.setFixedSize(600, 700)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建文本浏览器
        text_browser = QTextBrowser()
        text_browser.setHtml(about_text)
        text_browser.setOpenExternalLinks(True)
        text_browser.setContentsMargins(0, 0, 0, 0)
        text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px 0px 15px 15px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
                line-height: 1.6;
                margin-right: 0px;
                padding-right: 0px;
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
        """)
        layout.addWidget(text_browser)
        
        dialog.setLayout(layout)
        
        dialog.exec_()
        
    

    def closeEvent(self, event: "QCloseEvent") -> None:
        """处理窗口关闭事件"""
        self.timer.stop()
        for worker in self.download_workers:
            if worker.isRunning():
                worker.cancel()
        for worker in self.parse_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()

        self.settings.setValue("save_path", self.save_path)
        event.accept()
    
    def _is_video_already_added(self, video_id: str, video_title: str) -> bool:
        """检查视频是否已经添加到树形控件中"""
        try:
            # 遍历所有分辨率分组，检查是否已存在相同标题的视频
            for i in range(self.format_tree.topLevelItemCount()):
                root_item = self.format_tree.topLevelItem(i)
                for j in range(root_item.childCount()):
                    child_item = root_item.child(j)
                    filename = child_item.text(1)  # 文件名在第1列
                    
                    # 检查文件名是否包含相同的视频标题（去掉分辨率后缀）
                    if video_title in filename or video_id in filename:
                        return True
                    
                    # 检查是否包含相同的视频ID
                    if video_id != "unknown" and video_id in filename:
                        return True
            
            return False
        except Exception as e:
            logger.error(f"检查视频重复时出错: {e}")
            return False

    def _get_download_options(self, output_file: str) -> Dict:
        """获取统一的下载配置选项"""
        ydl_opts = {
            "outtmpl": output_file,
            "quiet": False,
            "ffmpeg_location": self.ffmpeg_path,
            
            # 增强下载稳定性配置
            "retries": 10,  # 增加重试次数
            "fragment_retries": 10,  # 增加片段重试次数
            "extractor_retries": 5,  # 增加提取器重试次数
            "socket_timeout": 60,  # 增加socket超时时间
            "http_chunk_size": 10485760,  # 10MB块大小，平衡速度和稳定性
            "buffersize": 4096,  # 增大缓冲区
            
            # 下载恢复和断点续传
            "continuedl": True,  # 启用断点续传
            "noprogress": False,  # 显示进度
            
            # 错误处理
            "ignoreerrors": False,  # 不忽略错误，确保错误被正确处理
            "no_warnings": False,  # 显示警告信息
            
            # 网络配置
            "prefer_insecure": True,  # 优先使用不安全的连接
            "no_check_certificate": True,  # 不检查证书
            
            # 请求头配置
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
        }
        
        # 添加速度限制
        speed_limit = self.speed_limit_input.text().strip()
        if speed_limit.isdigit():
            ydl_opts["ratelimit"] = int(speed_limit) * 1024
        
        return ydl_opts

    def _check_memory_usage(self) -> None:
        """检查内存使用情况并执行清理"""
        # 使用锁确保内存检查的线程安全
        if not self._memory_lock.acquire(blocking=False):
            return  # 如果锁被占用，跳过这次检查
        
        try:
            current_time = time.time()
            if current_time - self._last_memory_check < self._memory_check_interval:
                return
            
            self._last_memory_check = current_time
            
            # 获取当前进程的内存使用情况
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            logger.info(f"当前内存使用: {memory_mb:.1f} MB")
            
            # 如果内存使用超过警告阈值，执行清理
            if memory_mb > Config.MEMORY_WARNING_THRESHOLD:
                logger.warning(f"内存使用过高: {memory_mb:.1f} MB，执行清理...")
                self.cleanup_resources()
                
                # 强制垃圾回收
                gc.collect()
                
                # 重新检查内存使用
                memory_info = process.memory_info()
                memory_mb_after = memory_info.rss / 1024 / 1024
                logger.info(f"清理后内存使用: {memory_mb_after:.1f} MB")
                
                # 如果清理后内存仍然过高，执行更激进的清理
                if memory_mb_after > Config.MEMORY_CRITICAL_THRESHOLD:
                    logger.error(f"内存使用仍然过高: {memory_mb_after:.1f} MB，执行激进清理...")
                    self._aggressive_cleanup()
                    
        except Exception as e:
            logger.error(f"内存检查失败: {str(e)}")
        finally:
            self._memory_lock.release()

    def cleanup_resources(self) -> None:
        """清理资源，释放内存"""
        try:
            # 清理解析缓存
            with self._cache_lock:
                if len(self.parse_cache) > Config.CACHE_LIMIT // 2:
                    # 保留一半的缓存
                    items_to_remove = len(self.parse_cache) - Config.CACHE_LIMIT // 2
                    for _ in range(items_to_remove):
                        if self.parse_cache:
                            self.parse_cache.popitem()
            
            # 清理格式列表
            if len(self.formats) > Config.CACHE_LIMIT:
                self.formats = self.formats[-Config.CACHE_LIMIT:]
            
            # 清理已完成的工作线程
            self.parse_workers = [w for w in self.parse_workers if w.isRunning()]
            self.download_workers = [w for w in self.download_workers if w.isRunning()]

            self.netease_music_workers = [w for w in self.netease_music_workers if w.isRunning()]
            
            # 清理下载进度信息
            if len(self.download_progress) > 50:  # 限制进度信息数量
                keys_to_remove = list(self.download_progress.keys())[:-50]
                for key in keys_to_remove:
                    self.download_progress.pop(key, None)
            
            logger.info("资源清理完成")
            
        except Exception as e:
            logger.error(f"资源清理失败: {str(e)}")

    def _aggressive_cleanup(self) -> None:
        """激进的内存清理"""
        try:
            # 清空所有缓存
            with self._cache_lock:
                self.parse_cache.clear()
            
            # 清空格式列表
            self.formats.clear()
            
            # 清空下载进度
            self.download_progress.clear()
            
            # 强制终止所有非活动线程
            for worker in self.parse_workers[:]:
                if not worker.isRunning():
                    worker.deleteLater()
                    self.parse_workers.remove(worker)
            
            for worker in self.download_workers[:]:
                if not worker.isRunning():
                    worker.deleteLater()
                    self.download_workers.remove(worker)
            

            
            for worker in self.netease_music_workers[:]:
                if not worker.isRunning():
                    worker.deleteLater()
                    self.netease_music_workers.remove(worker)
            
            # 多次强制垃圾回收
            for _ in range(3):
                gc.collect()
            
            logger.info("激进内存清理完成")
            
        except Exception as e:
            logger.error(f"激进内存清理失败: {str(e)}")

    def _check_disk_space(self, required_size: int = 0) -> bool:
        """检查磁盘空间是否足够"""
        try:
            if not os.path.exists(self.save_path):
                return False
            
            disk_usage = shutil.disk_usage(self.save_path)
            free_space = disk_usage.free
            
            # 如果指定了所需大小，检查是否足够
            if required_size > 0:
                if free_space < required_size:
                    logger.warning(f"磁盘空间不足: 需要 {required_size} 字节，可用 {free_space} 字节")
                    return False
            
            # 检查是否有至少100MB的可用空间
            min_space = 100 * 1024 * 1024  # 100MB
            if free_space < min_space:
                logger.warning(f"磁盘空间不足: 可用空间 {free_space / 1024 / 1024:.1f} MB")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查磁盘空间失败: {str(e)}")
            return False




