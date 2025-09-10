#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软件更新管理器

该模块提供软件自动更新功能，包括：
- 版本检查和管理
- 多源更新检查（GitHub + Gitee）
- 文件下载和验证
- 更新进度管理
- 错误处理和重试机制

主要类：
- UpdateManager: 更新管理器主类
- VersionInfo: 版本信息类
- UpdateChecker: 更新检查器
- DownloadManager: 下载管理器

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import sys
import json
import hashlib
import requests
import threading
import time
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtWidgets import QApplication

from .config import Config
from ..utils.logger import logger


@dataclass
class VersionInfo:
    """版本信息数据类"""
    version: str
    release_date: str
    download_url: str
    file_size: int
    file_hash: Optional[str] = None
    release_notes: str = ""
    is_prerelease: bool = False
    source: str = ""  # "github" 或 "gitee"


class UpdateChecker(QThread):
    """更新检查器 - 在后台线程中检查更新"""
    
    # 信号定义
    update_available = pyqtSignal(VersionInfo)  # 发现新版本
    no_update = pyqtSignal()  # 无更新
    check_failed = pyqtSignal(str)  # 检查失败
    progress_updated = pyqtSignal(str)  # 进度更新
    
    def __init__(self):
        super().__init__()
        self.current_version = Config.APP_VERSION
        self.github_repo = "mrchzh/Yeguo-IDM"  # GitHub仓库（修正仓库名）
        self.gitee_repo = "mrchzh/ygmdm"  # Gitee仓库
        self.timeout = 10  # 请求超时时间
        self._stop_checking = False
        self.gitee_priority = True  # 优先使用码云
        
    def stop_checking(self):
        """停止检查"""
        self._stop_checking = True
        
    def run(self):
        """执行更新检查"""
        try:
            self.progress_updated.emit("正在检查更新...")
            
            if self.gitee_priority:
                # 优先检查Gitee（码云）
                if not self._stop_checking:
                    gitee_version = self._check_gitee()
                    if gitee_version:
                        self.progress_updated.emit("码云检查完成")
                        if self._is_newer_version(gitee_version.version):
                            self.update_available.emit(gitee_version)
                            return
                
                # 如果Gitee检查失败，检查GitHub作为备用
                if not self._stop_checking:
                    github_version = self._check_github()
                    if github_version:
                        self.progress_updated.emit("GitHub检查完成")
                        if self._is_newer_version(github_version.version):
                            self.update_available.emit(github_version)
                            return
            else:
                # 优先检查GitHub
                if not self._stop_checking:
                    github_version = self._check_github()
                    if github_version:
                        self.progress_updated.emit("GitHub检查完成")
                        if self._is_newer_version(github_version.version):
                            self.update_available.emit(github_version)
                            return
                
                # 如果GitHub检查失败，检查Gitee作为备用
                if not self._stop_checking:
                    gitee_version = self._check_gitee()
                    if gitee_version:
                        self.progress_updated.emit("码云检查完成")
                        if self._is_newer_version(gitee_version.version):
                            self.update_available.emit(gitee_version)
                            return
            
            # 没有找到新版本
            if not self._stop_checking:
                self.progress_updated.emit("检查完成，已是最新版本")
                self.no_update.emit()
                
        except Exception as e:
            logger.error(f"更新检查失败: {e}")
            self.check_failed.emit(str(e))
    
    def _check_github(self) -> Optional[VersionInfo]:
        """检查GitHub更新（备用源）"""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
            headers = {
                'User-Agent': Config.DEFAULT_USER_AGENT,
                'Accept': 'application/vnd.github.v3+json'
            }
            
            logger.info(f"正在检查GitHub更新（备用源）: {url}")
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            version_info = self._parse_github_release(data)
            
            if version_info:
                logger.info(f"GitHub检查成功，最新版本: v{version_info.version}")
            else:
                logger.warning("GitHub返回数据解析失败")
                
            return version_info
            
        except requests.exceptions.Timeout:
            logger.warning("GitHub更新检查超时")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("GitHub更新检查网络连接失败")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"GitHub更新检查HTTP错误: {e}")
            return None
        except Exception as e:
            logger.warning(f"GitHub更新检查失败: {e}")
            return None
    
    def _check_gitee(self) -> Optional[VersionInfo]:
        """检查Gitee更新（优先源）"""
        try:
            url = f"https://gitee.com/api/v5/repos/{self.gitee_repo}/releases/latest"
            headers = {
                'User-Agent': Config.DEFAULT_USER_AGENT,
                'Accept': 'application/json'
            }
            
            logger.info(f"正在检查码云更新: {url}")
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            version_info = self._parse_gitee_release(data)
            
            if version_info:
                logger.info(f"码云检查成功，最新版本: v{version_info.version}")
            else:
                logger.warning("码云返回数据解析失败")
                
            return version_info
            
        except requests.exceptions.Timeout:
            logger.warning("码云更新检查超时")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("码云更新检查网络连接失败")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"码云更新检查HTTP错误: {e}")
            return None
        except Exception as e:
            logger.warning(f"码云更新检查失败: {e}")
            return None
    
    def _parse_github_release(self, data: Dict) -> VersionInfo:
        """解析GitHub发布信息"""
        # 查找Windows exe文件
        download_url = None
        file_size = 0
        
        for asset in data.get('assets', []):
            if asset['name'].endswith('.exe'):
                download_url = asset['browser_download_url']
                file_size = asset['size']
                break
        
        return VersionInfo(
            version=data['tag_name'].lstrip('v'),
            release_date=data['published_at'][:10],
            download_url=download_url or "",
            file_size=file_size,
            release_notes=data.get('body', ''),
            is_prerelease=data.get('prerelease', False),
            source="github"
        )
    
    def _parse_gitee_release(self, data: Dict) -> VersionInfo:
        """解析Gitee发布信息"""
        try:
            # 查找Windows exe文件
            download_url = None
            file_size = 0
            
            # Gitee的assets结构可能不同，需要适配
            assets = data.get('assets', [])
            if not assets:
                # 如果没有assets，尝试从其他字段获取下载链接
                logger.warning("Gitee发布没有assets，尝试其他方式获取下载链接")
                return None
            
            for asset in assets:
                asset_name = asset.get('name', '')
                if asset_name.endswith('.exe'):
                    download_url = asset.get('browser_download_url', '')
                    file_size = asset.get('size', 0)
                    logger.info(f"找到Gitee下载文件: {asset_name}, 大小: {file_size} bytes")
                    break
            
            if not download_url:
                logger.warning("Gitee发布中没有找到exe文件")
                return None
            
            # 解析版本号
            tag_name = data.get('tag_name', '')
            if not tag_name:
                logger.warning("Gitee发布没有tag_name")
                return None
            
            version = tag_name.lstrip('v')
            
            # 解析发布日期
            created_at = data.get('created_at', '')
            release_date = created_at[:10] if created_at else ''
            
            # 解析发布说明
            body = data.get('body', '')
            if not body:
                body = data.get('description', '')
            
            return VersionInfo(
                version=version,
                release_date=release_date,
                download_url=download_url,
                file_size=file_size,
                release_notes=body,
                is_prerelease=data.get('prerelease', False),
                source="gitee"
            )
            
        except Exception as e:
            logger.error(f"解析Gitee发布信息失败: {e}")
            return None
    
    def _is_newer_version(self, new_version: str) -> bool:
        """比较版本号，判断是否有新版本"""
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            new_parts = [int(x) for x in new_version.split('.')]
            
            # 补齐版本号长度
            max_len = max(len(current_parts), len(new_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            new_parts.extend([0] * (max_len - len(new_parts)))
            
            return new_parts > current_parts
            
        except Exception as e:
            logger.error(f"版本号比较失败: {e}")
            return False


class DownloadManager(QThread):
    """下载管理器 - 在后台线程中下载更新文件"""
    
    # 信号定义
    download_progress = pyqtSignal(int)  # 下载进度 (0-100)
    download_completed = pyqtSignal(str)  # 下载完成，返回文件路径
    download_failed = pyqtSignal(str)  # 下载失败
    download_status = pyqtSignal(str)  # 下载状态信息
    
    def __init__(self, version_info: VersionInfo, download_dir: str):
        super().__init__()
        self.version_info = version_info
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._stop_download = False
        
    def stop_download(self):
        """停止下载"""
        self._stop_download = True
        
    def run(self):
        """执行下载"""
        try:
            if not self.version_info.download_url:
                self.download_failed.emit("下载链接无效")
                return
            
            self.download_status.emit("开始下载更新文件...")
            
            # 生成文件名
            filename = f"椰果IDM_v{self.version_info.version}.exe"
            filepath = self.download_dir / filename
            
            # 下载文件
            self._download_file(self.version_info.download_url, filepath)
            
            if not self._stop_download:
                # 验证文件
                if self._verify_file(filepath):
                    self.download_status.emit("下载完成，文件验证成功")
                    self.download_completed.emit(str(filepath))
                else:
                    self.download_failed.emit("文件验证失败")
                    filepath.unlink(missing_ok=True)
            else:
                self.download_failed.emit("下载已取消")
                filepath.unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"下载失败: {e}")
            self.download_failed.emit(str(e))
    
    def _download_file(self, url: str, filepath: Path):
        """下载文件"""
        headers = {
            'User-Agent': Config.DEFAULT_USER_AGENT,
            'Accept': 'application/octet-stream'
        }
        
        # 处理重定向，允许最多5次重定向
        response = requests.get(url, headers=headers, stream=True, timeout=30, allow_redirects=True, max_redirects=5)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if self._stop_download:
                    break
                    
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    if total_size > 0:
                        progress = int((downloaded_size / total_size) * 100)
                        self.download_progress.emit(progress)
                        self.download_status.emit(f"下载中... {progress}%")
    
    def _verify_file(self, filepath: Path) -> bool:
        """验证下载的文件"""
        try:
            # 检查文件是否存在
            if not filepath.exists():
                logger.warning("下载文件不存在")
                return False
            
            # 检查文件大小（如果码云返回的文件大小为0，跳过大小检查）
            actual_size = filepath.stat().st_size
            if actual_size == 0:
                logger.warning("下载文件大小为0")
                return False
            
            if self.version_info.file_size > 0:
                if abs(actual_size - self.version_info.file_size) > 1024:  # 允许1KB误差
                    logger.warning(f"文件大小不匹配: 期望 {self.version_info.file_size}, 实际 {actual_size}")
                    # 不返回False，因为码云可能返回不准确的文件大小
            
            # 检查文件扩展名
            if not filepath.suffix.lower() == '.exe':
                logger.warning(f"文件类型不正确: {filepath.suffix}")
                return False
            
            # 检查文件是否可执行（Windows）
            if sys.platform == "win32":
                try:
                    # 尝试读取PE文件头
                    with open(filepath, 'rb') as f:
                        header = f.read(2)
                        if header != b'MZ':  # PE文件签名
                            logger.warning("文件不是有效的Windows可执行文件")
                            return False
                except Exception:
                    pass
            
            logger.info(f"文件验证成功: {filepath.name}, 大小: {actual_size} bytes")
            return True
            
        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            return False


class UpdateManager(QObject):
    """更新管理器主类"""
    
    # 信号定义
    update_check_started = pyqtSignal()
    update_check_completed = pyqtSignal()
    update_available = pyqtSignal(VersionInfo)
    no_update_available = pyqtSignal()
    update_check_failed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.checker = None
        self.downloader = None
        self.last_check_time = 0
        self.check_interval = 24 * 60 * 60  # 24小时检查一次
        
    def check_for_updates(self, force: bool = False) -> None:
        """检查更新"""
        current_time = time.time()
        
        # 如果不是强制检查且距离上次检查时间太短，则跳过
        if not force and (current_time - self.last_check_time) < self.check_interval:
            logger.info("距离上次检查时间太短，跳过更新检查")
            return
        
        # 停止之前的检查
        if self.checker and self.checker.isRunning():
            self.checker.stop_checking()
            self.checker.wait(3000)
        
        # 创建新的检查器
        self.checker = UpdateChecker()
        self.checker.update_available.connect(self.update_available.emit)
        self.checker.no_update.connect(self.no_update_available.emit)
        self.checker.check_failed.connect(self.update_check_failed.emit)
        
        # 启动检查
        self.checker.start()
        self.last_check_time = current_time
        self.update_check_started.emit()
        
        logger.info("开始检查软件更新")
    
    def download_update(self, version_info: VersionInfo, download_dir: str) -> None:
        """下载更新"""
        # 停止之前的下载
        if self.downloader and self.downloader.isRunning():
            self.downloader.stop_download()
            self.downloader.wait(3000)
        
        # 创建新的下载器
        self.downloader = DownloadManager(version_info, download_dir)
        
        # 启动下载
        self.downloader.start()
        logger.info(f"开始下载更新: v{version_info.version}")
    
    def stop_download(self) -> None:
        """停止下载"""
        if self.downloader and self.downloader.isRunning():
            self.downloader.stop_download()
            self.downloader.wait(3000)
    
    def set_gitee_priority(self, priority: bool) -> None:
        """设置码云优先级"""
        self.gitee_priority = priority
        if self.checker:
            self.checker.gitee_priority = priority
        logger.info(f"更新源优先级设置: {'码云优先' if priority else 'GitHub优先'}")
    
    def cleanup(self) -> None:
        """清理资源"""
        if self.checker and self.checker.isRunning():
            self.checker.stop_checking()
            self.checker.wait(3000)
        
        if self.downloader and self.downloader.isRunning():
            self.downloader.stop_download()
            self.downloader.wait(3000)


# 全局更新管理器实例
update_manager = UpdateManager()
