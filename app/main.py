"""应用主入口 - Clean架构重构版"""

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

# Windows 和 Linux 的文件锁
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

# On Windows, the default asyncio event loop (ProactorEventLoop) does not support
# subprocesses, which Playwright needs to launch browsers.
# We switch to SelectorEventLoop, which does.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv

# 在所有模块导入前，从 .env 文件加载环境变量
# 添加错误处理，避免 .env 文件格式错误导致启动失败
try:
    load_dotenv()
except Exception as e:  # noqa: BLE001
    # logger 还未导入，使用 print 输出警告
    print(f"Warning: Failed to load .env file: {e}. Continuing with environment variables...")

from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .config_loader import load_digest_schedule
from .infrastructure import setup_logging, SchedulerManager
from .infrastructure.db import init_db
from .presentation import get_index_html
from .services import DigestService, BackupService

# 全局调度器管理器
scheduler_manager: Optional[SchedulerManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时启动 scheduler，关闭时关闭 scheduler"""
    global scheduler_manager

    # 配置日志系统
    setup_logging()
    logger.info("=" * 80)
    logger.info("应用启动，初始化日志系统和调度器...")
    
    # 初始化数据库
    try:
        await init_db()
        logger.info("[数据库] 数据库初始化完成")
    except Exception as e:
        logger.error(f"[数据库] 数据库初始化失败: {e}")
        # 数据库初始化失败不影响应用启动，但会记录错误
    
    # 创建调度器管理器
    scheduler_manager = SchedulerManager(timezone="Asia/Shanghai")
    scheduler = scheduler_manager.create_scheduler()
    
    # 从配置文件加载定时任务参数
    schedule = load_digest_schedule()
    digest_hour = schedule.hour
    digest_minute = schedule.minute
    digest_count = schedule.count

    # 创建服务实例
    digest_service = DigestService()
    backup_service = BackupService()

    # 配置推送任务触发器
    if schedule.cron:
        # 解析cron表达式，确保周一到周五正确解析
        # cron格式: 分 时 日 月 周
        # 周字段: 0=周日, 1=周一, ..., 6=周六
        # 1-5 表示周一到周五
        cron_parts = schedule.cron.strip().split()
        if len(cron_parts) == 5:
            minute, hour, day, month, day_of_week = cron_parts
            # 使用CronTrigger构造函数，明确指定day_of_week参数
            # APScheduler支持day_of_week='1-5'表示周一到周五
            # 直接传递字符串参数，让CronTrigger自己解析
            trigger_kwargs = {
                "timezone": "Asia/Shanghai"
            }
            if minute != '*':
                trigger_kwargs['minute'] = minute
            if hour != '*':
                trigger_kwargs['hour'] = hour
            if day != '*':
                trigger_kwargs['day'] = day
            if month != '*':
                trigger_kwargs['month'] = month
            if day_of_week != '*':
                trigger_kwargs['day_of_week'] = day_of_week
            trigger = CronTrigger(**trigger_kwargs)
        else:
            # 如果解析失败，使用from_crontab作为后备
            trigger = CronTrigger.from_crontab(schedule.cron, timezone="Asia/Shanghai")
        scheduler_manager.add_job(
            digest_service.send_daily_digest,
            trigger=trigger,
            job_id="daily_ai_digest",
            kwargs={"digest_count": digest_count},
        )
        logger.info(
            "[调度器] 已添加推送任务，使用 cron 表达式: %r, 每次推送 %d 篇文章",
            schedule.cron,
            digest_count,
        )
    else:
        scheduler_manager.add_cron_job(
            digest_service.send_daily_digest,
            hour=digest_hour,
            minute=digest_minute,
            job_id="daily_ai_digest",
            kwargs={"digest_count": digest_count},
        )
        logger.info(
            "[调度器] 已添加推送任务，每日推送时间: %02d:%02d (Asia/Shanghai), "
            "每次推送 %d 篇文章",
            digest_hour,
            digest_minute,
            digest_count,
        )
    
    # 验证任务是否已正确添加
    job = scheduler_manager.get_job("daily_ai_digest")
    if job:
        next_run = getattr(job, 'next_run_time', None)
        if next_run:
            logger.info(f"[调度器] 推送任务已确认添加，下次执行时间: {next_run}")
        else:
            logger.info("[调度器] 推送任务已确认添加（启动后显示执行时间）")
    else:
        logger.error("[调度器] 警告：推送任务添加失败，未找到任务！")

    # 添加数据备份任务：每天 23:00 执行（备份config目录）
    # 已禁用每日定时备份
    # scheduler_manager.add_cron_job(
    #     backup_service.backup_data_to_github,
    #     hour=23,
    #     minute=0,
    #     job_id="daily_data_backup",
    # )
    # logger.info("[调度器] 已添加数据备份任务，每日 23:00 执行（备份config目录）")
    
    # 启动调度器
    scheduler_manager.start()

    yield  # 应用运行期间

    # 关闭时
    if scheduler_manager is not None:
        scheduler_manager.shutdown(wait=True)
        scheduler_manager = None


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title="Daily Digest API",
        description="每日新闻精选 - 自动抓取、筛选、推送系统",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 挂载静态资源目录，用于提供公众号二维码等图片
    static_dir = Path(__file__).resolve().parent / "presentation" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 首页路由（支持所有前端路由）
    @app.get("/", response_class=HTMLResponse)
    @app.get("/news", response_class=HTMLResponse)
    @app.get("/ai-news", response_class=HTMLResponse)
    @app.get("/tools", response_class=HTMLResponse)
    @app.get("/hot-news", response_class=HTMLResponse)
    @app.get("/recent", response_class=HTMLResponse)
    @app.get("/submit", response_class=HTMLResponse)
    @app.get("/submit-tool", response_class=HTMLResponse)
    @app.get("/wechat-mp", response_class=HTMLResponse)
    @app.get("/prompts", response_class=HTMLResponse)
    @app.get("/rules", response_class=HTMLResponse)
    @app.get("/resources", response_class=HTMLResponse)
    @app.get("/weekly/{weekly_id}", response_class=HTMLResponse)
    @app.get("/category/{category}", response_class=HTMLResponse)
    @app.get("/tool/{tool_id_or_identifier}", response_class=HTMLResponse)
    async def root(
        category: str = None,
        tool_id_or_identifier: str = None,
        weekly_id: str = None
    ):
        """AICoding基地 首页（支持所有前端路由）"""
        html = get_index_html()
        return HTMLResponse(content=html)

    @app.get("/health")
    async def health_check():
        """健康检查接口"""
        return {"status": "ok", "service": "100kwhy-wechat-mp"}

    # 注册路由
    from .presentation.routes import wechat, digest
    app.include_router(wechat.router, prefix="/wechat", tags=["wechat"])
    app.include_router(digest.router, prefix="/digest", tags=["digest"])
    
    # 注册API路由
    from .presentation.routes import api
    app.include_router(api.router, prefix="/api", tags=["api"])
    
    # 注册AI助手路由
    from .presentation.routes import ai_assistant
    app.include_router(ai_assistant.router, prefix="/api/ai-assistant", tags=["ai-assistant"])

    return app


app = create_app()
