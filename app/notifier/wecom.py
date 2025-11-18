import os
from typing import Iterable, List

import httpx
from loguru import logger


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
    lines: List[str] = []
    lines.append(f"**AI 编程优质文章推荐｜{date_str}**")
    lines.append("")
    lines.append(f"> 今日主题：{theme}")
    lines.append("")

    for idx, item in enumerate(items, start=1):
        title = item["title"]
        url = item["url"]
        source = item.get("source", "")
        summary = item.get("summary") or ""

        lines.append(f"{idx}. [{title}]({url})")
        if source:
            lines.append(f"   - 来源：{source}")
        if summary:
            lines.append(f"   - 摘要：{summary}")
        lines.append("")

    lines.append("> 更多关于 AI 编程的实践与思考，见：100kwhy.fun")

    return "\n".join(lines)


