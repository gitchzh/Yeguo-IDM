"""
配置管理模块

该模块包含应用程序的全局配置参数，负责：
- 应用程序版本信息管理
- 下载和解析的配置参数
- 系统限制和性能参数
- 全局常量和默认值

主要类：
- Config: 应用程序全局配置类

作者: 椰果IDM开发团队
版本: 1.5.0
"""

from typing import Optional


class Config:
    """
    应用程序全局配置类
    
    包含应用程序运行所需的各种配置参数，如并发下载数、缓存限制等。
    所有配置项都集中在此类中管理，便于维护和修改。
    """
    
    # 最大并发下载数量，避免过多线程影响系统性能
    MAX_CONCURRENT_DOWNLOADS = 5
    
    # 解析结果缓存限制，避免内存占用过多
    CACHE_LIMIT = 20  # 增加缓存限制，但添加内存监控
    
    # 内存使用监控阈值（MB）
    MEMORY_WARNING_THRESHOLD = 500  # 500MB警告阈值
    MEMORY_CRITICAL_THRESHOLD = 1000  # 1GB临界阈值
    
    # 默认下载速度限制（KB/s），None 表示无限制
    DEFAULT_SPEED_LIMIT: Optional[int] = None
    
    # 应用程序版本号
    APP_VERSION = "1.5.0"
    
    # 文件名最大长度限制，避免系统文件名过长问题
    MAX_FILENAME_LENGTH = 200
    
    # 线程安全配置
    MAX_THREAD_WAIT_TIME = 30  # 线程最大等待时间（秒）
    THREAD_CLEANUP_INTERVAL = 60  # 线程清理间隔（秒）
    
    # 错误处理配置
    MAX_RETRY_ATTEMPTS = 3  # 最大重试次数
    RETRY_DELAY = 2  # 重试延迟（秒）
    
    # 超时配置 - 改进版本
    DEFAULT_TIMEOUT = 60  # 默认超时时间（秒）
    YOUTUBE_TIMEOUT = 90  # YouTube超时时间（秒）
    BILIBILI_TIMEOUT = 180  # B站超时时间（秒）
    
    # 网络超时配置
    NETWORK_TIMEOUTS = {
        'socket_timeout': 30,        # Socket超时（秒）
        'connect_timeout': 15,       # 连接超时（秒）
        'read_timeout': 60,          # 读取超时（秒）
        'write_timeout': 60,         # 写入超时（秒）
        'retry_timeout': 5,          # 重试间隔（秒）
        'max_retry_timeout': 300,    # 最大重试超时（秒）
    }
    
    # 智能超时配置
    SMART_TIMEOUT_ENABLED = True    # 是否启用智能超时
    TIMEOUT_ADAPTATION_FACTOR = 1.5 # 超时自适应因子
    MIN_TIMEOUT = 5                 # 最小超时时间（秒）
    MAX_TIMEOUT = 600               # 最大超时时间（秒）
    

    
    # 启动配置
    STARTUP_SHOW_WARNINGS = False   # 启动时是否显示警告信息

    
    @classmethod
    def validate_config(cls) -> tuple[bool, list[str]]:
        """
        验证配置参数的有效性 - 改进版本
        
        Returns:
            tuple[bool, list[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        try:
            # 验证数值配置
            if cls.MAX_CONCURRENT_DOWNLOADS <= 0:
                errors.append(f"MAX_CONCURRENT_DOWNLOADS 必须大于0，当前值: {cls.MAX_CONCURRENT_DOWNLOADS}")
            elif cls.MAX_CONCURRENT_DOWNLOADS > 10:
                errors.append(f"MAX_CONCURRENT_DOWNLOADS 建议不超过10，当前值: {cls.MAX_CONCURRENT_DOWNLOADS}")
            
            if cls.CACHE_LIMIT <= 0:
                errors.append(f"CACHE_LIMIT 必须大于0，当前值: {cls.CACHE_LIMIT}")
            elif cls.CACHE_LIMIT > 100:
                errors.append(f"CACHE_LIMIT 建议不超过100，当前值: {cls.CACHE_LIMIT}")
            
            if cls.MEMORY_WARNING_THRESHOLD <= 0:
                errors.append(f"MEMORY_WARNING_THRESHOLD 必须大于0，当前值: {cls.MEMORY_WARNING_THRESHOLD}")
            elif cls.MEMORY_WARNING_THRESHOLD > 2000:
                errors.append(f"MEMORY_WARNING_THRESHOLD 建议不超过2000MB，当前值: {cls.MEMORY_WARNING_THRESHOLD}")
            
            if cls.MEMORY_CRITICAL_THRESHOLD <= 0:
                errors.append(f"MEMORY_CRITICAL_THRESHOLD 必须大于0，当前值: {cls.MEMORY_CRITICAL_THRESHOLD}")
            elif cls.MEMORY_CRITICAL_THRESHOLD > 5000:
                errors.append(f"MEMORY_CRITICAL_THRESHOLD 建议不超过5000MB，当前值: {cls.MEMORY_CRITICAL_THRESHOLD}")
            
            if cls.MEMORY_CRITICAL_THRESHOLD <= cls.MEMORY_WARNING_THRESHOLD:
                errors.append(f"MEMORY_CRITICAL_THRESHOLD ({cls.MEMORY_CRITICAL_THRESHOLD}) 必须大于 MEMORY_WARNING_THRESHOLD ({cls.MEMORY_WARNING_THRESHOLD})")
            
            if cls.MAX_FILENAME_LENGTH <= 0:
                errors.append(f"MAX_FILENAME_LENGTH 必须大于0，当前值: {cls.MAX_FILENAME_LENGTH}")
            elif cls.MAX_FILENAME_LENGTH > 500:
                errors.append(f"MAX_FILENAME_LENGTH 建议不超过500，当前值: {cls.MAX_FILENAME_LENGTH}")
            
            if cls.MAX_THREAD_WAIT_TIME <= 0:
                errors.append(f"MAX_THREAD_WAIT_TIME 必须大于0，当前值: {cls.MAX_THREAD_WAIT_TIME}")
            elif cls.MAX_THREAD_WAIT_TIME > 300:
                errors.append(f"MAX_THREAD_WAIT_TIME 建议不超过300秒，当前值: {cls.MAX_THREAD_WAIT_TIME}")
            
            if cls.THREAD_CLEANUP_INTERVAL <= 0:
                errors.append(f"THREAD_CLEANUP_INTERVAL 必须大于0，当前值: {cls.THREAD_CLEANUP_INTERVAL}")
            elif cls.THREAD_CLEANUP_INTERVAL > 600:
                errors.append(f"THREAD_CLEANUP_INTERVAL 建议不超过600秒，当前值: {cls.THREAD_CLEANUP_INTERVAL}")
            
            if cls.MAX_RETRY_ATTEMPTS <= 0:
                errors.append(f"MAX_RETRY_ATTEMPTS 必须大于0，当前值: {cls.MAX_RETRY_ATTEMPTS}")
            elif cls.MAX_RETRY_ATTEMPTS > 10:
                errors.append(f"MAX_RETRY_ATTEMPTS 建议不超过10，当前值: {cls.MAX_RETRY_ATTEMPTS}")
            
            if cls.RETRY_DELAY < 0:
                errors.append(f"RETRY_DELAY 不能为负数，当前值: {cls.RETRY_DELAY}")
            elif cls.RETRY_DELAY > 60:
                errors.append(f"RETRY_DELAY 建议不超过60秒，当前值: {cls.RETRY_DELAY}")
            
            if cls.DEFAULT_TIMEOUT <= 0:
                errors.append(f"DEFAULT_TIMEOUT 必须大于0，当前值: {cls.DEFAULT_TIMEOUT}")
            elif cls.DEFAULT_TIMEOUT > 600:
                errors.append(f"DEFAULT_TIMEOUT 建议不超过600秒，当前值: {cls.DEFAULT_TIMEOUT}")
            
            
            
            # 验证版本号格式
            if not cls.APP_VERSION or not isinstance(cls.APP_VERSION, str):
                errors.append("APP_VERSION 必须是有效的版本号字符串")
            elif not cls.APP_VERSION.replace('.', '').replace('v', '').isdigit():
                errors.append(f"APP_VERSION 格式无效: {cls.APP_VERSION}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"配置验证过程中发生异常: {e}")
            return False, errors
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """
        获取配置摘要信息
        
        Returns:
            dict: 配置摘要
        """
        return {
            "version": cls.APP_VERSION,
            "max_concurrent_downloads": cls.MAX_CONCURRENT_DOWNLOADS,
            "cache_limit": cls.CACHE_LIMIT,
            "memory_warning_threshold_mb": cls.MEMORY_WARNING_THRESHOLD,
            "memory_critical_threshold_mb": cls.MEMORY_CRITICAL_THRESHOLD,
            "max_filename_length": cls.MAX_FILENAME_LENGTH,
            "max_thread_wait_time": cls.MAX_THREAD_WAIT_TIME,
            "thread_cleanup_interval": cls.THREAD_CLEANUP_INTERVAL,
            "max_retry_attempts": cls.MAX_RETRY_ATTEMPTS,
            "retry_delay": cls.RETRY_DELAY,
            "default_timeout": cls.DEFAULT_TIMEOUT,
            "startup_show_warnings": cls.STARTUP_SHOW_WARNINGS
        }
