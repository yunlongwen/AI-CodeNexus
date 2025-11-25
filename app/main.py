import asyncio
import os
import sys
import subprocess
from pathlib import Path

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

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

# 在所有模块导入前，从 .env 文件加载环境变量
# 添加错误处理，避免 .env 文件格式错误导致启动失败
try:
    load_dotenv()
except Exception as e:  # noqa: BLE001
    # logger 还未导入，使用 print 输出警告
    print(f"Warning: Failed to load .env file: {e}. Continuing with environment variables...")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .config_loader import load_digest_schedule, load_crawler_keywords


def setup_logging():
    """
    配置日志系统，将日志保存到文件
    """
    # 创建 logs 目录
    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # 移除默认的控制台输出（如果需要的话，可以保留）
    # logger.remove()
    
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
from .notifier.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from .routes import wechat, digest
from .sources.ai_articles import pick_daily_ai_articles, todays_theme, clear_articles, save_article_to_config, get_all_articles
from .sources.ai_candidates import promote_candidates_to_articles, clear_candidate_pool
from .crawlers.sogou_wechat import search_articles_by_keyword
import random

# 全局 scheduler 实例
scheduler: Optional[AsyncIOScheduler] = None

# 任务执行锁，防止并发执行（进程内）
_digest_job_lock = asyncio.Lock()

# 文件锁路径，用于跨进程锁
_lock_file_path: Optional[Path] = None


def _get_lock_file_path() -> Path:
    """获取文件锁路径"""
    global _lock_file_path
    if _lock_file_path is None:
        project_root = Path(__file__).resolve().parent.parent
        lock_dir = project_root / "data" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        _lock_file_path = lock_dir / "digest_job.lock"
    return _lock_file_path


# 全局变量保存文件描述符，用于释放锁
_lock_fd: Optional[int] = None


def _acquire_file_lock(timeout: float = 0.1) -> bool:
    """
    尝试获取文件锁（跨进程锁）
    返回 True 如果成功获取锁，False 如果锁已被其他进程占用
    """
    global _lock_fd
    lock_file = _get_lock_file_path()
    try:
        # 尝试以独占模式打开文件
        if sys.platform == "win32":
            # Windows 使用 msvcrt
            _lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
            try:
                msvcrt.locking(_lock_fd, msvcrt.LK_NBLCK, 1)  # 非阻塞锁定
                return True
            except IOError:
                os.close(_lock_fd)
                _lock_fd = None
                return False
        else:
            # Linux/Mac 使用 fcntl
            _lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
            try:
                fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except IOError:
                os.close(_lock_fd)
                _lock_fd = None
                return False
    except Exception as e:
        logger.warning(f"[定时推送] 获取文件锁失败: {e}")
        if _lock_fd is not None:
            try:
                os.close(_lock_fd)
            except Exception:
                pass
            _lock_fd = None
        return False


def _release_file_lock():
    """释放文件锁"""
    global _lock_fd
    try:
        if _lock_fd is not None:
            if sys.platform == "win32":
                msvcrt.locking(_lock_fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            os.close(_lock_fd)
            _lock_fd = None
        
        # 删除锁文件
        lock_file = _get_lock_file_path()
        if lock_file.exists():
            lock_file.unlink()
    except Exception as e:
        logger.warning(f"[定时推送] 释放文件锁失败: {e}")
        _lock_fd = None


async def crawl_and_pick_articles_by_keywords() -> int:
    """
    按关键字抓取文章，每个关键字随机选一篇，直接放到文章列表。
    
    Returns:
        成功添加到文章列表的文章数量
    """
    try:
        # 1. 读取关键词
        keywords = load_crawler_keywords()
        if not keywords:
            logger.warning("[自动抓取] 关键词列表为空，无法抓取文章")
            return 0
        
        logger.info(f"[自动抓取] 开始按关键字抓取文章，关键词数量: {len(keywords)}")
        
        # 2. 获取所有已存在的 URL 用于去重
        existing_urls = set()
        main_pool_articles = get_all_articles()
        for article in main_pool_articles:
            if article.get("url"):
                existing_urls.add(article["url"].strip())
        
        logger.info(f"[自动抓取] 已存在 {len(existing_urls)} 篇文章，用于去重")
        
        # 3. 遍历关键词并抓取，每个关键词随机选一篇
        selected_articles = []
        for keyword in keywords:
            try:
                logger.info(f"[自动抓取] 正在抓取关键词 '{keyword}' 的文章...")
                found_candidates = await search_articles_by_keyword(keyword, pages=1)
                
                if not found_candidates:
                    logger.warning(f"[自动抓取] 关键词 '{keyword}' 未找到文章")
                    continue
                
                # 过滤掉已存在的URL
                new_candidates = [
                    c for c in found_candidates 
                    if c.url.strip() not in existing_urls
                ]
                
                if not new_candidates:
                    logger.info(f"[自动抓取] 关键词 '{keyword}' 的文章都已存在，跳过")
                    continue
                
                # 随机选择一篇
                selected = random.choice(new_candidates)
                selected_articles.append({
                    "title": selected.title,
                    "url": selected.url,
                    "source": selected.source,
                    "summary": selected.summary,
                })
                
                # 添加到已存在URL集合，避免同一批次重复
                existing_urls.add(selected.url.strip())
                
                logger.info(f"[自动抓取] 关键词 '{keyword}' 已选择文章: {selected.title[:50]}...")
                
            except Exception as e:
                logger.error(f"[自动抓取] 抓取关键词 '{keyword}' 失败: {e}")
                # 单个关键词失败不中断整个任务
                continue
        
        if not selected_articles:
            logger.warning("[自动抓取] 未找到新文章")
            return 0
        
        # 4. 直接保存到文章列表
        saved_count = 0
        for article in selected_articles:
            if save_article_to_config(article):
                saved_count += 1
        
        logger.info(f"[自动抓取] 成功抓取并保存 {saved_count} 篇文章到文章列表")
        return saved_count
        
    except Exception as e:
        logger.error(f"[自动抓取] 抓取文章失败: {e}", exc_info=True)
        return 0


async def job_backup_data_to_github() -> None:
    """
    定时任务：将 data/ 和 config/ 目录的数据提交到 GitHub
    每天 23:00 执行
    """
    try:
        now = datetime.now()
        logger.info(f"[数据备份] 开始执行数据备份任务，时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取项目根目录
        project_root = Path(__file__).resolve().parent.parent
        
        # 检查是否是 Git 仓库
        git_dir = project_root / ".git"
        if not git_dir.exists():
            logger.warning("[数据备份] 当前目录不是 Git 仓库，跳过备份")
            return
        
        # 切换到项目根目录执行 Git 命令
        def run_git_command(cmd: list, env: dict = None) -> Tuple[str, str, int]:
            """执行 Git 命令"""
            try:
                # 确保使用 HTTPS 协议，避免 SSH host key 验证问题
                cmd_env = os.environ.copy()
                if env:
                    cmd_env.update(env)
                # 强制使用 HTTPS，禁用 SSH
                cmd_env['GIT_SSH_COMMAND'] = ''
                cmd_env['GIT_TERMINAL_PROMPT'] = '0'
                
                result = subprocess.run(
                    cmd,
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=60,
                    env=cmd_env
                )
                return result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired:
                logger.error("[数据备份] Git 命令执行超时")
                return "", "Timeout", -1
            except Exception as e:
                logger.error(f"[数据备份] Git 命令执行失败: {e}")
                return "", str(e), -1
        
        # 1. 检查是否有变更
        stdout, stderr, code = await asyncio.to_thread(
            run_git_command, 
            ["git", "status", "--porcelain", "data/", "config/"]
        )
        
        if code != 0:
            logger.error(f"[数据备份] 检查 Git 状态失败: {stderr}")
            return
        
        if not stdout.strip():
            logger.info("[数据备份] data/ 和 config/ 目录没有变更，跳过提交")
            return
        
        # 2. 添加变更的文件
        logger.info("[数据备份] 添加变更的文件...")
        stdout, stderr, code = await asyncio.to_thread(
            run_git_command,
            ["git", "add", "data/", "config/"]
        )
        
        if code != 0:
            logger.error(f"[数据备份] 添加文件失败: {stderr}")
            return
        
        # 3. 提交变更
        commit_message = f"chore: auto backup data and config - {now.strftime('%Y-%m-%d %H:%M:%S')}"
        logger.info(f"[数据备份] 提交变更: {commit_message}")
        stdout, stderr, code = await asyncio.to_thread(
            run_git_command,
            ["git", "commit", "-m", commit_message]
        )
        
        if code != 0:
            if "nothing to commit" in stderr.lower() or "nothing to commit" in stdout.lower():
                logger.info("[数据备份] 没有需要提交的变更")
                return
            logger.error(f"[数据备份] 提交失败: {stderr}")
            return
        
        logger.info(f"[数据备份] 提交成功: {stdout.strip()}")
        
        # 4. 推送到远程仓库
        logger.info("[数据备份] 推送到远程仓库...")
        # 获取远程仓库 URL，确保使用 HTTPS
        stdout, stderr, code = await asyncio.to_thread(
            run_git_command,
            ["git", "config", "--get", "remote.origin.url"]
        )
        remote_url = stdout.strip() if code == 0 else ""
        
        # 如果远程 URL 是 SSH 格式，转换为 HTTPS
        if remote_url.startswith("git@") or remote_url.startswith("ssh://"):
            logger.warning(f"[数据备份] 检测到 SSH 格式的远程 URL，尝试转换为 HTTPS: {remote_url}")
            # 将 git@github.com:user/repo.git 转换为 https://github.com/user/repo.git
            if "git@" in remote_url:
                remote_url = remote_url.replace("git@github.com:", "https://github.com/")
            elif remote_url.startswith("ssh://"):
                remote_url = remote_url.replace("ssh://git@github.com/", "https://github.com/")
            logger.info(f"[数据备份] 转换后的 URL: {remote_url}")
        
        stdout, stderr, code = await asyncio.to_thread(
            run_git_command,
            ["git", "push", "origin", "master"]
        )
        
        if code != 0:
            # 检查是否是 SSH host key 验证错误
            if "Host key verification failed" in stderr or "host key" in stderr.lower():
                logger.error(f"[数据备份] 推送失败: SSH host key 验证失败")
                logger.error(f"[数据备份] 错误详情: {stderr}")
                logger.warning("[数据备份] 提示: 请确保远程仓库使用 HTTPS 协议，或配置 SSH host key")
                logger.warning("[数据备份] 解决方案: 运行 'git remote set-url origin https://github.com/...' 切换到 HTTPS")
            else:
                logger.error(f"[数据备份] 推送失败: {stderr}")
            
            # 如果推送失败，尝试拉取最新代码后再推送
            logger.info("[数据备份] 尝试拉取最新代码...")
            stdout, stderr, code = await asyncio.to_thread(
                run_git_command,
                ["git", "pull", "origin", "master", "--rebase"]
            )
            if code == 0:
                logger.info("[数据备份] 拉取成功，重新推送...")
                stdout, stderr, code = await asyncio.to_thread(
                    run_git_command,
                    ["git", "push", "origin", "master"]
                )
                if code == 0:
                    logger.info("[数据备份] 推送成功")
                else:
                    if "Host key verification failed" in stderr or "host key" in stderr.lower():
                        logger.error(f"[数据备份] 重新推送失败: SSH host key 验证失败")
                        logger.error(f"[数据备份] 错误详情: {stderr}")
                    else:
                        logger.error(f"[数据备份] 重新推送失败: {stderr}")
            else:
                if "Host key verification failed" in stderr or "host key" in stderr.lower():
                    logger.error(f"[数据备份] 拉取失败: SSH host key 验证失败")
                    logger.error(f"[数据备份] 错误详情: {stderr}")
                else:
                    logger.error(f"[数据备份] 拉取失败: {stderr}")
            return
        
        logger.info(f"[数据备份] 推送成功: {stdout.strip()}")
        logger.info("[数据备份] 数据备份任务执行成功")
        
    except Exception as e:
        logger.error(f"[数据备份] 数据备份任务执行失败: {e}", exc_info=True)


async def job_send_daily_ai_digest(digest_count: int) -> None:
    """Send AI coding articles digest to WeCom group."""
    # 首先尝试获取文件锁（跨进程锁），防止多个进程同时执行
    if not _acquire_file_lock():
        logger.warning("[定时推送] 检测到其他进程正在执行推送任务，跳过本次执行以避免重复推送")
        return
    
    try:
        # 使用进程内锁防止同一进程内的并发执行
        if _digest_job_lock.locked():
            logger.warning("[定时推送] 检测到任务正在执行中，跳过本次执行以避免重复推送")
            _release_file_lock()
            return
        
        async with _digest_job_lock:
            now = datetime.now()
            logger.info(f"[定时推送] 开始执行定时推送任务，时间: {now.strftime('%Y-%m-%d %H:%M:%S')}, 目标篇数: {digest_count}")
            
            articles = pick_daily_ai_articles(k=digest_count)
            if not articles:
                logger.info("[定时推送] 文章池为空，尝试从候选池提升文章...")
                promoted = promote_candidates_to_articles(per_keyword=2)
                if promoted:
                    logger.info(f"[定时推送] 从候选池提升了 {promoted} 篇文章")
                    articles = pick_daily_ai_articles(k=digest_count)
            
            # 如果文章池和候选池都为空，按关键字抓取文章
            if not articles:
                logger.info("[定时推送] 文章池和候选池都为空，开始按关键字自动抓取文章...")
                crawled_count = await crawl_and_pick_articles_by_keywords()
                if crawled_count > 0:
                    logger.info(f"[定时推送] 自动抓取成功，获得 {crawled_count} 篇文章")
                    articles = pick_daily_ai_articles(k=digest_count)
                else:
                    logger.warning("[定时推送] 自动抓取失败或未找到新文章，跳过推送")
                    return

            if not articles:
                logger.warning("[定时推送] 文章池为空且无法获取文章，跳过推送")
                return

            logger.info(f"[定时推送] 准备推送 {len(articles)} 篇文章")
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
            logger.info("[定时推送] 正在发送到企业微信群...")
            success = await send_markdown_to_wecom(content)
            if not success:
                logger.error("[定时推送] 推送失败，但继续清理文章池和候选池")
            else:
                logger.info("[定时推送] 推送成功")
            
            logger.info("[定时推送] 正在清理文章池和候选池...")
            clear_articles()
            clear_candidate_pool()
            if success:
                logger.info("[定时推送] 定时推送任务执行成功")
            else:
                logger.warning("[定时推送] 定时推送任务完成，但推送失败")
    except Exception as e:
        logger.error(f"[定时推送] 定时推送任务执行失败: {e}", exc_info=True)
    finally:
        # 确保释放文件锁
        _release_file_lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时启动 scheduler，关闭时关闭 scheduler"""
    global scheduler

    # 配置日志系统
    setup_logging()
    logger.info("=" * 80)
    logger.info("应用启动，初始化日志系统和调度器...")
    
    # 如果调度器已存在，先关闭它（防止热重载时重复初始化）
    if scheduler is not None:
        try:
            if scheduler.running:
                logger.warning("[调度器] 检测到已有调度器在运行，正在关闭...")
                scheduler.shutdown(wait=False)
        except Exception as e:
            logger.warning(f"[调度器] 关闭旧调度器时出错: {e}")
        scheduler = None
    
    # 从配置文件加载定时任务参数
    schedule = load_digest_schedule()
    digest_hour = schedule.hour
    digest_minute = schedule.minute
    digest_count = schedule.count

    # 启动时
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    logger.info("[调度器] 调度器实例已创建")

    # 配置触发器：优先使用 cron 表达式
    # 注意：在启动前添加任务，启动后会自动调度
    
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
            "[调度器] 已添加推送任务，使用 cron 表达式: %r, 每次推送 %d 篇文章",
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
            "[调度器] 已添加推送任务，每日推送时间: %02d:%02d (Asia/Shanghai), "
            "每次推送 %d 篇文章",
            digest_hour,
            digest_minute,
            digest_count,
        )
    
    # 验证任务是否已正确添加
    job = scheduler.get_job("daily_ai_digest")
    if job:
        # 调度器启动前，next_run_time 可能不可用
        next_run = getattr(job, 'next_run_time', None)
        if next_run:
            logger.info(f"[调度器] 推送任务已确认添加，下次执行时间: {next_run}")
        else:
            logger.info("[调度器] 推送任务已确认添加（启动后显示执行时间）")
    else:
        logger.error("[调度器] 警告：推送任务添加失败，未找到任务！")

    # 添加数据备份任务：每天 23:00 执行
    scheduler.add_job(
        job_backup_data_to_github,
        "cron",
        hour=23,
        minute=0,
        id="daily_data_backup",
        replace_existing=True,
    )
    logger.info("[调度器] 已添加数据备份任务，每日 23:00 执行")
    
    # 启动调度器
    scheduler.start()
    
    # 列出所有已添加的任务（启动后才能获取 next_run_time）
    all_jobs = scheduler.get_jobs()
    logger.info(f"[调度器] 当前共有 {len(all_jobs)} 个定时任务:")
    for job in all_jobs:
        # 安全获取 next_run_time，可能在某些版本中属性名不同
        next_run = getattr(job, 'next_run_time', None) or getattr(job, 'next_run', None)
        if next_run:
            logger.info(f"[调度器]   - {job.id}: 下次执行时间 = {next_run}")
        else:
            logger.info(f"[调度器]   - {job.id}: 已添加（执行时间待计算）")
    logger.info("[调度器] 调度器已启动，等待触发定时任务...")

    yield  # 应用运行期间

    # 关闭时
    if scheduler is not None:
        try:
            if scheduler.running:
                scheduler.shutdown(wait=True)
                logger.info("[调度器] 调度器已关闭")
            else:
                logger.info("[调度器] 调度器未运行，无需关闭")
        except Exception as e:
            logger.error(f"[调度器] 关闭调度器时出错: {e}")
        finally:
            scheduler = None


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
    @app.get("/news", response_class=HTMLResponse)
    @app.get("/ai-news", response_class=HTMLResponse)
    @app.get("/tools", response_class=HTMLResponse)
    @app.get("/hot-news", response_class=HTMLResponse)
    @app.get("/recent", response_class=HTMLResponse)
    @app.get("/submit", response_class=HTMLResponse)
    @app.get("/submit-tool", response_class=HTMLResponse)
    @app.get("/wechat-mp", response_class=HTMLResponse)
    @app.get("/category/{category}", response_class=HTMLResponse)
    @app.get("/tool/{tool_id_or_identifier}", response_class=HTMLResponse)
    async def root(category: str = None, tool_id_or_identifier: str = None):
        """AICoding基地 首页（支持所有前端路由）"""
        html = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>AI-CodeNexus - 编程资讯与工具聚合平台</title>
          <link rel="preconnect" href="https://fonts.googleapis.com">
          <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
          <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap" rel="stylesheet">
          <script src="https://cdn.tailwindcss.com"></script>
          <script>
            // 限制 Tailwind CSS 只影响当前页面，避免全局样式冲突
            tailwind.config = {
              important: true,
              corePlugins: {
                preflight: false,  // 禁用全局重置样式
              },
              theme: {
                extend: {
                  colors: {
                    neon: {
                      cyan: '#00f0ff',
                      purple: '#a855f7',
                      blue: '#3b82f6',
                      pink: '#ec4899',
                    },
                    dark: {
                      bg: '#0a0e27',
                      card: '#111827',
                      border: '#1f2937',
                    }
                  }
                }
              }
            }
          </script>
          <style>
            /* 确保 Tailwind CSS 只影响当前页面 */
            body { margin: 0; padding: 0; }
            
            /* 科技感字体 */
            .tech-font {
              font-family: 'Orbitron', 'Rajdhani', sans-serif;
              letter-spacing: 0.05em;
            }
            
            .tech-font-bold {
              font-family: 'Orbitron', sans-serif;
              font-weight: 700;
              letter-spacing: 0.1em;
            }
            
            .tech-font-nav {
              font-family: 'Rajdhani', sans-serif;
              font-weight: 600;
              letter-spacing: 0.05em;
            }
            
            /* 科技感背景渐变 */
            .tech-bg {
              background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
              position: relative;
            }
            
            .tech-bg::before {
              content: '';
              position: fixed;
              top: 0;
              left: 0;
              right: 0;
              bottom: 0;
              background: 
                radial-gradient(circle at 20% 50%, rgba(0, 240, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(168, 85, 247, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 50%);
              pointer-events: none;
              z-index: 0;
            }
            
            /* 玻璃态效果 */
            .glass {
              background: rgba(17, 24, 39, 0.7);
              backdrop-filter: blur(10px);
              border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            /* 霓虹发光效果 */
            .neon-glow {
              box-shadow: 0 0 10px rgba(0, 240, 255, 0.5),
                          0 0 20px rgba(0, 240, 255, 0.3),
                          0 0 30px rgba(0, 240, 255, 0.2);
            }
            
            .neon-glow-purple {
              box-shadow: 0 0 10px rgba(168, 85, 247, 0.5),
                          0 0 20px rgba(168, 85, 247, 0.3),
                          0 0 30px rgba(168, 85, 247, 0.2);
            }
            
            /* 文字发光效果 */
            .text-glow {
              text-shadow: 0 0 10px rgba(0, 240, 255, 0.8),
                          0 0 20px rgba(0, 240, 255, 0.5),
                          0 0 30px rgba(0, 240, 255, 0.3);
            }
            
            /* 悬停发光动画 */
            @keyframes pulse-glow {
              0%, 100% {
                box-shadow: 0 0 10px rgba(0, 240, 255, 0.5),
                            0 0 20px rgba(0, 240, 255, 0.3);
              }
              50% {
                box-shadow: 0 0 20px rgba(0, 240, 255, 0.8),
                            0 0 40px rgba(0, 240, 255, 0.5);
              }
            }
            
            .hover-glow:hover {
              animation: pulse-glow 2s ease-in-out infinite;
            }
            
            /* 滚动条样式 */
            ::-webkit-scrollbar {
              width: 8px;
            }
            
            ::-webkit-scrollbar-track {
              background: #0a0e27;
            }
            
            ::-webkit-scrollbar-thumb {
              background: rgba(0, 240, 255, 0.5);
              border-radius: 4px;
            }
            
            ::-webkit-scrollbar-thumb:hover {
              background: rgba(0, 240, 255, 0.8);
            }
            
            /* 卡片悬停效果 */
            .card-hover {
              transition: all 0.3s ease;
            }
            
            .card-hover:hover {
              transform: translateY(-4px);
              box-shadow: 0 10px 30px rgba(0, 240, 255, 0.3),
                          0 0 20px rgba(168, 85, 247, 0.2);
              border-color: rgba(0, 240, 255, 0.5);
            }
            
            /* 导航项动画 */
            .nav-item {
              position: relative;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .nav-item::before {
              content: '';
              position: absolute;
              left: 0;
              top: 0;
              bottom: 0;
              width: 3px;
              background: linear-gradient(to bottom, #00f0ff, #a855f7);
              transform: scaleY(0);
              transform-origin: center;
              transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .nav-item.active::before,
            .nav-item:hover::before {
              transform: scaleY(1);
            }
            
            .nav-item.active {
              background: rgba(0, 240, 255, 0.1);
              color: #00f0ff;
              border-left: 3px solid #00f0ff;
            }
            
            /* 顶部导航动画 */
            .top-nav-item {
              position: relative;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .top-nav-item::after {
              content: '';
              position: absolute;
              bottom: 0;
              left: 50%;
              width: 0;
              height: 2px;
              background: linear-gradient(to right, #00f0ff, #a855f7);
              transform: translateX(-50%);
              transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .top-nav-item.active::after,
            .top-nav-item:hover::after {
              width: 80%;
            }
            
            .top-nav-item.active {
              color: #00f0ff;
            }
          </style>
        </head>
        <body class="tech-bg text-gray-100" style="position: relative; z-index: 1;">
          <div class="flex flex-col min-h-screen" style="position: relative; z-index: 1;">
            <!-- 顶部导航栏 -->
            <header class="glass border-b border-dark-border fixed top-0 left-0 right-0" style="z-index: 20; height: 80px;">
              <div class="max-w-7xl mx-auto px-6 h-full">
                <div class="flex items-center justify-between h-full w-full">
              <!-- Logo -->
                  <div class="flex items-center flex-shrink-0">
                    <h1 class="text-2xl tech-font-bold text-neon-cyan text-glow">AI-CodeNexus</h1>
                    <p class="text-sm text-gray-400 ml-4 hidden md:block tech-font">AI · 编程 · 工具聚合</p>
              </div>
              
              <!-- 主导航和管理员入口 -->
              <div class="flex items-center gap-2 flex-1 justify-end">
                  <nav class="flex items-center gap-2 flex-wrap">
                    <a href="/news" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                  📰 编程资讯
                </a>
                    <a href="/ai-news" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple rounded-lg transition-all whitespace-nowrap">
                  🤖 AI资讯
                </a>
                    <a href="/hot-news" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      🔥 热门资讯
                </a>
                    <a href="/recent" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      ⏰ 最新资讯
                </a>
                    <a href="/submit" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple rounded-lg transition-all whitespace-nowrap">
                      ✍️ 提交资讯
                </a>
                    <a href="/wechat-mp" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      📱 微信公众号
                </a>
              </nav>
                  
                  <!-- 管理员入口（隐藏，需要输入授权码后显示，放在最右侧） -->
                  <a href="/digest/panel" id="admin-entry" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple rounded-lg transition-all hidden whitespace-nowrap ml-2" style="display: none;">
                    🔐 管理员入口
                  </a>
              </div>
                </div>
              </div>
            </header>
            
            <div class="flex flex-1" style="margin-top: 80px;">
              <!-- 左侧边栏 -->
              <aside class="w-64 glass border-r border-dark-border flex flex-col fixed" style="top: 80px; height: calc(100vh - 80px); z-index: 10;">
              
              <!-- 工具分类 -->
                <div class="flex-1 p-5 overflow-y-auto">
                  <div class="space-y-2">
                    <a href="/tools" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      🔥 热门工具
                    </a>
                    <a href="/category/ide" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      💻 开发IDE
                  </a>
                    <a href="/category/plugin" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      🔌 IDE插件
                  </a>
                    <a href="/category/cli" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      ⌨️ 命令行工具
                  </a>
                    <a href="/category/codeagent" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      🤖 CodeAgent
                  </a>
                    <a href="/category/ai-test" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      🧪 AI测试
                  </a>
                    <a href="/category/review" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      ✅ 代码审查
                  </a>
                    <a href="/category/devops" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      🚀 DevOps 工具
                  </a>
                    <a href="/category/doc" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      📚 文档相关
                  </a>
                    <a href="/category/design" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      🎨 设计工具
                  </a>
                    <a href="/category/ui" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      🖼️ UI生成
                  </a>
                    <a href="/category/mcp" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      🔌 MCP工具
                  </a>
                    <a href="/submit-tool" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      ➕ 提交工具
                  </a>
                </div>
              </div>
              
            </aside>
            
            <!-- 主内容区域 -->
              <main class="flex-1 ml-64 pt-20" style="position: relative; z-index: 1;">
              <div class="max-w-6xl mx-auto p-8">
                <!-- 动态内容区域 -->
                <div id="main-content">
                  <!-- 内容将通过JavaScript动态加载 -->
                  <div class="text-center py-20">
                    <div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div>
                  </div>
                </div>
              </div>
            </main>
                </div>
                
            <script>
              // API基础URL
              const API_BASE = '/api';
              
              // 配置文件
              let pageConfig = {};
              
              // 当前页面状态
              let currentPage = {
                type: 'tools',
                page: 1,
                pageSize: 20,
                category: null,
                loading: false
              };
              
              // 加载配置文件
              async function loadConfig() {
                try {
                  const response = await fetch(`${API_BASE}/config`);
                  pageConfig = await response.json();
                } catch (error) {
                  console.error('加载配置失败:', error);
                }
              }
              
              // 获取页面配置
              function getPageConfig(pageType, category = null) {
                if (!pageConfig.pages) return { title: '', description: '' };
                
                // 如果是分类页面
                if (category && pageConfig.categories && pageConfig.categories.tools) {
                  const catConfig = pageConfig.categories.tools[category];
                  if (catConfig) {
                    return {
                      title: catConfig.name,
                      description: catConfig.description
                    };
                  }
                }
                
                // 普通页面
                const config = pageConfig.pages[pageType];
                return config || { title: '', description: '' };
              }
              
              // 加载工具列表
              async function loadTools(featured = false, category = null, page = 1) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  let url = featured 
                    ? `${API_BASE}/tools/featured?page=${page}&page_size=${currentPage.pageSize}&sort_by=view_count`
                    : `${API_BASE}/tools?page=${page}&page_size=${currentPage.pageSize}`;
                  
                  if (category) {
                    url += `&category=${category}`;
                  }
                  
                  const response = await fetch(url);
                  if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                  }
                  const data = await response.json();
                  
                  console.log('加载工具数据:', { items: data.items?.length, total: data.total, featured });
                  
                  renderTools(data.items, data.total, data.page, data.total_pages, category, featured);
                } catch (error) {
                  console.error('加载工具失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败，请刷新重试</div>';
                }
              }
              
              // 渲染工具列表
              function renderTools(tools, total, page, totalPages, category = null, isFeatured = true) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                // 获取页面配置
                const pageType = isFeatured ? 'tools' : 'all-tools';
                const config = getPageConfig(pageType, category);
                const title = config.title || (isFeatured ? '热门工具' : '全部工具');
                const description = config.description || '发现最优秀的开发工具和资源';
                
                let html = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description} (共 ${total} 个)</p>
                </div>
                
                  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8" id="tools-grid">
                `;
                
                if (tools.length === 0) {
                  html += '<div class="col-span-full text-center py-20 text-gray-400">暂无工具数据</div>';
                } else {
                  tools.forEach(tool => {
                    const iconColor = tool.category === 'codeagent' || tool.category === 'ai-test' 
                      ? 'from-neon-purple to-neon-pink' 
                      : 'from-neon-cyan to-neon-blue';
                    const glowClass = tool.category === 'codeagent' || tool.category === 'ai-test'
                      ? 'neon-glow-purple'
                      : 'neon-glow';
                    const viewCount = tool.view_count || 0;
                    
                    html += `
                      <div class="glass rounded-xl border border-dark-border p-6 card-hover cursor-pointer" onclick="window.location.href='/tool/${tool.identifier || tool.id}'">
                    <div class="flex items-start gap-3 mb-4">
                          <div class="w-10 h-10 rounded-lg bg-gradient-to-br ${iconColor} flex items-center justify-center text-dark-bg text-lg font-bold flex-shrink-0 ${glowClass}">
                            ${tool.icon || '</>'}
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                              <h3 class="text-lg font-bold text-gray-100 truncate">${tool.name}</h3>
                              <span class="text-yellow-400 text-sm">⭐</span>
                        </div>
                            <div class="flex items-center gap-2">
                              <p class="text-xs text-gray-400">${getCategoryName(tool.category)}</p>
                              ${isFeatured ? `<span class="text-xs text-yellow-400">🔥 ${viewCount} 次访问</span>` : ''}
                      </div>
                    </div>
                        </div>
                        <p class="text-sm text-gray-300 line-clamp-3 mb-4">
                          ${tool.description || ''}
                        </p>
                        <a href="${tool.url}" target="_blank" rel="noopener noreferrer" 
                           class="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r ${iconColor} text-dark-bg text-sm rounded-lg hover:from-neon-blue hover:to-neon-cyan transition-all font-medium hover-glow"
                           onclick="event.stopPropagation(); recordToolClick('${tool.identifier || tool.id}');">
                      访问工具
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                    `;
                  });
                }
                
                html += '</div>';
                
                // 分页控件
                if (totalPages > 1) {
                  const categoryParam = category ? `'${category}'` : 'null';
                  html += `
                    <div class="flex items-center justify-center gap-2 mt-8">
                      <button onclick="changePage(${page - 1}, ${categoryParam}, ${isFeatured})" 
                              ${page <= 1 ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        上一页
                      </button>
                      <span class="px-4 py-2 text-gray-400 tech-font">
                        第 ${page} / ${totalPages} 页
                      </span>
                      <button onclick="changePage(${page + 1}, ${categoryParam}, ${isFeatured})" 
                              ${page >= totalPages ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        下一页
                      </button>
                      </div>
                  `;
                }
                
                mainContent.innerHTML = html;
              }
              
              // 加载文章列表
              async function loadArticles(category = 'programming', page = 1) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  const url = category === 'ai_news'
                    ? `${API_BASE}/ai-news?page=${page}&page_size=${currentPage.pageSize}`
                    : `${API_BASE}/news?category=${category}&page=${page}&page_size=${currentPage.pageSize}`;
                  
                  const response = await fetch(url);
                  const data = await response.json();
                  
                  renderArticles(data.items, data.total, data.page, data.total_pages, category);
                } catch (error) {
                  console.error('加载文章失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败，请刷新重试</div>';
                }
              }
              
              // 渲染文章列表
              function renderArticles(articles, total, page, totalPages, category) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                // 获取页面配置
                const pageType = category === 'ai_news' ? 'ai-news' : 'news';
                const config = getPageConfig(pageType);
                const title = config.title || (category === 'ai_news' ? 'AI资讯' : '编程资讯');
                const description = config.description || '最新技术文章和资讯';
                
                let html = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description} (共 ${total} 篇)</p>
                        </div>
                  
                  <div class="space-y-4 mb-8">
                `;
                
                if (articles.length === 0) {
                  html += '<div class="text-center py-20 text-gray-400">暂无文章数据</div>';
                } else {
                  articles.forEach(article => {
                    // 处理日期：优先使用 archived_at（采纳日期），其次 published_time，最后 created_at
                    let dateStr = '未知日期';
                    const dateValue = article.archived_at || article.published_time || article.created_at;
                    if (dateValue) {
                      try {
                        const date = new Date(dateValue);
                        if (!isNaN(date.getTime())) {
                          dateStr = date.toLocaleDateString('zh-CN');
                        }
                      } catch (e) {
                        // 日期解析失败，使用默认值
                      }
                    }
                    
                    // 处理来源：如果source为空字符串，显示"未知来源"
                    const source = (article.source && article.source.trim()) ? article.source : '未知来源';
                    
                    // 合并标签：tool_tags 和 tags
                    const allTags = [];
                    if (article.tool_tags && article.tool_tags.length > 0) {
                      allTags.push(...article.tool_tags.map(tag => ({ tag, isTool: true })));
                    }
                    if (article.tags && article.tags.length > 0) {
                      allTags.push(...article.tags.map(tag => ({ tag, isTool: false })));
                    }
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                        <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                          <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}')">${article.title}</a>
                        </h4>
                        <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                          <span>${source}</span>
                          <span>•</span>
                          <span>${dateStr}</span>
                      </div>
                        <p class="text-sm text-gray-300 leading-relaxed mb-3">
                          ${article.summary || ''}
                        </p>
                        ${allTags.length > 0 ? `
                        <div class="flex items-center gap-2 flex-wrap">
                          ${allTags.map(({ tag, isTool }) => 
                            isTool 
                              ? `<span class="px-2 py-1 glass text-neon-purple text-xs rounded border border-neon-purple/30 flex items-center gap-1">
                                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
                                  </svg>
                                  ${tag}
                                </span>`
                              : `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`
                          ).join('')}
                        </div>
                        ` : ''}
                      </article>
                    `;
                  });
                }
                
                html += '</div>';
                
                // 分页控件
                if (totalPages > 1) {
                  html += `
                    <div class="flex items-center justify-center gap-2 mt-8">
                      <button onclick="changeArticlePage(${page - 1}, '${category}')" 
                              ${page <= 1 ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        上一页
                      </button>
                      <span class="px-4 py-2 text-gray-400 tech-font">
                        第 ${page} / ${totalPages} 页
                      </span>
                      <button onclick="changeArticlePage(${page + 1}, '${category}')" 
                              ${page >= totalPages ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        下一页
                      </button>
                      </div>
                  `;
                }
                
                mainContent.innerHTML = html;
              }
              
              // 工具分类名称映射
              function getCategoryName(category) {
                const map = {
                  'ide': '开发IDE',
                  'plugin': 'IDE插件',
                  'cli': '命令行工具',
                  'codeagent': 'CodeAgent',
                  'ai-test': 'AI测试',
                  'review': '代码审查',
                  'devops': 'DevOps工具',
                  'doc': '文档相关',
                  'design': '设计工具',
                  'ui': 'UI生成',
                  'mcp': 'MCP工具'
                };
                return map[category] || category;
              }
              
              // 切换页面
              function changePage(newPage, category = null, featured = true) {
                if (newPage < 1) return;
                currentPage.page = newPage;
                if (category) currentPage.category = category;
                loadTools(featured, category || currentPage.category, newPage);
              }
              
              // 切换文章页面
              function changeArticlePage(newPage, category) {
                if (newPage < 1) return;
                loadArticles(category, newPage);
              }
              
              // 显示工具详情
              async function showToolDetail(toolIdOrIdentifier) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  const response = await fetch(`${API_BASE}/tools/${toolIdOrIdentifier}`);
                  if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                  }
                  const tool = await response.json();
                  
                  renderToolDetail(tool);
                  
                  // 更新URL（使用 identifier 如果存在，否则使用 ID）
                  const urlIdentifier = tool.identifier || tool.id;
                  window.history.pushState({}, '', `/tool/${urlIdentifier}`);
                } catch (error) {
                  console.error('加载工具详情失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败，请刷新重试</div>';
                }
              }
              
              // 渲染工具详情
              function renderToolDetail(tool) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                const iconColor = tool.category === 'codeagent' || tool.category === 'ai-test' 
                  ? 'from-neon-purple to-neon-pink' 
                  : 'from-neon-cyan to-neon-blue';
                const glowClass = tool.category === 'codeagent' || tool.category === 'ai-test'
                  ? 'neon-glow-purple'
                  : 'neon-glow';
                const viewCount = tool.view_count || 0;
                const relatedArticles = tool.related_articles || [];
                const relatedCount = tool.related_articles_count || 0;
                
                let html = `
                  <div class="mb-6">
                    <a href="javascript:void(0)" onclick="goBack()" class="inline-flex items-center gap-2 text-gray-400 hover:text-neon-cyan transition-colors mb-4">
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                      </svg>
                      <span>返回分类</span>
                    </a>
                    
                    <div class="glass rounded-xl border border-dark-border p-8">
                      <div class="flex items-start gap-6 mb-6">
                        <div class="w-16 h-16 rounded-xl bg-gradient-to-br ${iconColor} flex items-center justify-center text-dark-bg text-2xl font-bold flex-shrink-0 ${glowClass}">
                          ${tool.icon || '</>'}
                        </div>
                        <div class="flex-1">
                          <h1 class="text-3xl tech-font-bold text-neon-cyan text-glow mb-2">${tool.name}</h1>
                          <div class="flex items-center gap-4 text-sm text-gray-400 mb-4">
                            <span>${getCategoryName(tool.category)}</span>
                            <span>•</span>
                            <span>🔥 ${viewCount} 次访问</span>
                          </div>
                          <a href="${tool.url}" target="_blank" rel="noopener noreferrer" 
                             class="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r ${iconColor} text-dark-bg rounded-lg hover:from-neon-blue hover:to-neon-cyan transition-all font-medium hover-glow"
                             onclick="recordToolClick('${tool.identifier || tool.id}')">
                            访问工具
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        </div>
                      </div>
                      
                      <div class="mb-6">
                        <h2 class="text-xl font-semibold text-gray-100 mb-3">工具描述</h2>
                        <p class="text-gray-300 leading-relaxed">${tool.description || '暂无描述'}</p>
                      </div>
                      
                      ${tool.tags && tool.tags.length > 0 ? `
                        <div class="mb-6">
                          <h2 class="text-xl font-semibold text-gray-100 mb-3">标签</h2>
                          <div class="flex items-center gap-2 flex-wrap">
                            ${tool.tags.map(tag => 
                              `<span class="px-3 py-1 glass text-neon-cyan text-sm rounded border border-neon-cyan/30">${tag}</span>`
                            ).join('')}
                          </div>
                        </div>
                      ` : ''}
                    </div>
                    
                    <!-- 相关资讯 -->
                    <div class="mt-8">
                      <div class="flex items-center justify-between mb-4">
                        <h2 class="text-2xl tech-font-bold text-neon-cyan text-glow flex items-center gap-2">
                          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                          </svg>
                          相关资讯
                        </h2>
                        <div class="flex items-center gap-2">
                          <button onclick="refreshRelatedArticles('${tool.identifier || tool.id}')" 
                                  class="px-4 py-2 glass border border-dark-border text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all text-sm">
                            刷新
                          </button>
                          ${relatedCount > 10 ? `
                            <a href="javascript:void(0)" onclick="showMoreArticles('${tool.identifier || tool.id}')" 
                               class="px-4 py-2 glass border border-dark-border text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all text-sm">
                              查看更多 >
                            </a>
                          ` : ''}
                        </div>
                      </div>
                      
                      <div id="related-articles-list" class="space-y-4">
                `;
                
                if (relatedArticles.length === 0) {
                  html += `
                    <div class="glass rounded-xl border border-dark-border p-8 text-center text-gray-400">
                      <p>暂无相关资讯</p>
                    </div>
                  `;
                } else {
                  relatedArticles.forEach(article => {
                    const date = new Date(article.published_time || article.created_at || article.archived_at).toLocaleDateString('zh-CN');
                    const categoryLabel = article.category === 'ai_news' ? 'AI资讯' : '编程资讯';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                        <div class="flex items-start gap-3 mb-2">
                          <span class="text-sm px-2 py-1 glass border border-neon-cyan/30 text-neon-cyan rounded">${categoryLabel}</span>
                          <span class="text-xs text-gray-400">${date}</span>
                        </div>
                        <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                          <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}')">${article.title}</a>
                        </h4>
                        <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                          <span>${article.source || '未知来源'}</span>
                        </div>
                        <p class="text-sm text-gray-300 leading-relaxed mb-3">
                          ${article.summary || ''}
                        </p>
                        ${article.tool_tags && article.tool_tags.length > 0 ? `
                          <div class="flex items-center gap-2 flex-wrap">
                            ${article.tool_tags.map(tag => 
                              `<span class="px-2 py-1 glass text-neon-purple text-xs rounded border border-neon-purple/30 flex items-center gap-1">
                                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                  <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
                                </svg>
                                ${tag}
                              </span>`
                            ).join('')}
                          </div>
                        ` : ''}
                      </article>
                    `;
                  });
                }
                
                html += `
                      </div>
                    </div>
                `;
                
                mainContent.innerHTML = html;
              }
              
              // 返回上一页
              function goBack() {
                const path = window.location.pathname;
                if (path.includes('/tool/')) {
                  // 从工具详情页返回，尝试返回到分类页面
                  const category = localStorage.getItem('last_category') || 'tools';
                  window.history.pushState({}, '', `/${category}`);
                  handleRoute();
                } else {
                  window.history.back();
                }
              }
              
              // 刷新相关文章
              async function refreshRelatedArticles(toolIdOrIdentifier) {
                try {
                  const response = await fetch(`${API_BASE}/tools/${toolIdOrIdentifier}`);
                  if (!response.ok) throw new Error('刷新失败');
                  const tool = await response.json();
                  
                  const relatedArticles = tool.related_articles || [];
                  const relatedList = document.getElementById('related-articles-list');
                  if (!relatedList) return;
                  
                  if (relatedArticles.length === 0) {
                    relatedList.innerHTML = '<div class="glass rounded-xl border border-dark-border p-8 text-center text-gray-400"><p>暂无相关资讯</p></div>';
                    return;
                  }
                  
                  let html = '';
                  relatedArticles.forEach(article => {
                    const date = new Date(article.published_time || article.created_at || article.archived_at).toLocaleDateString('zh-CN');
                    const categoryLabel = article.category === 'ai_news' ? 'AI资讯' : '编程资讯';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                        <div class="flex items-start gap-3 mb-2">
                          <span class="text-sm px-2 py-1 glass border border-neon-cyan/30 text-neon-cyan rounded">${categoryLabel}</span>
                          <span class="text-xs text-gray-400">${date}</span>
                        </div>
                        <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                          <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}')">${article.title}</a>
                        </h4>
                        <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                          <span>${article.source || '未知来源'}</span>
                        </div>
                        <p class="text-sm text-gray-300 leading-relaxed mb-3">
                          ${article.summary || ''}
                        </p>
                        ${article.tool_tags && article.tool_tags.length > 0 ? `
                          <div class="flex items-center gap-2 flex-wrap">
                            ${article.tool_tags.map(tag => 
                              `<span class="px-2 py-1 glass text-neon-purple text-xs rounded border border-neon-purple/30 flex items-center gap-1">
                                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                  <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
                                </svg>
                                ${tag}
                              </span>`
                            ).join('')}
                          </div>
                        ` : ''}
                      </article>
                    `;
                  });
                  
                  relatedList.innerHTML = html;
                } catch (error) {
                  console.error('刷新相关文章失败:', error);
                }
              }
              
              // 显示更多文章
              function showMoreArticles(toolIdOrIdentifier) {
                // TODO: 实现分页加载更多文章
                console.log('显示更多文章:', toolIdOrIdentifier);
              }
              
              // 页面路由
              function handleRoute() {
                const path = window.location.pathname || '/news';
                currentPage.page = 1;
                
                // 移除开头的斜杠并转换为路由标识
                const route = path.startsWith('/') ? path.substring(1) : path;
                currentPage.type = route;
                
                if (route === 'news' || route === '') {
                  currentPage.category = null;
                  loadArticles('programming', 1);
                } else if (route === 'ai-news') {
                  currentPage.category = null;
                  loadArticles('ai_news', 1);
                } else if (route === 'tools') {
                  currentPage.category = null;
                  loadTools(true, null, 1);
                } else if (route === 'hot-news') {
                  currentPage.category = null;
                  loadHotNews(1);
                } else if (route === 'recent') {
                  currentPage.category = null;
                  loadRecent(1);
                } else if (route === 'submit') {
                  currentPage.category = null;
                  showSubmitForm();
                } else if (route === 'submit-tool') {
                  currentPage.category = null;
                  showSubmitToolForm();
                } else if (route === 'wechat-mp') {
                  currentPage.category = null;
                  showWeChatMP();
                } else if (route.startsWith('category/')) {
                  const category = route.substring(9); // 'category/'.length = 9
                  currentPage.category = category;
                  localStorage.setItem('last_category', `category/${category}`);
                  loadTools(false, category, 1);
                } else if (route.startsWith('tool/')) {
                  const toolIdOrIdentifier = route.substring(5); // 'tool/'.length = 5
                  if (toolIdOrIdentifier) {
                    showToolDetail(toolIdOrIdentifier);
                  } else {
                    // 默认显示热门工具
                    currentPage.category = null;
                    loadTools(true, null, 1);
                  }
                } else {
                  // 默认显示热门工具
                  currentPage.category = null;
                  loadTools(true, null, 1);
                }
              }
              
              // 加载最新资讯（合并编程资讯和AI资讯）
              let recentSearchQuery = '';
              
              async function loadRecent(page = 1, search = '') {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  let url = `${API_BASE}/recent?page=${page}&page_size=${currentPage.pageSize}`;
                  if (search) {
                    url += `&search=${encodeURIComponent(search)}`;
                  }
                  
                  const response = await fetch(url);
                  const data = await response.json();
                  
                  // 获取页面配置
                  const config = getPageConfig('recent');
                  const title = config.title || '最新资讯';
                  const description = config.description || '编程资讯和AI资讯的最新文章，按时间排序';
                  
                  let html = `
                    <div class="mb-6">
                      <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                      <p class="text-base text-gray-400 tech-font mb-4">${description} (共 ${data.total} 篇)</p>
                      
                      <!-- 搜索框 -->
                      <div class="flex gap-2 mb-4">
                        <input type="text" id="recent-search-input" 
                               class="flex-1 px-4 py-2 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan" 
                               placeholder="搜索文章标题或摘要..." 
                               value="${search}"
                               onkeypress="if(event.key==='Enter') handleRecentSearch()">
                        <button onclick="handleRecentSearch()" 
                                class="px-6 py-2 bg-gradient-to-r from-neon-cyan to-neon-blue text-dark-bg rounded-lg font-semibold hover:from-neon-blue hover:to-neon-cyan transition-all">
                          搜索
                        </button>
                        ${search ? `<button onclick="clearRecentSearch()" class="px-4 py-2 glass border border-dark-border text-gray-300 rounded-lg hover:bg-dark-card">清除</button>` : ''}
                        </div>
                      </div>
                    
                    <div class="space-y-4 mb-8">
                  `;
                  
                  if (data.items.length === 0) {
                    html += `<div class="text-center py-20 text-gray-400">${search ? '未找到相关文章' : '暂无文章'}</div>`;
                  } else {
                    data.items.forEach(article => {
                      const date = new Date(article.archived_at || article.published_time || article.created_at).toLocaleDateString('zh-CN');
                      const categoryLabel = article.category === 'ai_news' ? 'AI资讯' : '编程资讯';
                      
                      html += `
                        <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                          <div class="flex items-start gap-3 mb-2">
                            <span class="text-sm px-2 py-1 glass border border-neon-cyan/30 text-neon-cyan rounded">${categoryLabel}</span>
                            <span class="text-xs text-gray-400">${date}</span>
                    </div>
                          <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                            <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}'); return true;">${article.title}</a>
                          </h4>
                          <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                            <span>${article.source || '未知来源'}</span>
                          </div>
                          <p class="text-sm text-gray-300 leading-relaxed mb-3">
                            ${article.summary || ''}
                          </p>
                          <div class="flex items-center gap-2 flex-wrap">
                            ${(article.tags || []).map(tag => 
                              `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`
                            ).join('')}
                  </div>
                        </article>
                      `;
                    });
                  }
                  
                  html += '</div>';
                  
                  if (data.total_pages > 1) {
                    html += `
                      <div class="flex items-center justify-center gap-2 mt-8">
                        <button onclick="changeRecentPage(${data.page - 1}, '${search.replace(/'/g, "\\'")}')" 
                                ${data.page <= 1 ? 'disabled' : ''}
                                class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                          上一页
                        </button>
                        <span class="px-4 py-2 text-gray-400 tech-font">第 ${data.page} / ${data.total_pages} 页</span>
                        <button onclick="changeRecentPage(${data.page + 1}, '${search.replace(/'/g, "\\'")}')" 
                                ${data.page >= data.total_pages ? 'disabled' : ''}
                                class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                          下一页
                      </button>
                    </div>
                    `;
                  }
                  
                  mainContent.innerHTML = html;
                } catch (error) {
                  console.error('加载最新资讯失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败</div>';
                }
              }
              
              function changeRecentPage(page, search = '') {
                if (page < 1) return;
                recentSearchQuery = search;
                loadRecent(page, search);
              }
              
              function handleRecentSearch() {
                const searchInput = document.getElementById('recent-search-input');
                const query = searchInput ? searchInput.value.trim() : '';
                recentSearchQuery = query;
                loadRecent(1, query);
              }
              
              function clearRecentSearch() {
                recentSearchQuery = '';
                loadRecent(1, '');
              }
              
              // 加载热门资讯（按点击次数排序）
              async function loadHotNews(page = 1) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  // 获取热门文章（按热度排序，获取所有文章，不传category）
                  const response = await fetch(`${API_BASE}/news?page=${page}&page_size=${currentPage.pageSize}&sort_by=score`);
                  const data = await response.json();
                  
                  renderHotArticles(data.items, data.total, data.page, data.total_pages);
                } catch (error) {
                  console.error('加载热门资讯失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败</div>';
                }
              }
              
              // 渲染热门文章列表
              function renderHotArticles(articles, total, page, totalPages) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                const config = getPageConfig('hot-news');
                const title = config.title || '热门资讯';
                const description = config.description || '最受欢迎的技术文章';
                
                let html = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description} (共 ${total} 篇)</p>
                  </div>
                  
                  <div class="space-y-4 mb-8">
                `;
                
                if (articles.length === 0) {
                  html += '<div class="text-center py-20 text-gray-400">暂无文章数据</div>';
                } else {
                  articles.forEach(article => {
                    const date = new Date(article.archived_at || article.published_time || article.created_at).toLocaleDateString('zh-CN');
                    const viewCount = article.view_count || 0;
                    const categoryLabel = article.category === 'ai_news' ? 'AI资讯' : '编程资讯';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                        <div class="flex items-start gap-3 mb-2">
                          <span class="text-sm px-2 py-1 glass border border-neon-cyan/30 text-neon-cyan rounded">${categoryLabel}</span>
                          <span class="text-xs text-gray-400">${date}</span>
                          <span class="text-xs text-yellow-400">🔥 ${viewCount} 次点击</span>
                        </div>
                        <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                          <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}')">${article.title}</a>
                      </h4>
                        <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                          <span>${article.source || '未知来源'}</span>
                      </div>
                        <p class="text-sm text-gray-300 leading-relaxed mb-3">
                          ${article.summary || ''}
                        </p>
                        <div class="flex items-center gap-2 flex-wrap">
                          ${(article.tags || []).map(tag => 
                            `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`
                          ).join('')}
                      </div>
                    </article>
                    `;
                  });
                }
                
                html += '</div>';
                
                // 分页控件
                if (totalPages > 1) {
                  html += `
                    <div class="flex items-center justify-center gap-2 mt-8">
                      <button onclick="changeHotNewsPage(${page - 1})" 
                              ${page <= 1 ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        上一页
                      </button>
                      <span class="px-4 py-2 text-gray-400 tech-font">
                        第 ${page} / ${totalPages} 页
                      </span>
                      <button onclick="changeHotNewsPage(${page + 1})" 
                              ${page >= totalPages ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        下一页
                      </button>
                      </div>
                  `;
                }
                
                mainContent.innerHTML = html;
              }
              
              function changeHotNewsPage(page) {
                if (page < 1) return;
                loadHotNews(page);
              }
              
              // 记录文章点击
              async function recordArticleClick(url) {
                try {
                  await fetch(`${API_BASE}/articles/click?url=${encodeURIComponent(url)}`, {
                    method: 'POST'
                  });
                  // 如果是热门资讯页面，刷新页面以更新热度显示
                  if (window.location.pathname === '/hot-news') {
                    const currentPage = parseInt(document.querySelector('.tech-font')?.textContent?.match(/\d+/)?.[0]) || 1;
                    setTimeout(() => loadHotNews(currentPage), 500);
                  }
                } catch (error) {
                  console.error('记录点击失败:', error);
                }
              }
              
              // 记录工具点击
              async function recordToolClick(toolId) {
                try {
                  await fetch(`${API_BASE}/tools/${toolId}/click`, {
                    method: 'POST'
                  });
                  // 如果是热门工具页面，刷新页面以更新热度显示
                  if (window.location.pathname === '/tools') {
                    const currentPage = parseInt(document.querySelector('.tech-font')?.textContent?.match(/\d+/)?.[0]) || 1;
                    setTimeout(() => loadTools(true, null, currentPage), 500);
                  }
                } catch (error) {
                  console.error('记录工具点击失败:', error);
                }
              }
              
              // 显示提交资讯表单
              function showSubmitForm() {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                const config = getPageConfig('submit');
                const title = config.title || '提交资讯';
                const description = config.description || '分享优质的技术文章和资讯';
                
                mainContent.innerHTML = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description}</p>
                  </div>
                  
                  <!-- 审核说明 -->
                  <div class="glass rounded-xl border border-neon-cyan/30 p-6 mb-6 max-w-2xl">
                    <div class="flex items-start gap-3">
                      <span class="text-2xl">ℹ️</span>
                      <div>
                        <h3 class="text-lg font-semibold text-neon-cyan mb-2">审核说明</h3>
                        <p class="text-sm text-gray-300 leading-relaxed">
                          您提交的资讯将进入文章候选池，由管理员进行人工审核。我们会在<strong class="text-neon-cyan">一天内</strong>完成审核，审核通过后即可在网站上展示。
                        </p>
                        <p class="text-sm text-gray-400 mt-2">
                          审核期间，您可以在管理员面板查看审核状态。
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div class="glass rounded-xl border border-dark-border p-8 max-w-2xl">
                    <form id="submit-form" class="space-y-6">
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">文章标题 <span class="text-red-400">*</span></label>
                        <input type="text" id="submit-title" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan" placeholder="请输入文章标题" required>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">文章链接 <span class="text-red-400">*</span></label>
                        <input type="url" id="submit-url" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan" placeholder="https://..." required>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">文章分类 <span class="text-red-400">*</span></label>
                        <select id="submit-category" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan">
                          <option value="programming">编程资讯</option>
                          <option value="ai_news">AI资讯</option>
                        </select>
                  </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">推荐理由（可选）</label>
                        <textarea id="submit-reason" rows="4" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan" placeholder="为什么推荐这篇文章..."></textarea>
                </div>
                      <button type="submit" class="w-full px-6 py-3 bg-gradient-to-r from-neon-cyan to-neon-blue text-dark-bg rounded-lg font-semibold hover:from-neon-blue hover:to-neon-cyan transition-all hover-glow">
                        提交资讯
                      </button>
                    </form>
                    <div id="submit-status" class="mt-4 text-sm"></div>
              </div>
                `;
                
                // 绑定表单提交
                document.getElementById('submit-form').addEventListener('submit', async function(e) {
                  e.preventDefault();
                  const title = document.getElementById('submit-title').value.trim();
                  const url = document.getElementById('submit-url').value.trim();
                  const category = document.getElementById('submit-category').value;
                  const reason = document.getElementById('submit-reason').value.trim();
                  
                  if (!title || !url) {
                    const statusEl = document.getElementById('submit-status');
                    statusEl.textContent = '请填写必填项';
                    statusEl.className = 'mt-4 text-sm text-red-400';
                    return;
                  }
                  
                  const statusEl = document.getElementById('submit-status');
                  statusEl.textContent = '提交中...';
                  statusEl.className = 'mt-4 text-sm text-blue-400';
                  
                  try {
                    const response = await fetch(`${API_BASE}/articles/submit`, {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                        title: title,
                        url: url,
                        category: category,
                        summary: reason || ''
                      })
                    });
                    
                    const data = await response.json();
                    
                    if (data.ok) {
                      statusEl.textContent = '提交成功！您的资讯已进入审核队列，我们会在一天内完成审核。';
                      statusEl.className = 'mt-4 text-sm text-green-400';
                      document.getElementById('submit-form').reset();
                    } else {
                      statusEl.textContent = data.message || '提交失败，请稍后重试。';
                      statusEl.className = 'mt-4 text-sm text-red-400';
                    }
                  } catch (error) {
                    console.error('提交失败:', error);
                    statusEl.textContent = '提交失败，请稍后重试。';
                    statusEl.className = 'mt-4 text-sm text-red-400';
                  }
                });
              }
              
              // 显示提交工具表单
              function showSubmitToolForm() {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">提交工具</h1>
                    <p class="text-base text-gray-400 tech-font">分享优质的开发工具和资源</p>
                  </div>
                  
                  <!-- 审核说明 -->
                  <div class="glass rounded-xl border border-neon-purple/30 p-6 mb-6 max-w-2xl">
                    <div class="flex items-start gap-3">
                      <span class="text-2xl">ℹ️</span>
                      <div>
                        <h3 class="text-lg font-semibold text-neon-purple mb-2">审核说明</h3>
                        <p class="text-sm text-gray-300 leading-relaxed">
                          您提交的工具将进入工具候选池，由管理员进行人工审核。我们会在<strong class="text-neon-purple">一天内</strong>完成审核，审核通过后即可在网站上展示。
                        </p>
                        <p class="text-sm text-gray-400 mt-2">
                          审核期间，您可以在管理员面板查看审核状态。
                        </p>
                      </div>
                  </div>
                </div>
                  
                  <div class="glass rounded-xl border border-dark-border p-8 max-w-2xl">
                    <form id="submit-tool-form" class="space-y-6">
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">工具名称 <span class="text-red-400">*</span></label>
                        <input type="text" id="tool-name" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="请输入工具名称" required>
              </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">工具链接 <span class="text-red-400">*</span></label>
                        <input type="url" id="tool-url" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="https://..." required>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">工具描述 <span class="text-red-400">*</span></label>
                        <textarea id="tool-description" rows="3" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="请简要描述工具的功能和特点..." required></textarea>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">工具分类 <span class="text-red-400">*</span></label>
                        <select id="tool-category" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple">
                          <option value="ide">开发IDE</option>
                          <option value="plugin">IDE插件</option>
                          <option value="cli">命令行工具</option>
                          <option value="codeagent">CodeAgent</option>
                          <option value="ai-test">AI测试</option>
                          <option value="review">代码审查</option>
                          <option value="devops">DevOps工具</option>
                          <option value="doc">文档相关</option>
                          <option value="design">设计工具</option>
                          <option value="ui">UI生成</option>
                          <option value="mcp">MCP工具</option>
                          <option value="other">其他工具</option>
                        </select>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">标签（可选，用逗号分隔）</label>
                        <input type="text" id="tool-tags" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="例如：开源, AI, 前端">
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">图标（可选）</label>
                        <input type="text" id="tool-icon" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="例如：</> 或 🚀" value="</>">
                      </div>
                      <button type="submit" class="w-full px-6 py-3 bg-gradient-to-r from-neon-purple to-neon-pink text-dark-bg rounded-lg font-semibold hover:from-neon-pink hover:to-neon-purple transition-all hover-glow">
                        提交工具
                      </button>
                    </form>
                    <div id="submit-tool-status" class="mt-4 text-sm"></div>
                  </div>
                `;
                
                // 绑定表单提交
                document.getElementById('submit-tool-form').addEventListener('submit', async function(e) {
                  e.preventDefault();
                  const name = document.getElementById('tool-name').value.trim();
                  const url = document.getElementById('tool-url').value.trim();
                  const description = document.getElementById('tool-description').value.trim();
                  const category = document.getElementById('tool-category').value;
                  const tags = document.getElementById('tool-tags').value.trim();
                  const icon = document.getElementById('tool-icon').value.trim() || '</>';
                  
                  if (!name || !url || !description) {
                    const statusEl = document.getElementById('submit-tool-status');
                    statusEl.textContent = '请填写必填项';
                    statusEl.className = 'mt-4 text-sm text-red-400';
                    return;
                  }
                  
                  const statusEl = document.getElementById('submit-tool-status');
                  statusEl.textContent = '提交中...';
                  statusEl.className = 'mt-4 text-sm text-blue-400';
                  
                  try {
                    const response = await fetch(`${API_BASE}/tools/submit`, {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                        name: name,
                        url: url,
                        description: description,
                        category: category,
                        tags: tags,
                        icon: icon
                      })
                    });
                    
                    const data = await response.json();
                    
                    if (data.ok) {
                      statusEl.textContent = '提交成功！您的工具已进入审核队列，我们会在一天内完成审核。';
                      statusEl.className = 'mt-4 text-sm text-green-400';
                      document.getElementById('submit-tool-form').reset();
                      document.getElementById('tool-icon').value = '</>';
                    } else {
                      statusEl.textContent = data.message || '提交失败，请稍后重试。';
                      statusEl.className = 'mt-4 text-sm text-red-400';
                    }
                  } catch (error) {
                    console.error('提交失败:', error);
                    statusEl.textContent = '提交失败，请稍后重试。';
                    statusEl.className = 'mt-4 text-sm text-red-400';
                  }
                });
              }
              
              // 显示微信公众号页面
              function showWeChatMP() {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                const config = getPageConfig('wechat-mp');
                const title = config.title || '微信公众号';
                const description = config.description || '关注我们的微信公众号，获取最新技术资讯';
                
                mainContent.innerHTML = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description}</p>
                  </div>
                  
                  <div class="flex flex-col items-center gap-6">
                    <div class="glass rounded-xl border border-dark-border p-8 w-full max-w-md text-center">
                      <div class="mb-6">
                        <img src="/static/wechat_mp_qr.jpg" alt="微信公众号二维码" class="w-64 h-64 mx-auto rounded-lg border border-dark-border" onerror="this.style.display='none'">
                      </div>
                      <p class="text-gray-300 mb-4">扫描二维码关注我们的微信公众号</p>
                      <p class="text-sm text-gray-400">获取最新的编程资讯、AI动态和开发工具推荐</p>
                    </div>
                    
                    <div class="glass rounded-xl border border-dark-border p-8 w-full max-w-2xl">
                      <div class="flex items-center justify-center mb-4">
                        <svg class="w-8 h-8 mr-3 text-gray-300" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"></path>
                        </svg>
                        <h2 class="text-2xl tech-font-bold text-neon-purple text-glow">开源项目</h2>
                      </div>
                      <p class="text-gray-300 mb-4 text-center">这个平台是开源的！欢迎访问我们的 GitHub 仓库</p>
                      <div class="bg-dark-secondary rounded-lg p-4 mb-4 border border-dark-border">
                        <div class="text-center">
                          <a href="https://github.com/yunlongwen/AI-CodeNexus" target="_blank" rel="noopener noreferrer" class="text-neon-cyan hover:text-neon-green transition-colors text-lg font-medium inline-flex items-center justify-center">
                            <svg class="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                              <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"></path>
                            </svg>
                            <span>yunlongwen/AI-CodeNexus</span>
                            <svg class="w-4 h-4 ml-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                            </svg>
                          </a>
                          <p class="text-sm text-gray-400 mt-1">编程资讯与工具聚合平台</p>
                        </div>
                      </div>
                      <div class="text-center">
                        <p class="text-gray-300 mb-3">⭐ 如果这个项目对你有帮助，欢迎给个 Star！</p>
                        <a href="https://github.com/yunlongwen/AI-CodeNexus" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-6 py-3 bg-gradient-to-r from-neon-purple to-neon-cyan text-white rounded-lg font-medium hover:from-neon-cyan hover:to-neon-purple transition-all transform hover:scale-105 shadow-lg shadow-neon-purple/50">
                          <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.29-1.552 3.297-1.23 3.297-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"></path>
                          </svg>
                          前往 GitHub 点 Star
                        </a>
                      </div>
                    </div>
                  </div>
                `;
              }
              
              // 管理员入口授权码验证
              let adminCodeInput = '';
              let adminCodeTimeout = null;
              const ADMIN_CODE_MAX_LENGTH = 50; // 最大长度限制
              
              async function checkAdminCode(input) {
                if (input.length < 3) return; // 至少3个字符才开始验证
                
                try {
                  const response = await fetch(`${API_BASE}/admin/verify-code?code=${encodeURIComponent(input)}`);
                  const data = await response.json();
                  
                  if (data.ok && data.valid) {
                    // 授权码正确，显示管理员入口
                    const adminEntry = document.getElementById('admin-entry');
                    if (adminEntry) {
                      adminEntry.style.display = 'block';
                      adminEntry.classList.remove('hidden');
                      // 保存到localStorage，避免刷新后需要重新输入
                      localStorage.setItem('admin_verified', 'true');
                    }
                    // 清空输入
                    adminCodeInput = '';
                  }
                } catch (error) {
                  console.error('验证授权码失败:', error);
                }
              }
              
              // 监听键盘输入（盲敲）
              document.addEventListener('keydown', function(e) {
                // 排除输入框、文本域等元素
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
                  return;
                }
                
                // 只处理可打印字符
                if (e.key.length === 1) {
                  adminCodeInput += e.key;
                  
                  // 限制长度
                  if (adminCodeInput.length > ADMIN_CODE_MAX_LENGTH) {
                    adminCodeInput = adminCodeInput.slice(-ADMIN_CODE_MAX_LENGTH);
                  }
                  
                  // 清除之前的定时器
                  if (adminCodeTimeout) {
                    clearTimeout(adminCodeTimeout);
                  }
                  
                  // 延迟验证，避免频繁请求
                  adminCodeTimeout = setTimeout(() => {
                    checkAdminCode(adminCodeInput);
                  }, 500);
                } else if (e.key === 'Backspace' || e.key === 'Delete') {
                  // 允许退格删除
                  adminCodeInput = adminCodeInput.slice(0, -1);
                } else if (e.key === 'Escape') {
                  // ESC键清空输入
                  adminCodeInput = '';
                }
              });
              
              // 初始化
              document.addEventListener('DOMContentLoaded', async function() {
                // 先加载配置文件
                await loadConfig();
                
                // 检查是否已经验证过（从localStorage）
                if (localStorage.getItem('admin_verified') === 'true') {
                  const adminEntry = document.getElementById('admin-entry');
                  if (adminEntry) {
                    adminEntry.style.display = 'block';
                    adminEntry.classList.remove('hidden');
                  }
                }
                
                // 顶部导航激活状态管理
                const topNavItems = document.querySelectorAll('.top-nav-item');
                const currentPath = window.location.pathname || '/news';
                
                function updateActiveNav() {
                  topNavItems.forEach(item => {
                    const href = item.getAttribute('href');
                    if (href === currentPath || (currentPath === '/' && href === '/news')) {
                      item.classList.add('active');
                    } else {
                      item.classList.remove('active');
                    }
                  });
                }
                
                updateActiveNav();
                
                // 监听popstate事件（浏览器前进/后退）
                window.addEventListener('popstate', function() {
                  handleRoute();
                  updateActiveNav();
                });
                
                // 点击导航项
                topNavItems.forEach(item => {
                  item.addEventListener('click', function(e) {
                    const href = this.getAttribute('href');
                    // 如果链接是外部链接（如管理员入口），直接跳转
                    if (href.startsWith('http') || href.startsWith('/digest')) {
                      return; // 允许默认行为，直接跳转
                    }
                    e.preventDefault();
                    // 使用 history API 更新 URL
                    window.history.pushState({}, '', href);
                    handleRoute();
                    updateActiveNav();
                  });
                });
                
                // 左侧分类点击
                document.querySelectorAll('.nav-item').forEach(item => {
                  item.addEventListener('click', function(e) {
                    const href = this.getAttribute('href');
                    // 如果是外部链接，直接跳转
                    if (href.startsWith('http') || href.startsWith('/digest')) {
                      return;
                    }
                    e.preventDefault();
                    // 使用 history API 更新 URL
                    window.history.pushState({}, '', href);
                    handleRoute();
                    updateActiveNav();
                  });
                });
                
                // 初始加载
                handleRoute();
              });
            </script>
          </div>
          
          <!-- 浮动按钮 -->
          <div class="fixed bottom-8 right-8 flex flex-col gap-3" style="z-index: 100;">
            <!-- 反馈/联系按钮 -->
            <button id="feedback-btn" class="w-14 h-14 bg-gradient-to-br from-neon-cyan to-neon-blue text-dark-bg rounded-full shadow-lg hover:from-neon-blue hover:to-neon-cyan transition-all flex items-center justify-center neon-glow hover-glow" title="反馈/联系">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </button>
            <!-- 回到顶部按钮 -->
            <button id="scroll-top-btn" class="w-14 h-14 glass border border-dark-border text-neon-cyan rounded-full shadow-lg hover:bg-dark-card transition-all flex items-center justify-center hover:border-neon-cyan opacity-0 pointer-events-none" title="回到顶部">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </button>
          </div>
          
          <script>
            // 反馈/联系按钮功能
            document.getElementById('feedback-btn')?.addEventListener('click', function() {
              // 跳转到提交资讯页面
              window.location.href = '/submit';
            });
            
            // 回到顶部按钮功能
            const scrollTopBtn = document.getElementById('scroll-top-btn');
            if (scrollTopBtn) {
              // 监听滚动，显示/隐藏按钮
              window.addEventListener('scroll', function() {
                if (window.pageYOffset > 300) {
                  scrollTopBtn.classList.remove('opacity-0', 'pointer-events-none');
                  scrollTopBtn.classList.add('opacity-100');
                } else {
                  scrollTopBtn.classList.add('opacity-0', 'pointer-events-none');
                  scrollTopBtn.classList.remove('opacity-100');
                }
              });
              
              // 点击回到顶部
              scrollTopBtn.addEventListener('click', function() {
                window.scrollTo({
                  top: 0,
                  behavior: 'smooth'
                });
              });
            }
          </script>
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
    
    # 注册API路由
    from .routes import api
    app.include_router(api.router, prefix="/api", tags=["api"])

    return app


app = create_app()


