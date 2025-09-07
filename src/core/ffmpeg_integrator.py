#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg完全集成器 - 跨平台版本

该模块提供FFmpeg的完全集成功能，包括：
- 自动下载和安装FFmpeg
- 嵌入式FFmpeg管理
- 智能回退机制
- 真正的跨平台支持

主要类：
- FFmpegIntegrator: FFmpeg完全集成器

作者: 椰果IDM开发团队
版本: 1.1.0
"""

import os
import sys
import platform
import subprocess
import shutil
import zipfile
import tarfile
import requests
import stat
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging
import threading

logger = logging.getLogger(__name__)

class FFmpegIntegrator:
    """FFmpeg完全集成器 - 跨平台版本"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.resources_dir = self.project_root / "resources"
        self.ffmpeg_dir = self.resources_dir / "ffmpeg"
        self.ffmpeg_bin_dir = self.ffmpeg_dir / "bin"
        self.ffmpeg_exe = None
        self.ffmpeg_available = False
        self.installation_lock = threading.Lock()
        
        # 延迟初始化FFmpeg，避免在不需要时创建目录
        self._initialized = False
    
    def _ensure_initialized(self) -> None:
        """确保FFmpeg已初始化"""
        if not self._initialized:
            # 确保资源目录存在
            self.resources_dir.mkdir(exist_ok=True)
            self.ffmpeg_dir.mkdir(exist_ok=True)
            self.ffmpeg_bin_dir.mkdir(exist_ok=True)
            
            # 初始化FFmpeg
            self._initialize_ffmpeg()
            self._initialized = True
    
    def _initialize_ffmpeg(self) -> None:
        """初始化FFmpeg"""
        try:
            # 检查嵌入式FFmpeg
            if self._check_embedded_ffmpeg():
                self.ffmpeg_available = True
                logger.info("使用嵌入式FFmpeg")
                return
            
            # 检查系统FFmpeg
            if self._check_system_ffmpeg():
                self.ffmpeg_available = True
                logger.info("使用系统FFmpeg")
                return
            
            # 尝试自动安装FFmpeg
            if self._auto_install_ffmpeg():
                self.ffmpeg_available = True
                logger.info("FFmpeg自动安装成功")
                return
            
            # 最后尝试Python库回退
            if self._setup_python_fallback():
                self.ffmpeg_available = True
                logger.info("使用Python库回退方案")
                return
            
            logger.warning("无法找到或安装FFmpeg，某些功能可能受限")
            
        except Exception as e:
            logger.error(f"FFmpeg初始化失败: {e}")
    
    def _check_embedded_ffmpeg(self) -> bool:
        """检查嵌入式FFmpeg - 跨平台兼容"""
        try:
            system = platform.system().lower()
            
            # 根据平台确定可能的可执行文件名
            if system == "windows":
                # Windows: 尝试多个可能的文件名
                possible_names = ["ffmpeg.exe", "ffmpeg"]
            elif system == "darwin":  # macOS
                # macOS: 通常没有扩展名，但有时可能有
                possible_names = ["ffmpeg", "ffmpeg.exe"]
            else:  # Linux
                # Linux: 通常没有扩展名
                possible_names = ["ffmpeg", "ffmpeg.exe"]
            
            # 尝试每个可能的文件名
            for exe_name in possible_names:
                ffmpeg_path = self.ffmpeg_bin_dir / exe_name
                if ffmpeg_path.exists():
                    # 验证可执行性
                    if self._verify_ffmpeg_executable(str(ffmpeg_path)):
                        self.ffmpeg_exe = str(ffmpeg_path)
                        logger.info(f"找到嵌入式FFmpeg: {ffmpeg_path}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查嵌入式FFmpeg失败: {e}")
            return False
    
    def _check_system_ffmpeg(self) -> bool:
        """检查系统FFmpeg"""
        try:
            # 使用shutil.which跨平台查找
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                if self._verify_ffmpeg_executable(ffmpeg_path):
                    self.ffmpeg_exe = ffmpeg_path
                    logger.info(f"找到系统FFmpeg: {ffmpeg_path}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查系统FFmpeg失败: {e}")
            return False
    
    def _verify_ffmpeg_executable(self, ffmpeg_path: str) -> bool:
        """验证FFmpeg可执行文件 - 跨平台兼容"""
        try:
            # 检查文件是否存在
            if not os.path.exists(ffmpeg_path):
                return False
            
            # 在非Windows系统上检查可执行权限
            if platform.system().lower() != "windows":
                if not os.access(ffmpeg_path, os.X_OK):
                    logger.warning(f"文件没有执行权限: {ffmpeg_path}")
                    return False
            
            # 尝试运行FFmpeg获取版本信息
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"验证FFmpeg可执行文件失败: {e}")
            return False
    
    def _auto_install_ffmpeg(self) -> bool:
        """自动安装FFmpeg"""
        try:
            with self.installation_lock:
                if self.ffmpeg_exe:
                    return True
                
                logger.info("开始自动安装FFmpeg...")
                
                # 获取下载信息
                download_info = self._get_download_info()
                if not download_info:
                    logger.error("无法获取FFmpeg下载信息")
                    return False
                
                # 下载FFmpeg
                archive_path = self._download_ffmpeg(download_info)
                if not archive_path:
                    logger.error("FFmpeg下载失败")
                    return False
                
                # 解压FFmpeg
                if not self._extract_ffmpeg(archive_path, download_info):
                    logger.error("FFmpeg解压失败")
                    return False
                
                # 清理下载文件
                if archive_path.exists():
                    archive_path.unlink()
                
                # 验证安装
                if self._check_embedded_ffmpeg():
                    logger.info("FFmpeg自动安装完成")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"自动安装FFmpeg失败: {e}")
            return False
    
    def _get_download_info(self) -> Optional[Dict]:
        """获取FFmpeg下载信息 - 跨平台支持"""
        try:
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            if system == "windows":
                if "x86_64" in machine or "amd64" in machine:
                    return {
                        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
                        "filename": "ffmpeg-win64.zip",
                        "type": "zip",
                        "extract_path": "ffmpeg-master-latest-win64-gpl"
                    }
                else:
                    return {
                        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win32-gpl.zip",
                        "filename": "ffmpeg-win32.zip",
                        "type": "zip",
                        "extract_path": "ffmpeg-master-latest-win32-gpl"
                    }
            
            elif system == "darwin":  # macOS
                if "arm64" in machine or "aarch64" in machine:
                    return {
                        "url": "https://evermeet.cx/ffmpeg/getrelease/zip",
                        "filename": "ffmpeg-macos-arm64.zip",
                        "type": "zip",
                        "extract_path": "ffmpeg"
                    }
                else:
                    return {
                        "url": "https://evermeet.cx/ffmpeg/getrelease/zip",
                        "filename": "ffmpeg-macos-x64.zip",
                        "type": "zip",
                        "extract_path": "ffmpeg"
                    }
            
            else:  # Linux
                if "x86_64" in machine or "amd64" in machine:
                    return {
                        "url": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
                        "filename": "ffmpeg-linux-amd64.tar.xz",
                        "type": "tar",
                        "extract_path": "ffmpeg-*-amd64-static"
                    }
                else:
                    return {
                        "url": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz",
                        "filename": "ffmpeg-linux-i686.tar.xz",
                        "type": "tar",
                        "extract_path": "ffmpeg-*-i686-static"
                    }
            
        except Exception as e:
            logger.error(f"获取下载信息失败: {e}")
            return None
    
    def _download_ffmpeg(self, download_info: Dict) -> Optional[Path]:
        """下载FFmpeg"""
        try:
            url = download_info["url"]
            filename = download_info["filename"]
            archive_path = self.ffmpeg_dir / filename
            
            logger.info(f"开始下载FFmpeg: {url}")
            
            # 检查是否已存在
            if archive_path.exists():
                logger.info("FFmpeg压缩包已存在，跳过下载")
                return archive_path
            
            # 下载文件
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 显示下载进度
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            logger.info(f"下载进度: {progress:.1f}%")
            
            logger.info("FFmpeg下载完成")
            return archive_path
            
        except Exception as e:
            logger.error(f"下载FFmpeg失败: {e}")
            return None
    
    def _extract_ffmpeg(self, archive_path: Path, download_info: Dict) -> bool:
        """解压FFmpeg"""
        try:
            logger.info("开始解压FFmpeg...")
            
            if download_info["type"] == "zip":
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(self.ffmpeg_dir)
            elif download_info["type"] == "tar":
                with tarfile.open(archive_path, 'r:*') as tar_ref:
                    tar_ref.extractall(self.ffmpeg_dir)
            
            # 查找解压后的目录
            extract_path = download_info["extract_path"]
            if "*" in extract_path:
                # 处理通配符路径
                for item in self.ffmpeg_dir.iterdir():
                    if item.is_dir() and item.name.startswith(extract_path.replace("*", "")):
                        extract_path = item.name
                        break
            
            extracted_dir = self.ffmpeg_dir / extract_path
            if not extracted_dir.exists():
                logger.error(f"解压后的目录不存在: {extracted_dir}")
                return False
            
            # 移动文件到正确位置
            self._organize_ffmpeg_files(extracted_dir)
            
            logger.info("FFmpeg解压完成")
            return True
            
        except Exception as e:
            logger.error(f"解压FFmpeg失败: {e}")
            return False
    
    def _organize_ffmpeg_files(self, extracted_dir: Path) -> None:
        """整理FFmpeg文件结构 - 跨平台兼容"""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                # Windows: 查找bin目录下的可执行文件
                bin_dir = extracted_dir / "bin"
                if bin_dir.exists():
                    # 查找所有可能的可执行文件
                    for pattern in ["*.exe", "ffmpeg*"]:
                        for exe_file in bin_dir.glob(pattern):
                            if exe_file.is_file():
                                target_path = self.ffmpeg_bin_dir / exe_file.name
                                if target_path.exists():
                                    target_path.unlink()
                                shutil.copy2(exe_file, target_path)
                                logger.info(f"复制Windows可执行文件: {exe_file.name}")
            else:
                # macOS/Linux: 查找所有以ffmpeg开头的文件
                for item in extracted_dir.iterdir():
                    if item.is_file() and item.name.startswith("ffmpeg"):
                        target_path = self.ffmpeg_bin_dir / item.name
                        if target_path.exists():
                            target_path.unlink()
                        shutil.copy2(item, target_path)
                        
                        # 设置可执行权限（Unix系统）
                        try:
                            target_path.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                            logger.info(f"设置可执行权限: {item.name}")
                        except Exception as e:
                            logger.warning(f"设置权限失败: {e}")
                        
                        logger.info(f"复制Unix可执行文件: {item.name}")
            
            # 清理解压目录
            if extracted_dir.exists():
                shutil.rmtree(extracted_dir)
                
        except Exception as e:
            logger.error(f"整理FFmpeg文件失败: {e}")
    
    def _setup_python_fallback(self) -> bool:
        """设置Python库回退方案"""
        try:
            # 尝试安装必要的Python库
            required_packages = ["ffmpeg-python", "moviepy"]
            
            for package in required_packages:
                try:
                    __import__(package.replace("-", "_"))
                    logger.info(f"Python库 {package} 可用")
                except ImportError:
                    logger.info(f"尝试安装Python库: {package}")
                    try:
                        subprocess.check_call([
                            sys.executable, "-m", "pip", "install", package
                        ])
                        logger.info(f"成功安装 {package}")
                    except subprocess.CalledProcessError:
                        logger.warning(f"安装 {package} 失败")
            
            # 检查是否有可用的Python库
            try:
                import ffmpeg
                logger.info("ffmpeg-python库可用")
                return True
            except ImportError:
                try:
                    from moviepy.editor import VideoFileClip
                    logger.info("moviepy库可用")
                    return True
                except ImportError:
                    logger.warning("没有可用的Python FFmpeg库")
                    return False
                    
        except Exception as e:
            logger.error(f"设置Python回退方案失败: {e}")
            return False
    
    def get_ffmpeg_path(self) -> Optional[str]:
        """获取FFmpeg路径"""
        self._ensure_initialized()
        return self.ffmpeg_exe
    
    def is_available(self) -> bool:
        """检查FFmpeg是否可用"""
        self._ensure_initialized()
        return self.ffmpeg_available
    
    def get_installation_status(self) -> Dict:
        """获取安装状态"""
        self._ensure_initialized()
        return {
            "available": self.ffmpeg_available,
            "path": self.ffmpeg_exe,
            "type": "embedded" if self.ffmpeg_exe and "resources" in self.ffmpeg_exe else "system",
            "embedded_dir": str(self.ffmpeg_dir),
            "bin_dir": str(self.ffmpeg_bin_dir),
            "platform": platform.system().lower(),
            "architecture": platform.machine().lower()
        }
    
    def force_reinstall(self) -> bool:
        """强制重新安装FFmpeg"""
        try:
            logger.info("强制重新安装FFmpeg...")
            
            # 清理现有安装
            if self.ffmpeg_bin_dir.exists():
                for item in self.ffmpeg_bin_dir.iterdir():
                    if item.is_file():
                        item.unlink()
            
            # 重置状态
            self.ffmpeg_exe = None
            self.ffmpeg_available = False
            
            # 重新安装
            return self._auto_install_ffmpeg()
            
        except Exception as e:
            logger.error(f"强制重新安装失败: {e}")
            return False
    
    def cleanup(self) -> None:
        """清理FFmpeg安装"""
        try:
            if self.ffmpeg_dir.exists():
                shutil.rmtree(self.ffmpeg_dir)
            logger.info("FFmpeg安装已清理")
        except Exception as e:
            logger.error(f"清理FFmpeg失败: {e}")


# 注意：不再创建全局实例，避免在模块导入时自动创建目录
# 如需使用，请在需要时创建实例：FFmpegIntegrator()
