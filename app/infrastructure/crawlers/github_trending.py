"""GitHub Trending 抓取器"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any

import httpx
from bs4 import BeautifulSoup
from loguru import logger


async def fetch_github_trending(language: str = "python", max_items: int = 10) -> List[Dict[str, Any]]:
    """
    从 GitHub Trending 抓取热门项目
    
    Args:
        language: 编程语言（python, javascript, go 等），空字符串表示所有语言
        max_items: 最多抓取的项目数量
        
    Returns:
        项目列表，每个项目包含 title, url, source, summary
    """
    try:
        url = "https://github.com/trending"
        if language:
            url += f"/{language}"
        
        async with httpx.AsyncClient(timeout=10.0, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        articles = []
        
        # GitHub Trending 的 HTML 结构可能会变化，这里是一个基础实现
        repo_items = soup.select("article.Box-row")[:max_items]
        
        for item in repo_items:
            # 提取仓库名称和链接
            title_elem = item.select_one("h2 a")
            if not title_elem:
                continue
            
            repo_name = title_elem.get_text(strip=True)
            repo_url = "https://github.com" + title_elem.get("href", "")
            
            # 提取描述
            desc_elem = item.select_one("p.col-9")
            summary = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # 提取语言和星标数
            lang_elem = item.select_one("span[itemprop='programmingLanguage']")
            lang = lang_elem.get_text(strip=True) if lang_elem else ""
            
            stars_elem = item.select_one("a[href*='/stargazers']")
            stars = stars_elem.get_text(strip=True) if stars_elem else ""
            
            if lang:
                summary = f"[{lang}] {summary}" if summary else f"编程语言: {lang}"
            if stars:
                summary = f"{summary} ⭐ {stars}" if summary else f"⭐ {stars}"
            
            articles.append({
                "title": repo_name,
                "url": repo_url,
                "source": "100kwhy",  # 爬取的资讯统一使用"100kwhy"作为来源
                "summary": summary or "GitHub 热门项目",
            })
        
        logger.info(f"从 GitHub Trending ({language}) 抓取到 {len(articles)} 个项目")
        return articles
        
    except Exception as e:
        logger.error(f"抓取 GitHub Trending 失败: {e}")
        return []

