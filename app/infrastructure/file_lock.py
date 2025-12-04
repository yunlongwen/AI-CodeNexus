"""文件锁模块，用于跨进程锁"""

import os
import sys
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

from loguru import logger


class FileLock:
    """跨进程文件锁"""
    
    def __init__(self, lock_name: str = "digest_job.lock"):
        """
        初始化文件锁
        
        Args:
            lock_name: 锁文件名
        """
        self.lock_name = lock_name
        self._lock_file_path: Optional[Path] = None
        self._lock_fd: Optional[int] = None
    
    def _get_lock_file_path(self) -> Path:
        """获取文件锁路径"""
        if self._lock_file_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            lock_dir = project_root / "data" / ".locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            self._lock_file_path = lock_dir / self.lock_name
        return self._lock_file_path
    
    def acquire(self, timeout: float = 0.1) -> bool:
        """
        尝试获取文件锁（跨进程锁）
        
        Args:
            timeout: 超时时间（未使用，保持接口一致性）
            
        Returns:
            True 如果成功获取锁，False 如果锁已被其他进程占用
        """
        lock_file = self._get_lock_file_path()
        try:
            # 尝试以独占模式打开文件
            if sys.platform == "win32":
                # Windows 使用 msvcrt
                self._lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
                try:
                    msvcrt.locking(self._lock_fd, msvcrt.LK_NBLCK, 1)  # 非阻塞锁定
                    return True
                except IOError:
                    os.close(self._lock_fd)
                    self._lock_fd = None
                    return False
            else:
                # Linux/Mac 使用 fcntl
                self._lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
                try:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except IOError:
                    os.close(self._lock_fd)
                    self._lock_fd = None
                    return False
        except Exception as e:
            logger.warning(f"[定时推送] 获取文件锁失败: {e}")
            if self._lock_fd is not None:
                try:
                    os.close(self._lock_fd)
                except Exception:
                    pass
                self._lock_fd = None
            return False
    
    def release(self):
        """释放文件锁"""
        try:
            if self._lock_fd is not None:
                if sys.platform == "win32":
                    msvcrt.locking(self._lock_fd, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
                self._lock_fd = None
            
            # 删除锁文件
            lock_file = self._get_lock_file_path()
            if lock_file.exists():
                lock_file.unlink()
        except Exception as e:
            logger.warning(f"[定时推送] 释放文件锁失败: {e}")
            self._lock_fd = None
    
    def __enter__(self):
        """上下文管理器入口"""
        if not self.acquire():
            raise RuntimeError("无法获取文件锁")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()

