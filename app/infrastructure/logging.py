"""日志配置模块"""

from pathlib import Path
from loguru import logger


def setup_logging():
    """
    配置日志系统，将日志保存到文件
    """
    # 创建 logs 目录
    project_root = Path(__file__).resolve().parent.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # 配置主日志文件（所有日志）
    # 按日期轮转，保留30天，压缩旧日志
    logger.add(
        logs_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 每天午夜轮转
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        encoding="utf-8",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        enqueue=True,  # 异步写入，避免阻塞
    )
    
    # 配置错误日志文件（只记录 ERROR 及以上级别）
    logger.add(
        logs_dir / "error_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="90 days",  # 错误日志保留更久
        compression="zip",
        encoding="utf-8",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        enqueue=True,
    )
    
    # 配置定时任务专用日志文件（包含关键前缀的日志）
    # 使用过滤器只记录定时任务相关的日志
    def scheduler_filter(record):
        """过滤定时任务相关的日志"""
        message = record["message"]
        return any(
            prefix in message
            for prefix in [
                "[定时推送]",
                "[自动抓取]",
                "[数据备份]",
                "[调度器]",
            ]
        )
    
    logger.add(
        logs_dir / "scheduler_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="90 days",  # 定时任务日志保留更久
        compression="zip",
        encoding="utf-8",
        level="INFO",
        filter=scheduler_filter,  # 只记录定时任务相关日志
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
        enqueue=True,
    )
    
    logger.info("日志系统已配置，日志文件保存在 logs/ 目录")

