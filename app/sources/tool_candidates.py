"""
管理待审核的工具候选池（`data/tools/tool_candidates.json`）
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from loguru import logger


@dataclass
class CandidateTool:
    """待审核工具的数据结构"""
    name: str
    url: str
    description: str
    category: str
    tags: List[str] = None
    icon: str = "</>"
    submitted_by: str = ""  # 提交者信息（可选）
    submitted_at: str = ""  # 提交时间


def _candidate_data_path() -> Path:
    """获取工具候选池数据文件的路径"""
    return Path(__file__).resolve().parents[2] / "data" / "tools" / "tool_candidates.json"


def load_candidate_pool() -> List[CandidateTool]:
    """加载所有待审核的工具"""
    path = _candidate_data_path()
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            raw_items = json.load(f)
        
        if not isinstance(raw_items, list):
            logger.warning(f"Tool candidate config is not a list, found {type(raw_items)}. Resetting.")
            return []

        return [CandidateTool(**item) for item in raw_items]
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to load or parse candidate tools: {e}")
        return []


def save_candidate_pool(candidates: List[CandidateTool]) -> bool:
    """将候选工具列表完整写入配置文件（覆盖）"""
    path = _candidate_data_path()
    logger.info(f"保存工具候选池到: {path}, 工具数量: {len(candidates)}")
    
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为字典列表
        candidates_dict = [asdict(c) for c in candidates]
        logger.debug(f"转换后的候选工具数据: {candidates_dict[:2] if len(candidates_dict) > 0 else '[]'}")
        
        with path.open("w", encoding="utf-8") as f:
            json.dump(candidates_dict, f, ensure_ascii=False, indent=2)
        
        # 验证文件是否成功写入
        if path.exists():
            file_size = path.stat().st_size
            logger.info(f"工具候选池文件已保存，大小: {file_size} 字节")
            return True
        else:
            logger.error(f"工具候选池文件保存后不存在: {path}")
            return False
    except Exception as e:
        logger.error(f"保存工具候选池失败: {e}", exc_info=True)
        return False


def clear_candidate_pool() -> bool:
    """清空工具候选池"""
    return save_candidate_pool([])

