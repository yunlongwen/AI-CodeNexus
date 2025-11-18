import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from random import sample
from typing import List, Optional

from loguru import logger


@dataclass
class AiArticle:
    title: str
    url: str
    source: str
    summary: str


def _config_path() -> Path:
    """
    Get path to config/ai_articles.json relative to project root.
    """
    # app/sources/ai_articles.py -> project_root/config/ai_articles.json
    return Path(__file__).resolve().parents[2] / "config" / "ai_articles.json"


def load_ai_articles_pool() -> List[AiArticle]:
    """
    Load a pool of high-quality AI coding articles from JSON config file.

    Config file: config/ai_articles.json
    Structure:
      [
        {
          "title": "...",
          "url": "...",
          "source": "...",
          "summary": "..."
        },
        ...
      ]
    """
    path = _config_path()
    if not path.exists():
        logger.warning(f"AI articles config not found at {path}, return empty list.")
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            raw_items = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load AI articles config: {exc}")
        return []

    # 确保 raw_items 是列表
    if not isinstance(raw_items, list):
        logger.warning(f"Config file contains {type(raw_items).__name__}, expected list. Resetting to empty list.")
        # 修复配置文件
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            pass
        return []

    articles: List[AiArticle] = []
    for item in raw_items:
        try:
            articles.append(
                AiArticle(
                    title=item.get("title", "").strip(),
                    url=item.get("url", "").strip(),
                    source=item.get("source", "").strip(),
                    summary=item.get("summary", "").strip(),
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Invalid article item in config: {item}, error: {exc}")

    return articles


def pick_daily_ai_articles(k: int = 5) -> List[AiArticle]:
    pool = load_ai_articles_pool()
    if len(pool) <= k:
        return pool
    return sample(pool, k)


def todays_theme(now: Optional[datetime] = None) -> str:
    # 简单占位：后续可以根据星期 / 最近热点等自动生成主题
    return "AI 编程效率精选"


def save_article_to_config(article: dict) -> bool:
    """
    将文章保存到配置文件
    
    Args:
        article: 包含 title, url, source, summary 的字典
        
    Returns:
        bool: 是否保存成功
    """
    path = _config_path()
    
    # 确保目录存在
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 加载现有文章
    existing_articles = []
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                existing_articles = json.load(f)
            # 确保是列表格式
            if not isinstance(existing_articles, list):
                logger.warning(f"Config file contains {type(existing_articles).__name__}, expected list. Resetting to empty list.")
                existing_articles = []
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to load existing articles: {exc}")
            existing_articles = []
    
    # 检查是否已存在相同URL的文章
    article_url = article.get("url", "").strip()
    if article_url:
        for item in existing_articles:
            if item.get("url", "").strip() == article_url:
                logger.warning(f"文章已存在，URL: {article_url}")
                return False
    
    # 添加新文章
    new_article = {
        "title": article.get("title", "").strip(),
        "url": article_url,
        "source": article.get("source", "").strip(),
        "summary": article.get("summary", "").strip(),
    }
    
    existing_articles.append(new_article)
    
    # 保存到文件
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(existing_articles, f, ensure_ascii=False, indent=2)
        logger.info(f"成功保存文章到配置: {new_article['title'][:50]}...")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to save article to config: {exc}")
        return False


def delete_article_from_config(url: str) -> bool:
    """
    从配置文件中删除指定URL的文章
    
    Args:
        url: 要删除的文章URL
        
    Returns:
        bool: 是否删除成功
    """
    path = _config_path()
    
    if not path.exists():
        logger.warning(f"配置文件不存在: {path}")
        return False
    
    # 加载现有文章
    try:
        with path.open("r", encoding="utf-8") as f:
            existing_articles = json.load(f)
        # 确保是列表格式
        if not isinstance(existing_articles, list):
            logger.warning(f"Config file contains {type(existing_articles).__name__}, expected list. Resetting to empty list.")
            existing_articles = []
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load existing articles: {exc}")
        return False
    
    # 查找并删除
    url_to_delete = url.strip()
    original_count = len(existing_articles)
    existing_articles = [
        item for item in existing_articles
        if item.get("url", "").strip() != url_to_delete
    ]
    
    if len(existing_articles) == original_count:
        logger.warning(f"未找到要删除的文章，URL: {url_to_delete}")
        return False
    
    # 保存到文件
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(existing_articles, f, ensure_ascii=False, indent=2)
        logger.info(f"成功删除文章，URL: {url_to_delete}")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to delete article from config: {exc}")
        return False


def get_all_articles() -> List[dict]:
    """
    获取配置文件中所有文章
    
    Returns:
        List[dict]: 所有文章的列表
    """
    path = _config_path()
    
    if not path.exists():
        return []
    
    try:
        with path.open("r", encoding="utf-8") as f:
            articles = json.load(f)
        if not isinstance(articles, list):
            logger.warning(f"Config file contains {type(articles).__name__}, expected list. Resetting to empty list.")
            # 修复配置文件
            try:
                with path.open("w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            except Exception:  # noqa: BLE001
                pass
            return []
        return articles
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load all articles: {exc}")
        return []


