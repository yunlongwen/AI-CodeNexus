"""
管理待审核的文章候选池（`config/ai_candidates.json`）
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from loguru import logger


@dataclass
class CandidateArticle:
    """待审核文章的数据结构"""
    title: str
    url: str
    source: str
    summary: str
    # 可以增加爬取时间、关键词等元数据
    crawled_from: str = ""


def _candidate_config_path() -> Path:
    """获取候选池配置文件的路径"""
    return Path(__file__).resolve().parents[2] / "config" / "ai_candidates.json"


def load_candidate_pool() -> List[CandidateArticle]:
    """加载所有待审核的文章"""
    path = _candidate_config_path()
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            raw_items = json.load(f)
        
        if not isinstance(raw_items, list):
            logger.warning(f"Candidate config is not a list, found {type(raw_items)}. Resetting.")
            return []

        return [CandidateArticle(**item) for item in raw_items]
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to load or parse candidate articles: {e}")
        return []


def save_candidate_pool(candidates: List[CandidateArticle]) -> bool:
    """将候选文章列表完整写入配置文件（覆盖）"""
    path = _candidate_config_path()
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in candidates], f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save candidate pool: {e}")
        return False


def add_candidates_to_pool(new_candidates: List[CandidateArticle], existing_urls: set) -> int:
    """
    将一批新抓取的文章添加到候选池，同时进行去重。

    Args:
        new_candidates: 新抓取的候选文章列表。
        existing_urls: 已存在于正式文章池和候选池中的所有 URL，用于去重。

    Returns:
        成功添加的新文章数量。
    """
    if not new_candidates:
        return 0

    current_candidates = load_candidate_pool()
    
    added_count = 0
    for candidate in new_candidates:
        if candidate.url not in existing_urls:
            current_candidates.append(candidate)
            existing_urls.add(candidate.url)  # 避免在同一批次中重复添加
            added_count += 1
    
    if added_count > 0:
        save_candidate_pool(current_candidates)
        logger.info(f"Added {added_count} new candidates to the pool.")
    else:
        logger.info("No new unique candidates to add.")
        
    return added_count

