"""
搜狗微信搜索爬虫 (Playwright 版本)

使用无头浏览器模拟真实用户操作，以绕过反爬虫机制。
"""
import asyncio
from typing import List
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from ..sources.ai_candidates import CandidateArticle

def _parse_time_string(time_str: str) -> datetime:
    """
    将搜狗返回的时间字符串（如 '1小时前', '昨天', '2025-11-21'）转换为 datetime 对象。
    """
    now = datetime.now()
    if "小时前" in time_str:
        hours_ago = int(time_str.replace("小时前", ""))
        return now - timedelta(hours=hours_ago)
    if "分钟前" in time_str:
        minutes_ago = int(time_str.replace("分钟前", ""))
        return now - timedelta(minutes=minutes_ago)
    if "昨天" in time_str:
        return now - timedelta(days=1)
    # 默认按 YYYY-MM-DD 格式解析
    return datetime.strptime(time_str, "%Y-%m-%d")


async def search_articles_by_keyword(
    keyword: str, pages: int = 1
) -> List[CandidateArticle]:
    """
    通过搜狗微信搜索，使用 Playwright 根据关键词抓取公众号文章。

    Args:
        keyword: 搜索的关键词。
        pages: 要抓取的页数。

    Returns:
        抓取到的候选文章列表。
    """
    logger.info(f"Starting Playwright search for '{keyword}'...")
    candidates: List[CandidateArticle] = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # 1. 打开搜狗微信首页
            await page.goto("https://weixin.sogou.com/", wait_until="domcontentloaded")

            # 2. 输入关键词并点击搜索
            await page.locator("#query").fill(keyword)
            await page.locator("input[value='搜文章']").click()

            for i in range(1, pages + 1):
                logger.info(f"Parsing search results page {i} for '{keyword}'...")
                try:
                    # 等待搜索结果列表出现
                    await page.wait_for_selector("ul.news-list", timeout=15000)
                except PlaywrightTimeoutError:
                    logger.warning(
                        f"Timeout waiting for search results on page {i}. It might be a CAPTCHA page or empty results."
                    )
                    debug_dir = Path(__file__).resolve().parents[2] / "debug"
                    debug_dir.mkdir(exist_ok=True)
                    screenshot_path = debug_dir / f"playwright_timeout_{keyword}_{i}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"Saved timeout screenshot to {screenshot_path}")
                    break

                content = await page.content()
                soup = BeautifulSoup(content, "lxml")
                news_list = soup.find("ul", class_="news-list")

                if not news_list:
                    logger.warning(f"Could not find news list on page {i}, stopping.")
                    break

                items = news_list.find_all("li")
                if not items:
                    logger.info(f"No more articles found on page {i}.")
                    break

                for item in items:
                    title_tag = item.find("h3")
                    summary_tag = item.find("p", class_="txt-info")
                    source_tag = item.find("a", class_="account")
                    time_tag = item.find("span", class_="s2")

                    if not title_tag or not title_tag.a or not time_tag:
                        continue

                    title = title_tag.text.strip()
                    
                    # --- Start Date Filtering ---
                    time_str = time_tag.text.strip()
                    try:
                        article_dt = _parse_time_string(time_str)
                        # 只处理一天内的文章
                        if (datetime.now() - article_dt).days > 1:
                            logger.debug(f"Skipping old article: {title} (published on {article_dt.date()})")
                            continue
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse time string '{time_str}' for article: {title}")
                        continue
                    # --- End Date Filtering ---

                    temp_url = urljoin(page.url, title_tag.a["href"])
                    summary = summary_tag.text.strip() if summary_tag else ""
                    source = source_tag.text.strip() if source_tag else ""

                    try:
                        redirect_page = await context.new_page()
                        await redirect_page.goto(temp_url, wait_until="domcontentloaded", timeout=15000)
                        await redirect_page.wait_for_url("**/mp.weixin.qq.com/**", timeout=20000)
                        real_url = redirect_page.url
                        await redirect_page.close()

                        if "mp.weixin.qq.com" in real_url:
                            candidates.append(
                                CandidateArticle(
                                    title=title,
                                    url=real_url,
                                    source=source,
                                    summary=summary,
                                    crawled_from=f"sogou_wechat:{keyword}",
                                )
                            )
                            logger.debug(f"Successfully resolved: {title}")
                        else:
                            logger.warning(f"Resolved URL is not a Weixin article: {title} -> {real_url}")

                    except PlaywrightTimeoutError:
                        logger.warning(f"Timeout resolving real URL for: {title}")
                        if 'redirect_page' in locals() and not redirect_page.is_closed():
                            await redirect_page.close()
                    except Exception as e:
                        logger.error(f"Error resolving redirect for {title}: {e}")
                        if 'redirect_page' in locals() and not redirect_page.is_closed():
                            await redirect_page.close()
                
                # 翻页
                if i < pages:
                    next_page_button = page.locator("#sogou_next")
                    if await next_page_button.is_visible():
                        logger.info("Clicking 'Next Page' button...")
                        await next_page_button.click()
                    else:
                        logger.info("No 'Next Page' button found, stopping pagination.")
                        break

            await browser.close()

    except Exception as e:
        logger.error(f"An unexpected error occurred during Playwright execution: {e}")

    logger.info(f"Finished Playwright search. Found {len(candidates)} articles in total.")
    return candidates
