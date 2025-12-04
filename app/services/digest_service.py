"""推送服务模块"""

import asyncio
from datetime import datetime
from typing import List, Dict

from loguru import logger

from ..infrastructure.file_lock import FileLock
from ..infrastructure.notifiers.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from ..domain.sources.ai_articles import (
    pick_daily_ai_articles,
    todays_theme,
    clear_articles,
    get_all_articles,
    save_article_to_config,
)
from ..domain.sources.ai_candidates import promote_candidates_to_articles, clear_candidate_pool
from .crawler_service import CrawlerService


class DigestService:
    """推送服务"""
    
    def __init__(self):
        """初始化推送服务"""
        self._lock = asyncio.Lock()
        self._file_lock = FileLock()
        self._crawler_service = CrawlerService()
    
    async def send_daily_digest(self, digest_count: int) -> None:
        """
        发送每日推送
        
        Args:
            digest_count: 推送文章数量
        """
        # 首先尝试获取文件锁（跨进程锁），防止多个进程同时执行
        if not self._file_lock.acquire():
            logger.warning("[定时推送] 检测到其他进程正在执行推送任务，跳过本次执行以避免重复推送")
            return
        
        try:
            # 使用进程内锁防止同一进程内的并发执行
            if self._lock.locked():
                logger.warning("[定时推送] 检测到任务正在执行中，跳过本次执行以避免重复推送")
                self._file_lock.release()
                return
            
            async with self._lock:
                now = datetime.now()
                logger.info(
                    f"[定时推送] 开始执行定时推送任务，时间: {now.strftime('%Y-%m-%d %H:%M:%S')}, "
                    f"目标篇数: {digest_count}"
                )
                
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
                    crawled_count = await self._crawler_service.crawl_and_pick_articles_by_keywords()
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
            self._file_lock.release()

