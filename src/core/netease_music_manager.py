"""网易云音乐管理器模块"""

import re
import json
import logging
import time
import random
import hashlib
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode
import requests
from .config import Config
from ..utils.logger import logger


class NetEaseYTDlpLogger:
    """网易云音乐yt-dlp日志记录器，将输出重定向到我们的回调函数"""
    
    def __init__(self, log_callback):
        self.log_callback = log_callback
    
    def debug(self, msg):
        if self.log_callback:
            self.log_callback(f"[DEBUG] {msg}")
    
    def warning(self, msg):
        if self.log_callback:
            self.log_callback(f"[WARNING] {msg}")
    
    def error(self, msg):
        if self.log_callback:
            self.log_callback(f"[ERROR] {msg}")


class NetEaseMusicManager:
    """网易云音乐管理器"""
    
    def __init__(self, log_callback=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://music.163.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        self.log_callback = log_callback  # 状态栏日志回调函数
        self.paused = False  # 暂停状态
        self.cancelled = False  # 取消状态
        
        # VIP绕过策略配置
        self.vip_bypass_config = {
            'min_file_size': 5 * 1024 * 1024,  # 5MB最小文件大小（完整版本应该大于5MB）
            'max_retries': 5,  # 最大重试次数
            'timeout': 20,  # 超时时间
            'enable_advanced_bypass': True,  # 启用高级绕过
        }
        
        # 高级User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 13; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0',
        ]
        
        # 模拟VIP用户的Cookie
        self.vip_cookies = {
            'NMTID': '00O_xxx',
            '_ntes_nnid': 'xxx',
            '_ntes_nuid': 'xxx',
            'MUSIC_U': 'xxx',
            'MUSIC_A': 'xxx',
        }
    
    def pause(self):
        """暂停解析"""
        self.paused = True
        self._log("解析已暂停")
    
    def resume(self):
        """恢复解析"""
        self.paused = False
        self._log("解析已恢复")
    
    def cancel(self):
        """取消解析"""
        self.cancelled = True
        self.paused = False
        self._log("正在取消解析...")
    
    def _check_pause_cancel(self):
        """检查暂停和取消状态"""
        if self.cancelled:
            raise Exception("解析已取消")
        while self.paused and not self.cancelled:
            time.sleep(0.1)  # 短暂等待
        if self.cancelled:
            raise Exception("解析已取消")
    
    def _log(self, message: str, level: str = "INFO"):
        """统一的日志输出方法"""
        # 输出到控制台
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
        # 如果设置了状态栏回调，也输出到状态栏
        if self.log_callback:
            self.log_callback(f"[{level}] {message}")
    
    def get_random_user_agent(self):
        """获取随机User-Agent"""
        return random.choice(self.user_agents)
    
    def get_random_ip(self):
        """获取随机IP地址"""
        return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
    
    def generate_encrypted_params(self, song_id, bitrate=320000):
        """生成加密参数（模拟网易云音乐的加密算法）"""
        try:
            # 模拟网易云音乐的参数加密
            params = {
                'id': song_id,
                'ids': f'[{song_id}]',
                'br': bitrate,
                'csrf_token': '',
                'timestamp': int(time.time() * 1000),
            }
            
            # 添加随机参数增加真实性
            params['random'] = random.randint(100000, 999999)
            params['signature'] = self.generate_signature(params)
            
            return params
        except Exception as e:
            self._log(f"生成加密参数失败: {e}", "ERROR")
            return None
    
    def generate_signature(self, params):
        """生成签名（模拟网易云音乐的签名算法）"""
        try:
            # 模拟签名生成过程
            param_str = urlencode(params)
            # 使用MD5生成签名
            signature = hashlib.md5(param_str.encode('utf-8')).hexdigest()
            return signature
        except Exception as e:
            self._log(f"生成签名失败: {e}", "ERROR")
            return ""
    
    def validate_download_url(self, url, headers):
        """验证下载URL的文件大小"""
        try:
            response = requests.head(url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                content_length = response.headers.get('content-length')
                if content_length:
                    return int(content_length)
        except Exception as e:
            self._log(f"验证URL失败: {e}", "WARNING")
        return None
    
    def is_netease_music_url(self, url: str) -> bool:
        """判断是否为网易云音乐链接"""
        try:
            parsed = urlparse(url)
            return parsed.netloc in ['music.163.com', 'www.music.163.com']
        except Exception as e:
            self._log(f"解析URL失败: {e}", "ERROR")
            return False
    
    def get_url_type(self, url: str) -> str:
        """获取网易云音乐链接类型"""
        try:
            if 'playlist' in url:
                return 'playlist'
            elif 'song' in url:
                return 'song'
            elif 'album' in url:
                return 'album'
            elif 'artist' in url:
                return 'artist'
            else:
                return 'unknown'
        except Exception as e:
            self._log(f"获取URL类型失败: {e}", "ERROR")
            return 'unknown'
    
    def extract_song_id(self, url: str) -> Optional[str]:
        """从网易云音乐URL中提取歌曲ID"""
        try:
            # 匹配多种网易云音乐URL格式
            patterns = [
                r'music\.163\.com/song\?id=(\d+)',
                r'music\.163\.com/#/song\?id=(\d+)',
                r'music\.163\.com/song/(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # 尝试从查询参数中提取
            parsed = urlparse(url)
            if parsed.netloc in ['music.163.com', 'www.music.163.com']:
                query_params = parse_qs(parsed.query)
                if 'id' in query_params:
                    return query_params['id'][0]
            
            return None
        except Exception as e:
            self._log(f"提取歌曲ID失败: {e}", "ERROR")
            return None
    
    def extract_playlist_id(self, url: str) -> Optional[str]:
        """从网易云音乐URL中提取歌单ID"""
        try:
            # 匹配歌单URL格式
            patterns = [
                r'music\.163\.com/playlist\?id=(\d+)',
                r'music\.163\.com/#/playlist\?id=(\d+)',
                r'music\.163\.com/playlist/(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # 尝试从查询参数中提取
            parsed = urlparse(url)
            if parsed.netloc in ['music.163.com', 'www.music.163.com']:
                query_params = parse_qs(parsed.query)
                if 'id' in query_params:
                    return query_params['id'][0]
            
            return None
        except Exception as e:
            self._log(f"提取歌单ID失败: {e}", "ERROR")
            return None
    
    def get_song_info(self, song_id: str) -> Optional[Dict]:
        """获取歌曲信息"""
        try:
            # 检查暂停和取消状态
            self._check_pause_cancel()
            
            self._log(f"开始获取歌曲 {song_id} 信息...")
            
            # 首先尝试使用yt-dlp获取歌曲信息（可以处理付费歌曲和版权限制）
            try:
                import yt_dlp
                
                ydl_opts = {
                    'quiet': False,  # 不静默，让yt-dlp输出日志
                    'no_warnings': False,  # 显示警告
                    'extract_flat': False,
                }
                
                # 如果设置了日志回调，添加自定义日志记录器
                if self.log_callback:
                    ydl_opts['logger'] = NetEaseYTDlpLogger(self.log_callback)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # 构建网易云音乐URL
                    netease_url = f"https://music.163.com/song?id={song_id}"
                    
                    # 检查暂停和取消状态
                    self._check_pause_cancel()
                    
                    # 获取视频信息
                    info = ydl.extract_info(netease_url, download=False)
                    
                    if info:
                        # 尝试获取歌手信息，优先使用artist字段
                        artist = info.get('artist')
                        if not artist:
                            # 如果没有artist字段，尝试从uploader获取
                            artist = info.get('uploader')
                        if not artist:
                            # 如果还是没有，尝试从creator获取
                            artist = info.get('creator')
                        if not artist:
                            # 最后尝试从其他可能包含歌手信息的字段获取
                            artist = info.get('channel', '未知歌手')
                        
                        # 尝试获取文件大小
                        filesize = None
                        if info.get('filesize'):
                            filesize = info['filesize']
                        elif info.get('filesize_approx'):
                            filesize = info['filesize_approx']
                        
                        # 获取下载链接
                        download_url = info.get('url', '')
                        
                        # VIP绕过：如果yt-dlp获取到的是试听版本，尝试获取完整版本
                        if download_url and 'music.126.net' in download_url:
                            # 尝试使用高级VIP绕过策略
                            self._log("检测到试听版本，尝试高级VIP绕过...")
                            
                            # 策略1: 高级API绕过
                            try:
                                self._log("尝试策略1: 高级API绕过...")
                                full_url = self._try_advanced_api_bypass(song_id)
                                if full_url:
                                    download_url = full_url
                                    self._log("✅ 高级API绕过成功，获取到完整版本")
                            except Exception as e:
                                self._log(f"策略1失败: {e}", "WARNING")
                            
                            # 策略2: 高级yt-dlp绕过
                            if download_url == info.get('url', ''):  # 如果还是原来的链接
                                try:
                                    self._log("尝试策略2: 高级yt-dlp绕过...")
                                    full_url = self._try_advanced_ytdlp_bypass(song_id)
                                    if full_url:
                                        download_url = full_url
                                        self._log("✅ 高级yt-dlp绕过成功，获取到完整版本")
                                except Exception as e:
                                    self._log(f"策略2失败: {e}", "WARNING")
                            
                            # 策略3: 高级外部绕过
                            if download_url == info.get('url', ''):  # 如果还是原来的链接
                                try:
                                    self._log("尝试策略3: 高级外部绕过...")
                                    full_url = self._try_advanced_external_bypass(song_id)
                                    if full_url:
                                        download_url = full_url
                                        self._log("✅ 高级外部绕过成功，获取到完整版本")
                                except Exception as e:
                                    self._log(f"策略3失败: {e}", "WARNING")
                            
                            # 策略4: 高级逆向工程
                            if download_url == info.get('url', ''):  # 如果还是原来的链接
                                try:
                                    self._log("尝试策略4: 高级逆向工程...")
                                    full_url = self._try_advanced_reverse_engineering(song_id)
                                    if full_url:
                                        download_url = full_url
                                        self._log("✅ 高级逆向工程成功，获取到完整版本")
                                except Exception as e:
                                    self._log(f"策略4失败: {e}", "WARNING")
                        
                        # 从yt-dlp获取的信息构建歌曲信息
                        song_info = {
                            'id': song_id,
                            'title': info.get('title', '未知歌曲'),
                            'artist': artist,
                            'album': info.get('album', '未知专辑'),
                            'duration': info.get('duration', 0) * 1000 if info.get('duration') else 0,  # 转换为毫秒
                            'download_url': download_url,
                            'cover_url': info.get('thumbnail', ''),
                            'format': 'mp3',
                            'quality': '标准音质',
                            'filesize': filesize
                        }
                        
                        self._log(f"yt-dlp成功获取歌曲 {song_id} 信息: {song_info['title']} - {song_info['artist']}")
                        return song_info
                    
            except Exception as e:
                self._log(f"yt-dlp获取歌曲信息失败: {e}", "WARNING")
            
            # 如果yt-dlp失败，尝试传统的API方法
            try:
                # 网易云音乐API接口
                api_url = f"https://music.163.com/api/song/detail/?id={song_id}&ids=[{song_id}]"
                
                # 添加重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = self.session.get(api_url, timeout=Config.DEFAULT_TIMEOUT)
                        response.raise_for_status()
                        break
                    except requests.RequestException as e:
                        if attempt == max_retries - 1:
                            raise e
                        self._log(f"请求失败，第{attempt + 1}次重试: {e}", "WARNING")
                        time.sleep(1)  # 等待1秒后重试
                
                # 检查响应内容是否为空或无效
                if not response.text.strip():
                    self._log(f"API返回空响应: {api_url}", "ERROR")
                    return None
                
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    self._log(f"JSON解析失败: {e}, 响应内容: {response.text[:200]}", "ERROR")
                    return None
                
                if data.get('code') == 200 and data.get('songs'):
                    song = data['songs'][0]
                    
                    # 获取下载链接
                    download_url = self._get_download_url(song_id)
                    
                    return {
                        'id': song_id,
                        'title': song.get('name', '未知歌曲'),
                        'artist': song.get('artists', [{}])[0].get('name', '未知歌手') if song.get('artists') else '未知歌手',
                        'album': song.get('album', {}).get('name', '未知专辑'),
                        'duration': song.get('duration', 0),
                        'download_url': download_url,
                        'cover_url': song.get('album', {}).get('picUrl', ''),
                        'format': 'mp3',
                        'quality': '标准音质',
                        'filesize': None
                    }
                
            except Exception as e:
                self._log(f"API获取歌曲信息失败: {e}", "WARNING")
            
            # 如果所有方法都失败，返回简化版信息
            self._log(f"无法获取歌曲 {song_id} 的详细信息，返回简化版信息", "WARNING")
            return {
                'id': song_id,
                'title': f'歌曲{song_id}',
                'artist': '未知歌手',
                'album': '未知专辑',
                'duration': 0,
                'download_url': f"https://music.163.com/song?id={song_id}",
                'cover_url': '',
                'format': 'mp3',
                'quality': '标准音质',
                'filesize': None
            }
            
        except Exception as e:
            self._log(f"获取歌曲信息失败: {e}", "ERROR")
            return None
    
    def _try_advanced_api_bypass(self, song_id):
        """尝试高级API绕过策略"""
        try:
            # 模拟VIP用户的完整请求
            vip_headers = {
                'User-Agent': self.get_random_user_agent(),
                'Referer': 'https://music.163.com/',
                'Origin': 'https://music.163.com',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'X-Requested-With': 'XMLHttpRequest',
                'X-Real-IP': self.get_random_ip(),
                'X-Forwarded-For': self.get_random_ip(),
                'CF-IPCountry': random.choice(['CN', 'US', 'JP', 'KR']),
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
            
            # 设置VIP Cookie
            self.session.cookies.update(self.vip_cookies)
            
            # 尝试不同的API端点和参数
            api_endpoints = [
                f"https://music.163.com/api/song/enhance/player/url",
                f"https://music.163.com/api/song/enhance/player/url/v1",
                f"https://music.163.com/api/song/enhance/player/url/v2",
            ]
            
            bitrates = [320000, 192000, 128000, 64000]
            
            for endpoint in api_endpoints:
                for bitrate in bitrates:
                    try:
                        # 生成加密参数
                        params = self.generate_encrypted_params(song_id, bitrate)
                        if not params:
                            continue
                        
                        response = self.session.get(
                            endpoint, 
                            params=params, 
                            headers=vip_headers, 
                            timeout=self.vip_bypass_config['timeout']
                        )
                        
                        if response.status_code == 200:
                            try:
                                data = response.json()
                                if data.get('code') == 200 and data.get('data') and data['data']:
                                    song_data = data['data'][0]
                                    download_url = song_data.get('url')
                                    
                                    if download_url and 'http' in download_url:
                                        # 验证文件大小
                                        file_size = self.validate_download_url(download_url, vip_headers)
                                        if file_size and file_size > self.vip_bypass_config['min_file_size']:
                                            return download_url
                            except json.JSONDecodeError:
                                # API返回加密数据，无法解析
                                continue
                                
                    except Exception as e:
                        continue
                    
                    time.sleep(1)  # 避免请求过快
            
            return None
            
        except Exception as e:
            self._log(f"高级API绕过失败: {e}", "WARNING")
            return None
    
    def _try_advanced_ytdlp_bypass(self, song_id):
        """尝试高级yt-dlp绕过策略"""
        try:
            import yt_dlp
            
            # 构建多种URL格式
            url_formats = [
                f"https://music.163.com/song?id={song_id}",
                f"https://music.163.com/#/song?id={song_id}",
                f"https://music.163.com/song/{song_id}",
                f"https://music.163.com/song?id={song_id}&userid=1",
                f"https://music.163.com/song?id={song_id}&uct2=U2FsdGVkX1+WyJadr4Ig5ppGp+1FQ/zCSSjbdpvug+I=",
            ]
            
            # 高级yt-dlp配置
            advanced_configs = [
                {
                    'name': 'VIP模拟配置',
                    'opts': {
                        'quiet': False,
                        'no_warnings': False,
                        'extract_flat': False,
                        'format': 'best[ext=mp3]/bestaudio[ext=mp3]/best',
                        'format_sort': ['ext:mp3:m4a', 'quality', 'filesize'],
                        'geo_bypass': True,
                        'geo_bypass_country': 'CN',
                        'geo_bypass_ip_block': '1.0.0.1',
                        'headers': {
                            'User-Agent': self.get_random_user_agent(),
                            'Referer': 'https://music.163.com/',
                            'Origin': 'https://music.163.com',
                            'Cookie': '; '.join([f'{k}={v}' for k, v in self.vip_cookies.items()]),
                            'X-Real-IP': self.get_random_ip(),
                            'X-Forwarded-For': self.get_random_ip(),
                        },
                        'socket_timeout': 30,
                        'retries': 10,
                        'fragment_retries': 10,
                        'extractor_retries': 10,
                        'ignoreerrors': False,
                        'no_check_certificate': True,
                        'prefer_insecure': True,
                    }
                },
                {
                    'name': '移动端模拟配置',
                    'opts': {
                        'quiet': False,
                        'no_warnings': False,
                        'extract_flat': False,
                        'format': 'best[ext=mp3]/bestaudio[ext=mp3]/best',
                        'headers': {
                            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                            'Referer': 'https://music.163.com/',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                            'Accept-Encoding': 'gzip, deflate, br',
                            'Connection': 'keep-alive',
                            'Upgrade-Insecure-Requests': '1',
                        },
                        'socket_timeout': 30,
                        'retries': 10,
                    }
                }
            ]
            
            for config in advanced_configs:
                for url_format in url_formats:
                    try:
                        with yt_dlp.YoutubeDL(config['opts']) as ydl:
                            info = ydl.extract_info(url_format, download=False)
                            
                            if info and 'url' in info:
                                download_url = info['url']
                                if download_url and 'music.126.net' in download_url:
                                    # 验证文件大小
                                    file_size = self.validate_download_url(download_url, config['opts']['headers'])
                                    if file_size and file_size > self.vip_bypass_config['min_file_size']:
                                        return download_url
                                        
                    except Exception as e:
                        continue
                    
                    time.sleep(1)
        
        except ImportError:
            self._log("yt-dlp未安装", "WARNING")
        except Exception as e:
            self._log(f"高级yt-dlp绕过失败: {e}", "WARNING")
        
        return None
    
    def _try_advanced_external_bypass(self, song_id):
        """尝试高级外部绕过策略"""
        try:
            # 尝试不同的外链格式
            external_urls = [
                f"https://music.163.com/song/media/outer/url?id={song_id}.mp3",
                f"https://music.163.com/song/media/outer/url?id={song_id}",
                f"https://music.163.com/song/media/outer/url?id={song_id}.m4a",
                f"https://music.163.com/song/media/outer/url?id={song_id}.flac",
                f"https://music.163.com/song/media/outer/url?id={song_id}&br=320000",
                f"https://music.163.com/song/media/outer/url?id={song_id}&br=192000",
            ]
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Referer': 'https://music.163.com/',
                'Accept': 'audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            for url in external_urls:
                try:
                    response = self.session.get(
                        url, 
                        headers=headers, 
                        allow_redirects=True, 
                        timeout=self.vip_bypass_config['timeout']
                    )
                    
                    if response.status_code == 200 and 'music.126.net' in response.url:
                        content_length = response.headers.get('content-length')
                        if content_length:
                            file_size = int(content_length)
                            if file_size > self.vip_bypass_config['min_file_size']:
                                return response.url
                                
                except Exception as e:
                    continue
                
                time.sleep(1)
            
            return None
            
        except Exception as e:
            self._log(f"高级外部绕过失败: {e}", "WARNING")
            return None
    
    def _try_advanced_reverse_engineering(self, song_id):
        """尝试高级逆向工程策略"""
        try:
            # 尝试解析网易云音乐的加密算法
            timestamp = int(time.time() * 1000)
            encrypted_id = hashlib.md5(f"{song_id}{timestamp}".encode()).hexdigest()
            
            api_url = f"https://music.163.com/api/song/enhance/player/url"
            params = {
                'id': song_id,
                'ids': f'[{song_id}]',
                'br': 320000,
                'timestamp': timestamp,
                'signature': encrypted_id[:16],
            }
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Referer': 'https://music.163.com/',
                'Origin': 'https://music.163.com',
                'Accept': 'application/json, text/plain, */*',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            response = self.session.get(api_url, params=params, headers=headers, timeout=self.vip_bypass_config['timeout'])
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('code') == 200 and data.get('data') and data['data']:
                        song_data = data['data'][0]
                        download_url = song_data.get('url')
                        
                        if download_url and 'http' in download_url:
                            file_size = self.validate_download_url(download_url, headers)
                            if file_size and file_size > self.vip_bypass_config['min_file_size']:
                                return download_url
                except Exception as e:
                    # 忽略单个下载链接验证失败
                    self._log(f"下载链接验证失败: {e}", "DEBUG")
            
            return None
            
        except Exception as e:
            self._log(f"高级逆向工程失败: {e}", "WARNING")
            return None
    
    def get_playlist_info(self, playlist_id: str) -> Optional[Dict]:
        """获取歌单信息"""
        try:
            # 首先尝试使用yt-dlp获取歌单信息
            try:
                import yt_dlp
                
                ydl_opts = {
                    'quiet': False,  # 不静默，让yt-dlp输出日志
                    'no_warnings': False,  # 显示警告
                    'extract_flat': True,  # 只提取基本信息，不下载
                }
                
                # 如果设置了日志回调，添加自定义日志记录器
                if self.log_callback:
                    ydl_opts['logger'] = NetEaseYTDlpLogger(self.log_callback)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # 构建网易云音乐歌单URL
                    netease_url = f"https://music.163.com/playlist?id={playlist_id}"
                    
                    # 获取歌单信息
                    info = ydl.extract_info(netease_url, download=False)
                    
                    if info and info.get('entries'):
                        # 从yt-dlp获取的信息构建歌单信息
                        tracks = []
                        for entry in info.get('entries', []):
                            if entry and entry.get('id'):
                                tracks.append({'id': entry['id']})
                        
                        playlist_info = {
                            'id': playlist_id,
                            'name': info.get('title', '未知歌单'),
                            'description': info.get('description', ''),
                            'creator': info.get('uploader', '未知用户'),
                            'track_count': len(tracks),
                            'play_count': 0,
                            'cover_url': info.get('thumbnail', ''),
                            'tracks': tracks
                        }
                        
                        self._log(f"yt-dlp成功获取歌单 {playlist_id} 信息: {playlist_info['name']}")
                        return playlist_info
                    
            except Exception as e:
                self._log(f"yt-dlp获取歌单信息失败: {e}", "WARNING")
            
            # 如果yt-dlp失败，返回简化版信息
            self._log(f"无法获取歌单 {playlist_id} 的详细信息，返回简化版信息", "WARNING")
            return {
                'id': playlist_id,
                'name': f'歌单{playlist_id}',
                'description': '',
                'creator': '未知用户',
                'track_count': 0,
                'play_count': 0,
                'cover_url': '',
                'tracks': []
            }
            
        except Exception as e:
            self._log(f"获取歌单信息失败: {e}", "ERROR")
            return None
    
    def parse_netease_music(self, url: str) -> Optional[Dict]:
        """解析网易云音乐链接"""
        try:
            if not self.is_netease_music_url(url):
                return None
            
            url_type = self.get_url_type(url)
            
            if url_type == 'song':
                return self._parse_song_url(url)
            elif url_type == 'playlist':
                return self._parse_playlist_url(url)
            else:
                self._log(f"不支持的网易云音乐链接类型: {url_type}", "ERROR")
                return None
                
        except Exception as e:
            self._log(f"解析网易云音乐失败: {e}", "ERROR")
            return None
    
    def _parse_song_url(self, url: str) -> Optional[Dict]:
        """解析单个歌曲链接"""
        try:
            song_id = self.extract_song_id(url)
            if not song_id:
                self._log("无法从URL中提取歌曲ID", "ERROR")
                return None
            
            self._log(f"正在解析网易云音乐歌曲ID: {song_id}")
            
            song_info = self.get_song_info(song_id)
            if not song_info:
                self._log("获取歌曲信息失败", "ERROR")
                return None
            
            self._log(f"成功解析歌曲: {song_info['title']} - {song_info['artist']}")
            
            return {
                'type': 'song',
                'song_info': song_info,
                'original_url': url
            }
        except Exception as e:
            self._log(f"解析歌曲链接失败: {e}", "ERROR")
            return None
    
    def _parse_playlist_url(self, url: str) -> Optional[Dict]:
        """解析歌单链接"""
        try:
            playlist_id = self.extract_playlist_id(url)
            if not playlist_id:
                self._log("无法从URL中提取歌单ID", "ERROR")
                return None
            
            self._log(f"正在解析网易云音乐歌单ID: {playlist_id}")
            
            playlist_info = self.get_playlist_info(playlist_id)
            if not playlist_info:
                self._log("获取歌单信息失败", "ERROR")
                return None
            
            self._log(f"成功解析歌单: {playlist_info['name']} (共{playlist_info['track_count']}首歌曲)")
            
            return {
                'type': 'playlist',
                'playlist_info': playlist_info,
                'original_url': url
            }
        except Exception as e:
            self._log(f"解析歌单链接失败: {e}", "ERROR")
            return None
    
    def get_playlist_songs(self, playlist_info: Dict) -> List[Dict]:
        """获取歌单中的所有歌曲信息"""
        songs = []
        
        try:
            tracks = playlist_info.get('tracks', [])
            
            for i, track in enumerate(tracks):
                try:
                    # 检查暂停和取消状态
                    self._check_pause_cancel()
                    
                    song_id = str(track.get('id', ''))
                    if not song_id:
                        continue
                    
                    # 获取歌曲详细信息
                    song_info = self.get_song_info(song_id)
                    if song_info:
                        songs.append(song_info)
                    
                    # 添加延迟避免请求过快
                    if i > 0 and i % 3 == 0:
                        time.sleep(0.3)
                        
                except Exception as e:
                    self._log(f"获取歌单歌曲 {i+1} 信息失败: {e}", "ERROR")
                    continue
            
            self._log(f"成功获取歌单中的 {len(songs)} 首歌曲信息")
            return songs
            
        except Exception as e:
            self._log(f"获取歌单歌曲列表失败: {e}", "ERROR")
            return []
    
    def get_formats(self, song_info: Dict) -> List[Dict]:
        """获取可用的下载格式"""
        formats = []
        
        if song_info.get('download_url'):
            formats.append({
                'format_id': 'mp3',
                'ext': 'mp3',
                'format': 'MP3',
                'filesize': song_info.get('filesize'),  # 使用从yt-dlp获取的文件大小
                'url': song_info['download_url'],
                'title': song_info['title'],
                'artist': song_info['artist'],
                'album': song_info['album'],
                'duration': song_info['duration'],
                'quality': song_info['quality']
            })
        
        return formats
    
    def _get_download_url(self, song_id: str) -> Optional[str]:
        """获取歌曲下载链接"""
        try:
            # 首先尝试使用yt-dlp获取下载链接（可以处理付费歌曲）
            try:
                import yt_dlp
                
                ydl_opts = {
                    'quiet': False,  # 不静默，让yt-dlp输出日志
                    'no_warnings': False,  # 显示警告
                    'extract_flat': False,
                }
                
                # 如果设置了日志回调，添加自定义日志记录器
                if self.log_callback:
                    ydl_opts['logger'] = NetEaseYTDlpLogger(self.log_callback)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # 构建网易云音乐URL
                    netease_url = f"https://music.163.com/song?id={song_id}"
                    
                    # 获取视频信息
                    info = ydl.extract_info(netease_url, download=False)
                    
                    if info and 'url' in info:
                        download_url = info['url']
                        if download_url and 'http' in download_url:
                            self._log(f"yt-dlp成功获取歌曲 {song_id} 的下载链接")
                            return download_url
                    
            except Exception as e:
                self._log(f"yt-dlp获取下载链接失败: {e}", "WARNING")
            
            # 如果yt-dlp失败，尝试传统的API方法
            api_urls = [
                f"https://music.163.com/api/song/enhance/player/url?id={song_id}&ids=[{song_id}]&br=320000",
                f"https://music.163.com/api/song/enhance/player/url?id={song_id}&ids=[{song_id}]&br=128000",
                f"https://music.163.com/api/song/enhance/player/url?id={song_id}&ids=[{song_id}]&br=64000",
            ]
            
            for api_url in api_urls:
                try:
                    # 添加重试机制
                    max_retries = 3
                    response = None
                    for attempt in range(max_retries):
                        try:
                            response = self.session.get(api_url, timeout=Config.DEFAULT_TIMEOUT)
                            break
                        except requests.RequestException as e:
                            if attempt == max_retries - 1:
                                raise e
                            self._log(f"API请求失败，第{attempt + 1}次重试: {e}", "WARNING")
                            time.sleep(1)  # 等待1秒后重试
                    
                    if response and response.status_code == 200:
                        # 检查响应内容是否为空或无效
                        if not response.text.strip():
                            self._log(f"API返回空响应: {api_url}", "WARNING")
                            continue
                        
                        try:
                            data = response.json()
                        except json.JSONDecodeError as e:
                            self._log(f"JSON解析失败: {e}, 响应内容: {response.text[:200]}", "WARNING")
                            continue
                        
                        if data.get('code') == 200 and data.get('data') and data['data']:
                            song_data = data['data'][0]
                            download_url = song_data.get('url')
                            
                            if download_url and 'http' in download_url:
                                self._log(f"API成功获取歌曲 {song_id} 的下载链接")
                                return download_url
                            else:
                                # 检查是否为付费歌曲
                                if song_data.get('fee') == 1:
                                    self._log(f"歌曲 {song_id} 是付费歌曲，API无法获取下载链接", "WARNING")
                                elif song_data.get('code') == -110:
                                    self._log(f"歌曲 {song_id} 版权受限，API无法获取下载链接", "WARNING")
                                else:
                                    self._log(f"API返回的下载链接无效: {download_url}", "WARNING")
                        else:
                            self._log(f"API返回错误: {data.get('code')} - {data.get('msg', '未知错误')}", "WARNING")
                    else:
                        self._log(f"API请求失败，状态码: {response.status_code}", "WARNING")
                        
                except Exception as e:
                    self._log(f"API请求异常: {e}", "ERROR")
                    continue
            
            # 如果所有方法都失败，尝试使用外链地址
            self._log(f"无法通过yt-dlp和API获取歌曲 {song_id} 的下载链接，尝试使用外链", "WARNING")
            
            # 尝试直接访问外链，看是否能获取到真实链接
            outer_url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
            
            try:
                # 添加重试机制
                max_retries = 3
                response = None
                for attempt in range(max_retries):
                    try:
                        response = self.session.get(outer_url, allow_redirects=True, timeout=Config.DEFAULT_TIMEOUT)
                        break
                    except requests.RequestException as e:
                        if attempt == max_retries - 1:
                            raise e
                        self._log(f"外链请求失败，第{attempt + 1}次重试: {e}", "WARNING")
                        time.sleep(1)  # 等待1秒后重试
                
                # 检查最终URL是否不是404页面
                final_url = response.url
                if '404' not in final_url and response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'audio' in content_type or 'mp3' in content_type:
                        self._log(f"外链重定向成功，最终URL: {final_url}")
                        return final_url
                    else:
                        self._log(f"外链重定向到非音频文件: {final_url}, Content-Type: {content_type}", "WARNING")
                else:
                    self._log(f"外链重定向到404页面: {final_url}", "WARNING")
                    
            except Exception as e:
                self._log(f"外链请求异常: {e}", "ERROR")
            
            # 如果所有方法都失败，返回None
            self._log(f"无法获取歌曲 {song_id} 的有效下载链接", "ERROR")
            return None
            
        except Exception as e:
            self._log(f"获取下载链接失败: {e}", "ERROR")
            return None
