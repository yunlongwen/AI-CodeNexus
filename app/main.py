import asyncio
import sys

# On Windows, the default asyncio event loop (ProactorEventLoop) does not support
# subprocesses, which Playwright needs to launch browsers.
# We switch to SelectorEventLoop, which does.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 在所有模块导入前，从 .env 文件加载环境变量
load_dotenv()

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .config_loader import load_digest_schedule
from .notifier.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from .routes import wechat, digest
from .sources.ai_articles import pick_daily_ai_articles, todays_theme, clear_articles
from .sources.ai_candidates import promote_candidates_to_articles, clear_candidate_pool

# 全局 scheduler 实例
scheduler: Optional[AsyncIOScheduler] = None


async def job_send_daily_ai_digest(digest_count: int) -> None:
    """Send AI coding articles digest to WeCom group."""
    now = datetime.now()
    articles = pick_daily_ai_articles(k=digest_count)
    if not articles:
        logger.info("Article pool is empty before scheduled push, promoting from candidates...")
        promoted = promote_candidates_to_articles(per_keyword=2)
        if promoted:
            articles = pick_daily_ai_articles(k=digest_count)
        else:
            logger.warning("No candidates available to promote, skip sending.")
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
    clear_articles()
    clear_candidate_pool()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时启动 scheduler，关闭时关闭 scheduler"""
    global scheduler

    # 从配置文件加载定时任务参数
    schedule = load_digest_schedule()
    digest_hour = schedule.hour
    digest_minute = schedule.minute
    digest_count = schedule.count

    # 启动时
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    # 配置触发器：优先使用 cron 表达式
    if schedule.cron:
        trigger = CronTrigger.from_crontab(schedule.cron, timezone="Asia/Shanghai")
        scheduler.add_job(
            job_send_daily_ai_digest,
            trigger=trigger,
            id="daily_ai_digest",
            kwargs={"digest_count": digest_count},
            replace_existing=True,
        )
        logger.info(
            "Scheduler started with cron=%r, count=%d.",
            schedule.cron,
            digest_count,
        )
    else:
        scheduler.add_job(
            job_send_daily_ai_digest,
            "cron",
            hour=digest_hour,
            minute=digest_minute,
            id="daily_ai_digest",
            kwargs={"digest_count": digest_count},
            replace_existing=True,
        )
        logger.info(
            "Scheduler started. Daily digest will be sent at %02d:%02d (Asia/Shanghai), "
            "with up to %d articles.",
            digest_hour,
            digest_minute,
            digest_count,
        )

    scheduler.start()

    yield  # 应用运行期间

    # 关闭时
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Daily Digest API",
        description="每日新闻精选 - 自动抓取、筛选、推送系统",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 挂载静态资源目录，用于提供公众号二维码等图片
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Daily Digest 首页：介绍 + 入口"""
        html = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>Daily Digest · 每日新闻精选</title>
          <style>
            * { box-sizing: border-box; }
            body {
              margin: 0;
              font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              background: radial-gradient(circle at top, #eff6ff 0, #f9fafb 45%, #f3f4f6 100%);
              color: #111827;
            }
            .page {
              min-height: 100vh;
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              padding: 32px 16px;
            }
            .logo {
              font-weight: 800;
              font-size: 26px;
              letter-spacing: .08em;
              text-transform: uppercase;
              color: #111827;
              display: flex;
              align-items: center;
              gap: 8px;
              margin-bottom: 16px;
            }
            .logo-mark {
              width: 32px;
              height: 32px;
              border-radius: 12px;
              background: linear-gradient(135deg, #2563eb, #4f46e5);
              display: flex;
              align-items: center;
              justify-content: center;
              color: #fff;
              font-size: 18px;
              box-shadow: 0 10px 25px rgba(37,99,235,0.35);
            }
            .card {
              max-width: 640px;
              width: 100%;
              background: rgba(255,255,255,0.92);
              border-radius: 24px;
              padding: 24px 24px 20px;
              box-shadow:
                0 18px 45px rgba(15,23,42,0.18),
                0 0 0 1px rgba(148,163,184,0.18);
              backdrop-filter: blur(12px);
            }
            h1 {
              font-size: 24px;
              margin: 0 0 8px;
            }
            .subtitle {
              font-size: 14px;
              color: #6b7280;
              margin-bottom: 16px;
            }
            .badges {
              display: flex;
              flex-wrap: wrap;
              gap: 8px;
              margin-bottom: 16px;
            }
            .badge {
              font-size: 12px;
              padding: 4px 10px;
              border-radius: 999px;
              background: #eff6ff;
              color: #1d4ed8;
            }
            .badge.neutral {
              background: #f3f4f6;
              color: #4b5563;
            }
            .actions {
              display: flex;
              flex-wrap: wrap;
              gap: 10px;
              margin-top: 12px;
              margin-bottom: 8px;
            }
            .btn {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              padding: 9px 18px;
              border-radius: 999px;
              border: none;
              cursor: pointer;
              font-size: 14px;
              text-decoration: none;
              white-space: nowrap;
            }
            .btn-primary {
              background: linear-gradient(135deg, #2563eb, #4f46e5);
              color: #fff;
              box-shadow: 0 10px 25px rgba(37,99,235,0.45);
            }
            .btn-primary:hover {
              background: linear-gradient(135deg, #1d4ed8, #4338ca);
            }
            .btn-ghost {
              background: transparent;
              color: #374151;
              border: 1px solid rgba(156,163,175,0.7);
            }
            .btn-ghost:hover {
              background: rgba(249,250,251,0.8);
            }
            .qr-section {
              margin-top: 4px;
              margin-bottom: 10px;
              display: flex;
              align-items: center;
              gap: 12px;
            }
            .qr-section img {
              width: 80px;
              height: 80px;
              border-radius: 16px;
              box-shadow: 0 10px 25px rgba(15,23,42,0.18);
            }
            .qr-text {
              font-size: 13px;
              color: #4b5563;
            }
            .meta {
              font-size: 12px;
              color: #9ca3af;
              margin-top: 4px;
            }
            .meta a {
              color: #4b5563;
              text-decoration: none;
            }
            .meta a:hover {
              text-decoration: underline;
            }
            @media (max-width: 640px) {
              .card {
                padding: 20px 18px 18px;
                border-radius: 20px;
              }
              h1 {
                font-size: 20px;
              }
            }
          </style>
        </head>
        <body>
          <div class="page">
            <div class="logo">
              <div class="logo-mark">DN</div>
              <span>Daily Digest</span>
            </div>
            <div class="card">
              <h1>每日新闻精选 · 日报中心</h1>
              <div class="subtitle">
                聚焦最新行业与技术动态，每天将精选资讯自动推送到你的企业微信群。
              </div>
              <div class="badges">
                <span class="badge">每日定时推送</span>
                <span class="badge">企业微信机器人</span>
                <span class="badge neutral">后台管理面板</span>
              </div>
              <div class="actions">
                <a class="btn btn-primary" href="/digest/panel">进入管理员面板</a>
                <a class="btn btn-ghost" href="/static/wechat_mp_qr.jpg" target="_blank" rel="noopener noreferrer">
                  查看微信公众号
                </a>
              </div>
              <div class="meta">
                开源仓库：<a href="https://github.com/yunlongwen/100kwhy_wechat_mp" target="_blank" rel="noopener noreferrer">github.com/yunlongwen/100kwhy_wechat_mp</a>
              </div>
            </div>
          </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)

    @app.get("/health")
    async def health_check():
        """健康检查接口"""
        return {"status": "ok", "service": "100kwhy-wechat-mp"}

    app.include_router(wechat.router, prefix="/wechat", tags=["wechat"])
    app.include_router(digest.router, prefix="/digest", tags=["digest"])

    return app


app = create_app()


