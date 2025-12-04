"""抓取服务模块"""

import random
from typing import List, Dict

from loguru import logger

from ..config_loader import load_crawler_keywords
from ..infrastructure.crawlers.sogou_wechat import search_articles_by_keyword
from ..domain.sources.ai_articles import get_all_articles, save_article_to_config


class CrawlerService:
    """抓取服务"""
    
    async def crawl_and_pick_articles_by_keywords(self) -> int:
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

