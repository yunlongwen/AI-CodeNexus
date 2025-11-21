import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

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


