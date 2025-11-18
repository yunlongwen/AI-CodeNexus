from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from loguru import logger

from ..config_loader import load_digest_schedule
from ..notifier.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from ..sources.ai_articles import (
    delete_article_from_config,
    get_all_articles,
    pick_daily_ai_articles,
    save_article_to_config,
    todays_theme,
)
from ..sources.article_crawler import fetch_article_info

router = APIRouter()


class AddArticleRequest(BaseModel):
    url: str


class DeleteArticleRequest(BaseModel):
    url: str


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
async def preview_digest():
    """
    返回当前配置下将要推送的日报内容（不真正发送）。
    """
    digest = _build_digest()
    return digest


@router.post("/trigger")
async def trigger_digest():
    """
    手动触发一次企业微信推送，并返回本次发送的内容。
    """
    digest = _build_digest()
    content = build_wecom_digest_markdown(
        date_str=digest["date"],
        theme=digest["theme"],
        items=digest["articles"],
    )
    logger.info("Manual trigger: sending digest to WeCom group...")
    await send_markdown_to_wecom(content)
    return {"ok": True, **digest}


@router.get("/articles")
async def list_all_articles():
    """
    获取配置文件中所有文章列表。
    
    Returns:
        dict: 包含所有文章的列表
    """
    articles = get_all_articles()
    return {"ok": True, "articles": articles}


@router.post("/add-article")
async def add_article(request: AddArticleRequest):
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


@router.post("/delete-article")
async def delete_article(request: DeleteArticleRequest):
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
      <title>AI 编程日报面板</title>
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
      </style>
    </head>
    <body>
      <h1>AI 编程最新资讯 · 管理员面板</h1>
      
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

      <h2>文章列表</h2>
      <div class="add-article-form">
        <div class="status" id="list-status"></div>
        <div class="articles" id="article-list">加载中...</div>
      </div>

      <h2>预览 & 推送</h2>
      <div class="meta" id="meta">加载中...</div>
      <button id="trigger-btn">手动触发一次推送到企业微信群</button>
      <div class="status" id="status"></div>

      <div class="articles" id="articles"></div>

      <script>
        async function loadArticleList() {
          const listEl = document.getElementById("article-list");
          const statusEl = document.getElementById("list-status");
          statusEl.textContent = "";
          listEl.innerHTML = "加载中...";

          try {
            const res = await fetch("./articles");
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
            const res = await fetch("./delete-article", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ url: url })
            });
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
            const res = await fetch("./preview");
            const data = await res.json();
            metaEl.textContent = `日期：${data.date} ｜ 主题：${data.theme} ｜ 定时：${String(data.schedule.hour).padStart(2,'0')}:${String(data.schedule.minute).padStart(2,'0')} ｜ 篇数：${data.schedule.count}`;

            if (!data.articles || data.articles.length === 0) {
              listEl.innerHTML = "<p>当前配置下没有可用文章，请在服务器的 config/ai_articles.json 中添加。</p>";
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
            const res = await fetch("./add-article", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ url: url })
            });
            
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
            const res = await fetch("./trigger", { method: "POST" });
            const data = await res.json();
            if (data.ok) {
              statusEl.textContent = `✅ 已触发一次推送：${data.date} ｜ 主题：${data.theme}`;
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

        document.getElementById("add-article-btn").addEventListener("click", addArticle);
        document.getElementById("article-url").addEventListener("keypress", function(e) {
          if (e.key === "Enter") {
            addArticle();
          }
        });
        document.getElementById("trigger-btn").addEventListener("click", triggerOnce);
        loadArticleList();
        loadPreview();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


