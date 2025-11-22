import math
import os
from datetime import datetime
from typing import Optional

from dataclasses import asdict
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger
from pydantic import BaseModel

from ..config_loader import load_digest_schedule
from ..notifier.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from ..sources.ai_articles import (
    clear_articles,
    delete_article_from_config,
    get_all_articles,
    pick_daily_ai_articles,
    save_article_to_config,
    todays_theme,
)
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
      <button id="trigger-btn">手动触发一次推送到企业微信群</button>
      <div class="status" id="status"></div>



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

        // 初始加载：检查是否已有授权码，没有则弹出对话框
        initializePanel();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


