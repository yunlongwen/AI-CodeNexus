"""统一资讯源管理器"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from loguru import logger

from ...infrastructure.crawlers.rss import fetch_rss_articles
from ...infrastructure.crawlers.github_trending import fetch_github_trending
from ...infrastructure.crawlers.hackernews import fetch_hackernews_articles
from ...infrastructure.crawlers.sogou_wechat import search_articles_by_keyword


async def fetch_from_all_sources(
    keywords: List[str],
    rss_feeds: Optional[List[str]] = None,
    github_languages: Optional[List[str]] = None,
    hackernews_min_points: int = 100,
    max_per_source: int = 5,
) -> List[Dict[str, Any]]:
    """
    从所有配置的资讯源抓取文章
    
    Args:
        keywords: 关键词列表（用于搜狗微信搜索）
        rss_feeds: RSS Feed URL 列表
        github_languages: GitHub Trending 语言列表
        hackernews_min_points: Hacker News 最低分数
        max_per_source: 每个源最多抓取的文章数
        
    Returns:
        所有抓取到的文章列表
    """
    all_articles = []
    
    # 1. 搜狗微信搜索（关键词）
    if keywords:
        try:
            for keyword in keywords:
                articles = await search_articles_by_keyword(keyword, max_pages=1)
                all_articles.extend(articles[:max_per_source])
                await asyncio.sleep(1)  # 避免请求过快
        except Exception as e:
            logger.error(f"搜狗微信搜索失败: {e}")
    
    # 2. RSS Feeds
    if rss_feeds:
        tasks = [fetch_rss_articles(feed, max_per_source) for feed in rss_feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
    
    # 3. GitHub Trending
    if github_languages:
        tasks = [fetch_github_trending(lang, max_per_source) for lang in github_languages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
    
    # 4. Hacker News
    try:
        hn_articles = await fetch_hackernews_articles(hackernews_min_points, max_per_source * 2)
        all_articles.extend(hn_articles)
    except Exception as e:
        logger.error(f"Hacker News 抓取失败: {e}")
    
    # 计算热度分
    for article in all_articles:
        article["score"] = _calculate_article_score(article)
    
    # 按热度分排序
    all_articles.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    logger.info(f"从所有资讯源共抓取到 {len(all_articles)} 篇文章")
    return all_articles


def _calculate_article_score(article: Dict[str, Any]) -> float:
    """
    计算文章热度分
    
    考虑因素：
    - 来源权重
    - 时效性（今天发布的文章得分更高）
    - Hacker News points（如果有）
    - 标题长度（适中长度得分更高）
    """
    score = 0.0
    
    # 来源权重
    source = article.get("source", "").lower()
    if "hacker news" in source:
        score += article.get("points", 0) * 0.1  # Hacker News 分数加权
    elif "github" in source:
        score += 50  # GitHub Trending 基础分
    elif "rss" in source or "feed" in source:
        score += 30  # RSS Feed 基础分
    else:
        score += 20  # 其他来源基础分
    
    # 时效性：今天发布的文章额外加分
    if article.get("published_time"):
        try:
            pub_time = datetime.fromisoformat(article["published_time"])
            if pub_time.date() == datetime.now().date():
                score += 30
        except:
            pass
    
    # 标题长度：适中长度（20-60字符）得分更高
    title_len = len(article.get("title", ""))
    if 20 <= title_len <= 60:
        score += 10
    elif title_len > 0:
        score += 5
    
    # 有摘要的文章得分更高
    if article.get("summary"):
        score += 5
    
    return score

