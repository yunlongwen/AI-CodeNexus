import os
from typing import Iterable, List

import httpx
from loguru import logger

from ..config_loader import load_wecom_template

WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK", "")


async def send_markdown_to_wecom(content: str) -> None:
    """
    Send a markdown message to Enterprise WeChat group via robot webhook.

    Docs (CN): https://developer.work.weixin.qq.com/document/path/91770
    """
    if not WECOM_WEBHOOK:
        logger.warning("WECOM_WEBHOOK not set, skip sending message.")
        return

    payload = {"msgtype": "markdown", "markdown": {"content": content}}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(WECOM_WEBHOOK, json=payload)
        try:
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to parse WeCom response: {exc}")
            return

        if data.get("errcode") != 0:
            logger.error(f"WeCom robot send failed: {data}")
        else:
            logger.info("WeCom robot message sent successfully.")


def build_wecom_digest_markdown(
    date_str: str,
    theme: str,
    items: Iterable[dict],
) -> str:
    """
    Build a markdown message tailored for WeCom group.

    `items` is an iterable of dicts with keys:
      - title
      - url
      - source
      - summary (optional)
    """
    template = load_wecom_template()

    def _format(fmt: str, **kwargs: str) -> str:
        try:
            return fmt.format(**kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Invalid WeCom template expression {fmt!r}: {exc}")
            return fmt

    lines: List[str] = []
    title_fmt = template.get("title", "**AI 编程优质文章推荐｜{date}**")
    if title_fmt:
        lines.append(_format(title_fmt, date=date_str, theme=theme))
        lines.append("")

    theme_fmt = template.get("theme", "> 今日主题：{theme}")
    if theme_fmt:
        lines.append(_format(theme_fmt, date=date_str, theme=theme))
        lines.append("")

    item_template = template.get("item", {}) if isinstance(template.get("item"), dict) else {}
    title_line = item_template.get("title", "{idx}. [{title}]({url})")
    source_line = item_template.get("source", "   - 来源：{source}")
    summary_line = item_template.get("summary", "   - 摘要：{summary}")
    extra_lines = item_template.get("extra", [])
    if not isinstance(extra_lines, list):
        extra_lines = []

    for idx, item in enumerate(items, start=1):
        context = {
            "idx": idx,
            "title": item["title"],
            "url": item["url"],
            "source": item.get("source", ""),
            "summary": item.get("summary") or "",
            "theme": theme,
            "date": date_str,
        }

        if title_line:
            lines.append(_format(title_line, **context))
        if context["source"] and source_line:
            lines.append(_format(source_line, **context))
        if context["summary"] and summary_line:
            lines.append(_format(summary_line, **context))
        for extra in extra_lines:
            lines.append(_format(extra, **context))
        lines.append("")

    footer_fmt = template.get("footer", "> 更多关于 AI 编程的实践与思考，见：100kwhy.fun")
    if footer_fmt:
        lines.append(_format(footer_fmt, date=date_str, theme=theme))

    return "\n".join(lines)


