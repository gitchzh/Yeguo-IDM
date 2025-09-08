# 🥥 椰果IDM - 智能视频下载管理器

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.5.0-orange.svg)](CHANGELOG.md)

> 🚀 基于PyQt5开发的现代化视频下载管理器，支持多平台视频解析和批量下载

## ✨ 主要特性

- 🎯 **多平台支持**: YouTube、Bilibili、网易云音乐等主流视频平台
- 🚀 **智能解析**: 自动识别视频格式和质量选项
- 📱 **现代化UI**: 基于PyQt5的优雅用户界面，支持中英文切换
- 🔄 **批量下载**: 支持多任务并发下载
- 📊 **实时监控**: 下载进度、速度、状态实时显示
- 💾 **历史记录**: 完整的下载历史管理（内存数据库）
- ⚙️ **灵活配置**: 可自定义下载路径、格式等参数
- 🌐 **网络优化**: 支持断点续传和网络重试
- 🔧 **智能解析**: 自动识别视频链接类型
- 🌍 **国际化支持**: 完整的中英文界面切换
- 🎵 **字幕下载**: 支持多语言字幕下载
- 📧 **问题反馈**: 内置问题反馈系统

## 🖼️ 界面预览

```
┌─────────────────────────────────────────────────────────────┐
│ 🥥 椰果IDM - 智能视频下载管理器                    [─][□][×] │
├─────────────────────────────────────────────────────────────┤
│ 📥 下载管理  │  📋 下载历史  │  ⚙️ 设置  │  ❓ 帮助        │
├─────────────────────────────────────────────────────────────┤
│ 🔗 视频链接: [https://...                    ] [🔍 解析]   │
│                                                                 │
│ 📊 解析结果:                                                │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ ✅ 视频标题: 示例视频标题                                │   │
│ │ 📹 格式: MP4 1080P | 大小: 150MB                       │   │
│ │ 📁 保存路径: [C:\Downloads\...] [📁 选择路径]          │   │
│ │ [☑️ 选择] [🚀 开始下载]                                │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ 📈 下载进度: ████████████████████████████████████ 100%     │
│ 🚀 下载速度: 2.5 MB/s | ⏱️ 剩余时间: 00:00:30            │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- **操作系统**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- **Python版本**: 3.8 或更高版本
- **内存要求**: 最低 4GB RAM，推荐 8GB+
- **存储空间**: 至少 500MB 可用空间

### 安装步骤

1. **克隆项目**
   ```bash
   # 从Gitee克隆（推荐国内用户）
   git clone https://gitee.com/mrchzh/ygmdm.git
   cd ygmdm
   
   # 或从GitHub克隆
   git clone git@github.com:gitchzh/Yeguo-IDM.git
   cd Yeguo-IDM
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python main.py
   ```

### 一键打包

使用内置的打包系统生成独立的可执行文件：

```bash
# 自动生成spec文件并打包
python setup.py build_exe
```

打包完成后，可执行文件位于 `dist/椰果IDM.exe`

## 📖 使用指南

### 基本操作

1. **输入链接**: 在链接输入框中粘贴视频URL
2. **解析视频**: 点击"解析"按钮获取视频信息
3. **选择格式**: 从解析结果中选择合适的格式和质量
4. **设置路径**: 选择文件保存位置
5. **开始下载**: 点击"开始下载"按钮

### 高级功能

- **批量下载**: 支持多个链接同时解析和下载
- **字幕下载**: 支持多语言字幕下载
- **播放列表**: 支持YouTube播放列表批量下载
- **历史管理**: 完整的下载历史记录和管理（内存数据库）
- **设置管理**: 丰富的个性化设置选项
- **问题反馈**: 内置问题反馈和帮助系统

## 🛠️ 技术架构

```
椰果IDM/
├── 📁 src/                    # 源代码目录
│   ├── 🖥️ ui/                # 用户界面模块
│   │   ├── main_window.py     # 主窗口
│   │   ├── settings_dialog.py # 设置对话框
│   │   └── ...                # 其他UI组件
│   ├── ⚙️ core/              # 核心功能模块
│   │   ├── config.py          # 配置管理
│   │   ├── log_manager.py     # 日志管理
│   │   ├── history.py         # 历史记录（内存数据库）
│   │   └── ...                # 其他核心功能
│   ├── 🧵 workers/            # 工作线程模块
│   │   ├── download_worker.py # 下载工作器
│   │   └── ...                # 其他工作器
│   ├── 🌍 i18n/              # 国际化文件
│   │   ├── zh_CN.json         # 中文翻译
│   │   └── en_US.json         # 英文翻译
│   └── 🔧 utils/              # 工具模块
├── 🖼️ resources/             # 资源文件
├── 📄 main.py                 # 程序入口
├── 🔨 setup.py                # 打包配置
├── 📋 requirements.txt        # 依赖列表
└── 📄 ygmdm.spec              # PyInstaller配置
```

### 核心技术

- **GUI框架**: PyQt5 - 跨平台桌面应用开发
- **视频解析**: yt-dlp - 强大的视频下载库
- **视频处理**: 跨平台FFmpeg集成（系统FFmpeg + Python库）
- **网络请求**: requests - HTTP客户端库
- **数据存储**: SQLite内存数据库 - 轻量级数据库
- **打包工具**: PyInstaller - 可执行文件生成
- **国际化**: 自定义i18n系统 - 支持中英文切换

### 内存数据库特性

项目使用SQLite内存数据库存储下载历史，具有以下优势：

- **无文件生成**: 程序运行时不生成数据库文件
- **高性能**: 内存操作比磁盘操作更快
- **数据安全**: 程序关闭后数据自动清理
- **便携性**: 真正的单文件可执行程序

## ⚙️ 配置说明

### 下载设置

- **并发数**: 同时下载的任务数量（默认: 2）
- **下载路径**: 文件保存的默认位置
- **网络超时**: 连接和下载超时时间
- **重试次数**: 下载失败时的重试次数

### 界面设置

- **语言**: 支持中文/英文界面切换
- **字体**: 统一使用Microsoft YaHei字体
- **布局**: 界面元素排列方式
- **主题**: 默认浅色主题

## 🔧 开发指南

### 环境搭建

1. **安装开发依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **代码格式化**
   ```bash
   black src/
   isort src/
   ```

3. **代码检查**
   ```bash
   flake8 src/
   mypy src/
   ```

### 贡献指南

1. Fork 项目到你的GitHub账户或Gitee账户
2. 创建功能分支: `git checkout -b feature/AmazingFeature`
3. 提交更改: `git commit -m 'Add some AmazingFeature'`
4. 推送到分支: `git push origin feature/AmazingFeature`
5. 创建 Pull Request

**代码仓库地址:**
- **Gitee**: https://gitee.com/mrchzh/ygmdm.git
- **GitHub**: git@github.com:gitchzh/Yeguo-IDM.git

### 代码规范

- 遵循 PEP 8 Python代码规范
- 使用类型提示 (Type Hints)
- 编写详细的文档字符串
- 保持代码简洁和可读性

## 📊 性能指标

- **启动时间**: < 3秒 (Python版本) / < 1秒 (打包版本)
- **内存占用**: < 100MB
- **CPU使用率**: < 5% (空闲状态)
- **下载速度**: 支持满带宽下载
- **并发能力**: 支持10+任务同时下载
- **文件大小**: 44MB (打包后)

## 🐛 问题反馈

### 常见问题

**Q: 下载速度很慢怎么办？**
A: 检查网络连接，尝试更换下载服务器，或调整并发数设置。

**Q: 某些视频无法解析？**
A: 可能是平台更新了反爬虫机制，请等待程序更新或提交Issue。

**Q: 程序崩溃怎么办？**
A: 查看日志文件，重启程序，如问题持续请提交详细的错误报告。

**Q: 打包后的程序启动慢？**
A: 这是PyInstaller打包程序的正常现象，首次启动需要解压和初始化。

### 提交反馈

- **Gitee Issues**: [提交问题报告](https://gitee.com/mrchzh/ygmdm/issues)
- **GitHub Issues**: [提交问题报告](https://github.com/gitchzh/Yeguo-IDM/issues)
- **功能建议**: [Gitee功能请求](https://gitee.com/mrchzh/ygmdm/issues/new?template=feature_request.md) | [GitHub功能请求](https://github.com/gitchzh/Yeguo-IDM/issues/new?template=feature_request.md)
- **Bug报告**: [Gitee Bug报告](https://gitee.com/mrchzh/ygmdm/issues/new?template=bug_report.md) | [GitHub Bug报告](https://github.com/gitchzh/Yeguo-IDM/issues/new?template=bug_report.md)

## 📈 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细的版本更新历史。

### 最新版本 v1.6.0

- ✨ 新增多平台视频解析支持
- 🎨 全新现代化用户界面
- 🚀 性能优化和稳定性提升
- 🔧 修复多个已知问题
- 💾 内存数据库实现，无文件生成
- 📦 一键打包系统
- 🌍 完整的中英文国际化支持
- 🎯 UI布局优化：按钮左右对齐，界面更美观
- 📊 状态栏显示优化：实时显示解析进度和分组信息
- 📝 帮助页面内容更新：添加版权提醒和联系方式
- 🔧 解析完成弹窗国际化：支持中英文切换
- 📧 反馈页面优化：添加邮件联系方式和说明文字
- 🚫 **新增功能**: 立即取消下载机制，点击取消后立即停止所有下载任务
- 🌐 **完善翻译**: 完成所有界面元素的国际化翻译，包括设置页面、日志管理、字幕下载、下载历史等
- 🔧 **技术优化**: 增强下载取消机制，支持强制终止线程和实时取消检查
- 📱 **UI改进**: 修复按钮文字遮挡问题，优化界面元素尺寸适配

## ⚖️ 使用声明

**重要提醒**: 椰果IDM软件仅用于个人学习使用。知识是需要付费的，请不要下载别人付费的内容来传播盈利！我们真诚地相信您会遵守相关法律法规，合理使用本软件。

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

## 🙏 致谢

- **yt-dlp**: 强大的视频下载库
- **PyQt5**: 优秀的跨平台GUI框架
- **开源社区**: 为项目提供宝贵建议和贡献

## 📞 联系我们

- **项目主页**: 
  - [Gitee Repository](https://gitee.com/mrchzh/ygmdm)
  - [GitHub Repository](https://github.com/gitchzh/Yeguo-IDM)
- **问题反馈**: 
  - [Gitee Issues](https://gitee.com/mrchzh/ygmdm/issues)
  - [GitHub Issues](https://github.com/gitchzh/Yeguo-IDM/issues)
- **讨论交流**: 
  - [Gitee Discussions](https://gitee.com/mrchzh/ygmdm/pulls)
  - [GitHub Discussions](https://github.com/gitchzh/Yeguo-IDM/discussions)
- **邮箱联系**: gmrchzh@gmail.com

---

**🥥 椰果IDM - 让视频下载更简单、更高效**

[⭐ Gitee Star](https://gitee.com/mrchzh/ygmdm) | [⭐ GitHub Star](https://github.com/gitchzh/Yeguo-IDM) | [📖 文档](https://gitee.com/mrchzh/ygmdm) | [🚀 下载](https://gitee.com/mrchzh/ygmdm/releases)