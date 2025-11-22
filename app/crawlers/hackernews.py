"""Hacker News 抓取器"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any

import httpx
from loguru import logger


async def fetch_hackernews_articles(min_points: int = 100, max_items: int = 10) -> List[Dict[str, Any]]:
    """
    从 Hacker News 抓取高分文章
    
    Args:
        min_points: 最低分数阈值
        max_items: 最多抓取的文章数量
        
    Returns:
        文章列表，每个文章包含 title, url, source, summary, points
    """
    try:
        # Hacker News API
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 获取热门文章 ID 列表
            resp = await client.get(top_stories_url)
            resp.raise_for_status()
            story_ids = resp.json()[:max_items * 2]  # 多获取一些以便筛选
        
        articles = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 并发获取文章详情
            tasks = []
            for story_id in story_ids:
                tasks.append(_fetch_story_detail(client, story_id))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    continue
                if result and result.get("points", 0) >= min_points:
                    articles.append(result)
                    if len(articles) >= max_items:
                        break
        
        logger.info(f"从 Hacker News 抓取到 {len(articles)} 篇高分文章（≥{min_points} points）")
        return articles
        
    except Exception as e:
        logger.error(f"抓取 Hacker News 失败: {e}")
        return []


async def _fetch_story_detail(client: httpx.AsyncClient, story_id: int) -> Dict[str, Any]:
    """获取单篇文章详情"""
    try:
        url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("type") != "story" or not data.get("url"):
            return None
        
        return {
            "title": data.get("title", "无标题"),
            "url": data.get("url", ""),
            "source": "Hacker News",
            "summary": f"分数: {data.get('score', 0)} points | 评论: {data.get('descendants', 0)}",
            "points": data.get("score", 0),
        }
    except Exception as e:
        logger.debug(f"获取 Hacker News 文章 {story_id} 详情失败: {e}")
        return None

