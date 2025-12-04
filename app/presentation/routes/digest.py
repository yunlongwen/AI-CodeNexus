import math
import os
import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from dataclasses import asdict
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger
from pydantic import BaseModel

from ...config_loader import (
    load_digest_schedule,
    load_crawler_keywords,
    save_crawler_keywords,
    save_digest_schedule,
    load_wecom_template,
    save_wecom_template,
    load_env_var,
    save_env_var,
    load_tool_keywords,
    save_tool_keywords,
    add_tool_keyword,
)
from ...infrastructure.notifiers.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from ...infrastructure.notifiers.wechat_mp import WeChatMPClient
from ...domain.sources.ai_articles import (
    clear_articles,
    delete_article_from_config,
    get_all_articles,
    pick_daily_ai_articles,
    save_article_to_config,
    todays_theme,
)
from ...domain.sources.article_sources import fetch_from_all_sources
from ...infrastructure.crawlers.rss import fetch_rss_articles
from ...infrastructure.crawlers.github_trending import fetch_github_trending
from ...infrastructure.crawlers.hackernews import fetch_hackernews_articles
from ...domain.sources.article_crawler import fetch_article_info
from ...infrastructure.crawlers.sogou_wechat import search_articles_by_keyword
from ...infrastructure.crawlers.devmaster import fetch_tools_from_api
from ...domain.sources.ai_candidates import (
    add_candidates_to_pool,
    clear_candidate_pool,
    load_candidate_pool,
    promote_candidates_to_articles,
    save_candidate_pool,
)
from ...domain.sources.tool_candidates import (
    load_candidate_pool as load_tool_candidate_pool,
    save_candidate_pool as save_tool_candidate_pool,
    CandidateTool,
)
from ...services.weekly_digest import update_weekly_digest
import json
from pathlib import Path

router = APIRouter()


# 管理员授权码从环境变量中读取，避免敏感信息写死在代码里
ADMIN_CODE = os.getenv("AICODING_ADMIN_CODE")


def _require_admin(x_admin_code: Optional[str] = Header(default=None)) -> None:
    """
    简单的管理授权校验。

    - 前端在请求时通过 header: X-Admin-Code 传入授权码
    - 授权码从环境变量 AICODING_ADMIN_CODE 中读取
    - 如果环境变量未配置，则不启用认证（用于本地开发）
    """
    # 未配置管理员授权码：认为处于开发/测试环境，不做校验
    if not ADMIN_CODE:
        return

    if x_admin_code != ADMIN_CODE:
        raise HTTPException(status_code=403, detail="无权限：缺少或错误的授权码")


class AddArticleRequest(BaseModel):
    url: str


class DeleteArticleRequest(BaseModel):
    url: str

class ArchiveArticleFromPoolRequest(BaseModel):
    url: str
    category: str
    tool_tags: Optional[list[str]] = None

class KeywordsConfigRequest(BaseModel):
    keywords: list[str]

class ScheduleConfigRequest(BaseModel):
    cron: Optional[str] = None
    hour: Optional[int] = None
    minute: Optional[int] = None
    count: Optional[int] = None
    max_articles_per_keyword: Optional[int] = None

class WecomTemplateRequest(BaseModel):
    template: dict

class CandidateActionRequest(BaseModel):
    url: str

class ArchiveArticleRequest(BaseModel):
    url: str
    category: str  # 分类名称，如 programming, ai_news
    tool_tags: Optional[list[str]] = []  # 工具标签列表，可为空


def _clear_content_pools() -> None:
    """清空正式文章池与候选池"""
    clear_articles()
    clear_candidate_pool()


def _build_digest():
    now = datetime.now()
    schedule = load_digest_schedule()
    articles = pick_daily_ai_articles(k=schedule.count)

    items = [
        {
            "title": a.title,
            "url": a.url,
            "source": a.source,
            "summary": a.summary,
        }
        for a in articles
    ]

    digest = {
        "date": now.strftime("%Y-%m-%d"),
        "theme": todays_theme(now),
        "schedule": {
            "hour": schedule.hour,
            "minute": schedule.minute,
            "count": schedule.count,
            "cron": getattr(schedule, "cron", None),
        },
        "articles": items,
    }
    return digest


@router.get("/preview")
async def preview_digest(admin: None = Depends(_require_admin)):
    """
    返回当前配置下将要推送的日报内容（不真正发送）。
    """
    digest = _build_digest()
    return digest


@router.post("/trigger")
async def trigger_digest(admin: None = Depends(_require_admin)):
    """
    手动触发一次企业微信推送，并返回本次发送的内容。
    """
    try:
        logger.info("[手动推送] 开始执行手动推送任务")
        schedule = load_digest_schedule()
        articles = pick_daily_ai_articles(k=schedule.count)
        
        # 如果文章池为空，尝试从候选池提升
        if not articles:
            logger.info("[手动推送] 文章池为空，尝试从候选池提升文章...")
            promoted = promote_candidates_to_articles(per_keyword=2)
            if promoted:
                logger.info(f"[手动推送] 从候选池提升了 {promoted} 篇文章")
                articles = pick_daily_ai_articles(k=schedule.count)
        
        if not articles:
            logger.warning("[手动推送] 文章池为空且无法从候选池提升文章")
            raise HTTPException(status_code=400, detail="文章池为空，请先添加或抓取文章。")

        digest = _build_digest()
        content = build_wecom_digest_markdown(
            date_str=digest["date"],
            theme=digest["theme"],
            items=digest["articles"],
        )
        
        logger.info(f"[手动推送] 准备推送 {len(digest['articles'])} 篇文章")
        logger.info("[手动推送] 正在发送到企业微信群...")
        success = await send_markdown_to_wecom(content)
        
        if not success:
            logger.error("[手动推送] 推送失败")
            raise HTTPException(status_code=500, detail="推送失败，请检查企业微信配置和网络连接。")
        
        logger.info("[手动推送] 推送成功，正在清理文章池和候选池...")
        _clear_content_pools()
        logger.info("[手动推送] 手动推送任务执行成功")
        return {"ok": True, **digest}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[手动推送] 手动推送任务执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"推送失败: {str(e)}")


@router.get("/articles")
async def list_all_articles(admin: None = Depends(_require_admin)):
    """
    获取配置文件中所有文章列表，并检查归档状态。
    
    Returns:
        dict: 包含所有文章的列表，每个文章包含 is_archived 字段
    """
    from ...services.data_loader import DataLoader
    
    articles = get_all_articles()
    
    # 检查每篇文章的归档状态
    articles_with_status = []
    for article in articles:
        article_dict = article if isinstance(article, dict) else {
            "title": article.title if hasattr(article, 'title') else article.get("title", ""),
            "url": article.url if hasattr(article, 'url') else article.get("url", ""),
            "source": article.source if hasattr(article, 'source') else article.get("source", ""),
            "summary": article.summary if hasattr(article, 'summary') else article.get("summary", ""),
        }
        # 检查归档状态
        article_dict["is_archived"] = DataLoader.is_article_archived(article_dict.get("url", ""))
        articles_with_status.append(article_dict)
    
    return {"ok": True, "articles": articles_with_status}


@router.post("/add-article")
async def add_article(request: AddArticleRequest, admin: None = Depends(_require_admin)):
    """
    从URL爬取文章信息并添加到配置文件中。
    
    Args:
        request: 包含文章URL的请求体
        
    Returns:
        dict: 包含成功状态和文章信息的响应
    """
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")
    
    try:
        # 爬取文章信息
        logger.info(f"开始爬取文章信息: {url}")
        article_info = await fetch_article_info(url)
        
        # 保存到配置文件
        success = save_article_to_config(article_info)
        if not success:
            # 如果保存失败，可能是文章已存在
            return {
                "ok": False,
                "message": "文章已存在或保存失败",
                "article": article_info,
            }
        
        return {
            "ok": True,
            "message": "文章已成功添加到配置",
            "article": article_info,
        }
    except Exception as e:
        logger.error(f"添加文章失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加文章失败: {str(e)}")


@router.get("/candidates")
async def list_candidate_articles(admin: None = Depends(_require_admin)):
    """获取所有待审核的文章列表，并按关键词分组"""
    candidates = load_candidate_pool()
    logger.info(f"Endpoint /candidates: Found {len(candidates)} candidates in the pool.")

    # 检查归档状态
    from ...services.data_loader import DataLoader
    
    grouped_candidates = {}
    for candidate in candidates:
        # crawled_from format is "sogou_wechat:KEYWORD"
        try:
            source_parts = candidate.crawled_from.split(":", 1)
            keyword = source_parts[1] if len(source_parts) > 1 else "未知来源"
        except AttributeError:
            keyword = "未知来源"

        if keyword not in grouped_candidates:
            grouped_candidates[keyword] = []
        
        # 检查是否已归档
        candidate_dict = asdict(candidate)
        candidate_dict["is_archived"] = DataLoader.is_article_archived(candidate.url)
        grouped_candidates[keyword].append(candidate_dict)

    return {"ok": True, "grouped_candidates": grouped_candidates}


@router.post("/accept-candidate")
async def accept_candidate(request: CandidateActionRequest, admin: None = Depends(_require_admin)):
    """
    采纳一篇文章，从候选池移动到正式文章池
    
    重要说明：
    1. 工具关键字爬取的资讯（crawled_from 以 "tool_keyword:" 开头）：
       - 采纳后自动归档到"编程资讯"（programming.json）
       - 不会进入推送列表，不能用于定时推送
       - 只能手动触发爬取，不能定时自动爬取
    
    2. 推送定时爬取的资讯（crawled_from 以 "sogou_wechat:" 开头）：
       - 采纳后添加到推送列表（ai_articles.json），用于定时推送
       - 不会自动归档到资讯模块
       - 可以通过 archive-candidate API 手动归档到"AI资讯"或"编程资讯"
    """
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")

    candidates = load_candidate_pool()
    
    article_to_accept = None
    remaining_candidates = []
    is_tool_related = False
    candidate_to_accept = None
    
    for candidate in candidates:
        if candidate.url == url:
            candidate_to_accept = candidate
            # 自动从 crawled_from 中提取工具名称（如果是工具相关资讯）
            tool_tags = []
            if candidate.crawled_from and candidate.crawled_from.startswith("tool_keyword:"):
                is_tool_related = True
                tool_name = candidate.crawled_from.replace("tool_keyword:", "").strip()
                if tool_name:
                    tool_tags.append(tool_name)
            
            article_to_accept = {
                "title": candidate.title,
                "url": candidate.url,
                "source": "100kwhy",  # 爬取的资讯统一使用"100kwhy"作为来源
                "summary": candidate.summary or "",
                "tool_tags": tool_tags,  # 添加工具标签，用于工具详情页关联
            }
        else:
            remaining_candidates.append(candidate)

    if not article_to_accept:
        raise HTTPException(status_code=404, detail="在候选池中未找到该文章")

    # 1. 从候选池中移除
    save_candidate_pool(remaining_candidates)
    
    # 2. 根据资讯来源类型进行不同处理
    from ...services.data_loader import DataLoader
    
    if is_tool_related:
        # 工具关键字爬取的资讯：归档到编程资讯（programming.json）
        # 注意：工具关键字资讯只能手动触发爬取，采纳后只归档到编程资讯，不进入推送列表
        # category="programming" -> 文件: programming.json -> UI显示: "编程资讯"
        success = DataLoader.archive_article_to_category(
            article_to_accept, 
            category="programming",  # Category值，对应文件: programming.json
            tool_tags=article_to_accept.get("tool_tags", [])
        )
        if not success:
            # 如果归档失败，恢复候选池
            remaining_candidates.append(candidate_to_accept)
            save_candidate_pool(candidates)
            raise HTTPException(status_code=500, detail="归档文章失败")
        
        # 更新周报
        update_weekly_digest()
        
        return {"ok": True, "message": "文章已成功归档到编程资讯。"}
    else:
        # 推送定时爬取的资讯：添加到推送列表（ai_articles.json）
        # 注意：推送定时爬取的资讯采纳后只进入推送列表，不自动归档
        # 如需归档到资讯模块，请使用 archive-candidate API
        success = save_article_to_config(article_to_accept)
        if not success:
            # 如果添加失败（比如已存在），也算操作成功，只是不做添加
            logger.warning(f"Article already exists in main pool, but accepting from candidate: {url}")
            return {"ok": True, "message": "文章已存在于正式池中，已从候选池移除。"}
        return {"ok": True, "message": "文章已成功采纳到正式池。"}


@router.post("/reject-candidate")
async def reject_candidate(request: CandidateActionRequest, admin: None = Depends(_require_admin)):
    """忽略一篇文章，从候选池中删除"""
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")

    candidates = load_candidate_pool()
    
    original_count = len(candidates)
    remaining_candidates = [c for c in candidates if c.url != url]

    if len(remaining_candidates) == original_count:
        raise HTTPException(status_code=404, detail="在候选池中未找到该文章")

    save_candidate_pool(remaining_candidates)
    
    return {"ok": True, "message": "文章已成功从候选池中忽略。"}


@router.post("/archive-candidate")
async def archive_candidate(request: ArchiveArticleRequest, admin: None = Depends(_require_admin)):
    """
    归档一篇文章到指定分类的JSON文件（归档后文章仍保留在候选池中）
    
    重要说明：
    - 此接口主要用于归档推送定时爬取的资讯
    - 工具关键字爬取的资讯采纳时会自动归档，通常不需要使用此接口
    - 归档后文章仍保留在候选池中，可以继续采纳用于推送
    - 支持归档到"AI资讯"（ai_news.json）或"编程资讯"（programming.json）
    """
    url = request.url.strip()
    category = request.category.strip()
    tool_tags = request.tool_tags or []
    
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")
    
    if not category:
        raise HTTPException(status_code=400, detail="分类不能为空")
    
    # 验证分类是否有效
    # 
    # 分类映射关系：
    # - "programming" -> 文件: programming.json -> UI显示: "编程资讯"
    # - "ai_news" -> 文件: ai_news.json -> UI显示: "AI资讯"
    valid_categories = ["programming", "ai_news"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"无效的分类，支持的分类：{', '.join(valid_categories)}")
    
    candidates = load_candidate_pool()
    
    # 查找要归档的文章（不删除，保留在候选池中）
    article_to_archive = None
    for candidate in candidates:
        if candidate.url == url:
            # 自动从 crawled_from 中提取工具名称（如果是工具相关资讯）
            auto_tool_tags = []
            if candidate.crawled_from and candidate.crawled_from.startswith("tool_keyword:"):
                tool_name = candidate.crawled_from.replace("tool_keyword:", "").strip()
                if tool_name:
                    auto_tool_tags.append(tool_name)
            
            # 合并手动输入的工具标签和自动提取的标签
            final_tool_tags = list(set(tool_tags + auto_tool_tags))
            
            # 转换为文章格式
            # 如果是爬取的资讯（有crawled_from字段），统一使用"100kwhy"作为来源
            source = "100kwhy" if candidate.crawled_from else (candidate.source or "")
            
            article_to_archive = {
                "title": candidate.title,
                "url": candidate.url,
                "source": source,
                "summary": candidate.summary or "",
                "tags": final_tool_tags,  # 使用工具标签
                "tool_tags": final_tool_tags,  # 单独存储工具标签，方便查询
                "score": getattr(candidate, 'score', 8.0)
            }
            break
    
    if not article_to_archive:
        raise HTTPException(status_code=404, detail="在候选池中未找到该文章")
    
    # 使用DataLoader归档文章
    from ...services.data_loader import DataLoader
    success = DataLoader.archive_article_to_category(article_to_archive, category, tool_tags)
    
    if not success:
        raise HTTPException(status_code=500, detail="归档失败，请查看服务器日志")
    
    # 更新周报
    update_weekly_digest()
    
    # 注意：归档后不删除候选池中的文章，保留以便后续采纳
    
    return {"ok": True, "message": f"文章已成功归档到 {category} 分类。文章仍保留在候选池中，可继续采纳。"}


# ========== 工具候选池相关API ==========

@router.get("/tool-candidates")
async def list_candidate_tools(admin: None = Depends(_require_admin)):
    """获取所有待审核的工具列表"""
    try:
        candidates = load_tool_candidate_pool()
        logger.info(f"Endpoint /tool-candidates: Found {len(candidates)} tool candidates in the pool.")
        
        return {
            "ok": True,
            "candidates": [asdict(c) for c in candidates]
        }
    except Exception as e:
        logger.error(f"获取工具候选池失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工具候选池失败: {str(e)}")


@router.post("/accept-tool-candidate")
async def accept_tool_candidate(request: dict, admin: None = Depends(_require_admin)):
    """采纳一个工具，从候选池移动到正式工具池"""
    url = request.get("url", "").strip()
    category = request.get("category", "other").strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")
    
    try:
        candidates = load_tool_candidate_pool()
        
        tool_to_accept = None
        remaining_candidates = []
        for candidate in candidates:
            if candidate.url == url:
                tool_to_accept = candidate
            else:
                remaining_candidates.append(candidate)
        
        if not tool_to_accept:
            raise HTTPException(status_code=404, detail="在工具候选池中未找到该工具")
        
        # 1. 从候选池中移除
        save_tool_candidate_pool(remaining_candidates)
        
        # 2. 添加到正式工具池
        from ...services.data_loader import DataLoader
        from datetime import datetime
        
        # 生成工具ID（使用时间戳）
        tool_id = int(datetime.now().timestamp() * 1000) % 1000000
        
        tool_data = {
            "id": tool_id,
            "name": tool_to_accept.name,
            "url": tool_to_accept.url,
            "description": tool_to_accept.description,
            "category": category or tool_to_accept.category,
            "tags": tool_to_accept.tags or [],
            "icon": tool_to_accept.icon or "</>",
            "score": 0,
            "view_count": 0,
            "like_count": 0,
            "is_featured": False,
            "created_at": tool_to_accept.submitted_at or datetime.now().isoformat() + "Z"
        }
        
        # 保存到对应的分类文件
        success = DataLoader.archive_tool_to_category(tool_data, category or tool_to_accept.category)
        
        if not success:
            # 如果保存失败，恢复候选池
            remaining_candidates.append(tool_to_accept)
            save_tool_candidate_pool(remaining_candidates)
            raise HTTPException(status_code=500, detail="保存工具失败")
        
        # 3. 自动添加工具名称到关键字配置
        tool_name = tool_to_accept.name.strip()
        if tool_name:
            add_tool_keyword(tool_name)
            logger.info(f"已添加工具名称 '{tool_name}' 到关键字配置")
        
        return {"ok": True, "message": f"工具已成功采纳到 {category or tool_to_accept.category} 分类。"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"采纳工具失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"采纳工具失败: {str(e)}")


@router.post("/reject-tool-candidate")
async def reject_tool_candidate(request: dict, admin: None = Depends(_require_admin)):
    """忽略一个工具，从候选池中删除"""
    url = request.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")
    
    try:
        candidates = load_tool_candidate_pool()
        remaining_candidates = [c for c in candidates if c.url != url]
        
        if len(remaining_candidates) == len(candidates):
            raise HTTPException(status_code=404, detail="在工具候选池中未找到该工具")
        
        save_tool_candidate_pool(remaining_candidates)
        return {"ok": True, "message": "工具已从候选池中移除。"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"忽略工具失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"忽略工具失败: {str(e)}")


class CrawlToolsRequest(BaseModel):
    """工具爬取请求"""
    source_url: str  # 爬取源URL（API端点，如 http://example.com/api/tools）
    category: Optional[str] = None  # 指定分类，不传则爬取所有分类
    max_items: Optional[int] = 100  # 最多爬取数量


@router.post("/crawl-tools")
async def crawl_tools(request: CrawlToolsRequest, admin: None = Depends(_require_admin)):
    """
    差量爬取工具：只爬取本地没有的工具，添加到候选池
    
    Args:
        request: 爬取请求，包含分类和最大数量
    """
    try:
        from ...services.data_loader import DataLoader
        
        # 获取所有已存在的工具URL（包括正式工具库和候选池）
        # 使用规范化后的URL进行对比，避免因URL格式差异导致的重复
        def normalize_url(url: str) -> str:
            """规范化URL：统一小写、去除尾随斜杠、统一协议"""
            if not url:
                return ""
            url = url.strip().lower()
            # 统一协议（http和https视为相同，统一为https）
            if url.startswith("http://"):
                url = "https://" + url[7:]
            elif not url.startswith("http"):
                # 如果没有协议，添加https://
                url = "https://" + url
            # 去除尾随斜杠（但保留协议后的双斜杠）
            # 例如：https://example.com/ -> https://example.com
            #      https://example.com/path/ -> https://example.com/path
            if url.endswith("/"):
                # 去除尾随斜杠，但保留协议后的双斜杠
                url = url.rstrip("/")
            return url
        
        existing_urls = set()
        
        # 1. 从正式工具库获取所有URL（直接读取文件，避免分页和去重问题）
        from pathlib import Path
        tools_dir = Path(__file__).resolve().parent.parent.parent / "data" / "tools"
        tool_count = 0
        for tool_file in tools_dir.glob("*.json"):
            if tool_file.name == "tool_candidates.json":
                continue
            tools = DataLoader._load_json_file(tool_file)
            tool_count += len(tools)
            for tool in tools:
                url = tool.get("url", "").strip()
                if url:
                    normalized = normalize_url(url)
                    if normalized:
                        existing_urls.add(normalized)
        
        logger.info(f"正式工具库: {tool_count} 个工具，{len(existing_urls)} 个唯一URL")
        
        # 2. 从候选池获取所有URL
        existing_candidates = load_tool_candidate_pool()
        candidate_url_count = 0
        for candidate in existing_candidates:
            url = candidate.url.strip()
            if url:
                normalized = normalize_url(url)
                if normalized:
                    existing_urls.add(normalized)
                    candidate_url_count += 1
        
        logger.info(f"候选池: {len(existing_candidates)} 个工具，{candidate_url_count} 个URL")
        logger.info(f"总计已存在工具URL数量（已规范化）: {len(existing_urls)}")
        
        # 3. 爬取工具
        source_url = request.source_url.strip()
        if not source_url:
            raise HTTPException(status_code=400, detail="爬取源URL不能为空")
        
        # 验证URL格式
        if not source_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="URL格式不正确，必须以 http:// 或 https:// 开头")
        
        category = request.category if request.category else None
        max_items = request.max_items if request.max_items else 100
        
        logger.info(f"开始爬取工具: source_url={source_url}, category={category}, max_items={max_items}")
        
        # 从自定义URL爬取工具
        # 如果用户输入的是完整API URL，直接使用；否则拼接 /api/tools
        if "/api/" in source_url or source_url.endswith("/tools"):
            api_url = source_url
        else:
            # 如果只是基础URL，拼接 /api/tools
            api_url = f"{source_url.rstrip('/')}/api/tools"
        
        crawled_tools = await fetch_tools_from_api(api_url=api_url)
        
        # 如果指定了分类，进行筛选
        if category:
            crawled_tools = [t for t in crawled_tools if t.get("category") == category]
        
        # 限制数量
        if max_items:
            crawled_tools = crawled_tools[:max_items * 2]  # 多爬取一些，因为会有重复
        
        logger.info(f"爬取到 {len(crawled_tools)} 个工具")
        
        # 4. 筛选新工具（差量）- 使用规范化URL对比
        new_tools = []
        for tool in crawled_tools:
            tool_url = tool.get("url", "").strip()
            if not tool_url:
                continue
            
            # 规范化URL后对比
            normalized_url = normalize_url(tool_url)
            if normalized_url and normalized_url not in existing_urls:
                new_tools.append(tool)
                existing_urls.add(normalized_url)  # 避免同一批次重复
            else:
                logger.debug(f"跳过已存在的工具: {tool_url} (规范化后: {normalized_url})")
        
        duplicate_count = len(crawled_tools) - len(new_tools)
        logger.info(f"爬取结果: 共 {len(crawled_tools)} 个工具，其中 {duplicate_count} 个已存在，发现 {len(new_tools)} 个新工具")
        
        # 5. 转换为候选工具并添加到候选池
        from datetime import datetime
        current_candidates = load_tool_candidate_pool()
        added_count = 0
        skipped_count = 0
        
        for tool in new_tools:
            tool_url = tool.get("url", "").strip()
            normalized_url = normalize_url(tool_url)
            
            # 再次检查候选池（使用规范化URL）
            if any(normalize_url(c.url) == normalized_url for c in current_candidates):
                skipped_count += 1
                logger.debug(f"工具已在候选池中，跳过: {tool_url}")
                continue
            
            # 创建候选工具
            candidate = CandidateTool(
                name=tool.get("name", ""),
                url=tool_url,
                description=tool.get("description", ""),
                category=tool.get("category", "other"),
                tags=tool.get("tags", []) or [],
                icon=tool.get("icon", "🔧"),
                submitted_by="系统爬取",
                submitted_at=datetime.now().isoformat() + "Z"
            )
            current_candidates.append(candidate)
            added_count += 1
        
        # 6. 保存候选池
        if added_count > 0:
            save_tool_candidate_pool(current_candidates)
        
        return {
            "ok": True,
            "message": f"爬取完成：发现 {len(new_tools)} 个新工具，添加 {added_count} 个到候选池，跳过 {skipped_count} 个重复项",
            "crawled_count": len(crawled_tools),
            "new_count": len(new_tools),
            "added_count": added_count,
            "skipped_count": skipped_count
        }
    except Exception as e:
        logger.error(f"爬取工具失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"爬取工具失败: {str(e)}")


@router.post("/crawl-tool-articles")
async def crawl_tool_articles(request: dict, admin: None = Depends(_require_admin)):
    """
    手动触发工具相关资讯爬取
    
    重要说明：
    - 此接口只能手动触发，不能定时自动执行
    - 爬取的资讯会设置 crawled_from="tool_keyword:工具名称"
    - 采纳后会自动归档到"编程资讯"（programming.json），不会进入推送列表
    - 用于在工具详情页展示相关资讯
    
    Args:
        request: 包含 keyword 的请求体，如果未提供则爬取所有工具关键字
    
    Returns:
        爬取结果
    """
    keyword = request.get("keyword", "").strip()
    
    # 1. 读取工具关键字
    if keyword:
        keywords = [keyword]
    else:
        keywords = load_tool_keywords()
        if not keywords:
            raise HTTPException(status_code=400, detail="没有可用的工具关键字，请先添加工具")
    
    # 2. 获取所有已存在的 URL 用于去重
    existing_urls = set()
    # 来自正式文章池
    main_pool_articles = get_all_articles()
    for article in main_pool_articles:
        if article.get("url"):
            existing_urls.add(article["url"])
    # 来自现有候选池
    candidate_pool_articles = load_candidate_pool()
    for article in candidate_pool_articles:
        if article.url:
            existing_urls.add(article.url)
    
    logger.info(f"Found {len(existing_urls)} existing URLs to skip.")
    
    # 3. 遍历关键字并抓取（每个关键字只抓取1篇）
    all_new_candidates = []
    for kw in keywords:
        try:
            logger.info(f"Crawling tool keyword '{kw}' for 1 article...")
            found_candidates = await search_articles_by_keyword(kw, pages=1)
            
            # 只取第一篇
            if found_candidates:
                candidate = found_candidates[0]
                # 添加工具名称标签（格式：tool_keyword:工具名称）
                # 这样在归档时可以自动提取工具名称作为 tool_tags
                candidate.crawled_from = f"tool_keyword:{kw}"
                all_new_candidates.append(candidate)
                logger.info(f"Found article for keyword '{kw}': {candidate.title[:50]}")
        except Exception as e:
            logger.error(f"Error crawling for tool keyword '{kw}': {e}")
            # 单个关键字失败不中断整个任务
            continue
    
    # 4. 添加到候选池并去重
    if not all_new_candidates:
        return {"ok": True, "message": "抓取完成，但未发现任何新文章。", "added_count": 0}
    
    added_count = add_candidates_to_pool(all_new_candidates, existing_urls)
    
    return {
        "ok": True, 
        "message": f"抓取完成！共发现 {len(all_new_candidates)} 篇文章，成功添加 {added_count} 篇新文章到候选池。",
        "added_count": added_count,
        "keywords_processed": len(keywords)
    }


@router.get("/tool-keywords")
async def list_tool_keywords(admin: None = Depends(_require_admin)):
    """获取所有工具关键字列表"""
    keywords = load_tool_keywords()
    return {"ok": True, "keywords": keywords, "count": len(keywords)}


@router.post("/crawl-articles")
async def crawl_articles(admin: None = Depends(_require_admin)):
    """
    触发一次文章抓取任务（用于定时推送）。

    重要说明：
    - 此接口用于定时自动爬取，从 `config/crawler_keywords.json` 读取关键词
    - 爬取的资讯会设置 crawled_from="sogou_wechat:关键词"
    - 采纳后会添加到推送列表（ai_articles.json），用于定时推送
    - 不会自动归档到资讯模块，如需归档请使用 archive-candidate API
    - 归档时可以选择归档到"AI资讯"或"编程资讯"

    - 从 `config/crawler_keywords.json` 读取关键词。
    - 使用搜狗微信搜索爬虫抓取文章。
    - 对比现有文章池和候选池，进行去重。
    - 将新文章存入候选池 `data/articles/ai_candidates.json`。
    """
    # 1. 读取关键词
    keywords_path = Path(__file__).resolve().parents[2] / "config" / "crawler_keywords.json"
    if not keywords_path.exists():
        raise HTTPException(status_code=404, detail="关键词配置文件 crawler_keywords.json 未找到")
    
    try:
        with keywords_path.open("r", encoding="utf-8") as f:
            keywords = json.load(f)
        if not isinstance(keywords, list) or not keywords:
            raise HTTPException(status_code=400, detail="关键词配置格式错误或为空")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取关键词配置失败: {e}")

    # 2. 获取所有已存在的 URL 用于去重
    existing_urls = set()
    # 来自正式文章池
    main_pool_articles = get_all_articles()
    for article in main_pool_articles:
        if article.get("url"):
            existing_urls.add(article["url"])
    # 来自现有候选池
    candidate_pool_articles = load_candidate_pool()
    for article in candidate_pool_articles:
        if article.url:
            existing_urls.add(article.url)

    # 自动获取前清空候选池，避免旧数据混入
    if candidate_pool_articles:
        logger.info("Clearing candidate pool before crawling new articles.")
        clear_candidate_pool()
            
    logger.info(f"Found {len(existing_urls)} existing URLs to skip.")

    schedule = load_digest_schedule()
    max_articles = max(1, schedule.max_articles_per_keyword)
    max_pages = max(1, math.ceil(max_articles / 10))

    # 3. 遍历关键词并抓取
    all_new_candidates = []
    for keyword in keywords:
        try:
            logger.info(
                f"Crawling keyword '{keyword}' for up to {max_articles} articles "
                f"({max_pages} page(s))."
            )
            found_candidates = await search_articles_by_keyword(keyword, pages=max_pages)
            if len(found_candidates) > max_articles:
                found_candidates = found_candidates[:max_articles]
            all_new_candidates.extend(found_candidates)
        except Exception as e:
            logger.error(f"Error crawling for keyword '{keyword}': {e}")
            # 单个关键词失败不中断整个任务
            continue
            
    # 4. 添加到候选池并去重
    if not all_new_candidates:
        return {"ok": True, "message": "抓取完成，但未发现任何新文章。"}

    added_count = add_candidates_to_pool(all_new_candidates, existing_urls)
    
    return {
        "ok": True, 
        "message": f"抓取完成！共发现 {len(all_new_candidates)} 篇文章，成功添加 {added_count} 篇新文章到候选池。",
        "added_count": added_count
    }


@router.post("/delete-article")
async def delete_article(request: DeleteArticleRequest, admin: None = Depends(_require_admin)):
    """
    从所有相关数据源删除指定URL的文章，包括：
    - 文章池 (ai_articles.json)
    - 归档分类文件 (ai_news.json, programming.json, ai_coding.json)
    - 周报文件
    删除后自动更新周报。
    
    Args:
        request: 包含文章URL的请求体
        
    Returns:
        dict: 包含成功状态和删除详情的响应
    """
    from ...services.data_loader import DataLoader
    
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")
    
    try:
        deletion_results = {
            "from_pool": False,
            "from_categories": {},
            "from_weekly": False,
        }
        
        # 1. 从文章池删除
        success = delete_article_from_config(url)
        deletion_results["from_pool"] = success
        
        # 2. 从所有归档分类文件中删除
        category_results = DataLoader.delete_article_from_all_categories(url)
        deletion_results["from_categories"] = category_results
        
        # 3. 从周报中删除
        from ...services.weekly_digest import delete_article_from_weekly
        weekly_success = delete_article_from_weekly(url)
        deletion_results["from_weekly"] = weekly_success
        
        # 4. 更新周报（重新生成）
        update_weekly_digest()
        
        # 检查是否有任何删除成功
        any_success = (
            success or 
            any(category_results.values()) or 
            weekly_success
        )
        
        if not any_success:
            return {
                "ok": False,
                "message": "文章不存在或删除失败",
                "details": deletion_results,
            }
        
        # 生成成功消息
        messages = []
        if success:
            messages.append("文章池")
        deleted_categories = [cat for cat, result in category_results.items() if result]
        if deleted_categories:
            messages.append(f"归档分类 ({', '.join(deleted_categories)})")
        if weekly_success:
            messages.append("周报")
        
        message = f"文章已成功删除（{', '.join(messages)}）"
        
        return {
            "ok": True,
            "message": message,
            "details": deletion_results,
        }
    except Exception as e:
        logger.error(f"删除文章失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除文章失败: {str(e)}")


@router.post("/archive-article")
async def archive_article_from_pool(request: ArchiveArticleFromPoolRequest, admin: None = Depends(_require_admin)):
    """
    从文章池归档一篇文章到指定分类的JSON文件
    
    重要说明：
    - 此接口用于从文章池（ai_articles.json）归档文章到资讯列表
    - 支持归档到"AI资讯"（ai_news.json）或"编程资讯"（programming.json）
    - 归档后文章仍保留在文章池中，可以继续用于推送
    - 如果文章已归档，会返回错误
    """
    url = request.url.strip()
    category = request.category.strip()
    tool_tags = request.tool_tags or []
    
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")
    
    if not category:
        raise HTTPException(status_code=400, detail="分类不能为空")
    
    # 验证分类是否有效
    valid_categories = ["programming", "ai_news"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"无效的分类，支持的分类：{', '.join(valid_categories)}")
    
    # 检查文章是否已归档
    from ...services.data_loader import DataLoader
    if DataLoader.is_article_archived(url):
        raise HTTPException(status_code=400, detail="文章已归档，无法重复归档")
    
    # 从文章池中查找文章
    articles = get_all_articles()
    article_to_archive = None
    
    for article in articles:
        article_url = article.url if hasattr(article, 'url') else article.get("url", "")
        if article_url.strip() == url:
            # 转换为归档格式
            article_to_archive = {
                "title": article.title if hasattr(article, 'title') else article.get("title", ""),
                "url": article_url,
                "source": article.source if hasattr(article, 'source') else article.get("source", "100kwhy"),
                "summary": article.summary if hasattr(article, 'summary') else article.get("summary", ""),
                "tags": tool_tags,
                "tool_tags": tool_tags,
                "score": 8.0  # 默认评分
            }
            break
    
    if not article_to_archive:
        raise HTTPException(status_code=404, detail="在文章池中未找到该文章")
    
    # 使用DataLoader归档文章
    success = DataLoader.archive_article_to_category(article_to_archive, category, tool_tags)
    
    if not success:
        raise HTTPException(status_code=500, detail="归档失败，请查看服务器日志")
    
    # 更新周报
    update_weekly_digest()
    
    return {"ok": True, "message": f"文章已成功归档到 {category} 分类。文章仍保留在文章池中，可继续用于推送。"}


@router.get("/config/keywords")
async def get_keywords_config(admin: None = Depends(_require_admin)):
    """获取关键词配置"""
    keywords = load_crawler_keywords()
    return {"ok": True, "keywords": keywords}


@router.post("/config/keywords")
async def update_keywords_config(request: KeywordsConfigRequest, admin: None = Depends(_require_admin)):
    """更新关键词配置"""
    keywords = [k.strip() for k in request.keywords if k.strip()]
    if not keywords:
        raise HTTPException(status_code=400, detail="关键词列表不能为空")
    
    if not save_crawler_keywords(keywords):
        raise HTTPException(status_code=500, detail="保存关键词配置失败")
    
    return {"ok": True, "keywords": keywords}


@router.get("/config/schedule")
async def get_schedule_config(admin: None = Depends(_require_admin)):
    """获取调度配置"""
    schedule = load_digest_schedule()
    return {"ok": True, "schedule": asdict(schedule)}


@router.post("/config/schedule")
async def update_schedule_config(request: ScheduleConfigRequest, admin: None = Depends(_require_admin)):
    """更新调度配置"""
    payload = request.dict(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="请提供至少一项调度配置")
    
    if not save_digest_schedule(payload):
        raise HTTPException(status_code=500, detail="保存调度配置失败")
    
    schedule = load_digest_schedule()
    return {"ok": True, "schedule": asdict(schedule)}


@router.get("/config/wecom-template")
async def get_wecom_template_config(admin: None = Depends(_require_admin)):
    """获取企业微信模板配置"""
    template = load_wecom_template()
    return {"ok": True, "template": template}


@router.post("/config/wecom-template")
async def update_wecom_template_config(request: WecomTemplateRequest, admin: None = Depends(_require_admin)):
    """更新企业微信模板配置"""
    if not request.template:
        raise HTTPException(status_code=400, detail="模板不能是空对象")
    
    if not save_wecom_template(request.template):
        raise HTTPException(status_code=500, detail="保存企业微信模板失败")
    
    template = load_wecom_template()
    return {"ok": True, "template": template}


@router.get("/config/env")
async def get_env_config(admin: None = Depends(_require_admin)):
    """获取环境变量配置"""
    admin_code = load_env_var("AICODING_ADMIN_CODE")
    wecom_webhook = load_env_var("WECOM_WEBHOOK")
    return {
        "ok": True,
        "env": {
            "admin_code": admin_code,
            "wecom_webhook": wecom_webhook,
        }
    }


@router.post("/config/env")
async def update_env_config(request: dict, admin: None = Depends(_require_admin)):
    """更新环境变量配置"""
    admin_code = request.get("admin_code", "").strip()
    wecom_webhook = request.get("wecom_webhook", "").strip()
    
    if admin_code:
        if not save_env_var("AICODING_ADMIN_CODE", admin_code):
            raise HTTPException(status_code=500, detail="保存管理员验证码失败")
    
    if wecom_webhook:
        if not save_env_var("WECOM_WEBHOOK", wecom_webhook):
            raise HTTPException(status_code=500, detail="保存企业微信推送地址失败")
    
    return {
        "ok": True,
        "env": {
            "admin_code": load_env_var("AICODING_ADMIN_CODE"),
            "wecom_webhook": load_env_var("WECOM_WEBHOOK"),
        }
    }


@router.post("/test/rss")
async def test_rss_source(request: dict, admin: None = Depends(_require_admin)):
    """测试 RSS Feed 抓取"""
    feed_url = request.get("feed_url", "").strip()
    if not feed_url:
        raise HTTPException(status_code=400, detail="请提供 RSS Feed URL")
    
    try:
        articles = await fetch_rss_articles(feed_url, max_items=5)
        return {
            "ok": True,
            "count": len(articles),
            "articles": articles
        }
    except Exception as e:
        logger.error(f"测试 RSS Feed 失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.post("/test/github-trending")
async def test_github_trending_source(request: dict, admin: None = Depends(_require_admin)):
    """测试 GitHub Trending 抓取"""
    language = request.get("language", "python").strip()
    
    try:
        articles = await fetch_github_trending(language, max_items=5)
        return {
            "ok": True,
            "count": len(articles),
            "articles": articles
        }
    except Exception as e:
        logger.error(f"测试 GitHub Trending 失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.post("/test/hackernews")
async def test_hackernews_source(request: dict, admin: None = Depends(_require_admin)):
    """测试 Hacker News 抓取"""
    min_points = request.get("min_points", 50)
    
    try:
        articles = await fetch_hackernews_articles(min_points=min_points, max_items=5)
        return {
            "ok": True,
            "count": len(articles),
            "articles": articles
        }
    except Exception as e:
        logger.error(f"测试 Hacker News 失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.post("/test/all-sources")
async def test_all_sources(request: dict, admin: None = Depends(_require_admin)):
    """测试所有资讯源"""
    keywords = request.get("keywords", [])
    rss_feeds = request.get("rss_feeds", [])
    github_languages = request.get("github_languages", [])
    hackernews_min_points = request.get("hackernews_min_points", 50)
    max_per_source = request.get("max_per_source", 3)
    
    try:
        articles = await fetch_from_all_sources(
            keywords=keywords,
            rss_feeds=rss_feeds,
            github_languages=github_languages,
            hackernews_min_points=hackernews_min_points,
            max_per_source=max_per_source,
        )
        return {
            "ok": True,
            "count": len(articles),
            "articles": articles[:20]  # 只返回前20条
        }
    except Exception as e:
        logger.error(f"测试所有资讯源失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


# ========== 微信公众号功能已暂时屏蔽 ==========
# @router.post("/wechat-mp/create-draft")
async def create_wechat_mp_draft_disabled(request: dict, admin: None = Depends(_require_admin)):
    """创建微信公众号草稿（已禁用）"""
    articles = request.get("articles", [])
    if not articles:
        raise HTTPException(status_code=400, detail="请提供文章列表")
    
    try:
        client = WeChatMPClient()
        media_id = await client.create_draft(articles)
        
        if media_id:
            return {
                "ok": True,
                "media_id": media_id,
                "message": "草稿创建成功"
            }
        else:
            raise HTTPException(status_code=500, detail="创建草稿失败，请检查配置和日志")
    except Exception as e:
        logger.error(f"创建微信公众号草稿失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建草稿失败: {str(e)}")


# @router.post("/wechat-mp/publish")
async def publish_wechat_mp_disabled(request: dict, admin: None = Depends(_require_admin)):
    """发布微信公众号草稿"""
    media_id = request.get("media_id", "").strip()
    if not media_id:
        raise HTTPException(status_code=400, detail="请提供 media_id")
    
    try:
        client = WeChatMPClient()
        success = await client.publish(media_id)
        
        if success:
            return {
                "ok": True,
                "message": "发布成功"
            }
        else:
            raise HTTPException(status_code=500, detail="发布失败，请检查配置和日志")
    except Exception as e:
        logger.error(f"发布微信公众号失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


# @router.post("/wechat-mp/publish-digest")
async def publish_digest_to_wechat_mp_disabled(admin: None = Depends(_require_admin)):
    """将当前日报发布到微信公众号"""
    try:
        # 获取当前文章列表
        articles_data = get_all_articles()
        if not articles_data or not articles_data.get("articles"):
            raise HTTPException(status_code=400, detail="当前没有可发布的文章")
        
        # 构建微信公众号文章格式
        wechat_articles = []
        for article in articles_data["articles"][:8]:  # 最多8篇
            wechat_articles.append({
                "title": article.get("title", "无标题"),
                "author": article.get("source", "未知"),
                "digest": article.get("summary", "")[:120],  # 摘要限制120字
                "content": f"<p>{article.get('summary', '')}</p><p><a href='{article.get('url', '')}'>阅读原文</a></p>",
                "content_source_url": article.get("url", ""),
                "thumb_media_id": "",  # 需要先上传封面图
                "show_cover_pic": 1,
            })
        
        if not wechat_articles:
            raise HTTPException(status_code=400, detail="没有可发布的文章")
        
        # 创建草稿
        client = WeChatMPClient()
        media_id = await client.create_draft(wechat_articles)
        
        if not media_id:
            raise HTTPException(status_code=500, detail="创建草稿失败")
        
        # 发布草稿
        success = await client.publish(media_id)
        
        if success:
            return {
                "ok": True,
                "media_id": media_id,
                "message": "已成功发布到微信公众号"
            }
        else:
            return {
                "ok": False,
                "media_id": media_id,
                "message": "草稿已创建，但发布失败，请手动发布"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发布日报到微信公众号失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


# @router.get("/wechat-mp/drafts")
async def get_wechat_mp_drafts_disabled(offset: int = 0, count: int = 20, admin: None = Depends(_require_admin)):
    """获取微信公众号草稿箱列表"""
    try:
        client = WeChatMPClient()
        result = await client.get_draft_list(offset=offset, count=count)
        
        if result:
            return {
                "ok": True,
                "total_count": result.get("total_count", 0),
                "item_count": result.get("item_count", 0),
                "drafts": result.get("item", [])
            }
        else:
            raise HTTPException(status_code=500, detail="获取草稿列表失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取草稿列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取草稿列表失败: {str(e)}")


# @router.get("/wechat-mp/draft/{media_id}")
async def get_wechat_mp_draft_disabled(media_id: str, admin: None = Depends(_require_admin)):
    """获取微信公众号草稿详情"""
    try:
        client = WeChatMPClient()
        result = await client.get_draft(media_id)
        
        if result:
            return {
                "ok": True,
                "draft": result
            }
        else:
            raise HTTPException(status_code=500, detail="获取草稿详情失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取草稿详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取草稿详情失败: {str(e)}")


# @router.post("/wechat-mp/draft/{media_id}/update")
async def update_wechat_mp_draft_disabled(media_id: str, request: dict, admin: None = Depends(_require_admin)):
    """更新微信公众号草稿"""
    index = request.get("index", 0)
    article = request.get("article")
    
    if not article:
        raise HTTPException(status_code=400, detail="请提供文章数据")
    
    try:
        client = WeChatMPClient()
        success = await client.update_draft(media_id, index, article)
        
        if success:
            return {
                "ok": True,
                "message": "草稿更新成功"
            }
        else:
            raise HTTPException(status_code=500, detail="更新草稿失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新草稿失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新草稿失败: {str(e)}")


# @router.post("/wechat-mp/draft/{media_id}/delete")
async def delete_wechat_mp_draft_disabled(media_id: str, admin: None = Depends(_require_admin)):
    """删除微信公众号草稿"""
    try:
        client = WeChatMPClient()
        success = await client.delete_draft(media_id)
        
        if success:
            return {
                "ok": True,
                "message": "草稿删除成功"
            }
        else:
            raise HTTPException(status_code=500, detail="删除草稿失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除草稿失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除草稿失败: {str(e)}")


def decode_unicode_escapes(text: str) -> str:
    """
    解码字符串中的 Unicode 转义序列（如 \u5728 -> 在）
    
    Args:
        text: 可能包含 Unicode 转义序列的字符串
        
    Returns:
        str: 解码后的字符串
    """
    try:
        import codecs
        # 使用 codecs 解码 Unicode 转义序列
        # 需要先编码为 latin-1，然后解码为 unicode_escape
        return codecs.decode(text.encode('latin-1'), 'unicode_escape')
    except Exception:
        try:
            # 如果上面的方法失败，使用正则表达式逐个替换
            def replace_unicode(match):
                code_point = int(match.group(1), 16)
                return chr(code_point)
            
            # 匹配 \uXXXX 格式（4位十六进制）
            return re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
        except Exception:
            # 如果解码失败，返回原字符串
            return text


async def fetch_article_content_html(url: str) -> str:
    """
    从 URL 抓取文章的完整 HTML 内容
    
    Args:
        url: 文章 URL
        
    Returns:
        str: 清理后的 HTML 内容（适合微信公众号格式）
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            # 确保正确解码响应内容，使用 UTF-8 编码
            # 如果响应头没有指定编码，默认使用 UTF-8
            if response.encoding:
                html_content = response.text
            else:
                # 如果没有编码信息，尝试 UTF-8
                html_content = response.content.decode('utf-8', errors='ignore')
            
            # 如果内容中包含 Unicode 转义序列，立即解码（在 BeautifulSoup 处理之前）
            if '\\u' in html_content:
                html_content = decode_unicode_escapes(html_content)
                logger.info(f"检测到 Unicode 转义序列，已解码: {url}")
            
        # 使用 BeautifulSoup 解析 HTML，指定编码为 UTF-8
        soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
        
        # 移除 script 和 style 标签
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        # 尝试找到文章正文内容
        # 常见的文章内容选择器
        content_selectors = [
            'article',
            '.article-content',
            '.post-content',
            '.entry-content',
            '#article-content',
            '#post-content',
            '#entry-content',
            '.content',
            '#content',
            'main article',
            'main .content',
        ]
        
        article_body = None
        for selector in content_selectors:
            article_body = soup.select_one(selector)
            if article_body:
                break
        
        # 如果没找到，尝试查找包含最多文本的 div
        if not article_body:
            # 查找所有可能的正文容器
            candidates = soup.find_all(['div', 'article', 'main'], class_=re.compile(r'content|article|post|entry', re.I))
            if candidates:
                # 选择文本最长的那个
                article_body = max(candidates, key=lambda x: len(x.get_text()))
        
        # 如果还是没找到，使用 body 标签
        if not article_body:
            article_body = soup.find('body')
        
        if not article_body:
            # 如果完全找不到，返回默认内容
            logger.warning(f"无法从 {url} 提取文章内容，使用默认内容")
            return "<p>无法获取文章内容，请查看原文链接。</p>"
        
        # 直接提取 HTML 内容，保持原始格式和字符
        # 移除所有链接、图片等外部资源引用
        for a in article_body.find_all('a'):
            # 保留链接文本，移除链接
            a.replace_with(a.get_text())
        
        for img in article_body.find_all('img'):
            # 移除图片标签
            img.decompose()
        
        # 移除其他可能的外部资源
        for iframe in article_body.find_all('iframe'):
            iframe.decompose()
        
        # 获取清理后的 HTML 内容
        # 使用 get_text() 获取纯文本，然后手动构建 HTML，避免 BeautifulSoup 转义
        # 这样可以确保中文字符不被转义
        text_content = article_body.get_text(separator='\n', strip=True)
        
        # 解码可能存在的 Unicode 转义序列
        if '\\u' in text_content:
            text_content = decode_unicode_escapes(text_content)
        
        # 如果文本为空，尝试使用 decode_contents()
        if not text_content or not text_content.strip():
            html_content = article_body.decode_contents()
            # 再次解码 Unicode 转义序列
            if '\\u' in html_content:
                html_content = decode_unicode_escapes(html_content)
        else:
            # 将文本转换为 HTML 段落
            text_paragraphs = [p.strip() for p in text_content.split('\n') if p.strip()]
            if text_paragraphs:
                html_content = ''.join([f'<p>{p}</p>' for p in text_paragraphs])
            else:
                html_content = "<p>无法获取文章内容。</p>"
        
        # 如果内容为空，尝试获取纯文本
        if not html_content or not html_content.strip():
            text = article_body.get_text(separator='\n', strip=True)
            if text:
                # 解码文本中的 Unicode 转义序列
                if '\\u' in text:
                    text = decode_unicode_escapes(text)
                # 按换行符分割成段落
                text_paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                if text_paragraphs:
                    # 直接使用文本，不转义（因为我们要生成 HTML）
                    html_content = ''.join([f'<p>{p}</p>' for p in text_paragraphs])
                else:
                    return "<p>无法获取文章内容。</p>"
            else:
                return "<p>无法获取文章内容。</p>"
        
        # 确保所有段落都被 <p> 标签包裹
        # 如果内容中没有段落标签，尝试添加
        if '<p>' not in html_content and '<div>' not in html_content:
            # 按换行分割并包裹
            lines = [line.strip() for line in html_content.split('\n') if line.strip()]
            if lines:
                # 解码每行中的 Unicode 转义序列，但不转义 HTML（因为已经是 HTML 了）
                decoded_lines = [decode_unicode_escapes(line) if '\\u' in line else line for line in lines]
                html_content = ''.join([f'<p>{line}</p>' for line in decoded_lines])
        
        # 限制总长度（微信公众号限制 2 万字符）
        if len(html_content) > 20000:
            # 如果超过限制，截断到 20000 字符，并确保最后一个标签完整
            html_content = html_content[:20000]
            # 找到最后一个完整的 </p> 标签
            last_p = html_content.rfind('</p>')
            if last_p > 0:
                html_content = html_content[:last_p + 4]
            html_content += '<p>...</p>'
        
        return html_content
            
    except Exception as e:
        logger.error(f"抓取文章内容失败 {url}: {e}")
        return "<p>抓取文章内容失败，请查看原文链接。</p>"


# @router.post("/wechat-mp/create-draft-from-articles")
async def create_draft_from_articles_disabled(request: dict, admin: None = Depends(_require_admin)):
    """从文章池创建微信公众号草稿"""
    article_ids = request.get("article_ids", [])
    
    if not article_ids:
        raise HTTPException(status_code=400, detail="请选择要发布的文章")
    
    try:
        # 获取文章数据 - get_all_articles() 返回的是 List[dict]，不是字典
        all_articles = get_all_articles()
        if not all_articles or len(all_articles) == 0:
            raise HTTPException(status_code=400, detail="文章池为空")
        
        # 根据 URL 匹配文章（因为文章池使用 URL 作为唯一标识）
        selected_articles = []
        for article in all_articles:
            if article.get("url") in article_ids:
                selected_articles.append(article)
        
        if not selected_articles:
            raise HTTPException(status_code=400, detail="未找到选中的文章")
        
        # 转换为微信公众号格式
        wechat_articles = []
        for article in selected_articles[:8]:  # 最多8篇
            title = article.get("title", "").strip()
            author = article.get("source", "").strip() or "未知"
            url = article.get("url", "").strip()
            
            # 验证必填字段
            if not title:
                raise HTTPException(status_code=400, detail=f"文章标题不能为空: {url}")
            if not url or not url.startswith(("http://", "https://")):
                raise HTTPException(status_code=400, detail=f"文章 URL 格式不正确: {url}")
            
            # 确保标题在 20 个字符以内
            max_title_length = 20
            if len(title) > max_title_length:
                # 尝试在合适的位置截断（优先在标点符号、空格处）
                truncated = title[:max_title_length]
                # 查找最后一个标点符号或空格的位置（在截断范围内）
                for sep in ['。', '，', '、', '：', '；', '！', '？', ' ', '·', '-', '—', '–']:
                    last_sep_pos = truncated.rfind(sep)
                    if last_sep_pos > max_title_length * 0.6:  # 至少保留 60% 的内容
                        truncated = truncated[:last_sep_pos]
                        break
                title = truncated
                logger.info(f"标题已缩减: {article.get('title', '')[:50]}... -> {title}")
            
            # 从 URL 抓取完整的文章 HTML 内容
            logger.info(f"正在抓取文章内容: {url}")
            content_html = await fetch_article_content_html(url)
            logger.info(f"文章内容抓取完成，长度: {len(content_html)} 字符")
            
            # 构建文章对象，严格按照微信公众号 API 要求
            article_data = {
                "article_type": "news",  # 必填：图文消息类型
                "title": title,
                "author": author,
                "content": content_html,  # 从 URL 抓取的 HTML 内容
                # thumb_media_id 将在 create_draft 方法中自动添加
                # 可选字段
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
            
            wechat_articles.append(article_data)
        
        # 创建草稿
        client = WeChatMPClient()
        media_id = await client.create_draft(wechat_articles)
        
        if media_id:
            return {
                "ok": True,
                "media_id": media_id,
                "message": f"已成功创建草稿，包含 {len(wechat_articles)} 篇文章"
            }
        else:
            raise HTTPException(status_code=500, detail="创建草稿失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从文章池创建草稿失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建草稿失败: {str(e)}")


@router.get("/panel", response_class=HTMLResponse)
async def digest_panel():
    """
    简单的前端页面：展示预览内容 + 一键触发按钮。
    """
    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>每日新闻管理面板</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <script>
        tailwind.config = {
          corePlugins: {
            preflight: false,
          }
        }
      </script>
    </head>
    <body class="bg-gray-50 text-gray-900 font-sans">
      <div class="max-w-7xl mx-auto p-6">
        <!-- 顶部栏 -->
        <div class="flex justify-between items-center mb-6">
          <h1 class="text-2xl font-bold text-gray-900">每日新闻精选 · 管理员面板</h1>
          <div class="flex items-center gap-4">
            <div class="text-sm text-gray-600">
              开源仓库：
              <a href="https://github.com/yunlongwen/100kwhy_wechat_mp" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-700">
                github.com/yunlongwen/100kwhy_wechat_mp
              </a>
            </div>
            <button class="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-full hover:bg-blue-700 transition-colors" id="open-config-btn">配置管理</button>
          </div>
        </div>
        
        <!-- 添加文章 -->
        <div class="mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">添加文章</h2>
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div class="mb-4">
              <label for="article-url" class="block text-sm font-medium text-gray-700 mb-2">文章URL：</label>
              <input type="url" id="article-url" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="粘贴文章链接，例如：https://mp.weixin.qq.com/s/..." />
            </div>
            <div class="flex gap-2">
              <button id="add-article-btn" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">添加文章</button>
            </div>
            <div class="mt-3 text-sm" id="add-status"></div>
          </div>
        </div>

        <!-- 文章抓取与候选池 -->
        <div class="mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">文章抓取与候选池</h2>
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 class="text-sm font-semibold text-blue-900 mb-2">操作说明</h3>
              <ul class="text-xs text-blue-800 space-y-1">
                <li><strong>采纳</strong>：将文章添加到正式文章池，用于每日推送。采纳后文章会从候选池移除。</li>
                <li><strong>归档</strong>：将文章保存到资讯模块的JSON文件中，方便在前端页面展示。归档时可以选择关联的工具标签，设置后可在工具详情页查看相关资讯。归档后文章仍保留在候选池中，可继续采纳。</li>
                <li><strong>忽略</strong>：从候选池中删除文章，不再显示。</li>
              </ul>
            </div>
            <div class="flex gap-2 mb-4">
              <button id="crawl-btn" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">开始自动抓取</button>
            </div>
            <div class="text-sm mb-4" id="crawl-status"></div>
            
            <!-- 工具相关资讯爬取 -->
            <div class="border-t border-gray-200 pt-4 mt-4">
              <h3 class="text-sm font-semibold text-gray-700 mb-3">工具相关资讯爬取</h3>
              <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-3">
                <p class="text-xs text-yellow-800">
                  <strong>说明：</strong>工具相关资讯只能手动触发，每个工具关键字每次爬取1篇当天的文章。爬取到的文章会带有工具名称标签，可在工具详情页查看。
                </p>
              </div>
              <div class="flex gap-2 mb-3">
                <select id="tool-keyword-select" class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">-- 选择工具关键字 --</option>
                </select>
                <button id="crawl-tool-article-btn" class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">爬取该工具资讯</button>
                <button id="crawl-all-tool-articles-btn" class="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">爬取所有工具资讯</button>
              </div>
              <div class="text-sm mb-3" id="crawl-tool-article-status"></div>
              <div class="text-xs text-gray-500">
                当前工具关键字数量: <span id="tool-keyword-count">0</span>
              </div>
            </div>
            
            <div class="mt-4" id="candidate-list">加载中...</div>
          </div>
        </div>

        <!-- 工具候选池 -->
        <div class="mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">工具候选池</h2>
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <!-- 工具爬取区域 -->
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 class="text-sm font-semibold text-blue-900 mb-3">工具爬取</h3>
              <div class="space-y-3">
                <div>
                  <label class="block text-xs text-blue-800 mb-1">爬取源URL（API端点）<span class="text-red-500">*</span></label>
                  <input type="text" id="crawl-tool-url" placeholder="例如: http://example.com/api/tools" class="w-full px-3 py-2 text-sm border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" required>
                  <p class="text-xs text-blue-600 mt-1">请输入工具API的完整URL地址</p>
                </div>
                <div class="flex flex-wrap gap-3 items-end">
                  <div class="flex-1 min-w-[200px]">
                    <label class="block text-xs text-blue-800 mb-1">分类（可选，不选则爬取所有）</label>
                    <select id="crawl-tool-category" class="w-full px-3 py-2 text-sm border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                      <option value="">全部分类</option>
                      <option value="ide">开发IDE</option>
                      <option value="plugin">IDE插件</option>
                      <option value="cli">命令行工具</option>
                      <option value="codeagent">CodeAgent</option>
                      <option value="ai-test">AI测试</option>
                      <option value="review">代码审查</option>
                      <option value="devops">DevOps工具</option>
                      <option value="doc">文档相关</option>
                      <option value="design">设计工具</option>
                      <option value="ui">UI生成</option>
                      <option value="mcp">MCP工具</option>
                    </select>
                  </div>
                  <div class="min-w-[120px]">
                    <label class="block text-xs text-blue-800 mb-1">最大数量</label>
                    <input type="number" id="crawl-tool-max" value="100" min="1" max="500" class="w-full px-3 py-2 text-sm border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                  </div>
                  <button onclick="crawlTools()" class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                    🕷️ 开始爬取
                  </button>
                </div>
              </div>
              <div id="crawl-tool-status" class="mt-3 text-xs text-blue-700"></div>
            </div>
            
            <div class="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
              <h3 class="text-sm font-semibold text-purple-900 mb-2">操作说明</h3>
              <ul class="text-xs text-purple-800 space-y-1">
                <li><strong>爬取</strong>：差量爬取工具，只添加本地没有的工具到候选池。</li>
                <li><strong>采纳</strong>：将工具添加到正式工具池，选择分类后保存到对应的JSON文件。采纳后工具会从候选池移除。</li>
                <li><strong>忽略</strong>：从候选池中删除工具，不再显示。</li>
              </ul>
            </div>
            <div class="mt-4" id="tool-candidate-list">加载中...</div>
          </div>
        </div>

        <!-- 文章列表 -->
        <div class="mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">文章列表</h2>
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div class="text-sm mb-4" id="list-status"></div>
            <div class="mt-4" id="article-list">加载中...</div>
          </div>
        </div>

        <!-- 预览 & 推送 -->
        <div class="mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">预览 & 推送</h2>
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div class="text-sm text-gray-600 mb-4" id="meta">加载中...</div>
            <div id="articles" class="mb-4"></div>
            <button id="trigger-btn" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">手动触发一次推送到企业微信群</button>
            <div class="mt-3 text-sm" id="status"></div>
          </div>
        </div>

      <!-- 授权对话框 -->
      <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 hidden" id="auth-overlay">
        <div class="bg-white rounded-2xl p-6 w-80 shadow-xl">
          <h2 class="text-lg font-semibold text-gray-900 mb-2">输入授权码</h2>
          <p class="text-sm text-gray-600 mb-4">仅限管理员访问。请填写授权码后进入面板。</p>
          <input type="password" id="admin-code-input" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4" placeholder="授权码" />
          <div class="text-sm mb-4" id="auth-status"></div>
          <div class="flex justify-end gap-2">
            <button class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors" id="auth-submit-btn">确认</button>
          </div>
        </div>
      </div>

      <!-- 配置模态框 -->
      <div class="fixed inset-0 bg-black bg-opacity-45 flex items-center justify-center z-60 hidden" id="config-modal">
        <div class="bg-white rounded-2xl p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-xl relative">
          <button class="absolute top-4 right-4 w-8 h-8 rounded-full bg-gray-100 text-blue-600 hover:bg-gray-200 transition-colors flex items-center justify-center text-xl" id="close-config-btn">&times;</button>
          <h2 class="text-xl font-semibold text-gray-900 mb-6">配置管理</h2>
          <div class="flex gap-2 mb-6">
            <button class="flex-1 px-3 py-2 rounded-lg border border-gray-300 bg-blue-600 text-white text-sm font-medium config-menu-btn is-active" data-section="keywords">关键词</button>
            <button class="flex-1 px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 text-sm font-medium config-menu-btn" data-section="schedule">调度</button>
            <button class="flex-1 px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 text-sm font-medium config-menu-btn" data-section="template">企业微信模板</button>
            <button class="flex-1 px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 text-sm font-medium config-menu-btn" data-section="env">系统配置</button>
          </div>

          <div id="config-keywords-section" class="config-section block">
            <div class="mb-4">
              <label for="config-keywords-input" class="block text-sm font-medium text-gray-700 mb-2">关键词（每行一个）</label>
              <textarea id="config-keywords-input" class="w-full min-h-[150px] px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm resize-y" placeholder="例如：&#10;AI 编码&#10;数字孪生"></textarea>
              <p class="mt-2 text-xs text-gray-600">一行一个关键词，支持中文与英文。保存后下一次抓取会自动生效。</p>
            </div>
            <div class="flex gap-2">
              <button class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors" id="save-keywords-btn">保存关键词</button>
            </div>
            <div class="mt-3 text-sm" id="config-keywords-status"></div>
          </div>

          <div id="config-schedule-section" class="config-section hidden">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">调度方式</label>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input type="text" id="schedule-cron" class="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Cron 表达式（可选）" />
                <input type="number" id="schedule-hour" min="0" max="23" class="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="小时" />
                <input type="number" id="schedule-minute" min="0" max="59" class="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="分钟" />
              </div>
              <p class="mt-2 text-xs text-gray-600">
                • <strong>Cron 表达式</strong>（推荐）：5 字段格式，例如 <code>0 14 * * *</code> 表示每天 14:00 执行<br />
                • <strong>小时 + 分钟</strong>：仅在未设置 Cron 时生效，例如 14:00 表示每天下午 2 点
              </p>
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">数量控制</label>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input type="number" id="schedule-count" min="1" class="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="推送篇数" />
                <input type="number" id="schedule-max" min="1" class="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="每关键词最大篇数" />
              </div>
              <p class="mt-2 text-xs text-gray-600">
                • <strong>推送篇数</strong>：每期推送的文章总数<br />
                • <strong>每关键词最大篇数</strong>：每个关键词最多抓取的文章数量
              </p>
            </div>
            <div class="flex gap-2">
              <button class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors" id="save-schedule-btn">保存调度</button>
            </div>
            <div class="mt-3 text-sm" id="config-schedule-status"></div>
          </div>

          <div id="config-template-section" class="config-section hidden">
            <div class="mb-4">
              <label for="wecom-template-input" class="block text-sm font-medium text-gray-700 mb-2">企业微信模板（JSON 格式）</label>
              <textarea id="wecom-template-input" class="w-full min-h-[150px] px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm resize-y"></textarea>
              <p class="mt-2 text-xs text-gray-600">
                <strong>模板说明：</strong><br />
                填写完整的 JSON 对象，支持 Markdown 格式。推送时会自动替换以下占位符：<br />
                • <code>{date}</code> - 推送日期（如：2024-01-15）<br />
                • <code>{theme}</code> - 今日主题（如：AI 编码）<br />
                • <code>{idx}</code> - 文章序号（如：1, 2, 3）<br />
                • <code>{title}</code> - 文章标题<br />
                • <code>{url}</code> - 文章链接<br />
                • <code>{source}</code> - 文章来源<br />
                • <code>{summary}</code> - 文章摘要<br />
                <strong>示例结构：</strong>包含 <code>title</code>、<code>theme</code>、<code>item</code>（含 title/source/summary）、<code>footer</code> 等字段。
              </p>
            </div>
            <div class="flex gap-2">
              <button class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors" id="save-template-btn">保存模板</button>
            </div>
            <div class="mt-3 text-sm" id="config-template-status"></div>
          </div>

          <div id="config-env-section" class="config-section hidden">
            <div class="mb-4">
              <label for="env-admin-code" class="block text-sm font-medium text-gray-700 mb-2">管理员验证码</label>
              <input type="password" id="env-admin-code" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="用于保护管理面板的授权码" />
              <p class="mt-2 text-xs text-gray-600">设置后访问管理面板时需要输入此验证码。留空则不设置验证码（不推荐）。</p>
            </div>
            <div class="mb-4">
              <label for="env-wecom-webhook" class="block text-sm font-medium text-gray-700 mb-2">企业微信推送地址</label>
              <input type="text" id="env-wecom-webhook" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY" />
              <p class="mt-2 text-xs text-gray-600">企业微信群机器人的 Webhook URL。在企业微信群中添加机器人后获取。</p>
            </div>
            <div class="flex gap-2">
              <button class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors" id="save-env-btn">保存系统配置</button>
            </div>
            <div class="mt-3 text-sm" id="config-env-status"></div>
          </div>
        </div>
      </div>

      <div class="draft-modal" id="draft-edit-modal">
        <div class="draft-modal-content">
          <button class="config-modal-close" id="close-draft-edit-btn">&times;</button>
          <h2>编辑草稿</h2>
          <div id="draft-edit-content"></div>
        </div>
      </div>

      <!-- 归档对话框 -->
      <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 hidden" id="archive-modal">
        <div class="bg-white rounded-2xl p-6 w-[500px] shadow-xl max-h-[90vh] overflow-y-auto">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">选择归档模块</h2>
          <p class="text-sm text-gray-600 mb-4">请选择要将文章归档到的资讯模块和关联的工具标签：</p>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">资讯分类 <span class="text-red-500">*</span></label>
            <select id="archive-category" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="programming">编程资讯</option>
              <option value="ai_news">AI资讯</option>
            </select>
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">工具标签 <span class="text-gray-500">(可选，多个用逗号分隔)</span></label>
            <input type="text" id="archive-tool-tags" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="例如：warp, cursor, copilot" />
            <p class="mt-1 text-xs text-gray-500">输入工具名称，用逗号分隔。设置后，在工具详情页可以查看相关资讯。</p>
          </div>
          
          <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
            <p class="text-xs text-yellow-800">
              <strong>提示：</strong>归档后文章会保存到对应的资讯模块JSON文件中，并在前端页面展示。文章仍会保留在候选池中，可以继续采纳用于推送。
            </p>
          </div>
          
          <div class="text-sm mb-4" id="archive-status"></div>
          <div class="flex justify-end gap-2">
            <button class="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors" id="archive-cancel-btn">取消</button>
            <button class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors" id="archive-confirm-btn">确认归档</button>
          </div>
        </div>
      </div>

      <script>
        // 最开始的日志，确保脚本执行
        console.log('[DEBUG] ========== 管理员面板脚本开始执行 ==========');
        console.log('[DEBUG] 当前时间:', new Date().toISOString());
        
        const ADMIN_CODE_KEY = "aicoding_admin_code";
        let authFailCount = 0;
        let authBlockedUntil = 0; // timestamp ms

        function getAdminCode() {
          return localStorage.getItem(ADMIN_CODE_KEY) || "";
        }

        function setAdminCode(code) {
          localStorage.setItem(ADMIN_CODE_KEY, code || "");
        }

        function showAuthOverlay() {
          console.log('[DEBUG] showAuthOverlay 开始执行');
          const overlay = document.getElementById("auth-overlay");
          const input = document.getElementById("admin-code-input");
          const statusEl = document.getElementById("auth-status");
          
          console.log('[DEBUG] 授权对话框元素:', { overlay, input, statusEl });
          
          if (!overlay) {
            console.error('[DEBUG] 授权对话框元素未找到！');
            return;
          }
          
          console.log('[DEBUG] 授权对话框当前类名:', overlay.className);
          overlay.classList.remove("hidden");
          overlay.classList.add("flex");
          console.log('[DEBUG] 授权对话框更新后类名:', overlay.className);
          
          if (statusEl) {
            statusEl.textContent = "";
            statusEl.className = "text-sm";
          }
          if (input) {
            input.value = "";
            input.focus();
          }
          console.log('[DEBUG] 授权对话框应该已显示');
        }

        function hideAuthOverlay() {
          console.log('[DEBUG] 隐藏授权对话框');
          const overlay = document.getElementById("auth-overlay");
          if (overlay) {
            overlay.classList.add("hidden");
            overlay.classList.remove("flex");
          }
        }

        function handleAuthError(contextStatusEl) {
          const now = Date.now();
          if (authBlockedUntil && now < authBlockedUntil) {
            const seconds = Math.ceil((authBlockedUntil - now) / 1000);
            if (contextStatusEl) {
              contextStatusEl.textContent = `❌ 授权多次失败，请 ${seconds} 秒后再试`;
              contextStatusEl.className = "status error";
            }
            return false;
          }

          authFailCount += 1;
          if (authFailCount >= 5) {
            // 简单限流：5 次失败后，锁定 60 秒
            authBlockedUntil = now + 60 * 1000;
          }

          setAdminCode("");
          showAuthOverlay();
          if (contextStatusEl) {
            contextStatusEl.textContent = "❌ 授权码错误，请重新输入";
            contextStatusEl.className = "status error";
          }
          return false;
        }

        async function ensureAdminCode() {
          console.log('[DEBUG] ensureAdminCode 开始执行');
          let code = getAdminCode();
          console.log('[DEBUG] 从 localStorage 获取授权码:', code ? '已存在' : '不存在');
          if (!code) {
            console.log('[DEBUG] 授权码不存在，显示授权对话框');
            showAuthOverlay();
            return false;
          }
          console.log('[DEBUG] 授权码存在，继续执行');
          return true;
        }

        async function crawlArticles() {
            const btn = document.getElementById("crawl-btn");
            const statusEl = document.getElementById("crawl-status");

            btn.disabled = true;
            statusEl.textContent = "正在从网络抓取文章，请稍候...（可能需要几十秒）";
            statusEl.className = "text-sm";

            try {
                const adminCode = getAdminCode();
                const res = await fetch("./crawl-articles", {
                    method: "POST",
                    headers: { "X-Admin-Code": adminCode || "" }
                });

                if (res.status === 401 || res.status === 403) {
                    handleAuthError(statusEl);
                    return;
                }

                const data = await res.json();
                if (data.ok) {
                    statusEl.textContent = `✅ ${data.message}`;
                    statusEl.className = "text-sm text-green-600";
                    loadCandidateList(); // Refresh the list
                    loadCandidateList(); // Refresh the list
                } else {
                    statusEl.textContent = `❌ ${data.message || "抓取失败"}`;
                    statusEl.className = "text-sm text-red-600";
                }
            } catch (err) {
                console.error(err);
                statusEl.textContent = "❌ 请求失败，请查看浏览器控制台或服务器日志。";
                statusEl.className = "text-sm text-red-600";
            } finally {
                btn.disabled = false;
            }
        }

        async function loadToolKeywords() {
            try {
                const adminCode = getAdminCode();
                const res = await fetch("./tool-keywords", {
                    headers: { "X-Admin-Code": adminCode || "" }
                });
                if (res.status === 401 || res.status === 403) {
                    return;
                }
                const data = await res.json();
                if (data.ok) {
                    const select = document.getElementById("tool-keyword-select");
                    const countEl = document.getElementById("tool-keyword-count");
                    if (select) {
                        // 保留第一个选项
                        select.innerHTML = '<option value="">-- 选择工具关键字 --</option>';
                        data.keywords.forEach(keyword => {
                            const option = document.createElement("option");
                            option.value = keyword;
                            option.textContent = keyword;
                            select.appendChild(option);
                        });
                    }
                    if (countEl) {
                        countEl.textContent = data.count || 0;
                    }
                }
            } catch (err) {
                console.error("加载工具关键字失败:", err);
            }
        }

        async function crawlToolArticles(keyword = null) {
            const btn = keyword 
                ? document.getElementById("crawl-tool-article-btn")
                : document.getElementById("crawl-all-tool-articles-btn");
            const statusEl = document.getElementById("crawl-tool-article-status");

            btn.disabled = true;
            statusEl.textContent = keyword 
                ? `正在爬取工具 "${keyword}" 的相关资讯，请稍候...`
                : "正在爬取所有工具的相关资讯，请稍候...";
            statusEl.className = "text-sm";

            try {
                const adminCode = getAdminCode();
                const res = await fetch("./crawl-tool-articles", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Code": adminCode || ""
                    },
                    body: JSON.stringify({ keyword: keyword || "" })
                });

                if (res.status === 401 || res.status === 403) {
                    handleAuthError(statusEl);
                    return;
                }

                const data = await res.json();
                if (data.ok) {
                    statusEl.textContent = `✅ ${data.message}`;
                    statusEl.className = "text-sm text-green-600";
                    loadCandidateList(); // Refresh the list
                } else {
                    statusEl.textContent = `❌ ${data.message || "抓取失败"}`;
                    statusEl.className = "text-sm text-red-600";
                }
            } catch (err) {
                console.error(err);
                statusEl.textContent = "❌ 请求失败，请查看浏览器控制台或服务器日志。";
                statusEl.className = "text-sm text-red-600";
            } finally {
                btn.disabled = false;
            }
        }

        // 爬取工具
        async function crawlTools() {
            const sourceUrl = document.getElementById("crawl-tool-url").value.trim();
            const category = document.getElementById("crawl-tool-category").value;
            const maxItems = parseInt(document.getElementById("crawl-tool-max").value) || 100;
            const statusEl = document.getElementById("crawl-tool-status");
            
            // 验证URL
            if (!sourceUrl) {
                statusEl.innerHTML = '<span class="text-red-600">❌ 请输入爬取源URL</span>';
                return;
            }
            
            if (!sourceUrl.startsWith("http://") && !sourceUrl.startsWith("https://")) {
                statusEl.innerHTML = '<span class="text-red-600">❌ URL格式不正确，必须以 http:// 或 https:// 开头</span>';
                return;
            }
            
            statusEl.innerHTML = '<span class="text-blue-600">🔄 正在爬取工具，请稍候...</span>';
            
            try {
                const adminCode = getAdminCode();
                const res = await fetch("./crawl-tools", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Code": adminCode || "",
                    },
                    body: JSON.stringify({
                        source_url: sourceUrl,
                        category: category || null,
                        max_items: maxItems
                    }),
                });
                
                if (!res.ok) {
                    const error = await res.json();
                    throw new Error(error.detail || "爬取失败");
                }
                
                const data = await res.json();
                if (data.ok) {
                    statusEl.innerHTML = `<span class="text-green-600">✅ ${data.message}</span>`;
                    // 刷新工具候选池列表
                    setTimeout(() => {
                        loadToolCandidateList();
                        statusEl.innerHTML = "";
                    }, 1000);
                } else {
                    throw new Error(data.message || "爬取失败");
                }
            } catch (err) {
                console.error("爬取工具失败:", err);
                statusEl.innerHTML = `<span class="text-red-600">❌ 爬取失败: ${err.message}</span>`;
            }
        }
        
        // 加载工具候选池
        async function loadToolCandidateList() {
            const listEl = document.getElementById("tool-candidate-list");
            if (!listEl) return;
            
            try {
                const adminCode = getAdminCode();
                const res = await fetch("./tool-candidates", {
                    headers: {
                        "X-Admin-Code": adminCode || "",
                    },
                });
                
                if (res.status === 401 || res.status === 403) {
                    handleAuthError(listEl);
                    return;
                }
                
                const data = await res.json();
                if (!data.ok) {
                    listEl.innerHTML = `<p class="text-red-600">加载失败: ${data.message || "未知错误"}</p>`;
                    return;
                }
                
                const candidates = data.candidates || [];
                
                if (candidates.length === 0) {
                    listEl.innerHTML = '<p class="text-gray-500">暂无待审核的工具</p>';
                    return;
                }
                
                listEl.innerHTML = "";
                candidates.forEach((tool) => {
                    const div = document.createElement("div");
                    div.className = "border border-gray-200 rounded-lg p-4 mb-3";
                    const nameEscaped = tool.name.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                    const descEscaped = (tool.description || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                    const urlEscaped = tool.url.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                    
                    div.innerHTML = `
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex-1">
                                <h4 class="font-semibold text-gray-900">${nameEscaped}</h4>
                                <p class="text-sm text-gray-600 mt-1">${descEscaped}</p>
                                <a href="${urlEscaped}" target="_blank" class="text-sm text-blue-600 hover:underline mt-1 block">${urlEscaped}</a>
                                <div class="text-xs text-gray-500 mt-2">
                                    分类: ${tool.category || "未分类"} | 
                                    提交时间: ${tool.submitted_at ? new Date(tool.submitted_at).toLocaleString("zh-CN") : "未知"}
                                </div>
                            </div>
                        </div>
                        <div class="flex gap-2 mt-3">
                            <button class="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700" data-url="${urlEscaped}" data-category="${tool.category || "other"}">采纳</button>
                            <button class="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700" data-url="${urlEscaped}">忽略</button>
                        </div>
                    `;
                    
                    div.querySelector("button.bg-green-600").addEventListener("click", () => {
                        const promptText = "请选择工具分类:\\nide, plugin, cli, codeagent, ai-test, review, devops, doc, design, ui, mcp, other";
                        const category = prompt(promptText, tool.category || "other");
                        if (category) {
                            acceptToolCandidate(tool.url, category);
                        }
                    });
                    div.querySelector("button.bg-gray-600").addEventListener("click", () => rejectToolCandidate(tool.url));
                    
                    listEl.appendChild(div);
                });
            } catch (err) {
                console.error("加载工具候选池失败:", err);
                listEl.innerHTML = `<p class="text-red-600">加载失败: ${err.message}</p>`;
            }
        }
        
        async function acceptToolCandidate(url, category) {
            const listEl = document.getElementById("tool-candidate-list");
            const statusMsg = document.createElement("div");
            statusMsg.className = "text-sm text-blue-600 mb-2";
            statusMsg.textContent = "正在采纳工具...";
            listEl.insertBefore(statusMsg, listEl.firstChild);
            
            try {
                const adminCode = getAdminCode();
                const res = await fetch("./accept-tool-candidate", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Code": adminCode || "",
                    },
                    body: JSON.stringify({ url: url, category: category })
                });
                
                if (res.status === 401 || res.status === 403) {
                    handleAuthError(statusMsg);
                    return;
                }
                
                const data = await res.json();
                if (data.ok) {
                    statusMsg.textContent = `✅ ${data.message}`;
                    statusMsg.className = "text-sm text-green-600 mb-2";
                    setTimeout(() => {
                        statusMsg.remove();
                        loadToolCandidateList();
                    }, 2000);
                } else {
                    statusMsg.textContent = `❌ ${data.message || "采纳失败"}`;
                    statusMsg.className = "text-sm text-red-600 mb-2";
                }
            } catch (err) {
                console.error(err);
                statusMsg.textContent = "❌ 请求失败，请查看浏览器控制台。";
                statusMsg.className = "text-sm text-red-600 mb-2";
            }
        }
        
        async function rejectToolCandidate(url) {
            const listEl = document.getElementById("tool-candidate-list");
            const statusMsg = document.createElement("div");
            statusMsg.className = "text-sm text-blue-600 mb-2";
            statusMsg.textContent = "正在忽略工具...";
            listEl.insertBefore(statusMsg, listEl.firstChild);
            
            try {
                const adminCode = getAdminCode();
                const res = await fetch("./reject-tool-candidate", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Code": adminCode || "",
                    },
                    body: JSON.stringify({ url: url })
                });
                
                if (res.status === 401 || res.status === 403) {
                    handleAuthError(statusMsg);
                    return;
                }
                
                const data = await res.json();
                if (data.ok) {
                    statusMsg.textContent = `✅ ${data.message}`;
                    statusMsg.className = "text-sm text-green-600 mb-2";
                    setTimeout(() => {
                        statusMsg.remove();
                        loadToolCandidateList();
                    }, 2000);
                } else {
                    statusMsg.textContent = `❌ ${data.message || "忽略失败"}`;
                    statusMsg.className = "text-sm text-red-600 mb-2";
                }
            } catch (err) {
                console.error(err);
                statusMsg.textContent = "❌ 请求失败，请查看浏览器控制台。";
                statusMsg.className = "text-sm text-red-600 mb-2";
            }
        }

        async function loadCandidateList() {
            console.log('[DEBUG] loadCandidateList 开始执行');
            const listEl = document.getElementById("candidate-list");
            const statusEl = document.getElementById("crawl-status");
            if (!listEl) {
                console.error('[DEBUG] candidate-list 元素未找到');
                return;
            }
            listEl.innerHTML = "加载中...";

            try {
                const adminCode = getAdminCode();
                console.log('[DEBUG] 请求候选列表，URL: ./candidates');
                const res = await fetch(`./candidates?_t=${Date.now()}`, {
                    headers: { "X-Admin-Code": adminCode || "" }
                });
                console.log('[DEBUG] 候选列表响应状态:', res.status, res.statusText);

                if (res.status === 401 || res.status === 403) {
                    console.log('[DEBUG] 授权失败，状态码:', res.status);
                    handleAuthError(statusEl);
                    return;
                }

                if (!res.ok) {
                    console.error('[DEBUG] 请求失败，状态码:', res.status);
                    listEl.innerHTML = `<p class="text-red-600">请求失败: HTTP ${res.status}</p>`;
                    return;
                }

                const data = await res.json();
                console.log('[DEBUG] 候选列表数据:', data);
                if (!data.ok || !data.grouped_candidates || Object.keys(data.grouped_candidates).length === 0) {
                    console.log('[DEBUG] 没有候选文章');
                    listEl.innerHTML = '<p class="text-gray-600">当前没有待审核的文章。</p>';
                    return;
                }

                listEl.innerHTML = "";
                Object.keys(data.grouped_candidates).forEach(keyword => {
                    const articles = data.grouped_candidates[keyword];
                    const groupContainer = document.createElement("div");
                    groupContainer.className = "mb-6";
                    
                    const groupTitle = document.createElement("h3");
                    groupTitle.className = "text-base font-semibold text-gray-900 mb-3";
                    const keywordEscaped = keyword.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                    groupTitle.innerHTML = `关键词: ${keywordEscaped} <span class="text-gray-500">(${articles.length}篇)</span>`;
                    groupContainer.appendChild(groupTitle);

                    articles.forEach((item, idx) => {
                        // 保存候选文章信息，用于归档时自动填充工具标签
                        candidateArticlesMap[item.url] = item;
                        
                        const div = document.createElement("div");
                        div.className = "bg-white rounded-lg p-4 mb-3 border border-gray-200 shadow-sm";
                        const urlEscaped = item.url.replace(/'/g, "&#39;").replace(/"/g, "&quot;");
                        const titleEscaped = (item.title || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const sourceEscaped = (item.source || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const summaryEscaped = (item.summary || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const isArchived = item.is_archived || false;

                        // 构建标签区域
                        let tagsHtml = '';
                        if (isArchived) {
                            tagsHtml = '<span class="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">已归档</span>';
                        }

                        // 构建按钮区域
                        let archiveButtonHtml = '';
                        if (isArchived) {
                            archiveButtonHtml = '<button class="px-3 py-1 bg-gray-400 text-white text-xs rounded-lg cursor-not-allowed opacity-50" disabled>已归档</button>';
                        } else {
                            archiveButtonHtml = `<button class="px-3 py-1 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors archive-btn" data-url="${urlEscaped}">归档</button>`;
                        }

                        div.innerHTML = `
                            <div class="flex justify-between items-start mb-2">
                              <div class="flex-1">
                                <div class="font-semibold text-gray-900 mb-1 flex items-center gap-2">
                                  <span>${idx + 1}.</span>
                                  <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-700">${titleEscaped}</a>
                                  ${tagsHtml}
                                </div>
                              </div>
                              <div class="flex gap-2 ml-4">
                                <button class="px-3 py-1 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700 transition-colors" data-url="${urlEscaped}">采纳</button>
                                ${archiveButtonHtml}
                                <button class="px-3 py-1 bg-gray-600 text-white text-xs rounded-lg hover:bg-gray-700 transition-colors" data-url="${urlEscaped}">忽略</button>
                              </div>
                            </div>
                            <div class="text-xs text-gray-600 mb-1">来源：${sourceEscaped}</div>
                            <div class="text-sm text-gray-700">${summaryEscaped}</div>
                        `;
                        
                        div.querySelector("button.bg-green-600").addEventListener("click", () => acceptCandidate(item.url));
                        if (!isArchived) {
                            div.querySelector("button.archive-btn").addEventListener("click", () => showArchiveModal(item.url));
                        }
                        div.querySelector("button.bg-gray-600").addEventListener("click", () => rejectCandidate(item.url));

                        groupContainer.appendChild(div);
                    });
                    listEl.appendChild(groupContainer);
                });
            } catch (err) {
                console.error('[DEBUG] loadCandidateList 出错:', err);
                listEl.innerHTML = `<p class="text-red-600">加载候选文章失败: ${err.message}</p>`;
            }
        }

        async function acceptCandidate(url) {
            const statusEl = document.getElementById("crawl-status");
            statusEl.textContent = "正在采纳文章...";
            statusEl.className = "text-sm";

            try {
                const adminCode = getAdminCode();
                const res = await fetch("./accept-candidate", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Code": adminCode || "",
                    },
                    body: JSON.stringify({ url: url })
                });

                if (res.status === 401 || res.status === 403) {
                    handleAuthError(statusEl);
                    return;
                }

                const data = await res.json();
                if (data.ok) {
                    statusEl.textContent = `✅ ${data.message}`;
                    statusEl.className = "text-sm text-green-600";
                    loadCandidateList();
                    loadToolCandidateList();
                    loadArticleList();
                    loadPreview();
                } else {
                    statusEl.textContent = `❌ ${data.message || "采纳失败"}`;
                    statusEl.className = "text-sm text-red-600";
                }
            } catch (err) {
                console.error(err);
                statusEl.textContent = "❌ 请求失败，请查看浏览器控制台。";
                statusEl.className = "text-sm text-red-600";
            }
        }

        async function rejectCandidate(url) {
            const statusEl = document.getElementById("crawl-status");
            statusEl.textContent = "正在忽略文章...";
            statusEl.className = "text-sm";

            try {
                const adminCode = getAdminCode();
                const res = await fetch("./reject-candidate", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Code": adminCode || "",
                    },
                    body: JSON.stringify({ url: url })
                });

                if (res.status === 401 || res.status === 403) {
                    handleAuthError(statusEl);
                    return;
                }

                const data = await res.json();
                if (data.ok) {
                    statusEl.textContent = `✅ ${data.message}`;
                    statusEl.className = "text-sm text-green-600";
                    loadCandidateList();
                    loadPreview();
                } else {
                    statusEl.textContent = `❌ ${data.message || "忽略失败"}`;
                    statusEl.className = "text-sm text-red-600";
                }
            } catch (err) {
                console.error(err);
                statusEl.textContent = "❌ 请求失败，请查看浏览器控制台。";
                statusEl.className = "text-sm text-red-600";
            }
        }

        let currentArchiveUrl = null;
        let archiveSource = null; // 'candidate' 或 'article'
        let candidateArticlesMap = {}; // 存储候选文章信息，key为URL

        function showArchiveModal(url, source = 'candidate') {
            currentArchiveUrl = url;
            archiveSource = source; // 记录归档来源
            const modal = document.getElementById("archive-modal");
            const statusEl = document.getElementById("archive-status");
            const categorySelect = document.getElementById("archive-category");
            const toolTagsInput = document.getElementById("archive-tool-tags");
            
            if (modal) {
                modal.classList.remove("hidden");
                modal.classList.add("flex");
            }
            if (statusEl) {
                statusEl.textContent = "";
                statusEl.className = "text-sm";
            }
            if (categorySelect) {
                categorySelect.value = "programming";
            }
            if (toolTagsInput) {
                // 如果是候选池归档，自动从候选文章信息中提取工具名称
                if (source === 'candidate') {
                    const articleInfo = candidateArticlesMap[url];
                    if (articleInfo && articleInfo.crawled_from && articleInfo.crawled_from.startsWith("tool_keyword:")) {
                        const toolName = articleInfo.crawled_from.replace("tool_keyword:", "").trim();
                        toolTagsInput.value = toolName;
                    } else {
                        toolTagsInput.value = "";
                    }
                } else {
                    toolTagsInput.value = "";
                }
            }
        }

        function hideArchiveModal() {
            const modal = document.getElementById("archive-modal");
            if (modal) {
                modal.classList.add("hidden");
                modal.classList.remove("flex");
            }
            currentArchiveUrl = null;
            archiveSource = null;
        }

        async function archiveCandidate(url, category, toolTags) {
            const statusEl = document.getElementById("crawl-status");
            const archiveStatusEl = document.getElementById("archive-status");
            
            archiveStatusEl.textContent = "正在归档文章...";
            archiveStatusEl.className = "text-sm text-blue-600";

            try {
                const adminCode = getAdminCode();
                const res = await fetch("./archive-candidate", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Code": adminCode || "",
                    },
                    body: JSON.stringify({ 
                        url: url, 
                        category: category,
                        tool_tags: toolTags || []
                    })
                });

                if (res.status === 401 || res.status === 403) {
                    handleAuthError(statusEl);
                    hideArchiveModal();
                    return;
                }

                const data = await res.json();
                if (data.ok) {
                    archiveStatusEl.textContent = `✅ ${data.message}`;
                    archiveStatusEl.className = "text-sm text-green-600";
                    statusEl.textContent = `✅ ${data.message}`;
                    statusEl.className = "text-sm text-green-600";
                    
                    // 延迟关闭对话框，让用户看到成功消息
                    setTimeout(() => {
                        hideArchiveModal();
                        loadCandidateList();
                        loadPreview();
                    }, 1500);
                } else {
                    archiveStatusEl.textContent = `❌ ${data.message || "归档失败"}`;
                    archiveStatusEl.className = "text-sm text-red-600";
                }
            } catch (err) {
                console.error(err);
                archiveStatusEl.textContent = "❌ 请求失败，请查看浏览器控制台。";
                archiveStatusEl.className = "text-sm text-red-600";
            }
        }
        
        // 从文章池归档文章
        async function archiveArticleFromPool(url, category, toolTags) {
            const archiveStatusEl = document.getElementById("archive-status");
            
            if (!archiveStatusEl) {
                console.error("archive-status 元素未找到");
                return;
            }
            
            archiveStatusEl.textContent = "正在归档文章...";
            archiveStatusEl.className = "text-sm text-blue-600";

            try {
                const adminCode = getAdminCode();
                const res = await fetch("./archive-article", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Code": adminCode || "",
                    },
                    body: JSON.stringify({ 
                        url: url, 
                        category: category,
                        tool_tags: toolTags || []
                    })
                });

                if (res.status === 401 || res.status === 403) {
                    handleAuthError(archiveStatusEl);
                    hideArchiveModal();
                    return;
                }

                const data = await res.json();
                if (data.ok) {
                    archiveStatusEl.textContent = `✅ ${data.message}`;
                    archiveStatusEl.className = "text-sm text-green-600";
                    
                    // 延迟关闭对话框，让用户看到成功消息，然后重新加载文章列表更新状态
                    setTimeout(() => {
                        hideArchiveModal();
                        loadArticleList(); // 重新加载文章列表，更新归档状态
                    }, 1500);
                } else {
                    archiveStatusEl.textContent = `❌ ${data.message || "归档失败"}`;
                    archiveStatusEl.className = "text-sm text-red-600";
                }
            } catch (err) {
                console.error(err);
                archiveStatusEl.textContent = "❌ 请求失败，请查看浏览器控制台。";
                archiveStatusEl.className = "text-sm text-red-600";
            }
        }

        async function loadArticleList() {
          console.log('[DEBUG] loadArticleList 开始执行');
          const listEl = document.getElementById("article-list");
          const statusEl = document.getElementById("list-status");
          if (!listEl) {
            console.error('[DEBUG] article-list 元素未找到');
            return;
          }
          if (statusEl) statusEl.textContent = "";
          listEl.innerHTML = "加载中...";

          try {
            const adminCode = getAdminCode();
            console.log('[DEBUG] 请求文章列表，URL: ./articles');
            const res = await fetch("./articles", {
              headers: { "X-Admin-Code": adminCode || "" },
            });
            console.log('[DEBUG] 文章列表响应状态:', res.status, res.statusText);

            if (res.status === 401 || res.status === 403) {
              console.log('[DEBUG] 授权失败，状态码:', res.status);
              handleAuthError(statusEl);
              return;
            }

            if (!res.ok) {
              console.error('[DEBUG] 请求失败，状态码:', res.status);
              listEl.innerHTML = `<p class="text-red-600">请求失败: HTTP ${res.status}</p>`;
              return;
            }

            const data = await res.json();
            console.log('[DEBUG] 文章列表数据:', data);
            
                if (!data.ok || !data.articles || data.articles.length === 0) {
              console.log('[DEBUG] 没有已配置的文章');
              listEl.innerHTML = '<p class="text-gray-600">当前没有已配置的文章。</p>';
              return;
            }

            listEl.innerHTML = "";
            data.articles.forEach((item, idx) => {
              const div = document.createElement("div");
              div.className = "bg-white rounded-lg p-4 mb-3 border border-gray-200 shadow-sm";
              const urlEscaped = item.url.replace(/'/g, "&#39;").replace(/"/g, "&quot;");
              const titleEscaped = (item.title || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
              const sourceEscaped = (item.source || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
              const summaryEscaped = (item.summary || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
              
              // 检查归档状态
              const isArchived = item.is_archived || false;
              let tagsHtml = '';
              if (isArchived) {
                tagsHtml = '<span class="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full font-medium mr-2">已归档</span>';
              }
              
              // 归档按钮
              let archiveButtonHtml = '';
              if (isArchived) {
                archiveButtonHtml = '<button class="px-3 py-1 bg-gray-400 text-white text-xs rounded-lg cursor-not-allowed opacity-50" disabled>已归档</button>';
              } else {
                archiveButtonHtml = `<button class="px-3 py-1 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors archive-article-btn" data-url="${urlEscaped}">归档</button>`;
              }
              
              div.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                  <div class="flex-1">
                    <div class="font-semibold text-gray-900 mb-1 flex items-center gap-2">
                      ${idx + 1}. <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-700">${titleEscaped}</a>
                      ${tagsHtml}
                    </div>
                  </div>
                  <div class="ml-4 flex gap-2">
                    ${archiveButtonHtml}
                    <button class="px-3 py-1 bg-red-600 text-white text-xs rounded-lg hover:bg-red-700 transition-colors delete-article-btn" data-url="${urlEscaped}">删除</button>
                  </div>
                </div>
                <div class="text-xs text-gray-600 mb-1">来源：${sourceEscaped}</div>
                <div class="text-sm text-gray-700">${summaryEscaped}</div>
              `;
              
              // 绑定删除按钮事件（使用更具体的class选择器）
              const deleteBtn = div.querySelector("button.delete-article-btn");
              if (deleteBtn) {
                deleteBtn.addEventListener("click", function() {
                  deleteArticle(item.url);
                });
              } else {
                console.error('[DEBUG] 删除按钮未找到，URL:', item.url);
              }
              
              // 绑定归档按钮事件
              if (!isArchived) {
                const archiveBtn = div.querySelector("button.archive-article-btn");
                if (archiveBtn) {
                  archiveBtn.addEventListener("click", function() {
                    showArchiveModal(item.url, 'article'); // 标记为从文章池归档
                  });
                }
              }
              
              listEl.appendChild(div);
            });
            console.log('[DEBUG] 文章列表加载完成，共', data.articles.length, '篇');
          } catch (err) {
            console.error('[DEBUG] loadArticleList 出错:', err);
            listEl.innerHTML = `<p class="text-red-600">加载失败: ${err.message}</p>`;
          }
        }

        async function deleteArticle(url) {
          if (!confirm("确定要删除这篇文章吗？")) {
            return;
          }

          const statusEl = document.getElementById("list-status");
          statusEl.textContent = "正在删除...";
          statusEl.className = "status";

          try {
            const adminCode = getAdminCode();
            const res = await fetch("./delete-article", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Code": adminCode || "",
              },
              body: JSON.stringify({ url: url })
            });
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            const data = await res.json();
            
            if (data.ok) {
              statusEl.textContent = `✅ ${data.message}`;
              statusEl.className = "text-sm text-green-600";
              // 重新加载文章列表和预览
              loadArticleList();
              loadPreview();
            } else {
              statusEl.textContent = `❌ ${data.message || "删除失败"}`;
              statusEl.className = "text-sm text-red-600";
            }
          } catch (err) {
            console.error(err);
            statusEl.textContent = "❌ 请求失败，请查看浏览器控制台或服务器日志。";
            statusEl.className = "status error";
          }
        }

        async function loadPreview() {
          console.log('[DEBUG] loadPreview 开始执行');
          const metaEl = document.getElementById("meta");
          const listEl = document.getElementById("articles");
          const statusEl = document.getElementById("status");
          if (!metaEl || !listEl || !statusEl) {
            console.error("[DEBUG] 预览元素未找到", { metaEl, listEl, statusEl });
            return;
          }
          statusEl.textContent = "";
          listEl.innerHTML = "";
          metaEl.textContent = "加载中...";

          try {
            const adminCode = getAdminCode();
            console.log('[DEBUG] 请求预览数据，URL: ./preview');
            const res = await fetch("./preview", {
              headers: { "X-Admin-Code": adminCode || "" }
            });
            console.log('[DEBUG] 预览响应状态:', res.status, res.statusText);
            
            if (res.status === 401 || res.status === 403) {
              console.log('[DEBUG] 授权失败，状态码:', res.status);
              handleAuthError(statusEl);
              return;
            }

            if (!res.ok) {
              console.error('[DEBUG] 请求失败，状态码:', res.status);
              metaEl.textContent = `请求失败: HTTP ${res.status}`;
              return;
            }

            const data = await res.json();
            console.log('[DEBUG] 预览数据:', data);
            metaEl.textContent = `日期：${data.date} ｜ 主题：${data.theme} ｜ 定时：${String(data.schedule.hour).padStart(2,'0')}:${String(data.schedule.minute).padStart(2,'0')} ｜ 篇数：${data.schedule.count}`;

            if (!data.articles || data.articles.length === 0) {
              console.log('[DEBUG] 预览中没有可用文章');
              listEl.innerHTML = '<p class="text-gray-600">当前配置下没有可用文章，请在服务器的 data/articles/ai_articles.json 中添加。</p>';
              return;
            }

            data.articles.forEach((item, idx) => {
              const div = document.createElement("div");
              div.className = "bg-white rounded-lg p-4 mb-3 border border-gray-200 shadow-sm";
              div.innerHTML = `
                <div class="font-semibold text-gray-900 mb-1">
                  ${idx + 1}. <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-700">${item.title}</a>
                </div>
                <div class="text-xs text-gray-600 mb-1">来源：${item.source}</div>
                <div class="text-sm text-gray-700">${item.summary || ""}</div>
              `;
              listEl.appendChild(div);
            });
            console.log('[DEBUG] 预览加载完成，共', data.articles.length, '篇');
          } catch (err) {
            console.error('[DEBUG] loadPreview 出错:', err);
            metaEl.textContent = `加载失败: ${err.message}`;
          }
        }

        async function addArticle() {
          const urlInput = document.getElementById("article-url");
          const btn = document.getElementById("add-article-btn");
          const statusEl = document.getElementById("add-status");
          const url = urlInput.value.trim();
          
          if (!url) {
            statusEl.textContent = "❌ 请输入文章URL";
            statusEl.className = "status error";
            return;
          }
          
          btn.disabled = true;
          statusEl.textContent = "正在爬取文章信息，请稍候...";
          statusEl.className = "status";
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./add-article", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Code": adminCode || "",
              },
              body: JSON.stringify({ url: url })
            });
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            
            // 检查 HTTP 状态码
            if (!res.ok) {
              let errorText = "未知错误";
              try {
                const errorData = await res.json();
                errorText = errorData.detail || errorData.message || errorText;
              } catch {
                try {
                  errorText = await res.text();
                } catch {
                  errorText = `HTTP ${res.status}`;
                }
              }
              statusEl.textContent = `❌ 服务器错误 (${res.status})：${errorText}`;
              statusEl.className = "text-sm text-red-600";
              return;
            }
            
            const data = await res.json();
            
            if (data.ok) {
              statusEl.textContent = `✅ ${data.message}：${data.article.title}`;
              statusEl.className = "text-sm text-green-600";
              urlInput.value = "";
              // 添加成功后重新加载文章列表和预览
              loadArticleList();
              loadPreview();
            } else {
              statusEl.textContent = `❌ ${data.message || "添加失败"}`;
              statusEl.className = "text-sm text-red-600";
            }
          } catch (err) {
            console.error(err);
            let errorMsg = "❌ 请求失败";
            if (err instanceof TypeError && err.message.includes("fetch")) {
              errorMsg += "：无法连接到服务器，请检查服务是否正常运行";
            } else if (err.message) {
              errorMsg += `：${err.message}`;
            } else {
              errorMsg += "，请查看浏览器控制台或服务器日志";
            }
            statusEl.textContent = errorMsg;
            statusEl.className = "status error";
          } finally {
            btn.disabled = false;
          }
        }

        async function triggerOnce() {
          const btn = document.getElementById("trigger-btn");
          const statusEl = document.getElementById("status");
          btn.disabled = true;
          statusEl.textContent = "正在触发推送，请稍候...";
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./trigger", {
              method: "POST",
              headers: { "X-Admin-Code": adminCode || "" }
            });
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            const data = await res.json();
            if (data.ok) {
              statusEl.textContent = `✅ 已触发一次推送：${data.date} ｜ 主题：${data.theme}`;
              loadArticleList();
              loadCandidateList();
            } else {
              statusEl.textContent = "❌ 推送失败，请查看服务器日志。";
            }
          } catch (err) {
            console.error(err);
            statusEl.textContent = "❌ 请求失败，请查看浏览器控制台或服务器日志。";
          } finally {
            btn.disabled = false;
            // 触发后重新加载预览，保证展示的内容与最近一次一致
            loadPreview();
          }
        }

        document.getElementById("crawl-btn").addEventListener("click", crawlArticles);
        document.getElementById("crawl-tool-article-btn").addEventListener("click", function() {
            const select = document.getElementById("tool-keyword-select");
            const keyword = select ? select.value : null;
            if (!keyword) {
                alert("请先选择工具关键字");
                return;
            }
            crawlToolArticles(keyword);
        });
        document.getElementById("crawl-all-tool-articles-btn").addEventListener("click", function() {
            crawlToolArticles(null);
        });
        document.getElementById("add-article-btn").addEventListener("click", addArticle);
        document.getElementById("article-url").addEventListener("keypress", function(e) {
          if (e.key === "Enter") {
            addArticle();
          }
        });
        document.getElementById("trigger-btn").addEventListener("click", triggerOnce);

        document.getElementById("auth-submit-btn").addEventListener("click", async function () {
          const input = document.getElementById("admin-code-input");
          const statusEl = document.getElementById("auth-status");
          const code = input.value.trim();
          if (!code) {
            statusEl.textContent = "❌ 请输入授权码";
            statusEl.className = "status error";
            return;
          }
          setAdminCode(code);
          hideAuthOverlay();
          await initializePanel();
        });

        document.getElementById("admin-code-input").addEventListener("keypress", function (e) {
          if (e.key === "Enter") {
            document.getElementById("auth-submit-btn").click();
          }
        });

        async function initializePanel() {
          console.log('[DEBUG] initializePanel 开始执行');
          const ok = await ensureAdminCode();
          console.log('[DEBUG] ensureAdminCode 返回:', ok);
          if (!ok) {
            console.log('[DEBUG] 授权码验证失败，停止初始化');
            return;
          }
          console.log('[DEBUG] 开始加载数据...');
          try {
            await Promise.all([
              loadCandidateList(),
              loadToolCandidateList(),
              loadArticleList(),
              loadPreview(),
              loadToolKeywords()
            ]);
            console.log('[DEBUG] 所有数据加载完成');
          } catch (err) {
            console.error('[DEBUG] 数据加载出错:', err);
          }
        }

        // 归档对话框事件绑定
        const archiveModal = document.getElementById("archive-modal");
        const archiveCancelBtn = document.getElementById("archive-cancel-btn");
        const archiveConfirmBtn = document.getElementById("archive-confirm-btn");
        const archiveCategory = document.getElementById("archive-category");

        if (archiveCancelBtn) {
          archiveCancelBtn.addEventListener("click", hideArchiveModal);
        }

        if (archiveConfirmBtn) {
          archiveConfirmBtn.addEventListener("click", function() {
            if (currentArchiveUrl) {
              const category = archiveCategory ? archiveCategory.value : "programming";
              const toolTagsInput = document.getElementById("archive-tool-tags");
              let toolTags = [];
              if (toolTagsInput && toolTagsInput.value.trim()) {
                // 解析工具标签（逗号分隔，去除空格）
                toolTags = toolTagsInput.value.split(',').map(tag => tag.trim()).filter(tag => tag);
              }
              
              // 根据归档来源调用不同的函数
              if (archiveSource === 'article') {
                archiveArticleFromPool(currentArchiveUrl, category, toolTags);
              } else {
                archiveCandidate(currentArchiveUrl, category, toolTags);
              }
            }
          });
        }

        // 点击背景关闭对话框
        if (archiveModal) {
          archiveModal.addEventListener("click", function(e) {
            if (e.target === archiveModal) {
              hideArchiveModal();
            }
          });
        }

        // 配置弹窗基础功能
        const configModal = document.getElementById("config-modal");
        const openConfigBtn = document.getElementById("open-config-btn");
        const closeConfigBtn = document.getElementById("close-config-btn");

        function openConfigModal() {
          if (configModal) {
            configModal.classList.remove("hidden");
            configModal.classList.add("flex");
            switchConfigSection("keywords");
          }
        }

        function closeConfigModal() {
          if (configModal) {
            configModal.classList.add("hidden");
            configModal.classList.remove("flex");
          }
        }

        async function loadKeywordConfig() {
          const textarea = document.getElementById("config-keywords-input");
          const statusEl = document.getElementById("config-keywords-status");
          if (!textarea) return;
          
          if (statusEl) statusEl.textContent = "";
          textarea.value = "";
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./config/keywords", {
              headers: { "X-Admin-Code": adminCode || "" }
            });
            
            if (res.status === 401 || res.status === 403) {
              if (statusEl) {
                statusEl.textContent = "❌ 需要授权";
                statusEl.className = "text-sm text-red-600";
              }
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok && data.keywords) {
              textarea.value = data.keywords.join("\\n");
            } else {
              textarea.value = "AI 编码\\n数字孪生\\nCursor";
            }
          } catch (err) {
            console.error("加载关键词失败:", err);
            textarea.value = "AI 编码\\n数字孪生\\nCursor";
          }
        }

        async function loadScheduleConfig() {
          const cronInput = document.getElementById("schedule-cron");
          const hourInput = document.getElementById("schedule-hour");
          const minuteInput = document.getElementById("schedule-minute");
          const countInput = document.getElementById("schedule-count");
          const maxInput = document.getElementById("schedule-max");
          const statusEl = document.getElementById("config-schedule-status");
          
          if (statusEl) statusEl.textContent = "";
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./config/schedule", {
              headers: { "X-Admin-Code": adminCode || "" }
            });
            
            if (res.status === 401 || res.status === 403) {
              if (statusEl) {
                statusEl.textContent = "❌ 需要授权";
                statusEl.className = "text-sm text-red-600";
              }
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok && data.schedule) {
              const s = data.schedule;
              if (cronInput) cronInput.value = s.cron || "";
              if (hourInput) hourInput.value = s.hour || "";
              if (minuteInput) minuteInput.value = s.minute || "";
              if (countInput) countInput.value = s.count || "";
              if (maxInput) maxInput.value = s.max_articles_per_keyword || "";
            }
          } catch (err) {
            console.error("加载调度配置失败:", err);
          }
        }

        async function loadWecomTemplateConfig() {
          const textarea = document.getElementById("wecom-template-input");
          const statusEl = document.getElementById("config-template-status");
          if (!textarea) return;
          
          if (statusEl) statusEl.textContent = "";
          
          const defaultTemplateObj = {
            "title": "**每日精选通知｜{date}**",
            "theme": "> 今日主题：{theme}",
            "item": {
              "title": "{idx}. [{title}]({url})",
              "source": "   - 来源：{source}",
              "summary": "   - 摘要：{summary}"
            },
            "footer": "> 以上内容每日推送，仅限内部分享。"
          };
          const defaultTemplate = JSON.stringify(defaultTemplateObj, null, 2);
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./config/wecom-template", {
              headers: { "X-Admin-Code": adminCode || "" }
            });
            
            if (res.status === 401 || res.status === 403) {
              if (statusEl) {
                statusEl.textContent = "❌ 需要授权";
                statusEl.className = "text-sm text-red-600";
              }
              textarea.value = defaultTemplate;
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok && data.template) {
              textarea.value = JSON.stringify(data.template, null, 2);
            } else {
              textarea.value = defaultTemplate;
            }
          } catch (err) {
            console.error("加载模板失败:", err);
            textarea.value = defaultTemplate;
          }
        }

        async function loadEnvConfig() {
          const adminCodeInput = document.getElementById("env-admin-code");
          const wecomWebhookInput = document.getElementById("env-wecom-webhook");
          const statusEl = document.getElementById("config-env-status");
          
          if (!adminCodeInput || !wecomWebhookInput) return;
          
          if (statusEl) statusEl.textContent = "";
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./config/env", {
              headers: { "X-Admin-Code": adminCode || "" }
            });
            
            if (res.status === 401 || res.status === 403) {
              if (statusEl) {
                statusEl.textContent = "❌ 需要授权";
                statusEl.className = "text-sm text-red-600";
              }
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok && data.env) {
              adminCodeInput.value = data.env.admin_code || "";
              wecomWebhookInput.value = data.env.wecom_webhook || "";
            }
          } catch (err) {
            console.error("加载系统配置失败:", err);
          }
        }

        async function saveEnvConfig() {
          const adminCodeInput = document.getElementById("env-admin-code");
          const wecomWebhookInput = document.getElementById("env-wecom-webhook");
          const statusEl = document.getElementById("config-env-status");
          
          if (!adminCodeInput || !wecomWebhookInput) return;
          
          const adminCode = adminCodeInput.value.trim();
          const wecomWebhook = wecomWebhookInput.value.trim();
          
          if (!adminCode && !wecomWebhook) {
            if (statusEl) {
              statusEl.textContent = "❌ 请至少填写一项配置";
              statusEl.className = "text-sm text-red-600";
            }
            return;
          }
          
          if (statusEl) {
            statusEl.textContent = "保存中...";
            statusEl.className = "text-sm";
          }
          
          try {
            const currentAdminCode = getAdminCode();
            const res = await fetch("./config/env", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Code": currentAdminCode || ""
              },
              body: JSON.stringify({
                admin_code: adminCode,
                wecom_webhook: wecomWebhook
              })
            });
            
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok) {
              if (statusEl) {
                statusEl.textContent = "✅ 系统配置已保存（需要重启服务后生效）";
                statusEl.className = "text-sm text-green-600";
              }
              // 如果更新了管理员验证码，更新本地存储
              if (adminCode) {
                localStorage.setItem(ADMIN_CODE_KEY, adminCode);
              }
            } else {
              throw new Error(data.message || "保存失败");
            }
          } catch (err) {
            console.error("保存系统配置失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 保存失败: " + err.message;
              statusEl.className = "text-sm text-red-600";
            }
          }
        }

        function switchConfigSection(sectionName) {
          const sections = ["keywords", "schedule", "template", "env"];
          const menuBtns = document.querySelectorAll(".config-menu-btn");
          
          sections.forEach(function(name) {
            const sectionEl = document.getElementById("config-" + name + "-section");
            const btn = document.querySelector('[data-section="' + name + '"]');
            if (sectionEl) {
              if (name === sectionName) {
                sectionEl.classList.remove("hidden");
                sectionEl.classList.add("block");
              } else {
                sectionEl.classList.add("hidden");
                sectionEl.classList.remove("block");
              }
            }
            if (btn) {
              if (name === sectionName) {
                btn.classList.add("is-active");
                btn.classList.remove("bg-gray-50", "text-gray-900");
                btn.classList.add("bg-blue-600", "text-white");
              } else {
                btn.classList.remove("is-active");
                btn.classList.remove("bg-blue-600", "text-white");
                btn.classList.add("bg-gray-50", "text-gray-900");
              }
            }
          });
          
          if (sectionName === "keywords") {
            loadKeywordConfig();
          } else if (sectionName === "schedule") {
            loadScheduleConfig();
          } else if (sectionName === "template") {
            loadWecomTemplateConfig();
          } else if (sectionName === "env") {
            loadEnvConfig();
          }
        }

        if (openConfigBtn) {
          openConfigBtn.addEventListener("click", openConfigModal);
        }
        if (closeConfigBtn) {
          closeConfigBtn.addEventListener("click", closeConfigModal);
        }
        if (configModal) {
          configModal.addEventListener("click", function(event) {
            if (event.target === configModal) {
              closeConfigModal();
            }
          });
        }

        async function saveKeywordConfig() {
          const textarea = document.getElementById("config-keywords-input");
          const statusEl = document.getElementById("config-keywords-status");
          if (!textarea) return;
          
          const keywords = textarea.value.split("\\n").map(function(k) {
            return k.trim();
          }).filter(function(k) {
            return k.length > 0;
          });
          
          if (keywords.length === 0) {
            if (statusEl) {
              statusEl.textContent = "❌ 关键词不能为空";
              statusEl.className = "text-sm text-red-600";
            }
            return;
          }
          
          if (statusEl) {
            statusEl.textContent = "保存中...";
            statusEl.className = "text-sm";
          }
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./config/keywords", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Code": adminCode || ""
              },
              body: JSON.stringify({ keywords: keywords })
            });
            
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok) {
              if (statusEl) {
                statusEl.textContent = "✅ 关键词已保存";
                statusEl.className = "text-sm text-green-600";
              }
            } else {
              throw new Error(data.message || "保存失败");
            }
          } catch (err) {
            console.error("保存关键词失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 保存失败: " + err.message;
              statusEl.className = "text-sm text-red-600";
            }
          }
        }

        async function saveScheduleConfig() {
          const cronInput = document.getElementById("schedule-cron");
          const hourInput = document.getElementById("schedule-hour");
          const minuteInput = document.getElementById("schedule-minute");
          const countInput = document.getElementById("schedule-count");
          const maxInput = document.getElementById("schedule-max");
          const statusEl = document.getElementById("config-schedule-status");
          
          const payload = {};
          if (cronInput && cronInput.value.trim()) {
            payload.cron = cronInput.value.trim();
          }
          if (hourInput && hourInput.value) {
            payload.hour = parseInt(hourInput.value, 10);
          }
          if (minuteInput && minuteInput.value) {
            payload.minute = parseInt(minuteInput.value, 10);
          }
          if (countInput && countInput.value) {
            payload.count = parseInt(countInput.value, 10);
          }
          if (maxInput && maxInput.value) {
            payload.max_articles_per_keyword = parseInt(maxInput.value, 10);
          }
          
          if (Object.keys(payload).length === 0) {
            if (statusEl) {
              statusEl.textContent = "❌ 请至少填写一项配置";
              statusEl.className = "text-sm text-red-600";
            }
            return;
          }
          
          if (statusEl) {
            statusEl.textContent = "保存中...";
            statusEl.className = "text-sm";
          }
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./config/schedule", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Code": adminCode || ""
              },
              body: JSON.stringify(payload)
            });
            
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok) {
              if (statusEl) {
                statusEl.textContent = "✅ 调度配置已保存";
                statusEl.className = "text-sm text-green-600";
              }
            } else {
              throw new Error(data.message || "保存失败");
            }
          } catch (err) {
            console.error("保存调度配置失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 保存失败: " + err.message;
              statusEl.className = "text-sm text-red-600";
            }
          }
        }

        async function saveWecomTemplateConfig() {
          const textarea = document.getElementById("wecom-template-input");
          const statusEl = document.getElementById("config-template-status");
          if (!textarea) return;
          
          let template;
          try {
            template = JSON.parse(textarea.value);
          } catch (err) {
            if (statusEl) {
              statusEl.textContent = "❌ JSON 格式错误: " + err.message;
              statusEl.className = "text-sm text-red-600";
            }
            return;
          }
          
          if (statusEl) {
            statusEl.textContent = "保存中...";
            statusEl.className = "text-sm";
          }
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./config/wecom-template", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Code": adminCode || ""
              },
              body: JSON.stringify({ template: template })
            });
            
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok) {
              if (statusEl) {
                statusEl.textContent = "✅ 企业微信模板已保存";
                statusEl.className = "text-sm text-green-600";
              }
            } else {
              throw new Error(data.message || "保存失败");
            }
          } catch (err) {
            console.error("保存模板失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 保存失败: " + err.message;
              statusEl.className = "text-sm text-red-600";
            }
          }
        }

        document.querySelectorAll(".config-menu-btn").forEach(function(btn) {
          btn.addEventListener("click", function() {
            const section = btn.getAttribute("data-section");
            if (section) {
              switchConfigSection(section);
            }
          });
        });

        document.getElementById("save-keywords-btn").addEventListener("click", saveKeywordConfig);
        document.getElementById("save-schedule-btn").addEventListener("click", saveScheduleConfig);
        document.getElementById("save-template-btn").addEventListener("click", saveWecomTemplateConfig);
        document.getElementById("save-env-btn").addEventListener("click", saveEnvConfig);

        // ========== 微信公众号草稿箱功能已暂时屏蔽 ==========
        // 以下函数暂时屏蔽，但保留代码以便后续启用
        /*
        async function loadDraftsList() {
          const listEl = document.getElementById("drafts-list");
          const statusEl = document.getElementById("drafts-status");
          
          if (!listEl) return;
          
          if (statusEl) statusEl.textContent = "";
          listEl.innerHTML = "加载中...";
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./wechat-mp/drafts?offset=0&count=20", {
              headers: { "X-Admin-Code": adminCode || "" }
            });
            
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              listEl.innerHTML = "<p>需要授权</p>";
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok && data.drafts) {
              if (data.drafts.length === 0) {
                listEl.innerHTML = "<p>草稿箱为空</p>";
                return;
              }
              
              listEl.innerHTML = "";
              data.drafts.forEach(function(draft) {
                const mediaId = draft.media_id || draft.media_id;
                const content = draft.content || {};
                const newsItem = content.news_item || [];
                const createTime = content.create_time ? new Date(content.create_time * 1000).toLocaleString() : "未知";
                
                const draftDiv = document.createElement("div");
                draftDiv.className = "draft-item";
                draftDiv.innerHTML = `
                  <div class="draft-header">
                    <div>
                      <div class="draft-title">草稿 #${mediaId.substring(0, 8)}...</div>
                      <div class="draft-meta">创建时间: ${createTime} | 文章数: ${newsItem.length}</div>
                    </div>
                  </div>
                  <div class="draft-articles">
                    ${newsItem.map(function(article, idx) {
                      const title = (article.title || "无标题").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                      const author = (article.author || "未知").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                      const url = article.content_source_url || "#";
                      return `
                        <div class="draft-article-item">
                          <strong>${idx + 1}. ${title}</strong>
                          <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">
                            作者: ${author} | 
                            <a href="${url}" target="_blank">原文链接</a>
                          </div>
                        </div>
                      `;
                    }).join("")}
                  </div>
                  <div class="draft-actions-btns">
                    <button class="btn-success" data-action="edit" data-media-id="${mediaId}">编辑</button>
                    <button class="btn-primary" data-action="publish" data-media-id="${mediaId}">发布</button>
                    <button class="btn-secondary" data-action="delete" data-media-id="${mediaId}">删除</button>
                  </div>
                `;
                listEl.appendChild(draftDiv);
              });
            } else {
              listEl.innerHTML = "<p>加载失败</p>";
            }
          } catch (err) {
            console.error("加载草稿列表失败:", err);
            listEl.innerHTML = "<p>加载失败: " + err.message + "</p>";
          }
        }

        async function createDraftFromArticles() {
          const statusEl = document.getElementById("drafts-status");
          const articlesData = await fetch("./articles", {
            headers: { "X-Admin-Code": getAdminCode() || "" }
          }).then(r => r.json());
          
          if (!articlesData.ok || !articlesData.articles || articlesData.articles.length === 0) {
            if (statusEl) {
              statusEl.textContent = "❌ 文章池为空，请先添加文章";
              statusEl.className = "text-sm text-red-600";
            }
            return;
          }
          
          // 让用户选择文章（简化版：使用所有文章）
          const articleUrls = articlesData.articles.map(a => a.url);
          
          if (statusEl) {
            statusEl.textContent = "正在创建草稿...";
            statusEl.className = "text-sm";
          }
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch("./wechat-mp/create-draft-from-articles", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Code": adminCode || ""
              },
              body: JSON.stringify({ article_ids: articleUrls })
            });
            
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok) {
              if (statusEl) {
                statusEl.textContent = "✅ " + data.message;
                statusEl.className = "text-sm text-green-600";
              }
              loadDraftsList();
            } else {
              throw new Error(data.message || "创建失败");
            }
          } catch (err) {
            console.error("创建草稿失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 创建失败: " + err.message;
              statusEl.className = "text-sm text-red-600";
            }
          }
        }

        window.editDraft = async function(mediaId) {
          const modal = document.getElementById("draft-edit-modal");
          const contentEl = document.getElementById("draft-edit-content");
          
          if (!modal || !contentEl) return;
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch(`./wechat-mp/draft/${mediaId}`, {
              headers: { "X-Admin-Code": adminCode || "" }
            });
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok && data.draft) {
              const draft = data.draft;
              const newsItem = draft.news_item || [];
              
              if (newsItem.length === 0) {
                contentEl.innerHTML = "<p>草稿中没有文章</p>";
                modal.classList.add("is-visible");
                return;
              }
              
              // 使用 DOM 方法创建元素，避免转义问题
              contentEl.innerHTML = "";
              newsItem.forEach(function(article, idx) {
                const formDiv = document.createElement("div");
                formDiv.className = "draft-edit-form";
                
                const h3 = document.createElement("h3");
                h3.textContent = "文章 " + (idx + 1);
                formDiv.appendChild(h3);
                
                // 标题（限制 20 个字符）
                const titleLabel = document.createElement("label");
                titleLabel.textContent = "标题（20字以内）";
                formDiv.appendChild(titleLabel);
                const titleInput = document.createElement("input");
                titleInput.type = "text";
                titleInput.id = "draft-title-" + idx;
                titleInput.value = article.title || "";
                titleInput.placeholder = "标题（20字以内）";
                titleInput.maxLength = 20;  // HTML5 最大长度限制
                // 添加实时字符计数提示
                const titleCounter = document.createElement("div");
                titleCounter.id = "draft-title-counter-" + idx;
                titleCounter.style.cssText = "font-size: 12px; color: #6b7280; margin-top: -10px; margin-bottom: 12px;";
                titleCounter.textContent = `已输入 ${(article.title || "").length} / 20 字符`;
                formDiv.appendChild(titleInput);
                formDiv.appendChild(titleCounter);
                // 监听输入变化，更新字符计数
                titleInput.addEventListener("input", function() {
                  const length = this.value.length;
                  titleCounter.textContent = `已输入 ${length} / 20 字符`;
                  if (length > 20) {
                    titleCounter.style.color = "#ef4444";
                  } else {
                    titleCounter.style.color = "#6b7280";
                  }
                });
                
                // 作者
                const authorLabel = document.createElement("label");
                authorLabel.textContent = "作者";
                formDiv.appendChild(authorLabel);
                const authorInput = document.createElement("input");
                authorInput.type = "text";
                authorInput.id = "draft-author-" + idx;
                authorInput.value = article.author || "";
                authorInput.placeholder = "作者";
                formDiv.appendChild(authorInput);
                
                // 内容（HTML编辑器）
                const contentLabel = document.createElement("label");
                contentLabel.textContent = "内容（HTML格式）";
                formDiv.appendChild(contentLabel);
                
                // 工具栏
                const toolbar = document.createElement("div");
                toolbar.style.cssText = "margin-bottom: 8px; padding: 8px; background: #f5f5f5; border-radius: 4px; display: flex; gap: 8px; flex-wrap: wrap;";
                toolbar.innerHTML = `
                  <button type="button" class="html-editor-btn" data-command="bold" title="粗体">B</button>
                  <button type="button" class="html-editor-btn" data-command="italic" title="斜体">I</button>
                  <button type="button" class="html-editor-btn" data-command="underline" title="下划线">U</button>
                  <button type="button" class="html-editor-btn" data-command="formatBlock" data-value="p" title="段落">P</button>
                  <button type="button" class="html-editor-btn" data-command="insertUnorderedList" title="无序列表">•</button>
                  <button type="button" class="html-editor-btn" data-command="insertOrderedList" title="有序列表">1.</button>
                `;
                formDiv.appendChild(toolbar);
                
                // HTML 编辑器（contenteditable div）
                const contentEditor = document.createElement("div");
                contentEditor.id = "draft-content-" + idx;
                contentEditor.contentEditable = true;
                contentEditor.style.cssText = "min-height: 200px; padding: 12px; border: 1px solid #d1d5db; border-radius: 4px; background: #fff; outline: none;";
                contentEditor.innerHTML = article.content || "";  // 直接设置 HTML 内容
                formDiv.appendChild(contentEditor);
                
                // 为工具栏按钮绑定事件
                toolbar.querySelectorAll(".html-editor-btn").forEach(function(btn) {
                  btn.addEventListener("click", function(e) {
                    e.preventDefault();
                    const command = this.getAttribute("data-command");
                    const value = this.getAttribute("data-value");
                    contentEditor.focus();
                    document.execCommand(command, false, value || null);
                  });
                });
                
                contentEl.appendChild(formDiv);
              });
              
              contentEl.innerHTML += `
                <div class="form-actions" style="margin-top: 20px;">
                  <button class="btn-success" data-save-draft="${mediaId}">保存修改</button>
                  <button class="btn-secondary" onclick="closeDraftEdit()">取消</button>
                </div>
              `;
              
              // 绑定保存按钮
              const saveBtn = contentEl.querySelector(`[data-save-draft="${mediaId}"]`);
              if (saveBtn) {
                saveBtn.addEventListener("click", function() {
                  saveDraftEdit(mediaId);
                });
              }
              
              modal.classList.add("is-visible");
            }
          } catch (err) {
            console.error("加载草稿详情失败:", err);
            alert("加载草稿详情失败: " + err.message);
          }
        }

        window.saveDraftEdit = async function(mediaId) {
          const contentEl = document.getElementById("draft-edit-content");
          if (!contentEl) return;
          
          const forms = contentEl.querySelectorAll(".draft-edit-form");
          const articles = [];
          
          forms.forEach(function(form, idx) {
            let title = document.getElementById(`draft-title-${idx}`).value.trim();
            const author = document.getElementById(`draft-author-${idx}`).value;
            // 从 contenteditable div 获取 HTML 内容
            const contentEditor = document.getElementById(`draft-content-${idx}`);
            const content = contentEditor ? contentEditor.innerHTML : "";
            
            // 确保标题在 20 个字符以内
            const maxTitleLength = 20;
            if (title.length > maxTitleLength) {
              // 尝试在合适的位置截断（优先在标点符号、空格处）
              let truncated = title.substring(0, maxTitleLength);
              // 查找最后一个标点符号或空格的位置（在截断范围内）
              const separators = ['。', '，', '、', '：', '；', '！', '？', ' ', '·', '-', '—', '–'];
              for (let i = 0; i < separators.length; i++) {
                const sep = separators[i];
                const lastSepPos = truncated.lastIndexOf(sep);
                if (lastSepPos > maxTitleLength * 0.6) {  // 至少保留 60% 的内容
                  truncated = truncated.substring(0, lastSepPos);
                  break;
                }
              }
              title = truncated;
              console.log(`标题已缩减: ${document.getElementById(`draft-title-${idx}`).value} -> ${title}`);
            }
            
            articles.push({
              title: title,
              author: author,
              content: content,
              // 不包含 content_source_url 和 digest
              thumb_media_id: "",
              show_cover_pic: 1,
            });
          });
          
          try {
            const adminCode = getAdminCode();
            // 更新每篇文章
            for (let i = 0; i < articles.length; i++) {
              const res = await fetch(`./wechat-mp/draft/${mediaId}/update`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "X-Admin-Code": adminCode || ""
                },
                body: JSON.stringify({
                  index: i,
                  article: articles[i]
                })
              });
              
              if (!res.ok) {
                throw new Error("更新失败");
              }
            }
            
            alert("草稿更新成功！");
            closeDraftEdit();
            loadDraftsList();
          } catch (err) {
            console.error("保存草稿失败:", err);
            alert("保存失败: " + err.message);
          }
        }

        window.closeDraftEdit = function() {
          const modal = document.getElementById("draft-edit-modal");
          if (modal) {
            modal.classList.remove("is-visible");
          }
        }

        window.publishDraft = async function(mediaId) {
          if (!confirm("确定要发布这个草稿吗？")) {
            return;
          }
          
          const statusEl = document.getElementById("drafts-status");
          if (statusEl) {
            statusEl.textContent = "正在发布...";
            statusEl.className = "text-sm";
          }
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch(`./wechat-mp/publish`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Code": adminCode || ""
              },
              body: JSON.stringify({ media_id: mediaId })
            });
            
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok) {
              if (statusEl) {
                statusEl.textContent = "✅ 发布成功！";
                statusEl.className = "text-sm text-green-600";
              }
              loadDraftsList();
            } else {
              throw new Error(data.message || "发布失败");
            }
          } catch (err) {
            console.error("发布草稿失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 发布失败: " + err.message;
              statusEl.className = "text-sm text-red-600";
            }
          }
        }

        window.deleteDraft = async function(mediaId) {
          if (!confirm("确定要删除这个草稿吗？")) {
            return;
          }
          
          try {
            const adminCode = getAdminCode();
            const res = await fetch(`./wechat-mp/draft/${mediaId}/delete`, {
              method: "POST",
              headers: { "X-Admin-Code": adminCode || "" }
            });
            
            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }
            
            const data = await res.json();
            if (data.ok) {
              loadDraftsList();
            } else {
              throw new Error(data.message || "删除失败");
            }
          } catch (err) {
            console.error("删除草稿失败:", err);
            alert("删除失败: " + err.message);
          }
        }

        // 绑定草稿箱按钮事件
        const createDraftBtn = document.getElementById("create-draft-btn");
        const refreshDraftsBtn = document.getElementById("refresh-drafts-btn");
        const closeDraftEditBtn = document.getElementById("close-draft-edit-btn");
        const draftEditModal = document.getElementById("draft-edit-modal");
        
        if (createDraftBtn) {
          createDraftBtn.addEventListener("click", createDraftFromArticles);
        }
        if (refreshDraftsBtn) {
          refreshDraftsBtn.addEventListener("click", loadDraftsList);
        }
        if (closeDraftEditBtn) {
          closeDraftEditBtn.addEventListener("click", closeDraftEdit);
        }
        if (draftEditModal) {
          draftEditModal.addEventListener("click", function(event) {
            if (event.target.id === "draft-edit-modal") {
              closeDraftEdit();
            }
          });
        }
        
        // 使用事件委托处理草稿操作按钮
        const draftsList = document.getElementById("drafts-list");
        if (draftsList) {
          draftsList.addEventListener("click", function(event) {
            const btn = event.target;
            if (btn.hasAttribute("data-action")) {
              const action = btn.getAttribute("data-action");
              const mediaId = btn.getAttribute("data-media-id");
              if (action === "edit") {
                editDraft(mediaId);
              } else if (action === "publish") {
                publishDraft(mediaId);
              } else if (action === "delete") {
                deleteDraft(mediaId);
              }
            }
          });
        }

        // 加载草稿列表（已屏蔽）
        // loadDraftsList();
        */
        
        // 初始加载：检查是否已有授权码，没有则弹出对话框
        console.log('[DEBUG] 脚本开始执行');
        
        // 确保 DOM 加载完成后再执行
        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', function() {
            console.log('[DEBUG] DOM 加载完成，开始初始化面板');
            initializePanel();
          });
        } else {
          console.log('[DEBUG] DOM 已就绪，立即初始化面板');
          initializePanel();
        }
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


