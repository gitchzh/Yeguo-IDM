"""
下载队列管理模块

该模块负责管理下载队列，包括：
- 队列的添加、删除、暂停、恢复
- 优先级调整
- 队列状态监控
- 批量操作

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import time
from typing import Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from queue import PriorityQueue
import threading


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"      # 等待中
    DOWNLOADING = "downloading"  # 下载中
    PAUSED = "paused"        # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class DownloadTask:
    """下载任务数据类"""
    url: str
    format_info: Dict
    priority: int = 5  # 优先级 1-10，1最高
    status: DownloadStatus = DownloadStatus.PENDING
    created_time: float = None
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    speed: str = "0 KB/s"
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = time.time()


class QueueManager:
    """下载队列管理器"""
    
    def __init__(self):
        self._queue = PriorityQueue()
        self._tasks: Dict[str, DownloadTask] = {}
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {
            'task_added': [],
            'task_removed': [],
            'task_status_changed': [],
            'task_progress_updated': [],
        }
    
    def add_task(self, url: str, format_info: Dict, priority: int = 5) -> str:
        """添加下载任务"""
        with self._lock:
            task_id = f"{url}_{format_info.get('format_id', 'unknown')}"
            task = DownloadTask(url=url, format_info=format_info, priority=priority)
            self._tasks[task_id] = task
            self._queue.put((priority, task_id))
            self._notify_callbacks('task_added', task_id, task)
            return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """移除下载任务"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status == DownloadStatus.DOWNLOADING:
                    task.status = DownloadStatus.CANCELLED
                else:
                    del self._tasks[task_id]
                self._notify_callbacks('task_removed', task_id, task)
                return True
            return False
    
    def pause_task(self, task_id: str) -> bool:
        """暂停下载任务"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status == DownloadStatus.DOWNLOADING:
                    task.status = DownloadStatus.PAUSED
                    self._notify_callbacks('task_status_changed', task_id, task)
                    return True
            return False
    
    def resume_task(self, task_id: str) -> bool:
        """恢复下载任务"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status == DownloadStatus.PAUSED:
                    task.status = DownloadStatus.PENDING
                    self._queue.put((task.priority, task_id))
                    self._notify_callbacks('task_status_changed', task_id, task)
                    return True
            return False
    
    def set_priority(self, task_id: str, priority: int) -> bool:
        """设置任务优先级"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                old_priority = task.priority
                task.priority = max(1, min(10, priority))  # 限制在1-10范围内
                if task.status == DownloadStatus.PENDING:
                    # 重新加入队列
                    self._queue.put((task.priority, task_id))
                self._notify_callbacks('task_status_changed', task_id, task)
                return True
            return False
    
    def get_next_task(self) -> Optional[DownloadTask]:
        """获取下一个待下载任务"""
        with self._lock:
            if not self._queue.empty():
                priority, task_id = self._queue.get()
                if task_id in self._tasks:
                    task = self._tasks[task_id]
                    if task.status == DownloadStatus.PENDING:
                        task.status = DownloadStatus.DOWNLOADING
                        task.started_time = time.time()
                        self._notify_callbacks('task_status_changed', task_id, task)
                        return task
        return None
    
    def update_task_progress(self, task_id: str, progress: float, speed: str) -> bool:
        """更新任务进度"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.progress = progress
                task.speed = speed
                self._notify_callbacks('task_progress_updated', task_id, task)
                return True
            return False
    
    def complete_task(self, task_id: str, success: bool = True, error_message: str = None) -> bool:
        """完成任务"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.completed_time = time.time()
                if success:
                    task.status = DownloadStatus.COMPLETED
                    task.progress = 100.0
                else:
                    task.status = DownloadStatus.FAILED
                    task.error_message = error_message
                self._notify_callbacks('task_status_changed', task_id, task)
                return True
            return False
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务信息"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[DownloadTask]:
        """获取所有任务"""
        with self._lock:
            return list(self._tasks.values())
    
    def get_tasks_by_status(self, status: DownloadStatus) -> List[DownloadTask]:
        """根据状态获取任务"""
        with self._lock:
            return [task for task in self._tasks.values() if task.status == status]
    
    def clear_completed_tasks(self) -> int:
        """清理已完成的任务"""
        with self._lock:
            completed_tasks = [task_id for task_id, task in self._tasks.items() 
                             if task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]]
            for task_id in completed_tasks:
                del self._tasks[task_id]
            return len(completed_tasks)
    
    def pause_all_tasks(self) -> int:
        """暂停所有下载中的任务"""
        with self._lock:
            count = 0
            for task in self._tasks.values():
                if task.status == DownloadStatus.DOWNLOADING:
                    task.status = DownloadStatus.PAUSED
                    count += 1
                    self._notify_callbacks('task_status_changed', task.url, task)
            return count
    
    def resume_all_tasks(self) -> int:
        """恢复所有暂停的任务"""
        with self._lock:
            count = 0
            for task in self._tasks.values():
                if task.status == DownloadStatus.PAUSED:
                    task.status = DownloadStatus.PENDING
                    self._queue.put((task.priority, task.url))
                    count += 1
                    self._notify_callbacks('task_status_changed', task.url, task)
            return count
    
    def get_queue_stats(self) -> Dict:
        """获取队列统计信息"""
        with self._lock:
            stats = {
                'total': len(self._tasks),
                'pending': len([t for t in self._tasks.values() if t.status == DownloadStatus.PENDING]),
                'downloading': len([t for t in self._tasks.values() if t.status == DownloadStatus.DOWNLOADING]),
                'paused': len([t for t in self._tasks.values() if t.status == DownloadStatus.PAUSED]),
                'completed': len([t for t in self._tasks.values() if t.status == DownloadStatus.COMPLETED]),
                'failed': len([t for t in self._tasks.values() if t.status == DownloadStatus.FAILED]),
                'cancelled': len([t for t in self._tasks.values() if t.status == DownloadStatus.CANCELLED]),
            }
            return stats
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """注册回调函数"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _notify_callbacks(self, event: str, task_id: str, task: DownloadTask) -> None:
        """通知回调函数"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(task_id, task)
            except Exception as e:
                print(f"回调函数执行失败: {e}")


# 全局队列管理器实例
queue_manager = QueueManager()
