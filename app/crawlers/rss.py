"""RSS/Atom Feed 抓取器"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from feedparser import parse as feedparse


async def fetch_rss_articles(feed_url: str, max_items: int = 10) -> List[Dict[str, Any]]:
    """
    从 RSS/Atom Feed 抓取文章
    
    Args:
        feed_url: RSS/Atom Feed URL
        max_items: 最多抓取的文章数量
        
    Returns:
        文章列表，每个文章包含 title, url, source, summary, published_time
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(feed_url)
            resp.raise_for_status()
            
        feed = feedparse(resp.text)
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed parse warning for {feed_url}: {feed.bozo_exception}")
        
        articles = []
        for entry in feed.entries[:max_items]:
            # 提取发布时间
            published_time = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_time = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_time = datetime(*entry.updated_parsed[:6])
            
            # 只抓取今天的文章
            if published_time and published_time.date() != datetime.now().date():
                continue
            
            # 提取摘要
            summary = ""
            if hasattr(entry, 'summary'):
                summary = entry.summary
            elif hasattr(entry, 'description'):
                summary = entry.description
            
            # 清理 HTML 标签
            if summary:
                soup = BeautifulSoup(summary, 'html.parser')
                summary = soup.get_text().strip()[:200]  # 限制长度
            
            articles.append({
                "title": entry.title if hasattr(entry, 'title') else "无标题",
                "url": entry.link if hasattr(entry, 'link') else "",
                "source": "100kwhy",  # 爬取的资讯统一使用"100kwhy"作为来源
                "summary": summary,
                "published_time": published_time.isoformat() if published_time else None,
            })
        
        logger.info(f"从 RSS Feed {feed_url} 抓取到 {len(articles)} 篇文章")
        return articles
        
    except Exception as e:
        logger.error(f"抓取 RSS Feed {feed_url} 失败: {e}")
        return []

