#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
椰果IDM v1.0.2 - 跨平台打包脚本
优化版本：支持压缩、多平台、实时输出、最小化文件大小

作者: mrchzh
邮箱: gmrchzh@gmail.com
创建日期: 2025年8月27日
更新日期: 2025年1月20日
"""

import os
import sys
import platform
import subprocess
import shutil
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional


class BuildLogger:
    """构建日志管理器"""
    
    def __init__(self):
        self.start_time = time.time()
        self.step_count = 0
    
    def log_step(self, message: str, color: str = 'white'):
        """记录构建步骤"""
        self.step_count += 1
        elapsed = time.time() - self.start_time
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print_colored(f"[{timestamp}] 步骤 {self.step_count}: {message}", color)
    
    def log_info(self, message: str):
        """记录信息"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print_colored(f"[{timestamp}] ℹ️  {message}", 'cyan')
    
    def log_success(self, message: str):
        """记录成功"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print_colored(f"[{timestamp}] ✅ {message}", 'green')
    
    def log_warning(self, message: str):
        """记录警告"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print_colored(f"[{timestamp}] ⚠️  {message}", 'yellow')
    
    def log_error(self, message: str):
        """记录错误"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print_colored(f"[{timestamp}] ❌ {message}", 'red')
    
    def log_progress(self, message: str):
        """记录进度"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print_colored(f"[{timestamp}] 📦 {message}", 'blue')


def print_colored(text: str, color: str = 'white'):
    """打印彩色文本"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'magenta': '\033[95m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")


class BuildManager:
    """构建管理器"""
    
    def __init__(self):
        self.logger = BuildLogger()
        self.platform_configs = {
            'Windows': {
                'ext': '.exe',
                'icon': 'resources/LOGO.png',
                'upx': True,
                'compression': 'lzma',
                'excludes': ['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas']
            },
            'Linux': {
                'ext': '',
                'icon': None,
                'upx': True,
                'compression': 'lzma',
                'excludes': ['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas']
            },
            'Darwin': {  # macOS
                'ext': '',
                'icon': 'resources/LOGO.png',
                'upx': False,  # macOS上UPX可能有问题
                'compression': 'lzma',
                'excludes': ['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas']
            }
        }
    
    def check_dependencies(self) -> bool:
        """检查并安装依赖"""
        self.logger.log_step("检查构建依赖", 'blue')
        
        # 检查PyInstaller
        try:
            import PyInstaller
            self.logger.log_success("PyInstaller 已安装")
        except ImportError:
            self.logger.log_info("正在安装 PyInstaller...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller>=5.0'])
                self.logger.log_success("PyInstaller 安装成功")
            except subprocess.CalledProcessError:
                self.logger.log_error("PyInstaller 安装失败")
                return False
        
        # 检查UPX（可选）
        upx_available = self.check_upx()
        if upx_available:
            self.logger.log_success("UPX 压缩工具可用")
        else:
            self.logger.log_warning("UPX 不可用，将使用内置压缩")
        
        return True
    
    def check_upx(self) -> bool:
        """检查UPX是否可用"""
        try:
            result = subprocess.run(['upx', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def clean_build_dirs(self):
        """清理构建目录"""
        self.logger.log_step("清理构建目录", 'blue')
        
        dirs_to_clean = ['dist', 'build']
        files_to_clean = ['*.spec']
        
        for dir_name in dirs_to_clean:
            if os.path.exists(dir_name):
                try:
                    shutil.rmtree(dir_name)
                    self.logger.log_info(f"已清理目录: {dir_name}")
                except PermissionError as e:
                    self.logger.log_warning(f"无法清理目录 {dir_name}: {str(e)}")
                except Exception as e:
                    self.logger.log_warning(f"清理目录 {dir_name} 时出错: {str(e)}")
        
        for pattern in files_to_clean:
            for file_path in Path('.').glob(pattern):
                try:
                    file_path.unlink()
                    self.logger.log_info(f"已清理文件: {file_path}")
                except PermissionError as e:
                    self.logger.log_warning(f"无法清理文件 {file_path}: {str(e)}")
                except Exception as e:
                    self.logger.log_warning(f"清理文件 {file_path} 时出错: {str(e)}")
    
    def get_platform_config(self, platform_name: str) -> Dict:
        """获取平台配置"""
        return self.platform_configs.get(platform_name, self.platform_configs['Windows'])
    
    def build_command(self, platform_name: str) -> List[str]:
        """生成构建命令"""
        config = self.get_platform_config(platform_name)
        
        cmd = [
            'pyinstaller',
            '--onefile',                    # 打包为单个文件
            '--windowed',                   # 无控制台窗口
            '--clean',                      # 清理临时文件
            '--noconfirm',                  # 不询问确认
            '--strip',                      # 去除调试信息
            f'--name=椰果IDM-{platform_name}',
            '--add-data=resources/LOGO.png;resources',  # 添加资源文件
            '--add-data=resources/ffmpeg.exe;resources',  # 添加FFmpeg
        ]
        
        # 添加图标（如果存在）
        if config['icon'] and os.path.exists(config['icon']):
            cmd.extend(['--icon', config['icon']])
        
        # 添加排除项
        for exclude in config['excludes']:
            cmd.extend(['--exclude-module', exclude])
        
        # 添加UPX压缩
        if config['upx'] and self.check_upx():
            cmd.append('--upx-dir=upx')
        
        # 添加图标（如果存在）
        if config['icon'] and os.path.exists(config['icon']):
            cmd.extend(['--icon', config['icon']])
        
        # 添加主程序文件
        cmd.append('main.py')
        
        return cmd
    
    def real_time_output(self, process: subprocess.Popen, platform_name: str):
        """实时输出构建信息"""
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                output = output.strip()
                if output:
                    # 过滤和格式化输出
                    if any(keyword in output for keyword in ['Building', 'Analyzing', 'Processing', 'Compiling']):
                        self.logger.log_progress(f"[{platform_name}] {output}")
                    elif any(keyword in output for keyword in ['ERROR', 'FAILED', 'Exception']):
                        self.logger.log_error(f"[{platform_name}] {output}")
                    elif any(keyword in output for keyword in ['SUCCESS', 'COMPLETE', 'Finished']):
                        self.logger.log_success(f"[{platform_name}] {output}")
                    elif 'WARNING' in output:
                        self.logger.log_warning(f"[{platform_name}] {output}")
                    else:
                        # 只显示重要信息，避免过多输出
                        if len(output) < 100 and not output.startswith('INFO:'):
                            self.logger.log_info(f"[{platform_name}] {output}")
    
    def build_for_platform(self, platform_name: str) -> bool:
        """为指定平台构建"""
        self.logger.log_step(f"开始构建 {platform_name} 版本", 'blue')
        
        # 创建输出目录
        os.makedirs(f'dist/{platform_name}', exist_ok=True)
        os.makedirs(f'build/{platform_name}', exist_ok=True)
        
        # 生成构建命令
        cmd = self.build_command(platform_name)
        
        try:
            self.logger.log_info(f"执行构建命令: {' '.join(cmd[:5])}...")
            
            # 启动构建进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd='.'  # 确保在正确的目录中运行
            )
            
            # 实时输出构建信息
            self.real_time_output(process, platform_name)
            
            # 等待进程完成
            return_code = process.poll()
            
            if return_code == 0:
                # 检查输出文件
                config = self.get_platform_config(platform_name)
                output_file = f"dist/椰果IDM-{platform_name}{config['ext']}"
                
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    size_mb = file_size / (1024 * 1024)
                    self.logger.log_success(f"{platform_name} 版本构建成功！文件大小: {size_mb:.1f}MB")
                    return True
                else:
                    self.logger.log_error(f"{platform_name} 版本构建失败：输出文件不存在")
                    return False
            else:
                self.logger.log_error(f"{platform_name} 版本构建失败，返回码: {return_code}")
                return False
                
        except Exception as e:
            self.logger.log_error(f"{platform_name} 版本构建异常: {str(e)}")
            return False
    
    def show_menu(self) -> List[str]:
        """显示平台选择菜单"""
        print_colored("\n📋 请选择要构建的平台:", 'cyan')
        print_colored("1. Windows 版本 (推荐)", 'white')
        print_colored("2. Linux 版本", 'white')
        print_colored("3. MacOS 版本", 'white')
        print_colored("4. 所有平台", 'white')
        print_colored("5. 退出", 'white')
        
        while True:
            choice = input("\n请输入选择 (1-5): ").strip()
            if choice == '1':
                return ['Windows']
            elif choice == '2':
                return ['Linux']
            elif choice == '3':
                return ['Darwin']
            elif choice == '4':
                return ['Windows', 'Linux', 'Darwin']
            elif choice == '5':
                return []
            else:
                print_colored("❌ 无效选择，请输入 1-5", 'red')
    
    def show_build_summary(self, results: Dict[str, bool]):
        """显示构建总结"""
        self.logger.log_step("构建完成，显示结果", 'blue')
        
        print_colored("\n" + "=" * 80, 'cyan')
        print_colored("📊 构建结果总结", 'cyan')
        print_colored("=" * 80, 'cyan')
        
        success_count = 0
        total_size = 0
        
        for platform_name, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            color = 'green' if success else 'red'
            
            if success:
                config = self.get_platform_config(platform_name)
                output_file = f"dist/椰果IDM-{platform_name}{config['ext']}"
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    size_mb = file_size / (1024 * 1024)
                    total_size += file_size
                    success_count += 1
                    print_colored(f"{platform_name:10} : {status} ({size_mb:.1f}MB)", color)
                else:
                    print_colored(f"{platform_name:10} : {status} (文件未找到)", color)
            else:
                print_colored(f"{platform_name:10} : {status}", color)
        
        print_colored("=" * 80, 'cyan')
        print_colored(f"总计: {len(results)} 个平台, 成功: {success_count} 个", 'cyan')
        
        if success_count > 0:
            total_size_mb = total_size / (1024 * 1024)
            print_colored(f"总文件大小: {total_size_mb:.1f}MB", 'cyan')
            print_colored(f"\n📁 可执行文件位置: dist/ 目录", 'green')
            print_colored("🎉 构建完成！", 'green')
            print_colored("💡 提示: 生成的文件无需任何依赖，可直接在任何同平台计算机上运行", 'yellow')
            print_colored("🔧 优化: 使用了LZMA压缩和UPX压缩，文件大小已最小化", 'yellow')
        else:
            print_colored("\n❌ 所有平台构建都失败了", 'red')
    
    def run(self):
        """运行构建流程"""
        print_colored("=" * 80, 'cyan')
        print_colored("    椰果IDM v1.0.2 - 跨平台打包工具 (优化版)", 'cyan')
        print_colored("=" * 80, 'cyan')
        print_colored(f"当前平台: {platform.system()} ({platform.machine()})", 'yellow')
        print_colored(f"Python版本: {sys.version}", 'yellow')
        print_colored("=" * 80, 'cyan')
        
        # 检查依赖
        if not self.check_dependencies():
            self.logger.log_error("无法继续，请手动安装依赖")
            return
        
        # 清理构建目录
        self.clean_build_dirs()
        
        # 显示菜单并获取选择
        platforms = self.show_menu()
        if not platforms:
            self.logger.log_info("用户取消构建")
            return
        
        # 开始构建
        self.logger.log_step("开始构建流程", 'blue')
        results = {}
        
        for platform_name in platforms:
            success = self.build_for_platform(platform_name)
            results[platform_name] = success
        
        # 显示总结
        self.show_build_summary(results)


def main():
    """主函数"""
    build_manager = BuildManager()
    
    try:
        build_manager.run()
    except KeyboardInterrupt:
        print_colored("\n\n👋 用户取消操作", 'yellow')
    except Exception as e:
        print_colored(f"\n❌ 脚本执行异常: {str(e)}", 'red')
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
