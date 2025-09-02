"""
YouTube 优化器模块

该模块提供针对 YouTube 的优化配置，包括：
- 温和的反检测策略
- 网络参数优化
- 格式选择策略

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import re
import random
from typing import Dict, Any, Optional

class YouTubeOptimizer:
    """YouTube 优化器"""
    
    def __init__(self):
        """初始化优化器"""
        pass
    
    def get_url_type(self, url: str) -> str:
        """获取URL类型"""
        if 'playlist' in url:
            return 'playlist'
        elif 'channel' in url or '/c/' in url or '/user/' in url:
            return 'channel'
        elif 'shorts' in url:
            return 'short'
        else:
            return 'video'
    
    def get_standard_options(self) -> Dict[str, Any]:
        """获取标准配置 - 极限快速解析策略"""
        return {
            # 基本配置
            "quiet": True,  # 静默模式，减少输出
            "no_warnings": True,  # 不显示警告
            "format": "all",  # 解析时获取所有格式
            "merge_output_format": "mp4",
            
            # 极限快速网络配置
            "socket_timeout": 10,  # 进一步减少超时
            "retries": 0,  # 不重试，快速失败
            "fragment_retries": 0,
            "extractor_retries": 0,
            "http_chunk_size": 4194304,  # 4MB，更大的块大小
            "buffersize": 4096,  # 更大的缓冲区
            
            # 优化的请求头 - 避免403错误
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            },
            
            # 格式排序 - 优先获取常用格式
            "format_sort": ["+res", "+fps", "+codec:h264", "+size"],
            "format_sort_force": True,
            
            # 极限解析优化 - 跳过所有不必要的检查
            "skip": ["dash", "live", "hls"],  # 跳过更多格式
            "nocheckcertificate": True,
            "prefer_insecure": True,
            "no_check_certificate": True,
            
            # 跳过格式测试 - 这是关键优化
            "check_formats": False,  # 不检查格式可用性
            "test": False,  # 不测试格式
            
            # 下载配置
            "continuedl": True,
            "noprogress": True,  # 不显示进度
            "ignoreerrors": True,  # 忽略错误
            "no_warnings": True,
        }
    
    def get_optimized_options(self, strategy: str = 'balanced', network_preset: str = 'balanced') -> Dict[str, Any]:
        """获取优化配置"""
        base_opts = self.get_standard_options()
        
        if strategy == 'fast':
            # 快速策略
            base_opts.update({
                "socket_timeout": 20,
                "retries": 2,
                "fragment_retries": 1,
                "extractor_retries": 1,
            })
        elif strategy == 'ultra_fast':
            # 超快速策略
            base_opts.update({
                "socket_timeout": 15,
                "retries": 1,
                "fragment_retries": 1,
                "extractor_retries": 1,
                "http_chunk_size": 2097152,  # 2MB
            })
        elif strategy == 'stable':
            # 稳定策略
            base_opts.update({
                "socket_timeout": 45,
                "retries": 5,
                "fragment_retries": 3,
                "extractor_retries": 3,
            })
        
        return base_opts
    
    def get_extreme_fast_parse_options(self) -> Dict[str, Any]:
        """获取极限快速解析配置 - 跳过格式测试"""
        return {
            # 基本配置
            "quiet": True,
            "no_warnings": True,
            "format": "all",
            "merge_output_format": "mp4",
            
            # 极限快速网络配置
            "socket_timeout": 8,  # 8秒超时
            "retries": 0,  # 不重试
            "fragment_retries": 0,
            "extractor_retries": 0,
            "http_chunk_size": 8388608,  # 8MB
            "buffersize": 8192,  # 8KB缓冲区
            
            # 优化的请求头
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            
            # 极限解析优化
            "skip": ["dash", "live", "hls", "m3u8"],
            "nocheckcertificate": True,
            "prefer_insecure": True,
            "no_check_certificate": True,
            
            # 关键：跳过格式测试
            "check_formats": False,
            "test": False,
            "no_check_formats": True,
            
            # 静默配置
            "continuedl": True,
            "noprogress": True,
            "ignoreerrors": True,
            "no_warnings": True,
        }
    
    def get_ultra_fast_parse_options(self) -> Dict[str, Any]:
        """获取超快速解析配置"""
        return self.get_extreme_fast_parse_options()
    
    def get_playlist_options(self, strategy: str = 'balanced') -> Dict[str, Any]:
        """获取播放列表配置"""
        return self.get_optimized_options(strategy)
    
    def get_channel_options(self, strategy: str = 'balanced') -> Dict[str, Any]:
        """获取频道配置"""
        return self.get_optimized_options(strategy)

    def get_extreme_fast_download_options(self) -> Dict[str, Any]:
        """
        终极绕过策略 - 使用最强大的配置绕过YouTube限制
        """
        return {
            # 基础配置
            "writethumbnail": False,
            "writesubtitles": False,
            "writeautomaticsub": False,

            # 终极网络配置 - 优化速度
            "socket_timeout": 60,
            "retries": 8,
            "fragment_retries": 3,
            "extractor_retries": 2,
            "http_chunk_size": 8388608,  # 8MB - 更大的块大小
            "buffersize": 32768,  # 32KB - 更大的缓冲区

            # 终极headers - 完整浏览器模拟 + 随机化
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,*",
                "Accept-Encoding": "gzip, deflate, br, identity",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Ch-Ua-Arch": '"x86"',
                "Sec-Ch-Ua-Bitness": '"64"',
                "Sec-Ch-Ua-Full-Version": '"120.0.0.0"',
                "Sec-Ch-Ua-Full-Version-List": '"Not_A Brand";v="8.0.0.0", "Chromium";v="120.0.6099.109", "Google Chrome";v="120.0.6099.109"',
                "Referer": "https://www.youtube.com/",
                "Origin": "https://www.youtube.com",
                "Sec-Purpose": "prefetch",
                "DNT": "1",
                "X-Requested-With": "XMLHttpRequest",
            },

            # 终极安全设置
            "nocheckcertificate": True,
            "prefer_insecure": True,

            # 终极地理绕过
            "geo_bypass": True,
            "geo_bypass_country": "US",
            "geo_bypass_ip_block": "1.0.0.1",

            # 代理服务器配置 (如果可用)
            # "proxy": "",  # 将在运行时动态设置

            # 错误处理
            "ignoreerrors": True,
            "ignore_no_formats_error": True,
            "skip_unavailable_fragments": True,

            # 显示进度
            "quiet": False,
            "no_warnings": False,
            "noprogress": False,

            # 高并发下载 - 核心优化
            "concurrent_fragment_downloads": 16,  # 从5增加到16
            "concurrent_fragments": 16,  # 从5增加到16

            # HLS优化参数
            "hls_prefer_native": True,
            "hls_use_mpegts": False,

            # 额外速度优化
            "sleep_interval": 0,
            "max_sleep_interval": 0,
            "sleep_interval_requests": 0,
        }

    def get_proxy_list(self) -> list[str]:
        """获取可用的代理服务器列表"""
        # 这里可以从配置文件或API获取代理列表
        # 暂时返回空列表，用户可以手动配置
        return []

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]
        return random.choice(user_agents)

    def get_ultimate_bypass_options(self, use_proxy: bool = False, custom_proxy: Optional[str] = None) -> Dict[str, Any]:
        """
        获取终极绕过配置 - 包含所有可能的绕过方法
        """
        base_opts = self.get_extreme_fast_download_options()

        # 随机化User-Agent
        base_opts["headers"]["User-Agent"] = self.get_random_user_agent()

        # 添加随机化参数到headers
        base_opts["headers"]["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        base_opts["headers"]["CF-IPCountry"] = random.choice(["US", "CA", "GB", "DE", "FR", "JP", "AU"])

        # 如果使用代理
        if use_proxy and custom_proxy:
            base_opts["proxy"] = custom_proxy
        elif use_proxy:
            proxy_list = self.get_proxy_list()
            if proxy_list:
                base_opts["proxy"] = random.choice(proxy_list)

        # 添加更多的绕过参数
        base_opts.update({
            # 额外的网络配置
            "sleep_interval": 0,
            "max_sleep_interval": 1,
            "sleep_interval_requests": 0,

            # 额外的错误处理
            "extract_flat": False,
            "lazy_playlist": True,
            "playlist_items": "1-100",

            # 额外的安全设置
            "bidi_workaround": True,
            "restrict_filenames": False,
        })

        return base_opts

    def get_high_speed_download_options(self) -> Dict[str, Any]:
        """
        极速下载策略 - 使用最激进的配置实现最快下载速度
        """
        return {
            # 基础配置
            "writethumbnail": False,
            "writesubtitles": False,
            "writeautomaticsub": False,

            # 极速网络配置
            "socket_timeout": 15,  # 更短超时
            "retries": 1,  # 最小重试
            "fragment_retries": 0,  # 不重试片段
            "extractor_retries": 0,  # 不重试解析
            "http_chunk_size": 33554432,  # 32MB - 最大块
            "buffersize": 131072,  # 128KB - 超大缓冲区

            # 优化的极速headers
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",  # 简化语言
                "Accept-Encoding": "gzip, deflate",  # 移除br减少解压开销
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },

            # 极速安全设置
            "nocheckcertificate": True,
            "prefer_insecure": True,

            # 极速地理绕过
            "geo_bypass": True,
            "geo_bypass_country": "US",

            # 极速错误处理
            "ignoreerrors": True,
            "skip_unavailable_fragments": True,

            # 显示进度
            "quiet": False,
            "no_warnings": True,  # 减少输出
            "noprogress": False,

            # 极限并发下载 - 核心优化
            "concurrent_fragment_downloads": 64,  # 64并发下载
            "concurrent_fragments": 64,  # 64并发片段

            # HLS极速优化
            "hls_prefer_native": False,  # 尝试ffmpeg下载器
            "hls_use_mpegts": True,  # 使用MPEG-TS容器
            "external_downloader": "ffmpeg",  # 使用ffmpeg下载器
            "external_downloader_args": {
                "ffmpeg": ["-hide_banner", "-loglevel", "error"]  # 减少ffmpeg输出
            },

            # 极限速度优化
            "sleep_interval": 0,
            "max_sleep_interval": 0,
            "sleep_interval_requests": 0,

            # 额外的极速优化
            "keep_fragments": False,  # 不保留片段
            "no_resize_buffer": True,  # 不调整缓冲区大小
            "prefer_ffmpeg": True,  # 优先使用ffmpeg
            "ffmpeg_location": None,  # 自动查找ffmpeg
        }

    def get_ultra_fast_download_options(self) -> Dict[str, Any]:
        """
        终极极速下载策略 - 牺牲稳定性追求极限速度
        """
        base_opts = self.get_high_speed_download_options()

        # 进一步优化速度参数
        base_opts.update({
            # 终极网络配置
            "socket_timeout": 10,  # 10秒超时
            "http_chunk_size": 67108864,  # 64MB - 极限块大小
            "buffersize": 262144,  # 256KB - 极限缓冲区

            # 终极并发
            "concurrent_fragment_downloads": 128,  # 128并发
            "concurrent_fragments": 128,  # 128并发片段

            # 移除所有不必要的检查
            "check_formats": False,
            "test": False,
            "no_check_formats": True,

            # 最小化输出
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,

            # 终极下载器配置 - 如果aria2c可用则使用，否则使用ffmpeg
            "external_downloader": "ffmpeg",  # 使用ffmpeg作为后备
            "external_downloader_args": {
                "ffmpeg": ["-hide_banner", "-loglevel", "quiet"],
                "aria2c": [
                    "--max-concurrent-downloads=16",
                    "--split=16",
                    "--min-split-size=1M",
                    "--max-connection-per-server=16",
                    "--optimize-concurrent-downloads=true",
                    "--check-certificate=false",
                    "--http-accept-gzip=true"
                ]
            }
        })

        return base_opts

    def get_mobile_client_options(self) -> Dict[str, Any]:
        """
        获取移动客户端配置 - 模拟手机访问
        """
        return {
            "writethumbnail": False,
            "writesubtitles": False,
            "writeautomaticsub": False,

            # 移动客户端网络配置
            "socket_timeout": 60,
            "retries": 8,
            "fragment_retries": 3,
            "http_chunk_size": 1048576,  # 1MB
            "buffersize": 4096,

            # 移动客户端headers
            "headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua-Mobile": "?1",
                "Sec-Ch-Ua-Platform": '"Android"',
            },

            # 移动客户端安全设置
            "nocheckcertificate": True,
            "prefer_insecure": True,

            # 移动客户端地理绕过
            "geo_bypass": True,
            "geo_bypass_country": "US",

            # 错误处理
            "ignoreerrors": True,

            # 显示进度
            "quiet": False,
            "no_warnings": False,
            "noprogress": False,
        }
