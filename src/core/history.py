"""
下载历史记录模块

该模块负责管理下载历史，包括：
- 历史记录的保存和加载
- 历史记录的查询和过滤
- 历史记录的清理和管理
- 重新下载功能

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading


@dataclass
class DownloadRecord:
    """下载记录数据类"""
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    filename: str = ""
    format_id: str = ""
    resolution: str = ""
    file_size: int = 0
    download_path: str = ""
    download_time: datetime = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    platform: str = ""  # youtube, bilibili等
    status: str = "completed"  # completed, failed, cancelled
    
    def __post_init__(self):
        if self.download_time is None:
            self.download_time = datetime.now()


class HistoryManager:
    """下载历史管理器"""
    
    def __init__(self, db_path: str = ":memory:"):
        """
        初始化历史管理器
        
        Args:
            db_path: 数据库路径，默认为内存数据库
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化数据库"""
        try:
            with self._lock:
                # 对于内存数据库，我们需要保持连接
                if self.db_path == ":memory:":
                    self._conn = sqlite3.connect(self.db_path)
                    self._conn.row_factory = sqlite3.Row  # 启用行工厂，便于访问列
                else:
                    self._conn = None  # 文件数据库在每次操作时创建连接
                
                cursor = self._get_cursor()
                
                # 创建下载历史表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS download_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        title TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        format_id TEXT NOT NULL,
                        resolution TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        download_path TEXT NOT NULL,
                        download_time TIMESTAMP NOT NULL,
                        duration INTEGER,
                        thumbnail_url TEXT,
                        platform TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'completed',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引以提高查询性能
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON download_history(url)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_download_time ON download_history(download_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_platform ON download_history(platform)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON download_history(status)')
                
                self._commit()
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"初始化数据库失败: {e}")
            self._rollback()
            raise
    
    def _get_cursor(self):
        """获取数据库游标"""
        if self.db_path == ":memory:" and hasattr(self, '_conn'):
            return self._conn.cursor()
        else:
            # 如果意外使用了文件数据库模式，抛出异常
            raise RuntimeError("文件数据库模式已被禁用，请使用内存数据库")
    
    def _commit(self):
        """提交事务"""
        if self.db_path == ":memory:" and hasattr(self, '_conn'):
            self._conn.commit()
    
    def _rollback(self):
        """回滚事务"""
        if self.db_path == ":memory:" and hasattr(self, '_conn'):
            self._conn.rollback()
    
    def _execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """执行数据库查询的通用方法"""
        cursor = None
        try:
            with self._lock:
                cursor = self._get_cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.lastrowid
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"数据库查询失败: {e}")
            return None
        finally:
            # 确保游标被正确关闭
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def add_record(self, record: DownloadRecord) -> int:
        """添加下载记录"""
        try:
            with self._lock:
                cursor = self._get_cursor()
                
                cursor.execute('''
                    INSERT INTO download_history 
                    (url, title, filename, format_id, resolution, file_size, download_path, 
                     download_time, duration, thumbnail_url, platform, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.url, record.title, record.filename, record.format_id,
                    record.resolution, record.file_size, record.download_path,
                    record.download_time.isoformat(), record.duration,
                    record.thumbnail_url, record.platform, record.status
                ))
                
                record_id = cursor.lastrowid
                self._commit()
                return record_id
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"添加下载记录失败: {e}")
            self._rollback()
            raise
    
    def get_record(self, record_id: int) -> Optional[DownloadRecord]:
        """根据ID获取下载记录"""
        row = self._execute_query('SELECT * FROM download_history WHERE id = ?', (record_id,), fetch_one=True)
        if row:
            return self._row_to_record(row)
        return None
    
    def get_records_by_url(self, url: str) -> List[DownloadRecord]:
        """根据URL获取下载记录"""
        rows = self._execute_query('SELECT * FROM download_history WHERE url = ? ORDER BY download_time DESC', (url,), fetch_all=True)
        if rows:
            return [self._row_to_record(row) for row in rows]
        return []
    
    def get_all_records(self, limit: Optional[int] = None, offset: int = 0) -> List[DownloadRecord]:
        """获取所有下载记录"""
        if limit:
            rows = self._execute_query('SELECT * FROM download_history ORDER BY download_time DESC LIMIT ? OFFSET ?', (limit, offset), fetch_all=True)
        else:
            rows = self._execute_query('SELECT * FROM download_history ORDER BY download_time DESC', fetch_all=True)
        
        if rows:
            return [self._row_to_record(row) for row in rows]
        return []
    
    def search_records(self, keyword: str, limit: Optional[int] = None) -> List[DownloadRecord]:
        """搜索下载记录"""
        search_pattern = f'%{keyword}%'
        if limit:
            rows = self._execute_query('''
                SELECT * FROM download_history 
                WHERE title LIKE ? OR filename LIKE ? OR url LIKE ?
                ORDER BY download_time DESC LIMIT ?
            ''', (search_pattern, search_pattern, search_pattern, limit), fetch_all=True)
        else:
            rows = self._execute_query('''
                SELECT * FROM download_history 
                WHERE title LIKE ? OR filename LIKE ? OR url LIKE ?
                ORDER BY download_time DESC
            ''', (search_pattern, search_pattern, search_pattern), fetch_all=True)
        
        if rows:
            return [self._row_to_record(row) for row in rows]
        return []
    
    def get_records_by_platform(self, platform: str, limit: Optional[int] = None) -> List[DownloadRecord]:
        """根据平台获取下载记录"""
        if limit:
            rows = self._execute_query('SELECT * FROM download_history WHERE platform = ? ORDER BY download_time DESC LIMIT ?', (platform, limit), fetch_all=True)
        else:
            rows = self._execute_query('SELECT * FROM download_history WHERE platform = ? ORDER BY download_time DESC', (platform,), fetch_all=True)
        
        if rows:
            return [self._row_to_record(row) for row in rows]
        return []
    
    def get_records_by_date_range(self, start_date: datetime, end_date: datetime) -> List[DownloadRecord]:
        """根据日期范围获取下载记录"""
        rows = self._execute_query('''
            SELECT * FROM download_history 
            WHERE download_time BETWEEN ? AND ?
            ORDER BY download_time DESC
        ''', (start_date.isoformat(), end_date.isoformat()), fetch_all=True)
        
        if rows:
            return [self._row_to_record(row) for row in rows]
        return []
    
    def get_recent_records(self, days: int = 7) -> List[DownloadRecord]:
        """获取最近几天的下载记录"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.get_records_by_date_range(start_date, end_date)
    
    def update_record_status(self, record_id: int, status: str) -> bool:
        """更新记录状态"""
        try:
            with self._lock:
                cursor = self._get_cursor()
                cursor.execute('UPDATE download_history SET status = ? WHERE id = ?', (status, record_id))
                affected_rows = cursor.rowcount
                self._commit()
                return affected_rows > 0
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"更新记录状态失败: {e}")
            return False
    
    def delete_record(self, record_id: int) -> bool:
        """删除下载记录"""
        try:
            with self._lock:
                cursor = self._get_cursor()
                cursor.execute('DELETE FROM download_history WHERE id = ?', (record_id,))
                affected_rows = cursor.rowcount
                self._commit()
                return affected_rows > 0
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"删除记录失败: {e}")
            return False
    
    def delete_records_by_url(self, url: str) -> int:
        """根据URL删除下载记录"""
        try:
            with self._lock:
                cursor = self._get_cursor()
                cursor.execute('DELETE FROM download_history WHERE url = ?', (url,))
                affected_rows = cursor.rowcount
                self._commit()
                return affected_rows
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"根据URL删除记录失败: {e}")
            return 0
    
    def clear_old_records(self, days: int = 30) -> int:
        """清理指定天数之前的记录"""
        try:
            with self._lock:
                cursor = self._get_cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute('DELETE FROM download_history WHERE download_time < ?', (cutoff_date,))
                affected_rows = cursor.rowcount
                self._commit()
                return affected_rows
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"清理旧记录失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """获取下载统计信息"""
        try:
            with self._lock:
                cursor = self._get_cursor()
                
                # 总记录数
                cursor.execute('SELECT COUNT(*) FROM download_history')
                total_records = cursor.fetchone()[0]
                
                # 按平台统计
                cursor.execute('SELECT platform, COUNT(*) FROM download_history GROUP BY platform')
                platform_stats = dict(cursor.fetchall())
                
                # 按状态统计
                cursor.execute('SELECT status, COUNT(*) FROM download_history GROUP BY status')
                status_stats = dict(cursor.fetchall())
                
                # 总文件大小
                cursor.execute('SELECT SUM(file_size) FROM download_history WHERE file_size > 0')
                total_size = cursor.fetchone()[0] or 0
                
                # 最近7天的下载数
                seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute('SELECT COUNT(*) FROM download_history WHERE download_time >= ?', (seven_days_ago,))
                recent_downloads = cursor.fetchone()[0]
                
                return {
                    'total_records': total_records,
                    'platform_stats': platform_stats,
                    'status_stats': status_stats,
                    'total_size': total_size,
                    'recent_downloads': recent_downloads
                }
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"获取统计信息失败: {e}")
            return {
                'total_records': 0,
                'platform_stats': {},
                'status_stats': {},
                'total_size': 0,
                'recent_downloads': 0
            }
    
    def export_history(self, file_path: str, format: str = 'json') -> bool:
        """导出下载历史"""
        try:
            records = self.get_all_records()
            
            if format.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([asdict(record) for record in records], f, ensure_ascii=False, indent=2, default=str)
            elif format.lower() == 'csv':
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # 写入表头
                    writer.writerow(['ID', 'URL', '标题', '文件名', '格式ID', '分辨率', '文件大小', '下载路径', '下载时间', '时长', '缩略图URL', '平台', '状态'])
                    # 写入数据
                    for record in records:
                        writer.writerow([
                            record.id, record.url, record.title, record.filename,
                            record.format_id, record.resolution, record.file_size,
                            record.download_path, record.download_time, record.duration,
                            record.thumbnail_url, record.platform, record.status
                        ])
            else:
                return False
            
            return True
        except Exception as e:
            logger.error(f"导出历史记录失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        try:
            if hasattr(self, '_conn') and self._conn:
                self._conn.close()
                self._conn = None
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"关闭数据库连接失败: {e}")
    
    def __del__(self):
        """析构函数，确保连接被关闭"""
        try:
            self.close()
        except Exception:
            pass
    
    def _row_to_record(self, row: Tuple) -> DownloadRecord:
        """将数据库行转换为DownloadRecord对象"""
        return DownloadRecord(
            id=row[0],
            url=row[1],
            title=row[2],
            filename=row[3],
            format_id=row[4],
            resolution=row[5],
            file_size=row[6],
            download_path=row[7],
            download_time=datetime.fromisoformat(row[8]) if row[8] else None,
            duration=row[9],
            thumbnail_url=row[10],
            platform=row[11],
            status=row[12]
        )


# 全局历史管理器实例
history_manager = HistoryManager()
