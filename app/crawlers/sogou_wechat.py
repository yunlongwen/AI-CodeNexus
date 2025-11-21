"""
搜狗微信搜索爬虫

根据关键词搜索公众号文章，并提取文章列表。
"""
from typing import List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from ..sources.ai_candidates import CandidateArticle


async def search_articles_by_keyword(keyword: str, pages: int = 1) -> List[CandidateArticle]:
    """
    通过搜狗微信搜索，根据关键词抓取公众号文章。

    Args:
        keyword: 搜索的关键词。
        pages: 要抓取的页数。

    Returns:
        抓取到的候选文章列表。
    """
    base_url = "https://weixin.sogou.com/weixin"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    candidates: List[CandidateArticle] = []
    
    async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
        for page in range(1, pages + 1):
            params = {
                "type": "2",  # 文章类型
                "query": keyword,
                "page": page,
            }
            
            try:
                logger.info(f"Searching Sogou Weixin for '{keyword}', page {page}... ")
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                
                # 查找文章列表项
                news_list = soup.find("ul", class_="news-list")
                if not news_list:
                    logger.warning(f"Could not find news list on page {page}. Maybe rate-limited?")
                    break
                
                items = news_list.find_all("li")
                if not items:
                    logger.info(f"No more articles found on page {page}.")
                    break
                
                for item in items:
                    title_tag = item.find("h3")
                    summary_tag = item.find("p", class_="txt-info")
                    source_tag = item.find("a", class_="account")
                    
                    if not title_tag or not title_tag.a:
                        continue
                        
                    title = title_tag.text.strip()
                    # 搜狗会给一个临时的 URL，需要从 header 中解析出真实的公众号文章链接
                    temp_url = urljoin(base_url, title_tag.a["href"])
                    
                    summary = summary_tag.text.strip() if summary_tag else ""
                    source = source_tag.text.strip() if source_tag else ""
                    
                    try:
                        # 请求临时 URL 以获取真实的永久链接
                        # 增加 Referer 头，模拟从搜索结果页点击
                        redirect_headers = {"Referer": str(response.url)}
                        redirect_res = await client.get(temp_url, headers=redirect_headers)
                        real_url = str(redirect_res.url)
                        
                        if "mp.weixin.qq.com" in real_url:
                            candidates.append(CandidateArticle(
                                title=title,
                                url=real_url,
                                source=source,
                                summary=summary,
                                crawled_from=f"sogou_wechat:{keyword}"
                            ))
                            logger.debug(f"Found article: {title}")
                        else:
                            logger.warning(f"Failed to resolve real URL for: {title}")
                    except httpx.HTTPError as e:
                        logger.error(f"Error resolving redirect for {title}: {e}")

            except httpx.HTTPError as e:
                logger.error(f"Error fetching Sogou search results for page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred on page {page}: {e}")
                break
                
    logger.info(f"Finished searching. Found {len(candidates)} articles in total.")
    return candidates

