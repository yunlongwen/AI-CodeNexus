import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
    )

    return schedule


