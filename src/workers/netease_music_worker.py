"""网易云音乐解析工作线程模块"""

import logging
from typing import Dict, List, Optional
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition

from ..core.netease_music_manager import NetEaseMusicManager

logger = logging.getLogger("VideoDownloader")


class NetEaseMusicParseWorker(QThread):
    """网易云音乐解析工作线程"""
    
    # 信号定义
    progress_signal = pyqtSignal(str)  # 进度信号
    music_parsed_signal = pyqtSignal(dict)  # 音乐解析完成信号
    error_signal = pyqtSignal(str)  # 错误信号
    finished_signal = pyqtSignal()  # 完成信号
    log_signal = pyqtSignal(str)  # 日志信号，用于状态栏显示
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        # 传递日志回调函数给NetEaseMusicManager
        self.netease_manager = NetEaseMusicManager(log_callback=self.log_signal.emit)
        
        # 线程控制
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.paused = False
        self.cancelled = False
    
    def run(self):
        """运行解析任务"""
        try:
            self.log_signal.emit("开始解析网易云音乐链接...")
            self.progress_signal.emit("开始解析网易云音乐链接...")
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            # 检查是否为网易云音乐链接
            if not self.netease_manager.is_netease_music_url(self.url):
                error_msg = "不是有效的网易云音乐链接"
                self.log_signal.emit(error_msg)
                self.error_signal.emit(error_msg)
                return
            
            # 获取URL类型
            url_type = self.netease_manager.get_url_type(self.url)
            self.log_signal.emit(f"检测到链接类型: {url_type}")
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            if url_type == 'song':
                self._parse_song()
            elif url_type == 'playlist':
                self._parse_playlist()
            else:
                error_msg = f"不支持的网易云音乐链接类型: {url_type}"
                self.log_signal.emit(error_msg)
                self.error_signal.emit(error_msg)
                return
            
        except Exception as e:
            error_msg = f"网易云音乐解析失败: {e}"
            logger.error(error_msg)
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
        finally:
            self.finished_signal.emit()
    
    def _parse_song(self):
        """解析单个歌曲"""
        try:
            self.log_signal.emit("正在解析单个歌曲...")
            self.progress_signal.emit("正在提取歌曲ID...")
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            # 解析歌曲
            result = self.netease_manager.parse_netease_music(self.url)
            if not result or result.get('type') != 'song':
                error_msg = "解析歌曲失败"
                self.log_signal.emit(error_msg)
                self.error_signal.emit(error_msg)
                return
            
            song_info = result['song_info']
            self.log_signal.emit(f"成功解析歌曲: {song_info['title']} - {song_info['artist']}")
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            self.log_signal.emit("正在获取下载格式...")
            
            # 获取可用格式
            formats = self.netease_manager.get_formats(song_info)
            if not formats:
                error_msg = "无法获取下载格式"
                self.log_signal.emit(error_msg)
                self.error_signal.emit(error_msg)
                return
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            self.log_signal.emit("歌曲解析完成")
            
            # 发送解析结果
            result_data = {
                'type': 'netease_music_song',
                'title': song_info['title'],
                'artist': song_info['artist'],
                'album': song_info['album'],
                'duration': song_info['duration'],
                'cover_url': song_info.get('cover_url', ''),
                'formats': formats,
                'original_url': self.url,
                'song_id': song_info['id']
            }
            
            self.music_parsed_signal.emit(result_data)
            
        except Exception as e:
            # 检查是否是取消异常
            if "解析已取消" in str(e):
                self.log_signal.emit("解析已取消")
                return
            error_msg = f"解析歌曲失败: {e}"
            logger.error(error_msg)
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
    
    def _parse_playlist(self):
        """解析歌单"""
        try:
            self.log_signal.emit("正在解析歌单...")
            self.progress_signal.emit("正在提取歌单ID...")
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            # 解析歌单
            result = self.netease_manager.parse_netease_music(self.url)
            if not result or result.get('type') != 'playlist':
                error_msg = "解析歌单失败"
                self.log_signal.emit(error_msg)
                self.error_signal.emit(error_msg)
                return
            
            playlist_info = result['playlist_info']
            self.log_signal.emit(f"成功解析歌单: {playlist_info['name']} (共{playlist_info['track_count']}首歌曲)")
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            self.log_signal.emit("正在获取歌单中的歌曲信息...")
            
            # 获取歌单中的所有歌曲
            songs = self.netease_manager.get_playlist_songs(playlist_info)
            if not songs:
                error_msg = "无法获取歌单中的歌曲信息"
                self.log_signal.emit(error_msg)
                self.error_signal.emit(error_msg)
                return
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            self.log_signal.emit(f"成功获取 {len(songs)} 首歌曲信息")
            
            # 为每首歌曲创建格式信息
            all_formats = []
            for i, song in enumerate(songs):
                try:
                    # 检查是否取消
                    if self._check_cancelled():
                        return
                    
                    self.log_signal.emit(f"正在处理第 {i+1}/{len(songs)} 首歌曲: {song['title']}")
                    
                    formats = self.netease_manager.get_formats(song)
                    if formats:
                        # 为每个格式添加歌曲信息
                        for fmt in formats:
                            fmt.update({
                                'song_title': song['title'],
                                'song_artist': song['artist'],
                                'song_album': song['album'],
                                'song_duration': song['duration'],
                                'song_id': song['id'],
                                'playlist_name': playlist_info['name'],
                                'playlist_creator': playlist_info['creator']
                            })
                        all_formats.extend(formats)
                    
                    # 添加延迟避免请求过快
                    if i > 0 and i % 5 == 0:
                        self.log_signal.emit("处理中，请稍候...")
                        
                except Exception as e:
                    logger.error(f"处理歌曲 {song.get('title', '未知')} 失败: {e}")
                    continue
            
            if not all_formats:
                error_msg = "无法获取任何歌曲的下载格式"
                self.log_signal.emit(error_msg)
                self.error_signal.emit(error_msg)
                return
            
            # 检查是否取消
            if self._check_cancelled():
                return
            
            self.log_signal.emit("歌单解析完成")
            
            # 发送解析结果
            result_data = {
                'type': 'netease_music_playlist',
                'playlist_name': playlist_info['name'],
                'playlist_creator': playlist_info['creator'],
                'playlist_description': playlist_info.get('description', ''),
                'track_count': playlist_info['track_count'],
                'play_count': playlist_info['play_count'],
                'cover_url': playlist_info.get('cover_url', ''),
                'formats': all_formats,
                'original_url': self.url,
                'playlist_id': playlist_info['id'],
                'songs': songs
            }
            
            self.music_parsed_signal.emit(result_data)
            
        except Exception as e:
            # 检查是否是取消异常
            if "解析已取消" in str(e):
                self.log_signal.emit("解析已取消")
                return
            error_msg = f"解析歌单失败: {e}"
            logger.error(error_msg)
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
    
    def pause(self):
        """暂停解析"""
        self.mutex.lock()
        self.paused = True
        self.mutex.unlock()
        # 同时暂停 NetEaseMusicManager
        if hasattr(self, 'netease_manager'):
            self.netease_manager.pause()
        self.log_signal.emit("解析已暂停")
        self.progress_signal.emit("解析已暂停")
    
    def resume(self):
        """恢复解析"""
        self.mutex.lock()
        self.paused = False
        self.wait_condition.wakeAll()
        self.mutex.unlock()
        # 同时恢复 NetEaseMusicManager
        if hasattr(self, 'netease_manager'):
            self.netease_manager.resume()
        self.log_signal.emit("解析已恢复")
        self.progress_signal.emit("解析已恢复")
    
    def cancel(self):
        """取消解析"""
        self.mutex.lock()
        self.cancelled = True
        self.paused = False
        self.wait_condition.wakeAll()
        self.mutex.unlock()
        # 同时取消 NetEaseMusicManager
        if hasattr(self, 'netease_manager'):
            self.netease_manager.cancel()
        self.log_signal.emit("正在取消解析...")
        self.progress_signal.emit("正在取消解析...")
        self.quit()
        self.wait()
    
    def _check_cancelled(self):
        """检查是否被取消或暂停"""
        self.mutex.lock()
        if self.cancelled:
            self.mutex.unlock()
            return True
        
        while self.paused and not self.cancelled:
            self.wait_condition.wait(self.mutex)
        
        cancelled = self.cancelled
        self.mutex.unlock()
        
        # 检查 NetEaseMusicManager 是否被取消
        if hasattr(self, 'netease_manager') and self.netease_manager.cancelled:
            return True
            
        return cancelled
