"""爬虫测试"""
import pytest
from app.infrastructure.crawlers.rss import fetch_rss_articles
from app.infrastructure.crawlers.github_trending import fetch_github_trending
from app.infrastructure.crawlers.hackernews import fetch_hackernews_articles


@pytest.mark.asyncio
async def test_fetch_rss_articles():
    """测试 RSS 抓取"""
    # 使用一个公开的 RSS Feed 进行测试
    articles = await fetch_rss_articles("https://rss.cnn.com/rss/edition.rss", max_items=5)
    assert isinstance(articles, list)
    # 注意：实际测试可能需要 mock 网络请求


@pytest.mark.asyncio
async def test_fetch_github_trending():
    """测试 GitHub Trending 抓取"""
    articles = await fetch_github_trending("python", max_items=5)
    assert isinstance(articles, list)


@pytest.mark.asyncio
async def test_fetch_hackernews():
    """测试 Hacker News 抓取"""
    articles = await fetch_hackernews_articles(min_points=50, max_items=5)
    assert isinstance(articles, list)

