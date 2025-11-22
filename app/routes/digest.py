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

from ..config_loader import (
    load_digest_schedule,
    load_crawler_keywords,
    save_crawler_keywords,
    save_digest_schedule,
    load_wecom_template,
    save_wecom_template,
    load_env_var,
    save_env_var,
)
from ..notifier.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from ..notifier.wechat_mp import WeChatMPClient
from ..sources.ai_articles import (
    clear_articles,
    delete_article_from_config,
    get_all_articles,
    pick_daily_ai_articles,
    save_article_to_config,
    todays_theme,
)
from ..sources.article_sources import fetch_from_all_sources
from ..crawlers.rss import fetch_rss_articles
from ..crawlers.github_trending import fetch_github_trending
from ..crawlers.hackernews import fetch_hackernews_articles
from ..sources.article_crawler import fetch_article_info
from ..crawlers.sogou_wechat import search_articles_by_keyword
from ..sources.ai_candidates import (
    add_candidates_to_pool,
    clear_candidate_pool,
    load_candidate_pool,
    promote_candidates_to_articles,
    save_candidate_pool,
)
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
    digest = _build_digest()
    content = build_wecom_digest_markdown(
        date_str=digest["date"],
        theme=digest["theme"],
        items=digest["articles"],
    )
    if not digest["articles"]:
        raise HTTPException(status_code=400, detail="文章池为空，请先添加或抓取文章。")

    logger.info("Manual trigger: sending digest to WeCom group...")
    await send_markdown_to_wecom(content)
    _clear_content_pools()
    return {"ok": True, **digest}


@router.get("/articles")
async def list_all_articles(admin: None = Depends(_require_admin)):
    """
    获取配置文件中所有文章列表。
    
    Returns:
        dict: 包含所有文章的列表
    """
    articles = get_all_articles()
    return {"ok": True, "articles": articles}


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
        grouped_candidates[keyword].append(asdict(candidate))

    return {"ok": True, "grouped_candidates": grouped_candidates}


@router.post("/accept-candidate")
async def accept_candidate(request: CandidateActionRequest, admin: None = Depends(_require_admin)):
    """采纳一篇文章，从候选池移动到正式文章池"""
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")

    candidates = load_candidate_pool()
    
    article_to_accept = None
    remaining_candidates = []
    for candidate in candidates:
        if candidate.url == url:
            article_to_accept = {
                "title": candidate.title,
                "url": candidate.url,
                "source": candidate.source,
                "summary": candidate.summary,
            }
        else:
            remaining_candidates.append(candidate)

    if not article_to_accept:
        raise HTTPException(status_code=404, detail="在候选池中未找到该文章")

    # 1. 从候选池中移除
    save_candidate_pool(remaining_candidates)
    
    # 2. 添加到正式文章池
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


@router.post("/crawl-articles")
async def crawl_articles(admin: None = Depends(_require_admin)):
    """
    触发一次文章抓取任务。

    - 从 `config/crawler_keywords.json` 读取关键词。
    - 使用搜狗微信搜索爬虫抓取文章。
    - 对比现有文章池和候选池，进行去重。
    - 将新文章存入候选池 `data/ai_candidates.json`。
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
    从配置文件中删除指定URL的文章。
    
    Args:
        request: 包含文章URL的请求体
        
    Returns:
        dict: 包含成功状态的响应
    """
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")
    
    try:
        success = delete_article_from_config(url)
        if not success:
            return {
                "ok": False,
                "message": "文章不存在或删除失败",
            }
        
        return {
            "ok": True,
            "message": "文章已成功删除",
        }
    except Exception as e:
        logger.error(f"删除文章失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文章失败: {str(e)}")


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
    <title>每日新闻管理面板</title>
      <style>
        body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f5f5f7; color: #111827; }
        h1 { font-size: 24px; margin-bottom: 8px; }
        h2 { font-size: 18px; margin-top: 24px; margin-bottom: 12px; }
        .meta { margin-bottom: 16px; color: #6b7280; }
        button { padding: 8px 16px; border-radius: 999px; border: none; cursor: pointer; background: #2563eb; color: #fff; font-size: 14px; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .add-article-form { background: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 24px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; margin-bottom: 4px; font-size: 13px; font-weight: 500; color: #374151; }
        .form-group input { width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; box-sizing: border-box; }
        .form-group input:focus { outline: none; border-color: #2563eb; }
        .form-actions { display: flex; gap: 8px; }
        .btn-secondary { background: #6b7280; }
        .btn-danger { background: #dc2626; font-size: 12px; padding: 6px 12px; }
        .btn-danger:hover { background: #b91c1c; }
        .articles { margin-top: 16px; }
        .article { background: #ffffff; border-radius: 12px; padding: 12px 16px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); position: relative; }
        .article-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px; }
        .article-title { font-weight: 600; margin-bottom: 4px; flex: 1; }
        .article-actions { display: flex; gap: 8px; }
        .article-meta { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
        .article-summary { font-size: 13px; color: #374151; }
        .status { margin-top: 12px; font-size: 13px; }
        .status.success { color: #059669; }
        .status.error { color: #dc2626; }
        a { color: #2563eb; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .top-bar-links { font-size: 13px; color: #6b7280; }
        .top-bar-links a { color: #2563eb; }
        .btn-success { background: #16a34a; font-size: 12px; padding: 6px 12px; }
        .btn-success:hover { background: #15803d; }
        .auth-overlay {
          position: fixed;
          inset: 0;
          background: rgba(15,23,42,0.65);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 50;
        }
        .auth-dialog {
          width: 320px;
          background: #ffffff;
          border-radius: 16px;
          padding: 20px 18px 16px;
          box-shadow: 0 18px 45px rgba(15,23,42,0.35);
        }
        .auth-dialog h2 {
          margin: 0 0 8px;
          font-size: 18px;
        }
        .auth-dialog p {
          margin: 0 0 12px;
          font-size: 13px;
          color: #6b7280;
        }
        .auth-dialog input {
          width: 100%;
          padding: 8px 12px;
          border-radius: 8px;
          border: 1px solid #d1d5db;
          font-size: 14px;
          box-sizing: border-box;
        }
        .auth-dialog input:focus {
          outline: none;
          border-color: #2563eb;
        }
        .auth-actions {
          margin-top: 12px;
          display: flex;
          justify-content: flex-end;
          gap: 8px;
        }
        .config-btn {
          border-radius: 999px;
          padding: 6px 16px;
          font-weight: 600;
          background: #2563eb;
          color: #fff;
          border: none;
          cursor: pointer;
          font-size: 14px;
        }
        .config-modal {
          display: none;
          position: fixed;
          inset: 0;
          background: rgba(15, 23, 42, 0.45);
          align-items: center;
          justify-content: center;
          z-index: 60;
        }
        .config-modal.is-visible {
          display: flex;
        }
        .config-modal-content {
          width: min(980px, 95vw);
          max-height: 90vh;
          overflow-y: auto;
          background: #fff;
          border-radius: 20px;
          padding: 24px;
          box-shadow: 0 25px 45px rgba(15, 23, 42, 0.25);
          position: relative;
        }
        .config-modal-close {
          position: absolute;
          top: 14px;
          right: 18px;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          border: none;
          background: #f4f5f7;
          color: #1d4ed8;
          font-size: 18px;
          cursor: pointer;
        }
        .config-menu {
          display: flex;
          gap: 8px;
          margin-bottom: 20px;
        }
        .config-menu-btn {
          flex: 1;
          padding: 8px 12px;
          border-radius: 8px;
          border: 1px solid #d1d5db;
          background: #f8fafc;
          color: #111827;
          cursor: pointer;
          font-size: 14px;
        }
        .config-menu-btn.is-active {
          background: #2563eb;
          color: #fff;
          border-color: #2563eb;
        }
        .config-section {
          display: none;
        }
        .config-section.is-active {
          display: block;
        }
        .config-textarea {
          width: 100%;
          min-height: 150px;
          padding: 8px 12px;
          border-radius: 8px;
          border: 1px solid #d1d5db;
          font-size: 13px;
          font-family: monospace;
          resize: vertical;
          box-sizing: border-box;
        }
        .config-note {
          margin-top: 8px;
          font-size: 12px;
          color: #6b7280;
          line-height: 1.5;
        }
        .form-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
        }
        .form-grid input {
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          box-sizing: border-box;
        }
        .draft-actions {
          display: flex;
          gap: 10px;
          margin-bottom: 12px;
        }
        .drafts-list {
          margin-top: 16px;
        }
        .draft-item {
          background: #ffffff;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 12px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          border: 1px solid #e5e7eb;
        }
        .draft-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .draft-title {
          font-weight: 600;
          font-size: 16px;
          color: #111827;
        }
        .draft-meta {
          font-size: 12px;
          color: #6b7280;
          margin-top: 4px;
        }
        .draft-articles {
          margin-top: 12px;
        }
        .draft-article-item {
          padding: 8px;
          background: #f9fafb;
          border-radius: 6px;
          margin-bottom: 8px;
        }
        .draft-article-item strong {
          color: #111827;
        }
        .draft-actions-btns {
          display: flex;
          gap: 8px;
          margin-top: 12px;
        }
        .draft-modal {
          display: none;
          position: fixed;
          inset: 0;
          background: rgba(15, 23, 42, 0.45);
          align-items: center;
          justify-content: center;
          z-index: 70;
        }
        .draft-modal.is-visible {
          display: flex;
        }
        .draft-modal-content {
          width: min(800px, 95vw);
          max-height: 90vh;
          overflow-y: auto;
          background: #fff;
          border-radius: 20px;
          padding: 24px;
          box-shadow: 0 25px 45px rgba(15, 23, 42, 0.25);
          position: relative;
        }
        .draft-edit-form {
          margin-top: 16px;
        }
        .draft-edit-form input,
        .draft-edit-form textarea {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          box-sizing: border-box;
          margin-bottom: 12px;
        }
        .draft-edit-form textarea {
          min-height: 100px;
          font-family: inherit;
        }
        .html-editor-btn {
          padding: 6px 12px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          background: #fff;
          cursor: pointer;
          font-size: 14px;
          font-weight: bold;
          color: #374151;
        }
        .html-editor-btn:hover {
          background: #f3f4f6;
          border-color: #9ca3af;
        }
        .html-editor-btn:active {
          background: #e5e7eb;
        }
        [contenteditable="true"] {
          outline: none;
        }
        [contenteditable="true"]:focus {
          border-color: #2563eb;
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
      </style>
    </head>
    <body>
      <div class="top-bar">
        <h1>每日新闻精选 · 管理员面板</h1>
        <div class="top-bar-links">
          开源仓库：
          <a href="https://github.com/yunlongwen/100kwhy_wechat_mp" target="_blank" rel="noopener noreferrer">
            github.com/yunlongwen/100kwhy_wechat_mp
          </a>
        </div>
        <button class="config-btn" id="open-config-btn">配置管理</button>
      </div>
      
      <h2>添加文章</h2>
      <div class="add-article-form">
        <div class="form-group">
          <label for="article-url">文章URL：</label>
          <input type="url" id="article-url" placeholder="粘贴文章链接，例如：https://mp.weixin.qq.com/s/..." />
        </div>
        <div class="form-actions">
          <button id="add-article-btn">添加文章</button>
        </div>
        <div class="status" id="add-status"></div>
      </div>

      <h2>文章抓取与候选池</h2>
      <div class="add-article-form">
        <div class="form-actions">
          <button id="crawl-btn">开始自动抓取</button>
        </div>
        <div class="status" id="crawl-status"></div>
        <div class="articles" id="candidate-list">加载中...</div>
      </div>

      <h2>文章列表</h2>
      <div class="add-article-form">
        <div class="status" id="list-status"></div>
        <div class="articles" id="article-list">加载中...</div>
      </div>

      <h2>预览 & 推送</h2>
      <div class="meta" id="meta">加载中...</div>
      <div id="articles"></div>
      <button id="trigger-btn">手动触发一次推送到企业微信群</button>
      <div class="status" id="status"></div>

      <!-- 微信公众号草稿箱功能已暂时屏蔽 -->
      <!--
      <h2>微信公众号草稿箱</h2>
      <div class="draft-actions">
        <button id="create-draft-btn" class="btn-success">从文章池创建草稿</button>
        <button id="refresh-drafts-btn" class="btn-secondary">刷新草稿列表</button>
      </div>
      <div class="status" id="drafts-status"></div>
      <div class="drafts-list" id="drafts-list">加载中...</div>
      -->



      <div class="auth-overlay" id="auth-overlay" style="display: none;">
        <div class="auth-dialog">
          <h2>输入授权码</h2>
          <p>仅限管理员访问。请填写授权码后进入面板。</p>
          <input type="password" id="admin-code-input" placeholder="授权码" />
          <div class="status" id="auth-status"></div>
          <div class="auth-actions">
            <button class="btn" id="auth-submit-btn">确认</button>
          </div>
        </div>
      </div>

      <div class="config-modal" id="config-modal">
        <div class="config-modal-content">
          <button class="config-modal-close" id="close-config-btn">&times;</button>
          <h2>配置管理</h2>
          <div class="config-menu">
            <button class="config-menu-btn is-active" data-section="keywords">关键词</button>
            <button class="config-menu-btn" data-section="schedule">调度</button>
            <button class="config-menu-btn" data-section="template">企业微信模板</button>
            <button class="config-menu-btn" data-section="env">系统配置</button>
          </div>

          <div id="config-keywords-section" class="config-section is-active">
            <div class="form-group">
              <label for="config-keywords-input">关键词（每行一个）</label>
              <textarea id="config-keywords-input" class="config-textarea" placeholder="例如：&#10;AI 编码&#10;数字孪生"></textarea>
              <p class="config-note">一行一个关键词，支持中文与英文。保存后下一次抓取会自动生效。</p>
            </div>
            <div class="form-actions">
              <button class="btn-success" id="save-keywords-btn">保存关键词</button>
            </div>
            <div class="status" id="config-keywords-status"></div>
          </div>

          <div id="config-schedule-section" class="config-section">
            <div class="form-group">
              <label>调度方式</label>
              <div class="form-grid">
                <input type="text" id="schedule-cron" placeholder="Cron 表达式（可选）" />
                <input type="number" id="schedule-hour" min="0" max="23" placeholder="小时" />
                <input type="number" id="schedule-minute" min="0" max="59" placeholder="分钟" />
              </div>
              <p class="config-note">
                • <strong>Cron 表达式</strong>（推荐）：5 字段格式，例如 <code>0 14 * * *</code> 表示每天 14:00 执行<br />
                • <strong>小时 + 分钟</strong>：仅在未设置 Cron 时生效，例如 14:00 表示每天下午 2 点
              </p>
            </div>
            <div class="form-group">
              <label>数量控制</label>
              <div class="form-grid">
                <input type="number" id="schedule-count" min="1" placeholder="推送篇数" />
                <input type="number" id="schedule-max" min="1" placeholder="每关键词最大篇数" />
              </div>
              <p class="config-note">
                • <strong>推送篇数</strong>：每期推送的文章总数<br />
                • <strong>每关键词最大篇数</strong>：每个关键词最多抓取的文章数量
              </p>
            </div>
            <div class="form-actions">
              <button class="btn-success" id="save-schedule-btn">保存调度</button>
            </div>
            <div class="status" id="config-schedule-status"></div>
          </div>

          <div id="config-template-section" class="config-section">
            <div class="form-group">
              <label for="wecom-template-input">企业微信模板（JSON 格式）</label>
              <textarea id="wecom-template-input" class="config-textarea"></textarea>
              <p class="config-note">
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
            <div class="form-actions">
              <button class="btn-success" id="save-template-btn">保存模板</button>
            </div>
            <div class="status" id="config-template-status"></div>
          </div>

          <div id="config-env-section" class="config-section">
            <div class="form-group">
              <label for="env-admin-code">管理员验证码</label>
              <input type="password" id="env-admin-code" class="config-textarea" style="min-height: auto; height: auto;" placeholder="用于保护管理面板的授权码" />
              <p class="config-note">设置后访问管理面板时需要输入此验证码。留空则不设置验证码（不推荐）。</p>
            </div>
            <div class="form-group">
              <label for="env-wecom-webhook">企业微信推送地址</label>
              <input type="text" id="env-wecom-webhook" class="config-textarea" style="min-height: auto; height: auto;" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY" />
              <p class="config-note">企业微信群机器人的 Webhook URL。在企业微信群中添加机器人后获取。</p>
            </div>
            <div class="form-actions">
              <button class="btn-success" id="save-env-btn">保存系统配置</button>
            </div>
            <div class="status" id="config-env-status"></div>
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

      <script>
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
          const overlay = document.getElementById("auth-overlay");
          const input = document.getElementById("admin-code-input");
          const statusEl = document.getElementById("auth-status");
          overlay.style.display = "flex";
          statusEl.textContent = "";
          statusEl.className = "status";
          input.value = "";
          input.focus();
        }

        function hideAuthOverlay() {
          const overlay = document.getElementById("auth-overlay");
          overlay.style.display = "none";
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
          let code = getAdminCode();
          if (!code) {
            showAuthOverlay();
            return false;
          }
          return true;
        }

        async function crawlArticles() {
            const btn = document.getElementById("crawl-btn");
            const statusEl = document.getElementById("crawl-status");

            btn.disabled = true;
            statusEl.textContent = "正在从网络抓取文章，请稍候...（可能需要几十秒）";
            statusEl.className = "status";

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
                    statusEl.className = "status success";
                    loadCandidateList(); // Refresh the list
                    loadCandidateList(); // Refresh the list
                } else {
                    statusEl.textContent = `❌ ${data.message || "抓取失败"}`;
                    statusEl.className = "status error";
                }
            } catch (err) {
                console.error(err);
                statusEl.textContent = "❌ 请求失败，请查看浏览器控制台或服务器日志。";
                statusEl.className = "status error";
            } finally {
                btn.disabled = false;
            }
        }

        async function loadCandidateList() {
            const listEl = document.getElementById("candidate-list");
            const statusEl = document.getElementById("crawl-status");
            listEl.innerHTML = "加载中...";

            try {
                const adminCode = getAdminCode();
                const res = await fetch(`./candidates?_t=${Date.now()}`, {
                    headers: { "X-Admin-Code": adminCode || "" }
                });

                if (res.status === 401 || res.status === 403) {
                    handleAuthError(statusEl);
                    return;
                }

                const data = await res.json();
                if (!data.ok || !data.grouped_candidates || Object.keys(data.grouped_candidates).length === 0) {
                    listEl.innerHTML = "<p>当前没有待审核的文章。</p>";
                    return;
                }

                listEl.innerHTML = "";
                Object.keys(data.grouped_candidates).forEach(keyword => {
                    const articles = data.grouped_candidates[keyword];
                    const groupContainer = document.createElement("div");
                    
                    const groupTitle = document.createElement("h3");
                    const keywordEscaped = keyword.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                    groupTitle.innerHTML = `关键词: ${keywordEscaped} <span class="article-count">(${articles.length}篇)</span>`;
                    groupContainer.appendChild(groupTitle);

                    articles.forEach((item, idx) => {
                        const div = document.createElement("div");
                        div.className = "article";
                        const urlEscaped = item.url.replace(/'/g, "&#39;").replace(/"/g, "&quot;");
                        const titleEscaped = (item.title || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const sourceEscaped = (item.source || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const summaryEscaped = (item.summary || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");

                        div.innerHTML = `
                            <div class="article-header">
                              <div class="article-title">
                                ${idx + 1}. <a href="${item.url}" target="_blank" rel="noopener noreferrer">${titleEscaped}</a>
                              </div>
                              <div class="article-actions">
                                <button class="btn-success" data-url="${urlEscaped}">采纳</button>
                                <button class="btn-secondary" data-url="${urlEscaped}">忽略</button>
                              </div>
                            </div>
                            <div class="article-meta">来源：${sourceEscaped}</div>
                            <div class="article-summary">${summaryEscaped}</div>
                        `;
                        
                        div.querySelector(".btn-success").addEventListener("click", () => acceptCandidate(item.url));
                        div.querySelector(".btn-secondary").addEventListener("click", () => rejectCandidate(item.url));

                        groupContainer.appendChild(div);
                    });
                    listEl.appendChild(groupContainer);
                });
            } catch (err) {
                console.error(err);
                listEl.innerHTML = "<p>加载候选文章失败，请检查服务是否正常运行。</p>";
            }
        }

        async function acceptCandidate(url) {
            const statusEl = document.getElementById("crawl-status");
            statusEl.textContent = "正在采纳文章...";
            statusEl.className = "status";

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
                    statusEl.className = "status success";
                    loadCandidateList();
                    loadArticleList();
                    loadPreview();
                } else {
                    statusEl.textContent = `❌ ${data.message || "采纳失败"}`;
                    statusEl.className = "status error";
                }
            } catch (err) {
                console.error(err);
                statusEl.textContent = "❌ 请求失败，请查看浏览器控制台。";
                statusEl.className = "status error";
            }
        }

        async function rejectCandidate(url) {
            const statusEl = document.getElementById("crawl-status");
            statusEl.textContent = "正在忽略文章...";
            statusEl.className = "status";

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
                    statusEl.className = "status success";
                    loadCandidateList();
                    loadPreview();
                } else {
                    statusEl.textContent = `❌ ${data.message || "忽略失败"}`;
                    statusEl.className = "status error";
                }
            } catch (err) {
                console.error(err);
                statusEl.textContent = "❌ 请求失败，请查看浏览器控制台。";
                statusEl.className = "status error";
            }
        }

        async function loadArticleList() {
          const listEl = document.getElementById("article-list");
          const statusEl = document.getElementById("list-status");
          statusEl.textContent = "";
          listEl.innerHTML = "加载中...";

          try {
            const adminCode = getAdminCode();
            const res = await fetch("./articles", {
              headers: { "X-Admin-Code": adminCode || "" },
            });

            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }

            const data = await res.json();
            
            if (!data.ok || !data.articles || data.articles.length === 0) {
              listEl.innerHTML = "<p>当前没有已配置的文章。</p>";
              return;
            }

            listEl.innerHTML = "";
            data.articles.forEach((item, idx) => {
              const div = document.createElement("div");
              div.className = "article";
              const urlEscaped = item.url.replace(/'/g, "&#39;").replace(/"/g, "&quot;");
              const titleEscaped = (item.title || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
              const sourceEscaped = (item.source || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
              const summaryEscaped = (item.summary || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
              div.innerHTML = `
                <div class="article-header">
                  <div class="article-title">
                    ${idx + 1}. <a href="${item.url}" target="_blank" rel="noopener noreferrer">${titleEscaped}</a>
                  </div>
                  <div class="article-actions">
                    <button class="btn-danger" data-url="${urlEscaped}">删除</button>
                  </div>
                </div>
                <div class="article-meta">来源：${sourceEscaped}</div>
                <div class="article-summary">${summaryEscaped}</div>
              `;
              // 绑定删除按钮事件
              const deleteBtn = div.querySelector(".btn-danger");
              deleteBtn.addEventListener("click", function() {
                deleteArticle(item.url);
              });
              listEl.appendChild(div);
            });
          } catch (err) {
            console.error(err);
            listEl.innerHTML = "<p>加载失败，请检查服务是否正常运行。</p>";
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
              statusEl.className = "status success";
              // 重新加载文章列表和预览
              loadArticleList();
              loadPreview();
            } else {
              statusEl.textContent = `❌ ${data.message || "删除失败"}`;
              statusEl.className = "status error";
            }
          } catch (err) {
            console.error(err);
            statusEl.textContent = "❌ 请求失败，请查看浏览器控制台或服务器日志。";
            statusEl.className = "status error";
          }
        }

        async function loadPreview() {
          const metaEl = document.getElementById("meta");
          const listEl = document.getElementById("articles");
          const statusEl = document.getElementById("status");
          if (!metaEl || !listEl || !statusEl) {
            console.error("预览元素未找到");
            return;
          }
          statusEl.textContent = "";
          listEl.innerHTML = "";
          metaEl.textContent = "加载中...";

          try {
            const adminCode = getAdminCode();
            const res = await fetch("./preview", {
              headers: { "X-Admin-Code": adminCode || "" }
            });
            if (res.status === 401 || res.status === 403) {
              handleAuthError(statusEl);
              return;
            }
            const data = await res.json();
            metaEl.textContent = `日期：${data.date} ｜ 主题：${data.theme} ｜ 定时：${String(data.schedule.hour).padStart(2,'0')}:${String(data.schedule.minute).padStart(2,'0')} ｜ 篇数：${data.schedule.count}`;

            if (!data.articles || data.articles.length === 0) {
              listEl.innerHTML = "<p>当前配置下没有可用文章，请在服务器的 data/ai_articles.json 中添加。</p>";
              return;
            }

            data.articles.forEach((item, idx) => {
              const div = document.createElement("div");
              div.className = "article";
              div.innerHTML = `
                <div class="article-title">${idx + 1}. <a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.title}</a></div>
                <div class="article-meta">来源：${item.source}</div>
                <div class="article-summary">${item.summary || ""}</div>
              `;
              listEl.appendChild(div);
            });
          } catch (err) {
            console.error(err);
            metaEl.textContent = "加载失败，请检查服务是否正常运行。";
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
              statusEl.className = "status error";
              return;
            }
            
            const data = await res.json();
            
            if (data.ok) {
              statusEl.textContent = `✅ ${data.message}：${data.article.title}`;
              statusEl.className = "status success";
              urlInput.value = "";
              // 添加成功后重新加载文章列表和预览
              loadArticleList();
              loadPreview();
            } else {
              statusEl.textContent = `❌ ${data.message || "添加失败"}`;
              statusEl.className = "status error";
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
          const ok = await ensureAdminCode();
          if (!ok) return;
          loadCandidateList();
          loadArticleList();
          loadPreview();
        }

        // 配置弹窗基础功能
        const configModal = document.getElementById("config-modal");
        const openConfigBtn = document.getElementById("open-config-btn");
        const closeConfigBtn = document.getElementById("close-config-btn");

        function openConfigModal() {
          if (configModal) {
            configModal.classList.add("is-visible");
            switchConfigSection("keywords");
          }
        }

        function closeConfigModal() {
          if (configModal) {
            configModal.classList.remove("is-visible");
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
                statusEl.className = "status error";
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
                statusEl.className = "status error";
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
                statusEl.className = "status error";
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
                statusEl.className = "status error";
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
              statusEl.className = "status error";
            }
            return;
          }
          
          if (statusEl) {
            statusEl.textContent = "保存中...";
            statusEl.className = "status";
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
                statusEl.className = "status success";
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
              statusEl.className = "status error";
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
                sectionEl.classList.add("is-active");
              } else {
                sectionEl.classList.remove("is-active");
              }
            }
            if (btn) {
              if (name === sectionName) {
                btn.classList.add("is-active");
              } else {
                btn.classList.remove("is-active");
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
              statusEl.className = "status error";
            }
            return;
          }
          
          if (statusEl) {
            statusEl.textContent = "保存中...";
            statusEl.className = "status";
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
                statusEl.className = "status success";
              }
            } else {
              throw new Error(data.message || "保存失败");
            }
          } catch (err) {
            console.error("保存关键词失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 保存失败: " + err.message;
              statusEl.className = "status error";
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
              statusEl.className = "status error";
            }
            return;
          }
          
          if (statusEl) {
            statusEl.textContent = "保存中...";
            statusEl.className = "status";
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
                statusEl.className = "status success";
              }
            } else {
              throw new Error(data.message || "保存失败");
            }
          } catch (err) {
            console.error("保存调度配置失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 保存失败: " + err.message;
              statusEl.className = "status error";
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
              statusEl.className = "status error";
            }
            return;
          }
          
          if (statusEl) {
            statusEl.textContent = "保存中...";
            statusEl.className = "status";
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
                statusEl.className = "status success";
              }
            } else {
              throw new Error(data.message || "保存失败");
            }
          } catch (err) {
            console.error("保存模板失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 保存失败: " + err.message;
              statusEl.className = "status error";
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
              statusEl.className = "status error";
            }
            return;
          }
          
          // 让用户选择文章（简化版：使用所有文章）
          const articleUrls = articlesData.articles.map(a => a.url);
          
          if (statusEl) {
            statusEl.textContent = "正在创建草稿...";
            statusEl.className = "status";
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
                statusEl.className = "status success";
              }
              loadDraftsList();
            } else {
              throw new Error(data.message || "创建失败");
            }
          } catch (err) {
            console.error("创建草稿失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 创建失败: " + err.message;
              statusEl.className = "status error";
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
            statusEl.className = "status";
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
                statusEl.className = "status success";
              }
              loadDraftsList();
            } else {
              throw new Error(data.message || "发布失败");
            }
          } catch (err) {
            console.error("发布草稿失败:", err);
            if (statusEl) {
              statusEl.textContent = "❌ 发布失败: " + err.message;
              statusEl.className = "status error";
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

        // 初始加载：检查是否已有授权码，没有则弹出对话框
        initializePanel();
        
        // 加载草稿列表（已屏蔽）
        // loadDraftsList();
        */
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


