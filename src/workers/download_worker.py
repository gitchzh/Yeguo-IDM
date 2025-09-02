#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载工作线程模块
"""

import os
import time
import random
from typing import Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal
from urllib.parse import urlparse
from src.core.youtube_optimizer import YouTubeOptimizer

class YTDlpLogger:
    """yt-dlp日志记录器，将输出重定向到我们的信号"""
    
    def __init__(self, log_signal):
        self.log_signal = log_signal
    
    def debug(self, msg):
        self.log_signal.emit(f"[DEBUG] {msg}")
    
    def warning(self, msg):
        self.log_signal.emit(f"[WARNING] {msg}")
    
    def error(self, msg):
        self.log_signal.emit(f"[ERROR] {msg}")

class DownloadWorker(QThread):
    """下载工作线程"""
    
    progress_signal = pyqtSignal(dict)  # progress data dictionary
    finished = pyqtSignal(str)  # filename
    error = pyqtSignal(str)  # error message
    log_signal = pyqtSignal(str)  # log message
    
    class DownloadCancelled(Exception):
        pass
    
    class DownloadPaused(Exception):
        pass
    
    def __init__(self, url: str, ydl_opts: Dict, format_id: Optional[str] = None):
        super().__init__()
        self.url = url
        self.ydl_opts = ydl_opts
        self.format_id = format_id
        self._is_cancelled = False
        self._is_paused = False
        self.last_filename = None
        self._start_time = time.time()
    
    def cancel(self):
        """取消下载"""
        self._is_cancelled = True
    
    def pause(self):
        """暂停下载"""
        self._is_paused = True
    
    def resume(self):
        """恢复下载"""
        self._is_paused = False
    
    def progress_hook(self, d: Dict) -> None:
        """下载进度回调"""
        # 检查是否被取消
        if self._is_cancelled:
            return
        
        # 检查是否被暂停
        if self._is_paused:
            # 等待恢复
            while self._is_paused and not self._is_cancelled:
                time.sleep(0.1)  # 短暂休眠，避免CPU占用过高
            if self._is_cancelled:
                return
        
        if d['status'] == 'downloading':
            # 获取文件名
            if 'filename' in d:
                self.last_filename = d['filename']
            
            # 获取进度信息
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            # 计算进度百分比
            if total_bytes > 0:
                progress = (downloaded_bytes / total_bytes) * 100
            else:
                progress = 0
            
            # 计算下载速度
            elapsed_time = time.time() - self._start_time
            if elapsed_time > 0:
                speed = downloaded_bytes / elapsed_time
            else:
                speed = 0
            
            # 格式化速度
            if speed > 1024 * 1024:
                speed_str = f"{speed / (1024 * 1024):.2f} MB/s"
            elif speed > 1024:
                speed_str = f"{speed / 1024:.2f} KB/s"
            else:
                speed_str = f"{speed:.0f} B/s"
            
            # 发送进度信号
            if self.last_filename:
                progress_data = {
                    "status": "downloading",
                    "filename": self.last_filename,
                    "_percent_str": f"{progress:.1f}%",
                    "_speed_str": speed_str
                }
                self.progress_signal.emit(progress_data)
            
            # 发送日志信号
            self.log_signal.emit(f"下载进度: {progress:.1f}% - {speed_str}")
        
        elif d['status'] == 'finished':
            self.log_signal.emit("下载完成，正在处理...")
            # 发送完成信号
            if self.last_filename:
                finished_data = {
                    "status": "finished",
                    "filename": self.last_filename
                }
                self.progress_signal.emit(finished_data)
    
    def run(self):
        """执行下载任务"""
        try:
            self.log_signal.emit(f"开始下载: {self.url}")
            
            # 检查是否为网易云音乐下载
            is_netease_music = "music.163.com" in self.url or "music.126.net" in self.url or "netease" in self.url.lower()
            
            if is_netease_music:
                self._download_netease_music()
            else:
                # 检查是否为YouTube URL
                is_youtube = "youtube.com" in self.url or "youtu.be" in self.url
                
                if is_youtube:
                    self._download_youtube_video()
                else:
                    self._download_general()
                
        except Exception as e:
            error_msg = str(e)
            self.log_signal.emit(f"❌ 下载失败: {error_msg}")
            if not self._is_cancelled:
                self.error.emit(error_msg)
    
    def _download_netease_music(self):
        """专门处理网易云音乐下载"""
        try:
            import yt_dlp
            import requests
            import os
            import time
            
            self.log_signal.emit("开始网易云音乐下载...")
            
            # 检查是否为直接的网易云音乐下载链接
            if "music.126.net" in self.url or "music.163.com" in self.url:
                # 直接下载链接，使用requests下载
                self._download_direct_url()
                return
            
            # 检查是否为直接的音频文件链接（避免重新解析）
            if self.url.endswith('.mp3') or self.url.endswith('.m4a') or 'audio' in self.url.lower():
                # 直接下载音频文件
                self._download_direct_url()
                return
            
            # 如果URL是网易云音乐页面链接，先尝试获取直接下载链接
            if "music.163.com/song" in self.url:
                self.log_signal.emit("检测到网易云音乐页面链接，尝试获取直接下载链接...")
                try:
                    # 从URL中提取歌曲ID
                    import re
                    song_id_match = re.search(r'id=(\d+)', self.url)
                    if song_id_match:
                        song_id = song_id_match.group(1)
                        self.log_signal.emit(f"提取到歌曲ID: {song_id}")
                        
                        # 尝试使用外链重定向获取完整版本
                        outer_url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Referer': 'https://music.163.com/',
                        }
                        
                        response = requests.get(outer_url, headers=headers, allow_redirects=True, timeout=10)
                        
                        if response.status_code == 200:
                            final_url = response.url
                            if '404' not in final_url and 'music.126.net' in final_url:
                                # 检查文件大小
                                try:
                                    head_response = requests.head(final_url, headers=headers, timeout=10)
                                    if head_response.status_code == 200:
                                        content_length = head_response.headers.get('content-length')
                                        if content_length:
                                            file_size = int(content_length)
                                            # 更智能的验证：大于2MB且不是明显的试听版本
                                            if file_size > 2 * 1024 * 1024:  # 大于2MB
                                                self.log_signal.emit(f"VIP绕过成功，获取到完整版本: {file_size}字节")
                                                # 使用获取到的直接下载链接
                                                self.url = final_url
                                                self._download_direct_url()
                                                return
                                            else:
                                                self.log_signal.emit(f"VIP绕过失败，文件太小: {file_size}字节")
                                        else:
                                            self.log_signal.emit("VIP绕过失败，无法获取文件大小")
                                except Exception as e:
                                    self.log_signal.emit(f"VIP绕过验证失败: {e}")
                            else:
                                self.log_signal.emit("VIP绕过失败，重定向到无效页面")
                        else:
                            self.log_signal.emit(f"VIP绕过失败，请求失败: {response.status_code}")
                except Exception as e:
                    self.log_signal.emit(f"VIP绕过尝试失败: {e}")
            
            # 如果VIP绕过失败，继续使用原来的方法
            self.log_signal.emit("VIP绕过失败，使用传统下载方法...")
            
            # 网易云音乐专用配置
            ydl_opts = self.ydl_opts.copy()
            
            # 增强的网易云音乐绕过策略
            ydl_opts.update({
                # 基础配置
                'quiet': False,
                'no_warnings': False,
                
                # 重试配置
                'retries': 20,
                'fragment_retries': 20,
                'extractor_retries': 15,
                'socket_timeout': 180,
                
                # 网络配置
                'http_chunk_size': 10485760,
                'buffersize': 16384,
                'prefer_insecure': True,
                'no_check_certificate': True,
                'nocheckcertificate': True,
                
                # 地理绕过
                'geo_bypass': True,
                'geo_bypass_country': 'CN',
                
                # 下载策略
                'concurrent_fragment_downloads': 3,
                'max_sleep_interval': 10,
                'sleep_interval': 2,
                'retry_sleep': 'exponential',
                
                # 格式选择
                'format': 'best[ext=mp3]/bestaudio[ext=mp3]/best',
                'format_sort': ['ext:mp3:m4a', 'quality', 'filesize'],
                
                # 请求头配置 - 模拟真实浏览器
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                    'Referer': 'https://music.163.com/',
                    'Origin': 'https://music.163.com',
                    'DNT': '1',
                },
                
                # 额外的HTTP头部
                'http_headers': {
                    'Referer': 'https://music.163.com/',
                    'Origin': 'https://music.163.com',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                
                # 进度回调
                'progress_hooks': [self.progress_hook],
                
                # 日志记录器
                'logger': YTDlpLogger(self.log_signal),
            })
            
            # 尝试多种下载策略
            download_strategies = [
                # 策略1: 直接下载
                {'extract_flat': False, 'format': 'best[ext=mp3]/best'},
                # 策略2: 提取信息后下载
                {'extract_flat': True, 'format': 'best[ext=mp3]/best'},
                # 策略3: 强制MP3格式
                {'extract_flat': False, 'format': 'best[ext=mp3]'},
                # 策略4: 最佳音频
                {'extract_flat': False, 'format': 'bestaudio[ext=mp3]/bestaudio'},
                # 策略5: 任何格式
                {'extract_flat': False, 'format': 'best'},
            ]
            
            for i, strategy in enumerate(download_strategies):
                try:
                    self.log_signal.emit(f"尝试网易云音乐下载策略 {i+1}: {strategy['format']}")
                    
                    # 更新策略配置
                    ydl_opts.update(strategy)
                    
                    # 执行下载
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([self.url])
                    
                    # 检查是否真的下载了文件
                    if self.last_filename and os.path.exists(self.last_filename):
                        self.log_signal.emit(f"网易云音乐下载成功: {self.last_filename}")
                        self.finished.emit(self.last_filename)
                        return
                    else:
                        self.log_signal.emit(f"策略 {i+1} 下载完成但文件未找到，尝试下一策略")
                        
                except Exception as e:
                    error_msg = str(e)
                    self.log_signal.emit(f"策略 {i+1} 失败: {error_msg}")
                    
                    # 如果是403错误，等待更长时间
                    if "403" in error_msg or "Forbidden" in error_msg:
                        self.log_signal.emit("检测到403错误，等待5秒后尝试下一策略")
                        time.sleep(5)
                    else:
                        time.sleep(2)
                    
                    continue
            
            # 所有策略都失败了
            raise Exception("所有网易云音乐下载策略都失败了")
            
        except Exception as e:
            error_msg = f"网易云音乐下载失败: {str(e)}"
            self.log_signal.emit(error_msg)
            self.error.emit(error_msg)
    
    def _download_direct_url(self):
        """直接下载网易云音乐链接"""
        try:
            import requests
            import os
            import time
            from urllib.parse import urlparse
            
            self.log_signal.emit("使用直接下载方式...")
            
            # 从ydl_opts中获取输出文件名
            output_file = self.ydl_opts.get("outtmpl", "")
            if not output_file:
                # 如果没有指定输出文件名，生成一个
                filename = f"netease_music_{int(time.time())}.mp3"
                # 使用当前工作目录，但确保目录存在且有写入权限
                output_file = os.path.join(os.getcwd(), filename)
            
            # 确保输出目录存在且有写入权限
            output_dir = os.path.dirname(output_file)
            if output_dir:
                try:
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)
                    # 测试写入权限
                    test_file = os.path.join(output_dir, "test_write.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                except (OSError, PermissionError) as e:
                    # 如果无法写入指定目录，使用用户桌面或文档目录
                    self.log_signal.emit(f"无法写入指定目录: {output_dir}, 错误: {e}")
                    import tempfile
                    output_dir = tempfile.gettempdir()
                    filename = os.path.basename(output_file)
                    output_file = os.path.join(output_dir, filename)
                    self.log_signal.emit(f"改用临时目录: {output_file}")
            
            # 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://music.163.com/',
                'Range': 'bytes=0-',  # 支持断点续传
            }
            
            # 开始下载
            self.log_signal.emit(f"开始下载到: {output_file}")
            
            # 记录开始时间
            start_time = time.time()
            
            with requests.get(self.url, headers=headers, stream=True, timeout=180) as response:
                response.raise_for_status()
                
                # 获取文件大小
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                # 写入文件
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        # 检查是否被取消
                        if self._is_cancelled:
                            self.log_signal.emit("下载已取消")
                            return
                        
                        # 检查是否被暂停
                        if self._is_paused:
                            self.log_signal.emit("下载已暂停")
                            # 等待恢复
                            while self._is_paused and not self._is_cancelled:
                                time.sleep(0.1)  # 短暂休眠，避免CPU占用过高
                            if self._is_cancelled:
                                self.log_signal.emit("下载已取消")
                                return
                            self.log_signal.emit("下载已恢复")
                        
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # 更新进度
                            if total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                elapsed_time = time.time() - start_time
                                if elapsed_time > 0:
                                    speed = downloaded_size / elapsed_time
                                    
                                    # 发送进度信号
                                    progress_data = {
                                        "status": "downloading",
                                        "filename": output_file,
                                        "_percent_str": f"{progress:.1f}%",
                                        "_speed_str": f"{speed/1024/1024:.2f} MB/s"
                                    }
                                    self.progress_signal.emit(progress_data)
                                    
                                    # 更新日志
                                    self.log_signal.emit(f"下载进度: {progress:.1f}% ({downloaded_size}/{total_size} bytes)")
            
            # 检查文件是否下载成功
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                self.log_signal.emit(f"直接下载成功: {output_file}")
                
                # 发送完成信号
                finished_data = {
                    "status": "finished",
                    "filename": output_file
                }
                self.progress_signal.emit(finished_data)
                
                self.finished.emit(output_file)
            else:
                raise Exception("文件下载失败或文件为空")
                
        except Exception as e:
            error_msg = f"直接下载失败: {str(e)}"
            self.log_signal.emit(error_msg)
            self.error.emit(error_msg)
    
    def _download_youtube_video(self):
        """处理YouTube视频下载"""
        try:
            import yt_dlp
            
            # 使用终极绕过策略
            youtube_optimizer = YouTubeOptimizer()

            # 尝试多种策略：终极极速、极速下载、标准、移动客户端、终极绕过
            download_strategies = [
                ("终极极速", youtube_optimizer.get_ultra_fast_download_options()),
                ("极速下载", youtube_optimizer.get_high_speed_download_options()),
                ("标准绕过", youtube_optimizer.get_extreme_fast_download_options()),
                ("移动客户端", youtube_optimizer.get_mobile_client_options()),
                ("终极绕过", youtube_optimizer.get_ultimate_bypass_options()),
            ]

            # 优先使用传入的配置，确保下载路径正确
            for strategy_name, ydl_opts in download_strategies:
                if self.ydl_opts:
                    ydl_opts.update(self.ydl_opts)

                self.log_signal.emit(f"🎯 尝试下载策略: {strategy_name}")

                # 智能格式降级策略
                format_strategies = []

                # 如果有特定格式ID，优先尝试
                if self.format_id:
                    format_strategies.append(self.format_id)
                    self.log_signal.emit(f"格式策略1: 使用指定格式 {self.format_id}")

                # 极速格式策略 - 最快找到可用格式
                format_strategies.extend([
                    "best[ext=mp4]",       # MP4格式 - 最兼容最快 ⭐⭐⭐
                    "best[height>=720]",   # 720P MP4 - 常用高质量 ⭐⭐
                    "best[height>=480]",   # 480P MP4 - 平衡选择 ⭐⭐
                    "best[height>=360]",   # 360P MP4 - 流畅播放 ⭐⭐
                    "bestvideo+bestaudio", # 分离MP4 - 速度最快 ⭐⭐
                    "best",                # 系统最佳 - 通常可用 ⭐
                    "best[height>=1080]",  # 1080P - 高清但可能慢
                    "best[height>=240]",   # 240P - 最低要求
                    "worst",               # 最低质量 - 保底
                    "bestvideo",           # 仅视频 - 备用
                    "bestaudio",           # 仅音频 - 备用
                    "best[ext=webm]",      # WebM - 兼容性差
                    "best[ext=m4a]",       # M4A - 备用音频
                    "best[ext=mp3]"        # MP3 - 最后选择
                ])

                # 尝试不同的格式策略
                max_format_retries = 3  # 减少格式策略重试次数，避免过多重试
                format_retry_count = 0
                
                for i, format_strategy in enumerate(format_strategies):
                    # 检查重试次数限制
                    if format_retry_count >= max_format_retries:
                        self.log_signal.emit(f"达到最大格式策略重试次数 ({max_format_retries})，停止重试")
                        break
                        
                    try:
                        self.log_signal.emit(f"尝试格式策略 {i+1}: {format_strategy}")

                        # 更新格式策略
                        ydl_opts["format"] = format_strategy

                        # 设置进度回调
                        ydl_opts["progress_hooks"] = [self.progress_hook]

                        # 设置自定义日志记录器
                        ydl_opts["logger"] = YTDlpLogger(self.log_signal)
                        
                        # 执行下载
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([self.url])

                        # 检查是否真的下载了文件
                        if self.last_filename and os.path.exists(self.last_filename):
                            self.log_signal.emit(f"✅ {strategy_name} + 格式策略 {i+1} 成功！")
                            if not self._is_cancelled:
                                self.finished.emit(self.last_filename)
                            return
                        else:
                            # 没有下载到文件，继续尝试下一个策略
                            self.log_signal.emit(f"{strategy_name} + 格式策略 {i+1} 失败：没有下载到文件")
                            format_retry_count += 1
                            continue

                    except Exception as e:
                        error_msg = str(e)
                        self.log_signal.emit(f"{strategy_name} + 格式策略 {i+1} 失败: {error_msg}")

                        # 如果是格式不可用错误，继续尝试下一个策略
                        if ("Requested format is not available" in error_msg or
                            "HTTP Error 403" in error_msg or
                            "No video formats found!" in error_msg or
                            "ffmpeg exited with code 1" in error_msg):
                            self.log_signal.emit(f"{strategy_name} + 格式策略 {i+1} 格式不可用，尝试下一个策略...")
                            format_retry_count += 1
                            continue
                        elif "HTTP Error 403" in error_msg:
                            # 403错误通常是访问限制，直接跳过这个策略
                            self.log_signal.emit(f"{strategy_name} + 格式策略 {i+1} 访问被限制 (403)，跳过此策略")
                            format_retry_count += 1
                            continue
                        else:
                            # 其他错误，尝试下一个下载策略
                            self.log_signal.emit(f"{strategy_name} 失败，尝试下一个下载策略...")
                            break

                # 如果所有格式策略都失败，继续尝试下一个下载策略
                else:
                    self.log_signal.emit(f"{strategy_name} 的所有格式策略都失败，继续尝试下一个下载策略...")

            # 所有下载策略都失败了
            raise Exception("所有下载策略都失败了，请稍后重试或尝试其他方法")
            
        except Exception as e:
            error_msg = f"YouTube下载失败: {str(e)}"
            self.log_signal.emit(error_msg)
            self.error.emit(error_msg)
    
    def _download_general(self):
        """处理一般URL下载"""
        try:
            import yt_dlp
            
            # 非YouTube URL使用传入的配置或默认配置
            if self.ydl_opts:
                ydl_opts = self.ydl_opts.copy()
            else:
                ydl_opts = {
                    "format": "best",
                    "outtmpl": "%(title)s.%(ext)s",
                    "socket_timeout": 30,
                    "retries": 3,
                    "http_chunk_size": 1048576,  # 1MB
                    "buffersize": 1024,  # 1KB
                    "quiet": False,
                    "no_warnings": False,
                    "noprogress": False,
                    "ignoreerrors": True,
                }
            
            # 设置进度回调
            ydl_opts["progress_hooks"] = [self.progress_hook]
            
            # 设置自定义日志记录器
            ydl_opts["logger"] = YTDlpLogger(self.log_signal)
            
            # 执行下载
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            self.log_signal.emit("✅ 下载成功！")
            if not self._is_cancelled:
                self.finished.emit(self.last_filename or "")
                
        except Exception as e:
            error_msg = f"一般下载失败: {str(e)}"
            self.log_signal.emit(error_msg)
            self.error.emit(error_msg)
    

