"""
字幕管理模块

该模块负责处理字幕下载和管理，包括：
- 字幕格式的识别和下载
- 字幕文件的格式转换
- 字幕的预览和选择
- 字幕文件的保存和管理

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal


@dataclass
class SubtitleInfo:
    """字幕信息数据类"""
    language: str
    language_code: str
    format: str  # vtt, srt, ass等
    url: str
    name: str = ""
    is_auto: bool = False  # 是否为自动生成的字幕


class SubtitleDownloader(QThread):
    """字幕下载线程"""
    
    download_finished = pyqtSignal(str, str)  # language_code, subtitle_path
    download_failed = pyqtSignal(str, str)    # language_code, error_message
    
    def __init__(self, url: str, subtitle_info: SubtitleInfo, save_path: str):
        super().__init__()
        self.url = url
        self.subtitle_info = subtitle_info
        self.save_path = save_path
    
    def run(self):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [self.subtitle_info.language_code],
                'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                'skip_download': True,  # 只下载字幕，不下载视频
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            # 查找下载的字幕文件
            subtitle_path = self._find_subtitle_file()
            if subtitle_path:
                self.download_finished.emit(self.subtitle_info.language_code, subtitle_path)
            else:
                self.download_failed.emit(self.subtitle_info.language_code, "未找到字幕文件")
                
        except Exception as e:
            self.download_failed.emit(self.subtitle_info.language_code, str(e))
    
    def _find_subtitle_file(self) -> Optional[str]:
        """查找下载的字幕文件"""
        for filename in os.listdir(self.save_path):
            if filename.endswith(f'.{self.subtitle_info.language_code}.{self.subtitle_info.format}'):
                return os.path.join(self.save_path, filename)
        return None


class SubtitleManager:
    """字幕管理器"""
    
    def __init__(self):
        self.supported_formats = ['vtt', 'srt', 'ass', 'ssa', 'ttml']
        self.language_names = {
            'en': '英语',
            'zh': '中文',
            'zh-CN': '简体中文',
            'zh-TW': '繁体中文',
            'ja': '日语',
            'ko': '韩语',
            'fr': '法语',
            'de': '德语',
            'es': '西班牙语',
            'ru': '俄语',
            'ar': '阿拉伯语',
            'pt': '葡萄牙语',
            'it': '意大利语',
            'nl': '荷兰语',
            'sv': '瑞典语',
            'no': '挪威语',
            'da': '丹麦语',
            'fi': '芬兰语',
            'pl': '波兰语',
            'tr': '土耳其语',
            'hi': '印地语',
            'th': '泰语',
            'vi': '越南语',
            'id': '印尼语',
            'ms': '马来语',
            'fa': '波斯语',
            'he': '希伯来语',
            'uk': '乌克兰语',
            'cs': '捷克语',
            'hu': '匈牙利语',
            'ro': '罗马尼亚语',
            'bg': '保加利亚语',
            'hr': '克罗地亚语',
            'sk': '斯洛伐克语',
            'sl': '斯洛文尼亚语',
            'et': '爱沙尼亚语',
            'lv': '拉脱维亚语',
            'lt': '立陶宛语',
            'mt': '马耳他语',
            'ga': '爱尔兰语',
            'cy': '威尔士语',
            'eu': '巴斯克语',
            'ca': '加泰罗尼亚语',
            'gl': '加利西亚语',
            'is': '冰岛语',
            'mk': '马其顿语',
            'sq': '阿尔巴尼亚语',
            'sr': '塞尔维亚语',
            'bs': '波斯尼亚语',
            'me': '黑山语',
            'ka': '格鲁吉亚语',
            'hy': '亚美尼亚语',
            'az': '阿塞拜疆语',
            'kk': '哈萨克语',
            'ky': '吉尔吉斯语',
            'uz': '乌兹别克语',
            'tg': '塔吉克语',
            'mn': '蒙古语',
            'ne': '尼泊尔语',
            'si': '僧伽罗语',
            'my': '缅甸语',
            'km': '高棉语',
            'lo': '老挝语',
            'ka': '格鲁吉亚语',
            'am': '阿姆哈拉语',
            'sw': '斯瓦希里语',
            'zu': '祖鲁语',
            'af': '南非荷兰语',
            'xh': '科萨语',
            'st': '南索托语',
            'tn': '茨瓦纳语',
            'ts': '聪加语',
            've': '文达语',
            'nr': '南恩德贝莱语',
            'ss': '斯威士语',
            'sn': '绍纳语',
            'ny': '奇切瓦语',
            'rw': '卢旺达语',
            'lg': '干达语',
            'ak': '阿坎语',
            'yo': '约鲁巴语',
            'ig': '伊博语',
            'ha': '豪萨语',
            'so': '索马里语',
            'om': '奥罗莫语',
            'ti': '提格里尼亚语',
            'or': '奥里亚语',
            'as': '阿萨姆语',
            'bn': '孟加拉语',
            'gu': '古吉拉特语',
            'pa': '旁遮普语',
            'te': '泰卢固语',
            'kn': '卡纳达语',
            'ml': '马拉雅拉姆语',
            'ta': '泰米尔语',
            'ur': '乌尔都语',
            'ps': '普什图语',
            'sd': '信德语',
            'bo': '藏语',
            'dz': '宗卡语',
            'my': '缅甸语',
            'ka': '格鲁吉亚语',
            'hy': '亚美尼亚语',
            'az': '阿塞拜疆语',
            'kk': '哈萨克语',
            'ky': '吉尔吉斯语',
            'uz': '乌兹别克语',
            'tg': '塔吉克语',
            'mn': '蒙古语',
            'ne': '尼泊尔语',
            'si': '僧伽罗语',
            'my': '缅甸语',
            'km': '高棉语',
            'lo': '老挝语',
        }
    
    def get_available_subtitles(self, url: str) -> List[SubtitleInfo]:
        """获取可用的字幕列表"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'listsubtitles': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return []
                
                subtitles = []
                
                # 处理手动字幕
                if 'subtitles' in info:
                    for lang_code, lang_subtitles in info['subtitles'].items():
                        for subtitle in lang_subtitles:
                            subtitle_info = SubtitleInfo(
                                language=self._get_language_name(lang_code),
                                language_code=lang_code,
                                format=subtitle.get('ext', 'vtt'),
                                url=subtitle.get('url', ''),
                                name=subtitle.get('name', ''),
                                is_auto=False
                            )
                            subtitles.append(subtitle_info)
                
                # 处理自动生成字幕
                if 'automatic_captions' in info:
                    for lang_code, lang_subtitles in info['automatic_captions'].items():
                        for subtitle in lang_subtitles:
                            subtitle_info = SubtitleInfo(
                                language=f"{self._get_language_name(lang_code)} (自动)",
                                language_code=lang_code,
                                format=subtitle.get('ext', 'vtt'),
                                url=subtitle.get('url', ''),
                                name=subtitle.get('name', ''),
                                is_auto=True
                            )
                            subtitles.append(subtitle_info)
                
                return subtitles
                
        except Exception as e:
            print(f"获取字幕列表失败: {e}")
            return []
    
    def _get_language_name(self, language_code: str) -> str:
        """获取语言名称"""
        return self.language_names.get(language_code, language_code)
    
    def download_subtitle(self, url: str, subtitle_info: SubtitleInfo, save_path: str) -> SubtitleDownloader:
        """下载字幕"""
        downloader = SubtitleDownloader(url, subtitle_info, save_path)
        return downloader
    
    def convert_subtitle_format(self, input_path: str, output_format: str) -> Optional[str]:
        """转换字幕格式"""
        try:
            if not os.path.exists(input_path):
                return None
            
            # 读取原字幕文件
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 根据输入格式解析内容
            if input_path.endswith('.vtt'):
                parsed_content = self._parse_vtt(content)
            elif input_path.endswith('.srt'):
                parsed_content = self._parse_srt(content)
            else:
                return None
            
            # 转换为目标格式
            if output_format == 'srt':
                converted_content = self._convert_to_srt(parsed_content)
            elif output_format == 'vtt':
                converted_content = self._convert_to_vtt(parsed_content)
            else:
                return None
            
            # 保存转换后的文件
            output_path = input_path.rsplit('.', 1)[0] + f'.{output_format}'
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(converted_content)
            
            return output_path
            
        except Exception as e:
            print(f"转换字幕格式失败: {e}")
            return None
    
    def _parse_vtt(self, content: str) -> List[Dict]:
        """解析VTT格式字幕"""
        subtitles = []
        lines = content.strip().split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过WEBVTT头部
            if line.startswith('WEBVTT'):
                i += 1
                continue
            
            # 跳过空行
            if not line:
                i += 1
                continue
            
            # 解析时间戳
            if '-->' in line:
                time_parts = line.split(' --> ')
                if len(time_parts) == 2:
                    start_time = self._parse_vtt_time(time_parts[0])
                    end_time = self._parse_vtt_time(time_parts[1])
                    
                    # 收集字幕文本
                    text_lines = []
                    i += 1
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    subtitle = {
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': '\n'.join(text_lines)
                    }
                    subtitles.append(subtitle)
            
            i += 1
        
        return subtitles
    
    def _parse_srt(self, content: str) -> List[Dict]:
        """解析SRT格式字幕"""
        subtitles = []
        blocks = content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # 跳过序号
                time_line = lines[1]
                if ' --> ' in time_line:
                    time_parts = time_line.split(' --> ')
                    if len(time_parts) == 2:
                        start_time = self._parse_srt_time(time_parts[0])
                        end_time = self._parse_srt_time(time_parts[1])
                        
                        # 收集字幕文本
                        text_lines = lines[2:]
                        subtitle = {
                            'start_time': start_time,
                            'end_time': end_time,
                            'text': '\n'.join(text_lines)
                        }
                        subtitles.append(subtitle)
        
        return subtitles
    
    def _parse_vtt_time(self, time_str: str) -> int:
        """解析VTT时间格式"""
        # VTT格式: HH:MM:SS.mmm
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        
        return hours * 3600000 + minutes * 60000 + seconds * 1000 + milliseconds
    
    def _parse_srt_time(self, time_str: str) -> int:
        """解析SRT时间格式"""
        # SRT格式: HH:MM:SS,mmm
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split(',')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        
        return hours * 3600000 + minutes * 60000 + seconds * 1000 + milliseconds
    
    def _format_vtt_time(self, milliseconds: int) -> str:
        """格式化VTT时间"""
        hours = milliseconds // 3600000
        minutes = (milliseconds % 3600000) // 60000
        seconds = (milliseconds % 60000) // 1000
        ms = milliseconds % 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"
    
    def _format_srt_time(self, milliseconds: int) -> str:
        """格式化SRT时间"""
        hours = milliseconds // 3600000
        minutes = (milliseconds % 3600000) // 60000
        seconds = (milliseconds % 60000) // 1000
        ms = milliseconds % 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
    
    def _convert_to_srt(self, subtitles: List[Dict]) -> str:
        """转换为SRT格式"""
        srt_content = []
        
        for i, subtitle in enumerate(subtitles, 1):
            srt_content.append(str(i))
            srt_content.append(f"{self._format_srt_time(subtitle['start_time'])} --> {self._format_srt_time(subtitle['end_time'])}")
            srt_content.append(subtitle['text'])
            srt_content.append('')
        
        return '\n'.join(srt_content)
    
    def _convert_to_vtt(self, subtitles: List[Dict]) -> str:
        """转换为VTT格式"""
        vtt_content = ['WEBVTT', '']
        
        for subtitle in subtitles:
            vtt_content.append(f"{self._format_vtt_time(subtitle['start_time'])} --> {self._format_vtt_time(subtitle['end_time'])}")
            vtt_content.append(subtitle['text'])
            vtt_content.append('')
        
        return '\n'.join(vtt_content)
    
    def preview_subtitle(self, subtitle_path: str, max_lines: int = 10) -> str:
        """预览字幕内容"""
        try:
            if not os.path.exists(subtitle_path):
                return "字幕文件不存在"
            
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 提取字幕文本（跳过时间戳和序号）
            text_lines = []
            for line in lines:
                line = line.strip()
                if line and not re.match(r'^\d+$', line) and '-->' not in line and not line.startswith('WEBVTT'):
                    text_lines.append(line)
            
            # 限制预览行数
            preview_lines = text_lines[:max_lines]
            preview_text = '\n'.join(preview_lines)
            
            if len(text_lines) > max_lines:
                preview_text += f'\n... (共{len(text_lines)}行)'
            
            return preview_text
            
        except Exception as e:
            return f"预览失败: {e}"


# 全局字幕管理器实例
subtitle_manager = SubtitleManager()
