"""
解析工作线程模块

该模块包含视频解析的工作线程类，负责：
- 异步解析视频URL获取格式信息
- 支持暂停、恢复和取消操作
- 线程安全的信号通信
- 错误处理和状态反馈
- 实时进度反馈和边解析边写入功能

主要类：
- ParseWorker: 视频解析工作线程类

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import time
import threading
import logging
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
import yt_dlp
from src.core.youtube_optimizer import YouTubeOptimizer

class YTDlpLogger:
    """yt-dlp日志记录器，将输出重定向到我们的信号"""
    
    def __init__(self, signal):
        self.signal = signal
    
    def debug(self, msg):
        self.signal.emit(f"[DEBUG] {msg}")
    
    def warning(self, msg):
        self.signal.emit(f"[WARNING] {msg}")
    
    def error(self, msg):
        self.signal.emit(f"[ERROR] {msg}")

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
            elif 'youtube.com' in self.url or 'youtu.be' in self.url:
                timeout_duration = 90  # YouTube中等时间
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
                    # 处理播放列表或频道 - 边解析边发送结果
                    total_entries = len(info['entries'])
                    self.status_signal.emit(f"发现播放列表，包含 {total_entries} 个视频")
                    
                    for i, entry in enumerate(info["entries"]):
                        if self._check_cancelled():
                            return
                        
                        if entry:
                            # 发送进度信号
                            self.progress_signal.emit(i + 1, total_entries)
                            
                            # 检查是否需要重新解析单个视频以获取格式信息
                            if "formats" not in entry or not entry["formats"]:
                                # 重新解析单个视频以获取完整的格式信息
                                video_url = entry.get("webpage_url") or entry.get("url")
                                if video_url:
                                    self.status_signal.emit(f"重新解析视频 {i+1}/{total_entries}: {entry.get('title', 'Unknown')}")
                                    
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
                                            else:
                                                self.status_signal.emit(f"无法获取视频格式信息")
                                    except Exception as e:
                                        self.status_signal.emit(f"重新解析视频失败: {str(e)}")
                                        # 如果重新解析失败，使用空格式列表
                                        entry["formats"] = []
                            
                            # 立即发送单个视频解析完成信号
                            self.video_parsed_signal.emit(entry, self.url)
                            
                            # 短暂延迟，避免UI阻塞
                            time.sleep(0.1)
                    
                    # 发送最终完成信号
                    self.finished.emit(info)
                else:
                    # 单个视频，直接发送结果
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
            # 用户取消解析，不显示错误信息
            self.log_signal.emit(f"解析已取消: {self.url}")
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
            "merge_output_format": "mp4",
            "socket_timeout": 30,  # 适中的超时时间
            "retries": 3,  # 适中的重试次数
            "fragment_retries": 2,  # 片段重试
            "extractor_retries": 2,  # 提取器重试
        }
        
        # 检测平台并添加特定配置
        if 'youtube.com' in self.url or 'youtu.be' in self.url:
            # 使用极限快速的 YouTube 配置 - 跳过格式测试
            youtube_optimizer = YouTubeOptimizer()
            base_opts.update(youtube_optimizer.get_extreme_fast_parse_options())
                
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
    
    def pause(self) -> None:
        """暂停解析"""
        self._mutex.lock()
        self._paused = True
        self._mutex.unlock()
        self.status_signal.emit("解析已暂停")
    
    def resume(self) -> None:
        """恢复解析"""
        self._mutex.lock()
        self._paused = False
        self._condition.wakeAll()
        self._mutex.unlock()
        self.status_signal.emit("解析已恢复")
    
    def cancel(self) -> None:
        """取消解析"""
        self._mutex.lock()
        self._cancelled = True
        self._paused = False
        self._condition.wakeAll()
        self._mutex.unlock()
        self.status_signal.emit("正在取消解析...")
        
        # 中断正在进行的提取
        self._interrupt_extraction()
        
        self.quit()
        self.wait()
    
    def _check_pause(self) -> None:
        """检查是否需要暂停"""
        self._mutex.lock()
        while self._paused and not self._cancelled:
            self._condition.wait(self._mutex)
        self._mutex.unlock()
    
    def _check_cancelled(self) -> bool:
        """检查是否已取消"""
        self._mutex.lock()
        cancelled = self._cancelled
        self._mutex.unlock()
        return cancelled
    
    def _check_paused(self) -> bool:
        """检查是否暂停"""
        self._mutex.lock()
        paused = self._paused
        self._mutex.unlock()
        return paused
