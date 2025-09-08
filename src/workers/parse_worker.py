"""
Parse Worker Thread Module

This module contains video parsing worker thread classes, responsible for:
- Asynchronous video URL parsing to get format information
- Support for pause, resume, and cancel operations
- Thread-safe signal communication
- Error handling and status feedback
- Real-time progress feedback and parsing while writing functionality

Main Classes:
- ParseWorker: Video parsing worker thread class

Author: Yeguo IDM Development Team
Version: 1.0.0
"""

import time
import threading
import logging
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
import yt_dlp
from src.core.youtube_optimizer import YouTubeOptimizer
from src.utils.logger import logger
from src.utils.ytdlp_logger import YTDlpLogger

# YTDlpLogger 已移动到 src/utils/ytdlp_logger.py

class ParseWorker(QThread):
    """视频解析工作线程"""
    
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)  # 状态信号
    progress_signal = pyqtSignal(int, int)  # 新增：进度信号 (当前进度, 总数量)
    video_parsed_signal = pyqtSignal(dict, str)  # 新增：单个视频解析完成信号 (视频信息, URL)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self._paused = False
        self._cancelled = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()
        self._extraction_result = None
        self._extraction_error = None
        # 移除threading.Event，统一使用PyQt5的线程安全机制
        self._extraction_completed = threading.Event()
        self._extraction_thread = None

    def run(self) -> None:
        try:
            
            self.status_signal.emit("开始解析视频...")
            self._check_pause()
            if self._check_cancelled():
                return
            
            # 根据平台设置不同的解析选项
            self.status_signal.emit("配置解析选项...")
            ydl_opts = self._get_platform_specific_options()
            
            self.status_signal.emit("初始化下载器...")
            self._check_pause()
            if self._check_cancelled():
                return
            
            # 使用动态超时机制，根据平台调整超时时间
            # 根据平台设置不同的超时时间
            if 'bilibili.com' in self.url:
                timeout_duration = 180  # B站播放列表需要更长时间
                # 检查是否是B站多P视频
                if 'bilibili.com/video/' in self.url and '?p=' not in self.url:
                    self.log_signal.emit("🔍 检测到B站视频URL，尝试获取所有分P")
            elif 'youtube.com' in self.url or 'youtu.be' in self.url:
                timeout_duration = 300  # YouTube增加超时时间到5分钟，确保稳定性
            else:
                timeout_duration = 60  # 其他平台默认时间
            
            try:
                # 使用可中断的 yt-dlp 调用
                self.status_signal.emit("正在获取视频信息...")
                info = self._extract_info_with_interrupt(ydl_opts, timeout_duration)
                
                if info is None:
                    raise ValueError("无法提取视频信息")
                
                self.status_signal.emit("处理视频格式...")
                self._check_pause()
                if self._check_cancelled():
                    return
                
                if "entries" in info:
                    # 检查是否是B站多P视频
                    if 'bilibili.com' in self.url and 'bilibili.com/video/' in self.url:
                        # B站多P视频，使用特殊处理逻辑
                        self.log_signal.emit("🔍 检测到B站多P视频，使用特殊处理逻辑")
                        self._handle_bilibili_multi_part(info)
                        return
                    else:
                        # 其他播放列表或频道 - 边解析边发送结果
                        total_entries = len(info['entries'])
                        self.status_signal.emit(f"发现播放列表，包含 {total_entries} 个视频")
                        self.log_signal.emit(f"🔍 开始处理播放列表，总条目数: {total_entries}")
                    
                    for i, entry in enumerate(info["entries"]):
                        if self._check_cancelled():
                            return
                        
                        self.log_signal.emit(f"🔍 处理条目 {i+1}/{total_entries}")
                        
                        if entry:
                            entry_title = entry.get("title", "未知标题")
                            entry_id = entry.get("id", "未知ID")
                            self.log_signal.emit(f"  - 标题: {entry_title}")
                            self.log_signal.emit(f"  - ID: {entry_id}")
                            self.log_signal.emit(f"  - 是否有formats: {'formats' in entry}")
                            
                            # 发送进度信号
                            self.progress_signal.emit(i + 1, total_entries)
                            
                            # 检查是否需要重新解析单个视频以获取格式信息
                            if "formats" not in entry or not entry["formats"]:
                                # 重新解析单个视频以获取完整的格式信息
                                video_url = entry.get("webpage_url") or entry.get("url")
                                self.log_signal.emit(f"  - 需要重新解析，URL: {video_url}")
                                
                                if video_url:
                                    self.status_signal.emit(f"重新解析视频 {i+1}/{total_entries}: {entry.get('title', 'Unknown')}")
                                    self.log_signal.emit(f"🔄 开始重新解析: {entry_title}")
                                    
                                    try:
                                        # 使用单个视频的解析选项
                                        single_video_opts = self._get_single_video_options()
                                        
                                        # 设置自定义日志记录器
                                        single_video_opts["logger"] = YTDlpLogger(self.log_signal)
                                        
                                        with yt_dlp.YoutubeDL(single_video_opts) as ydl:
                                            video_info = ydl.extract_info(video_url, download=False)
                                            if video_info and "formats" in video_info:
                                                entry["formats"] = video_info["formats"]
                                                # 合并其他有用的信息
                                                entry["duration"] = video_info.get("duration", entry.get("duration"))
                                                entry["thumbnail"] = video_info.get("thumbnail", entry.get("thumbnail"))
                                                entry["uploader"] = video_info.get("uploader", entry.get("uploader"))
                                                entry["upload_date"] = video_info.get("upload_date", entry.get("upload_date"))
                                                entry["view_count"] = video_info.get("view_count", entry.get("view_count"))
                                                
                                                self.status_signal.emit(f"成功获取视频格式: {len(video_info['formats'])} 个格式")
                                                self.log_signal.emit(f"✅ 重新解析成功，获得 {len(video_info['formats'])} 个格式")
                                            else:
                                                self.status_signal.emit(f"无法获取视频格式信息")
                                                self.log_signal.emit(f"❌ 重新解析失败：无法获取格式信息")
                                    except Exception as e:
                                        self.status_signal.emit(f"重新解析视频失败: {str(e)}")
                                        self.log_signal.emit(f"❌ 重新解析异常: {str(e)}")
                                        # 如果重新解析失败，使用空格式列表
                                        entry["formats"] = []
                                else:
                                    self.log_signal.emit(f"❌ 无法获取视频URL")
                            else:
                                self.log_signal.emit(f"✅ 已有格式信息，跳过重新解析")
                            
                            # 立即发送单个视频解析完成信号
                            self.log_signal.emit(f"📤 发送视频解析信号: {entry_title}")
                            self.video_parsed_signal.emit(entry, self.url)
                            
                            # 短暂延迟，避免UI阻塞
                            time.sleep(0.1)
                        else:
                            self.log_signal.emit(f"❌ 条目 {i+1} 为空，跳过")
                    
                    # 发送最终完成信号
                    self.finished.emit(info)
                else:
                    # 单个视频，检查是否是B站多P视频
                    if 'bilibili.com' in self.url and 'bilibili.com/video/' in self.url and '?p=' not in self.url:
                        # 特殊处理B站多P视频 - 尝试获取所有分P
                        self.log_signal.emit("🔍 检测到B站视频，尝试获取所有分P信息")
                        self._handle_bilibili_multi_part(info)
                    else:
                        # 普通单个视频，直接发送结果
                        self.progress_signal.emit(1, 1)
                        self.video_parsed_signal.emit(info, self.url)
                        self.finished.emit(info)
                        
            finally:
                pass
                    
        except TimeoutError as e:
            error_msg = f"解析 {self.url} 超时: {str(e)}"
            self.error.emit(error_msg)
            # 提供超时建议
            self.log_signal.emit("建议：检查网络连接，或尝试重新解析")
        except InterruptedError as e:
            # 用户取消解析，发送友好的提示信息
            self.log_signal.emit("解析已取消")
            # 不发送error信号，避免显示错误对话框
        except Exception as e:
            error_msg = f"解析 {self.url} 失败: {str(e)}"
            self.error.emit(error_msg)
            # 提供失败建议
            self.log_signal.emit("建议：检查视频链接是否有效，或尝试重新解析")

    def _extract_info_with_interrupt(self, ydl_opts: dict, timeout: int) -> dict:
        """可中断的视频信息提取"""
        self._extraction_result = None
        self._extraction_error = None
        self._extraction_completed.clear()
        self._extraction_thread = None
        
        try:
            # 创建提取线程
            self._extraction_thread = threading.Thread(
                target=self._extract_info_worker,
                args=(ydl_opts,)
            )
            self._extraction_thread.daemon = True
            self._extraction_thread.start()
            
            # 等待提取完成或超时
            start_time = time.time()
            while not self._extraction_completed.is_set():
                # 检查是否取消
                if self._check_cancelled():
                    # 尝试中断线程
                    self._interrupt_extraction()
                    raise InterruptedError("解析已取消")
                
                # 检查是否暂停
                if self._check_paused():
                    # 暂停时等待恢复
                    while self._check_paused() and not self._check_cancelled():
                        time.sleep(0.1)
                    if self._check_cancelled():
                        raise InterruptedError("解析已取消")
                
                # 检查是否超时
                if time.time() - start_time > timeout:
                    self._interrupt_extraction()
                    raise TimeoutError("解析超时")
                
                # 检查线程是否完成
                if self._extraction_thread and not self._extraction_thread.is_alive():
                    self._extraction_completed.set()
                    break
                
                # 短暂等待
                time.sleep(0.01)
            
            # 检查是否有错误
            if self._extraction_error:
                raise self._extraction_error
            
            if self._extraction_result is None:
                raise ValueError("无法提取视频信息")
            
            return self._extraction_result
            
        except Exception as e:
            # 确保线程被清理
            self._interrupt_extraction()
            raise e
        finally:
            # 清理线程引用
            self._extraction_thread = None

    def _extract_info_worker(self, ydl_opts: dict):
        """在单独线程中执行 yt-dlp 提取"""
        try:
            # 设置自定义日志记录器
            ydl_opts["logger"] = YTDlpLogger(self.log_signal)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                self._extraction_result = info
        except Exception as e:
            self._extraction_error = e
        finally:
            self._extraction_completed.set()

    def _interrupt_extraction(self):
        """中断提取线程"""
        try:
            if self._extraction_thread and self._extraction_thread.is_alive():
                # 注意：Python 线程无法被强制终止，但我们可以设置标志
                # 实际的 yt-dlp 调用可能仍然会继续，但我们会忽略结果
                self._extraction_completed.set()
                # 等待线程自然结束，但设置最大等待时间
                self._extraction_thread.join(timeout=2.0)
        except Exception as e:
            # 忽略中断过程中的错误
            pass
    
    def _get_platform_specific_options(self) -> dict:
        """根据平台获取特定的解析选项"""
        base_opts = {
            "quiet": False,
            "no_warnings": False,
            "format_sort": ["+res", "+fps", "+codec:h264", "+size"],  # 优先按分辨率排序
            "merge_output_format": "mp4",  # 允许FFmpeg进行音视频合并
            "socket_timeout": 30,  # 适中的超时时间
            "retries": 3,  # 适中的重试次数
            "fragment_retries": 2,  # 片段重试
            "extractor_retries": 2,  # 提取器重试
        }
        
        # 检测平台并添加特定配置
        if 'youtube.com' in self.url or 'youtu.be' in self.url:
            # 使用优化的 YouTube 配置 - 平衡速度和稳定性
            youtube_optimizer = YouTubeOptimizer()
            base_opts.update({
                # 基础配置
                "quiet": False,
                "no_warnings": False,
                "format": "all",  # 获取所有格式
                "merge_output_format": "mp4",
                
                # 网络优化配置
                "socket_timeout": 45,  # 增加超时时间
                "retries": 5,  # 增加重试次数
                "fragment_retries": 3,
                "extractor_retries": 3,
                "http_chunk_size": 8388608,  # 8MB块大小
                "buffersize": 32768,  # 32KB缓冲区
                
                # 并发优化
                "concurrent_fragment_downloads": 8,  # 8并发
                "concurrent_fragments": 8,
                
                # 跳过不必要的检查
                "check_formats": False,  # 不检查格式可用性
                "test": False,  # 不测试格式
                
                # 优化的请求头
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
                
                # 安全设置
                "nocheckcertificate": True,
                "prefer_insecure": True,
                
                # 地理绕过
                "geo_bypass": True,
                "geo_bypass_country": "US",
            })
                
        elif 'bilibili.com' in self.url:
            # Bilibili 优化配置
            base_opts.update({
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://www.bilibili.com/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                }
            })
        
        return base_opts
    
    def _get_single_video_options(self) -> dict:
        """获取单个视频解析选项"""
        return {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": False,
            "socket_timeout": 20,  # 单个视频解析使用更短超时
            "retries": 2,
        }
    
    def _handle_bilibili_multi_part(self, info: dict) -> None:
        """处理B站多P视频"""
        try:
            # 调试：输出完整的视频信息结构
            self.log_signal.emit(f"🔍 B站视频信息结构:")
            self.log_signal.emit(f"  - 标题: {info.get('title', '未知')}")
            self.log_signal.emit(f"  - ID: {info.get('id', '未知')}")
            self.log_signal.emit(f"  - 网页URL: {info.get('webpage_url', '未知')}")
            self.log_signal.emit(f"  - 所有键: {list(info.keys())}")
            
            # 尝试从多个可能的字段获取分P数量
            page_count = 1
            possible_page_fields = ['page_count', 'pages', 'total_pages', 'episode_count']
            
            for field in possible_page_fields:
                if field in info:
                    page_count = info[field]
                    self.log_signal.emit(f"  - 从字段 '{field}' 获取分P数量: {page_count}")
                    break
            
            # 如果没有找到分P数量，尝试从其他信息推断
            if page_count == 1:
                # 检查是否有entries信息
                if 'entries' in info and info['entries']:
                    page_count = len(info['entries'])
                    self.log_signal.emit(f"  - 从entries获取分P数量: {page_count}")
                else:
                    # 尝试从标题中推断分P数量
                    title = info.get('title', '')
                    import re
                    p_matches = re.findall(r'[Pp](\d+)', title)
                    if p_matches:
                        max_p = max(int(p) for p in p_matches)
                        page_count = max_p
                        self.log_signal.emit(f"  - 从标题推断分P数量: {page_count}")
            
            self.log_signal.emit(f"🔍 最终确定B站视频有 {page_count} 个分P")
            
            # 如果有entries，直接处理entries而不是重新解析
            if 'entries' in info and info['entries']:
                self.log_signal.emit("🔍 使用entries信息处理B站多P视频")
                self._process_bilibili_entries(info['entries'])
                return
            
            if page_count > 1:
                # 获取基础URL（去掉p参数）
                base_url = self.url.split('?')[0]
                
                # 逐个解析每个分P
                for p_num in range(1, page_count + 1):
                    if self._check_cancelled():
                        return
                    
                    p_url = f"{base_url}?p={p_num}"
                    self.log_signal.emit(f"🔄 解析分P {p_num}/{page_count}: {p_url}")
                    
                    try:
                        # 使用单个视频的解析选项
                        single_video_opts = self._get_single_video_options()
                        single_video_opts["logger"] = YTDlpLogger(self.log_signal)
                        
                        with yt_dlp.YoutubeDL(single_video_opts) as ydl:
                            p_info = ydl.extract_info(p_url, download=False)
                            if p_info:
                                # 修改标题以包含P数信息
                                original_title = p_info.get('title', '未知标题')
                                if f'P{p_num}' not in original_title:
                                    p_info['title'] = f"{original_title} P{p_num}"
                                
                                self.log_signal.emit(f"✅ 成功解析分P {p_num}: {p_info['title']}")
                                
                                # 发送解析完成信号
                                self.progress_signal.emit(p_num, page_count)
                                self.video_parsed_signal.emit(p_info, p_url)
                                
                                # 短暂延迟
                                time.sleep(0.2)
                            else:
                                self.log_signal.emit(f"❌ 解析分P {p_num} 失败")
                    except Exception as e:
                        self.log_signal.emit(f"❌ 解析分P {p_num} 异常: {str(e)}")
                
                # 发送最终完成信号
                self.finished.emit(info)
            else:
                # 只有一个分P，按普通视频处理
                self.log_signal.emit("🔍 只有一个分P，按普通视频处理")
                self.progress_signal.emit(1, 1)
                self.video_parsed_signal.emit(info, self.url)
                self.finished.emit(info)
                
        except Exception as e:
            self.log_signal.emit(f"❌ 处理B站多P视频失败: {str(e)}")
            # 回退到普通处理
            self.progress_signal.emit(1, 1)
            self.video_parsed_signal.emit(info, self.url)
            self.finished.emit(info)
    
    def _process_bilibili_entries(self, entries: list) -> None:
        """处理B站多P视频的entries"""
        try:
            total_entries = len(entries)
            self.log_signal.emit(f"🔍 开始处理B站多P视频entries，共 {total_entries} 个分P")
            
            for i, entry in enumerate(entries):
                if self._check_cancelled():
                    return
                
                if entry:
                    entry_title = entry.get("title", "未知标题")
                    entry_id = entry.get("id", "未知ID")
                    entry_url = entry.get("webpage_url", "")
                    
                    self.log_signal.emit(f"🔍 处理分P {i+1}/{total_entries}: {entry_title}")
                    self.log_signal.emit(f"  - ID: {entry_id}")
                    self.log_signal.emit(f"  - URL: {entry_url}")
                    
                    # 检查是否需要重新解析单个视频以获取格式信息
                    if "formats" not in entry or not entry["formats"]:
                        self.log_signal.emit(f"  - 需要重新解析以获取格式信息")
                        
                        try:
                            # 使用单个视频的解析选项
                            single_video_opts = self._get_single_video_options()
                            single_video_opts["logger"] = YTDlpLogger(self.log_signal)
                            
                            with yt_dlp.YoutubeDL(single_video_opts) as ydl:
                                video_info = ydl.extract_info(entry_url, download=False)
                                if video_info and "formats" in video_info:
                                    entry["formats"] = video_info["formats"]
                                    # 合并其他有用的信息
                                    entry["duration"] = video_info.get("duration", entry.get("duration"))
                                    entry["thumbnail"] = video_info.get("thumbnail", entry.get("thumbnail"))
                                    entry["uploader"] = video_info.get("uploader", entry.get("uploader"))
                                    entry["upload_date"] = video_info.get("upload_date", entry.get("upload_date"))
                                    entry["view_count"] = video_info.get("view_count", entry.get("view_count"))
                                    
                                    # 验证格式信息的有效性
                                    valid_formats = []
                                    for fmt in video_info["formats"]:
                                        if fmt.get("vcodec", "none") != "none" and fmt.get("resolution", "unknown") != "unknown":
                                            valid_formats.append(fmt)
                                    
                                    if valid_formats:
                                        self.log_signal.emit(f"✅ 成功获取格式信息: {len(video_info['formats'])} 个格式，{len(valid_formats)} 个有效")
                                    else:
                                        self.log_signal.emit(f"⚠️ 获取格式信息但无有效格式: {len(video_info['formats'])} 个格式")
                                else:
                                    self.log_signal.emit(f"❌ 无法获取格式信息")
                                    entry["formats"] = []
                        except Exception as e:
                            self.log_signal.emit(f"❌ 重新解析失败: {str(e)}")
                            entry["formats"] = []
                    else:
                        # 验证已有格式信息的有效性
                        valid_formats = []
                        for fmt in entry["formats"]:
                            if fmt.get("vcodec", "none") != "none" and fmt.get("resolution", "unknown") != "unknown":
                                valid_formats.append(fmt)
                        
                        if valid_formats:
                            self.log_signal.emit(f"✅ 已有格式信息: {len(entry['formats'])} 个格式，{len(valid_formats)} 个有效")
                        else:
                            self.log_signal.emit(f"⚠️ 已有格式信息但无有效格式: {len(entry['formats'])} 个格式")
                    
                    # 发送进度信号
                    self.progress_signal.emit(i + 1, total_entries)
                    
                    # 发送视频解析完成信号
                    self.log_signal.emit(f"📤 发送分P解析信号: {entry_title}")
                    self.log_signal.emit(f"🔍 分P信号详情: ID={entry_id}, URL={entry_url}")
                    self.video_parsed_signal.emit(entry, entry_url)
                    
                    # 短暂延迟，避免UI阻塞
                    time.sleep(0.1)
                else:
                    self.log_signal.emit(f"❌ 分P {i+1} 为空，跳过")
            
            # 发送最终完成信号
            self.finished.emit({"entries": entries})
            
        except Exception as e:
            self.log_signal.emit(f"❌ 处理B站entries失败: {str(e)}")
            # 回退到普通处理
            self.progress_signal.emit(1, 1)
            self.finished.emit({"entries": entries})
    
    def pause(self) -> None:
        """暂停解析 - 使用PyQt5线程安全机制"""
        self._mutex.lock()
        try:
            self._paused = True
        finally:
            self._mutex.unlock()
        self.status_signal.emit("解析已暂停")
    
    def resume(self) -> None:
        """恢复解析 - 使用PyQt5线程安全机制"""
        self._mutex.lock()
        try:
            self._paused = False
            self._condition.wakeAll()
        finally:
            self._mutex.unlock()
        self.status_signal.emit("解析已恢复")
    
    def cancel(self) -> None:
        """取消解析 - 使用PyQt5线程安全机制"""
        self._mutex.lock()
        try:
            self._cancelled = True
            self._paused = False
            self._condition.wakeAll()
        finally:
            self._mutex.unlock()
        self.status_signal.emit("正在取消解析...")
        
        # 中断正在进行的提取
        self._interrupt_extraction()
        
        self.quit()
        self.wait()
    
    def _check_pause(self) -> None:
        """检查是否需要暂停 - 使用PyQt5线程安全机制"""
        self._mutex.lock()
        try:
            while self._paused and not self._cancelled:
                self._condition.wait(self._mutex)
        finally:
            self._mutex.unlock()
    
    def _check_cancelled(self) -> bool:
        """检查是否已取消 - 使用PyQt5线程安全机制"""
        self._mutex.lock()
        try:
            return self._cancelled
        finally:
            self._mutex.unlock()
    
    def _check_paused(self) -> bool:
        """检查是否暂停 - 使用PyQt5线程安全机制"""
        self._mutex.lock()
        try:
            return self._paused
        finally:
            self._mutex.unlock()
    
    
