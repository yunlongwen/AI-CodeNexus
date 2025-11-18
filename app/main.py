from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from loguru import logger

from .notifier.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from .routes import wechat
from .sources.ai_articles import pick_daily_ai_articles, todays_theme

# 全局 scheduler 实例
scheduler: Optional[AsyncIOScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时启动 scheduler，关闭时关闭 scheduler"""
    global scheduler

    # 启动时
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    @scheduler.scheduled_job("cron", hour=14, minute=0)
    async def job_send_daily_ai_digest() -> None:
        """Every day at 14:00, send 5 AI coding articles to WeCom group."""
        now = datetime.now()
        articles = pick_daily_ai_articles(k=5)
        if not articles:
            logger.warning("No AI articles available for today, skip sending.")
            return

        theme = todays_theme(now)
        date_str = now.strftime("%Y-%m-%d")
        items = [
            {
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "summary": a.summary,
            }
            for a in articles
        ]

        content = build_wecom_digest_markdown(date_str=date_str, theme=theme, items=items)
        logger.info("Sending daily AI digest to WeCom group...")
        await send_markdown_to_wecom(content)

    scheduler.start()
    logger.info("Scheduler started. Daily digest will be sent at 14:00 (Asia/Shanghai).")

    yield  # 应用运行期间

    # 关闭时
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="100kwhy WeChat MP Backend",
        lifespan=lifespan,
    )

    app.include_router(wechat.router, prefix="/wechat", tags=["wechat"])

    return app


app = create_app()


