"""
播放列表管理模块

该模块负责处理播放列表的解析和管理，包括：
- 播放列表URL的识别和解析
- 播放列表内容的提取
- 批量下载管理
- 播放列表信息显示

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yt_dlp


@dataclass
class PlaylistInfo:
    """播放列表信息数据类"""
    playlist_id: str
    title: str
    description: str
    uploader: str
    video_count: int
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    webpage_url: str = ""
    extractor: str = ""


@dataclass
class PlaylistVideo:
    """播放列表中的视频信息"""
    video_id: str
    title: str
    url: str
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    uploader: str = ""
    view_count: Optional[int] = None
    upload_date: Optional[str] = None


class PlaylistManager:
    """播放列表管理器"""
    
    def __init__(self):
        self.supported_playlist_patterns = {
            'youtube': [
                r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
                r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*list=([a-zA-Z0-9_-]+)',
                r'(?:https?://)?(?:www\.)?youtube\.com/channel/[^/]+/playlists',
            ],
            'bilibili': [
                r'(?:https?://)?(?:www\.)?bilibili\.com/medialist/play/([0-9]+)',
                r'(?:https?://)?(?:www\.)?bilibili\.com/playlist/[0-9]+',
            ],

        }
    
    def is_playlist_url(self, url: str) -> bool:
        """判断是否为播放列表URL"""
        for platform, patterns in self.supported_playlist_patterns.items():
            for pattern in patterns:
                if re.match(pattern, url, re.IGNORECASE):
                    return True
        return False
    
    def get_playlist_info(self, url: str) -> Optional[PlaylistInfo]:
        """获取播放列表信息"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # 只提取基本信息，不下载
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info or 'entries' not in info:
                    return None
                
                return PlaylistInfo(
                    playlist_id=info.get('id', ''),
                    title=info.get('title', ''),
                    description=info.get('description', ''),
                    uploader=info.get('uploader', ''),
                    video_count=len(info.get('entries', [])),
                    duration=info.get('duration'),
                    thumbnail_url=info.get('thumbnail'),
                    webpage_url=info.get('webpage_url', ''),
                    extractor=info.get('extractor', '')
                )
        except Exception as e:
            print(f"获取播放列表信息失败: {e}")
            return None
    
    def get_playlist_videos(self, url: str, limit: Optional[int] = None) -> List[PlaylistVideo]:
        """获取播放列表中的视频列表"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info or 'entries' not in info:
                    return []
                
                videos = []
                entries = info.get('entries', [])
                
                # 限制视频数量
                if limit:
                    entries = entries[:limit]
                
                for entry in entries:
                    if entry:  # 确保条目不为空
                        video = PlaylistVideo(
                            video_id=entry.get('id', ''),
                            title=entry.get('title', ''),
                            url=entry.get('url', ''),
                            duration=entry.get('duration'),
                            thumbnail_url=entry.get('thumbnail'),
                            uploader=entry.get('uploader', ''),
                            view_count=entry.get('view_count'),
                            upload_date=entry.get('upload_date')
                        )
                        videos.append(video)
                
                return videos
        except Exception as e:
            print(f"获取播放列表视频失败: {e}")
            return []
    
    def get_playlist_video_urls(self, url: str, limit: Optional[int] = None) -> List[str]:
        """获取播放列表中所有视频的URL"""
        videos = self.get_playlist_videos(url, limit)
        return [video.url for video in videos if video.url]
    
    def extract_playlist_id(self, url: str) -> Optional[str]:
        """从URL中提取播放列表ID"""
        for platform, patterns in self.supported_playlist_patterns.items():
            for pattern in patterns:
                match = re.match(pattern, url, re.IGNORECASE)
                if match:
                    return match.group(1) if match.groups() else None
        return None
    
    def get_platform_from_url(self, url: str) -> Optional[str]:
        """从URL中识别平台"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'bilibili.com' in url:
            return 'bilibili'

        return None
    
    def validate_playlist_url(self, url: str) -> Tuple[bool, str]:
        """验证播放列表URL的有效性"""
        if not url.strip():
            return False, "URL不能为空"
        
        if not self.is_playlist_url(url):
            return False, "不支持的播放列表URL格式"
        
        platform = self.get_platform_from_url(url)
        if not platform:
            return False, "无法识别的视频平台"
        
        return True, f"支持的{platform}播放列表"
    
    def get_playlist_download_options(self, url: str) -> Dict:
        """获取播放列表下载选项"""
        info = self.get_playlist_info(url)
        if not info:
            return {}
        
        return {
            'playlist_title': info.title,
            'video_count': info.video_count,
            'uploader': info.uploader,
            'platform': self.get_platform_from_url(url),
            'estimated_duration': info.duration,
            'description': info.description[:200] + "..." if len(info.description) > 200 else info.description
        }
    
    def create_playlist_download_tasks(self, url: str, selected_indices: List[int] = None) -> List[Dict]:
        """创建播放列表下载任务"""
        videos = self.get_playlist_videos(url)
        if not videos:
            return []
        
        # 如果指定了索引，只选择指定的视频
        if selected_indices:
            videos = [videos[i] for i in selected_indices if 0 <= i < len(videos)]
        
        tasks = []
        for video in videos:
            task = {
                'url': video.url,
                'title': video.title,
                'video_id': video.video_id,
                'duration': video.duration,
                'uploader': video.uploader,
                'thumbnail_url': video.thumbnail_url
            }
            tasks.append(task)
        
        return tasks
    
    def get_playlist_progress(self, url: str, downloaded_urls: List[str]) -> Dict:
        """获取播放列表下载进度"""
        all_videos = self.get_playlist_videos(url)
        if not all_videos:
            return {'total': 0, 'downloaded': 0, 'remaining': 0, 'progress': 0}
        
        total_count = len(all_videos)
        downloaded_count = len([v for v in all_videos if v.url in downloaded_urls])
        remaining_count = total_count - downloaded_count
        progress = (downloaded_count / total_count * 100) if total_count > 0 else 0
        
        return {
            'total': total_count,
            'downloaded': downloaded_count,
            'remaining': remaining_count,
            'progress': round(progress, 2)
        }


# 全局播放列表管理器实例
playlist_manager = PlaylistManager()
