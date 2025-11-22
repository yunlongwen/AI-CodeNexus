import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


def _project_root() -> Path:
    # app/config_loader.py -> project_root
    return Path(__file__).resolve().parents[1]


@dataclass
class DigestSchedule:
    """
    每日推送配置。

    - 兼容老版本：使用 hour + minute
    - 推荐新方式：使用 cron 表达式（5 字段），例如：
      - 每天 14:00：      "0 14 * * *"
      - 每周一三五 9:30： "30 9 * * 1,3,5"
    """

    hour: int = 14
    minute: int = 0
    count: int = 5
    cron: Optional[str] = None  # 可选 cron 表达式（优先使用）
    max_articles_per_keyword: int = 5  # 每个关键词最多抓取的文章数


def _digest_schedule_path() -> Path:
    return _project_root() / "config" / "digest_schedule.json"


def load_digest_schedule() -> DigestSchedule:
    """
    Load daily digest schedule from config/digest_schedule.json.

    支持两种配置方式：
    1）老版：
    {
      "hour": 14,
      "minute": 0,
      "count": 5
    }

    2）推荐：使用 cron 表达式（5 字段，分 时 日 月 周）：
    {
      "cron": "0 14 * * *",
      "count": 5
    }
    """
    path = _digest_schedule_path()
    default = DigestSchedule()

    if not path.exists():
        logger.warning(f"Digest schedule config not found at {path}, using defaults: {default}.")
        return default

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load digest schedule config: {exc}, using defaults: {default}.")
        return default

    def _get_int(name: str, fallback: int) -> int:
        raw = data.get(name)
        if raw is None:
            return fallback
        try:
            return int(raw)
        except (TypeError, ValueError):
            logger.warning(f"Invalid value for digest schedule {name}={raw!r}, fallback to {fallback}.")
            return fallback

    # 解析 cron 表达式（可选）
    cron_raw = data.get("cron")
    cron_expr: Optional[str] = None
    hour = _get_int("hour", default.hour)
    minute = _get_int("minute", default.minute)

    if isinstance(cron_raw, str):
        cron_candidate = cron_raw.strip()
        if cron_candidate:
            cron_expr = cron_candidate
            parts = cron_candidate.split()
            # 简单从 cron 表达式中抽取「分 时」用于 UI 展示（不影响实际调度）
            if len(parts) >= 2:
                try:
                    minute = int(parts[0])
                    hour = int(parts[1])
                except ValueError:
                    logger.warning(
                        "Invalid cron minute/hour in %r, will still use cron for scheduling but "
                        "fallback to explicit hour/minute for UI.",
                        cron_candidate,
                    )

    schedule = DigestSchedule(
        hour=hour,
        minute=minute,
        count=_get_int("count", default.count),
        cron=cron_expr,
        max_articles_per_keyword=_get_int(
            "max_articles_per_keyword", default.max_articles_per_keyword
        ),
    )

    return schedule


def _crawler_keywords_path() -> Path:
    return _project_root() / "config" / "crawler_keywords.json"


def load_crawler_keywords() -> List[str]:
    path = _crawler_keywords_path()
    if not path.exists():
        logger.warning(f"Crawler keywords config not found at {path}.")
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("crawler keywords file must be a JSON array")

        return [str(item).strip() for item in data if str(item).strip()]
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load crawler keywords: {exc}.")
        return []


def save_crawler_keywords(keywords: List[str]) -> bool:
    path = _crawler_keywords_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    clean_keywords = [str(item).strip() for item in keywords if str(item).strip()]
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(clean_keywords, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(clean_keywords)} crawler keywords.")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to save crawler keywords: {exc}.")
        return False


def _tool_keywords_path() -> Path:
    return _project_root() / "config" / "tool_keywords.json"


def load_tool_keywords() -> List[str]:
    """加载工具关键字列表"""
    path = _tool_keywords_path()
    if not path.exists():
        logger.warning(f"Tool keywords config not found at {path}.")
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("tool keywords file must be a JSON array")

        return [str(item).strip() for item in data if str(item).strip()]
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load tool keywords: {exc}.")
        return []


def save_tool_keywords(keywords: List[str]) -> bool:
    """保存工具关键字列表"""
    path = _tool_keywords_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    clean_keywords = [str(item).strip() for item in keywords if str(item).strip()]
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(clean_keywords, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(clean_keywords)} tool keywords.")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to save tool keywords: {exc}.")
        return False


def add_tool_keyword(tool_name: str) -> bool:
    """添加工具名称到关键字配置（如果不存在）"""
    keywords = load_tool_keywords()
    tool_name = tool_name.strip()
    
    if not tool_name:
        return False
    
    # 检查是否已存在
    if tool_name in keywords:
        logger.debug(f"Tool keyword '{tool_name}' already exists")
        return True
    
    # 添加到列表
    keywords.append(tool_name)
    return save_tool_keywords(keywords)


def save_digest_schedule(schedule: Dict[str, Any]) -> bool:
    path = _digest_schedule_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    sanitized: Dict[str, Any] = {}
    numeric_keys = {
        "hour",
        "minute",
        "count",
        "max_articles_per_keyword",
    }

    for key in numeric_keys:
        if key in schedule:
            try:
                sanitized[key] = int(schedule[key])
            except (ValueError, TypeError):
                logger.warning(f"Ignoring invalid schedule value for {key}: {schedule[key]!r}")

    if "cron" in schedule and isinstance(schedule["cron"], str):
        sanitized["cron"] = schedule["cron"].strip()

    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(sanitized, f, ensure_ascii=False, indent=2)
        logger.info("Digest schedule saved.")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to save digest schedule: {exc}.")
        return False


def save_wecom_template(template: Dict[str, Any]) -> bool:
    path = _wecom_template_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        logger.info("WeCom template saved.")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to save WeCom template: {exc}.")
        return False


DEFAULT_WECOM_TEMPLATE: Dict[str, object] = {
    "title": "**AI 编程优质文章推荐｜{date}**",
    "theme": "> 今日主题：{theme}",
    "item": {
        "title": "{idx}. [{title}]({url})",
        "source": "   - 来源：{source}",
        "summary": "   - 摘要：{summary}",
    },
    "footer": "> 更多关于 AI 编程的实践与思考，见：100kwhy.fun",
}


def _wecom_template_path() -> Path:
    return _project_root() / "config" / "wecom_template.json"


def _deep_merge(base: Dict[str, object], override: Dict[str, object]) -> Dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_wecom_template() -> Dict[str, object]:
    """
    加载企业微信推送的样式模板。
    """
    path = _wecom_template_path()
    if not path.exists():
        logger.warning(f"WeCom template config not found at {path}, using defaults.")
        return DEFAULT_WECOM_TEMPLATE

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("template file must be a JSON object")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load WeCom template config: {exc}, using defaults.")
        return DEFAULT_WECOM_TEMPLATE

    return _deep_merge(DEFAULT_WECOM_TEMPLATE, data)


def _env_file_path() -> Path:
    """获取 .env 文件路径"""
    return _project_root() / ".env"


def load_env_var(key: str) -> str:
    """从 .env 文件读取环境变量值"""
    import os
    env_path = _env_file_path()
    if not env_path.exists():
        return os.getenv(key, "")
    
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == key:
                        return v
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to read .env file: {exc}")
    
    return os.getenv(key, "")


def save_env_var(key: str, value: str) -> bool:
    """更新 .env 文件中的环境变量"""
    env_path = _env_file_path()
    lines = []
    key_found = False
    
    # 读取现有内容
    if env_path.exists():
        try:
            with env_path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to read .env file: {exc}")
            return False
    
    # 转义值中的特殊字符，确保 .env 文件格式正确
    # 转义反斜杠、引号、换行符等
    escaped_value = (
        value
        .replace("\\", "\\\\")  # 先转义反斜杠
        .replace('"', '\\"')    # 转义双引号
        .replace("'", "\\'")    # 转义单引号
        .replace("\n", "\\n")   # 转义换行符
        .replace("\r", "\\r")   # 转义回车符
        .replace("$", "\\$")    # 转义美元符号（避免变量替换）
    )
    
    # 更新或添加变量
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        
        if "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k == key:
                # 使用双引号包裹，确保特殊字符被正确转义
                new_lines.append(f'{key}="{escaped_value}"\n')
                key_found = True
                continue
        
        new_lines.append(line)
    
    # 如果没找到，添加到末尾
    if not key_found:
        new_lines.append(f'{key}="{escaped_value}"\n')
    
    # 写入文件
    try:
        with env_path.open("w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info(f"Updated {key} in .env file")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to write .env file: {exc}")
        return False


