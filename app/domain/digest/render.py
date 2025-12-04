from textwrap import dedent

from .models import DailyDigest


def render_digest_for_mp(digest: DailyDigest) -> str:
    """
    Render daily digest to a simple Markdown-like text
    that you can直接复制到公众号后台，再做少量排版。
    """
    lines: list[str] = []
    lines.append(f"【AI 编程 & 团队管理日报】{digest.date:%Y-%m-%d}")
    lines.append("")
    lines.append(f"今日主题：{digest.theme}")
    lines.append("")

    for idx, item in enumerate(digest.items, start=1):
        lines.append(f"{idx}. {item.title}")
        lines.append(f"   - 来源：{item.source}")
        if item.summary:
            lines.append(f"   - 摘要：{item.summary}")
        if item.comment:
            lines.append(f"   - 点评：{item.comment}")
        lines.append(f"   - 原文链接：{item.url}")
        lines.append("")

    if digest.extra_note:
        lines.append("——")
        lines.append(digest.extra_note)

    return "\n".join(lines)


DAILY_TEMPLATE = dedent(
    """
    【AI 编程最新资讯 · 管理员面板】{date}

    今日主题：{theme}

    1. 示例标题：xxxx
       - 来源：示例公众号
       - 摘要：一句话说明这篇文章讲了什么，对谁有用。
       - 点评：你站在工程实践 / 管理视角的一句短评。
       - 原文链接：粘贴原文链接

    （按上面格式列出 3–5 条即可）

    —— 
    你可以在菜单里查看往期日报，也可以在站点 100kwhy.fun 上看到更多实战文章。
    """
).strip()


