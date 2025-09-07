#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
椰果下载器项目打包配置

该文件定义了项目的打包配置，包括：
- 项目元数据
- 依赖包列表
- 包含的文件和目录
- 打包选项

作者: 椰果IDM开发团队
版本: 1.0.0
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# 读取requirements文件
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# 项目配置
setup(
    name="ygmdm",
    version="1.0.0",
    author="椰果IDM开发团队",
    author_email="team@yeguo.com",
    description="椰果下载器 - 支持多种下载协议的多功能下载管理器",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yeguo/yguo-downloader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Multimedia :: Video",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-qt>=4.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.900",
        ],
        "full": [
            "libtorrent>=2.0.0",  # 磁力下载支持
        ],
    },
    entry_points={
        "console_scripts": [
            "ygmdm=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": [
            "resources/*",
            "*.md",
            "*.txt",
            "*.py",
        ],
    },
    data_files=[
        ("resources", [
            "resources/LOGO.png",
        ]),
        ("docs", [
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
        ]),
    ],
    zip_safe=False,
    keywords=[
        "download", "manager", "video", "audio", "magnet", "ed2k", "torrent",
        "youtube", "cloud", "storage"
    ],
    project_urls={
        "Bug Reports": "https://github.com/yeguo/yguo-downloader/issues",
        "Source": "https://github.com/yeguo/yguo-downloader",
        "Documentation": "https://github.com/yeguo/yguo-downloader/wiki",
    },
)
