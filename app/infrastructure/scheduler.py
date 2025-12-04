"""调度器管理模块"""

import asyncio
from typing import Optional, Callable, Any, Dict
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger


class SchedulerManager:
    """调度器管理器"""
    
    def __init__(self, timezone: str = "Asia/Shanghai"):
        """
        初始化调度器管理器
        
        Args:
            timezone: 时区
        """
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.timezone = timezone
        self._lock = asyncio.Lock()
    
    def create_scheduler(self) -> AsyncIOScheduler:
        """创建调度器实例"""
        if self.scheduler is not None and self.scheduler.running:
            logger.warning("[调度器] 检测到已有调度器在运行，正在关闭...")
            try:
                self.scheduler.shutdown(wait=False)
            except Exception as e:
                logger.warning(f"[调度器] 关闭旧调度器时出错: {e}")
        
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)
        logger.info("[调度器] 调度器实例已创建")
        return self.scheduler
    
    def add_job(
        self,
        func: Callable,
        trigger: str | CronTrigger,
        job_id: str,
        **kwargs: Any
    ) -> None:
        """
        添加定时任务
        
        Args:
            func: 要执行的函数
            trigger: 触发器（cron表达式字符串或CronTrigger对象）
            job_id: 任务ID
            **kwargs: 其他参数（如kwargs传递给函数）
        """
        if self.scheduler is None:
            raise RuntimeError("调度器未初始化，请先调用 create_scheduler()")
        
        # 如果trigger是字符串，转换为CronTrigger
        if isinstance(trigger, str):
            trigger = CronTrigger.from_crontab(trigger, timezone=self.timezone)
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        logger.info(f"[调度器] 已添加任务: {job_id}")
    
    def add_cron_job(
        self,
        func: Callable,
        hour: int,
        minute: int,
        job_id: str,
        **kwargs: Any
    ) -> None:
        """
        添加cron定时任务
        
        Args:
            func: 要执行的函数
            hour: 小时
            minute: 分钟
            job_id: 任务ID
            **kwargs: 其他参数
        """
        if self.scheduler is None:
            raise RuntimeError("调度器未初始化，请先调用 create_scheduler()")
        
        self.scheduler.add_job(
            func,
            "cron",
            hour=hour,
            minute=minute,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        logger.info(
            f"[调度器] 已添加任务: {job_id}, "
            f"执行时间: {hour:02d}:{minute:02d} ({self.timezone})"
        )
    
    def start(self) -> None:
        """启动调度器"""
        if self.scheduler is None:
            raise RuntimeError("调度器未初始化，请先调用 create_scheduler()")
        
        self.scheduler.start()
        logger.info("[调度器] 调度器已启动，等待触发定时任务...")
        
        # 列出所有已添加的任务
        all_jobs = self.scheduler.get_jobs()
        logger.info(f"[调度器] 当前共有 {len(all_jobs)} 个定时任务:")
        for job in all_jobs:
            next_run = getattr(job, 'next_run_time', None) or getattr(job, 'next_run', None)
            if next_run:
                logger.info(f"[调度器]   - {job.id}: 下次执行时间 = {next_run}")
            else:
                logger.info(f"[调度器]   - {job.id}: 已添加（执行时间待计算）")
    
    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器"""
        if self.scheduler is not None:
            try:
                if self.scheduler.running:
                    self.scheduler.shutdown(wait=wait)
                    logger.info("[调度器] 调度器已关闭")
                else:
                    logger.info("[调度器] 调度器未运行，无需关闭")
            except Exception as e:
                logger.error(f"[调度器] 关闭调度器时出错: {e}")
            finally:
                self.scheduler = None
    
    def get_job(self, job_id: str) -> Optional[Any]:
        """获取任务"""
        if self.scheduler is None:
            return None
        return self.scheduler.get_job(job_id)
    
    @property
    def running(self) -> bool:
        """检查调度器是否运行中"""
        return self.scheduler is not None and self.scheduler.running

