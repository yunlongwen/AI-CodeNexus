from dataclasses import dataclass
from datetime import datetime
from random import sample
from typing import List, Optional


@dataclass
class AiArticle:
    title: str
    url: str
    source: str
    summary: str


def load_ai_articles_pool() -> List[AiArticle]:
    """
    Placeholder: load a pool of high-quality AI coding articles.

    For now this is hard-coded. Later you can:
      - load from database
      - or from a JSON/CSV file maintained by your curation workflow.
    """
    return [
        AiArticle(
            title="用 AI 重构遗留代码的实战流程",
            url="https://mp.weixin.qq.com/example1",
            source="某AI编程公众号",
            summary="介绍如何用大模型理解和重构复杂遗留代码，并控制风险。",
        ),
        AiArticle(
            title="让代码评审更高效：AI + 模板化 Checklist",
            url="https://mp.weixin.qq.com/example2",
            source="某工程实践公众号",
            summary="结合 AI 自动生成代码评审要点，减少无效 Review。",
        ),
        AiArticle(
            title="在真实团队中落地 AI 代码生成的 5 个坑",
            url="https://mp.weixin.qq.com/example3",
            source="某工程管理公众号",
            summary="分享 AI 代码生成在团队落地时的常见问题与对策。",
        ),
        AiArticle(
            title="从提示到工作流：用 AI 改造你的开发流水线",
            url="https://mp.weixin.qq.com/example4",
            source="某AI工具公众号",
            summary="不只写代码，而是把 AI 接入到整个开发工作流。",
        ),
        AiArticle(
            title="如何让初级工程师安全地使用 AI 写代码",
            url="https://mp.weixin.qq.com/example5",
            source="某团队管理公众号",
            summary="从规范、代码库保护和评审制度上给出实操建议。",
        ),
        AiArticle(
            title="LLM 时代的代码质量保障：测试、静态检查与 AI",
            url="https://mp.weixin.qq.com/example6",
            source="某测试实践公众号",
            summary="探讨如何在大量使用 AI 生成代码的前提下保证质量。",
        ),
    ]


def pick_daily_ai_articles(k: int = 5) -> List[AiArticle]:
    pool = load_ai_articles_pool()
    if len(pool) <= k:
        return pool
    return sample(pool, k)


def todays_theme(now: Optional[datetime] = None) -> str:
    # 简单占位：后续可以根据星期 / 最近热点等自动生成主题
    return "AI 编程效率与工程实践精选"


