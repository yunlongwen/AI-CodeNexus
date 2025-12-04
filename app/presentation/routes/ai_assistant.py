"""AI助手路由 - 提供AI相关助手功能"""
import re
import html as html_lib
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from loguru import logger
import httpx
from bs4 import BeautifulSoup

from ...infrastructure.notifiers.wechat_mp import WeChatMPClient

router = APIRouter()


class MarkdownConvertRequest(BaseModel):
    """Markdown 转换请求"""
    markdown: str
    title: Optional[str] = None
    author: Optional[str] = "AI-CodeNexus"


class MarkdownConvertResponse(BaseModel):
    """Markdown 转换响应"""
    html: str
    wechat_html: str  # 适合微信公众号的 HTML


class PublishArticleRequest(BaseModel):
    """发表文章请求"""
    title: str
    content: str  # 微信公众号格式的 HTML
    author: Optional[str] = "AI-CodeNexus"
    digest: Optional[str] = None  # 摘要，不超过54字符
    thumb_media_id: Optional[str] = None  # 封面图 media_id
    content_source_url: Optional[str] = None  # 原文链接


class PublishArticleResponse(BaseModel):
    """发表文章响应"""
    success: bool
    message: str
    media_id: Optional[str] = None  # 草稿的 media_id


class WeChatArticleToMarkdownRequest(BaseModel):
    """微信公众号文章转 Markdown 请求"""
    url: Optional[str] = None  # 文章 URL
    html: Optional[str] = None  # 或者直接提供 HTML 内容


class WeChatArticleToMarkdownResponse(BaseModel):
    """微信公众号文章转 Markdown 响应"""
    markdown: str
    title: Optional[str] = None
    author: Optional[str] = None


def markdown_to_wechat_html(markdown_text: str) -> str:
    """
    将 Markdown 转换为适合微信公众号的 HTML 格式
    
    参考实现：https://github.com/xianmin/vscode-markdown-to-wechat
    
    微信公众号对 HTML 有一些限制：
    1. 不支持外部链接的图片（需要上传到微信服务器）
    2. 不支持 JavaScript
    3. 不支持某些 HTML 标签
    4. 样式需要内联
    5. 需要良好的排版和样式支持
    """
    # 先尝试导入 markdown
    try:
        import markdown
    except ImportError as e:
        logger.error(f"无法导入 markdown 库: {e}")
        raise HTTPException(
            status_code=500,
            detail="Markdown 转换功能需要 markdown 库，请安装: pip install markdown"
        )
    
    try:
        # 配置 Markdown 转换器（参考 vscode-markdown-to-wechat）
        md = markdown.Markdown(
            extensions=[
                'codehilite',      # 代码高亮
                'fenced_code',     # 围栏代码块
                'tables',          # 表格支持
                'nl2br',          # 换行转 <br>
                'toc',            # 目录（可选）
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': False,  # 不使用 Pygments，避免依赖
                }
            }
        )
        
        # 转换为 HTML
        html = md.convert(markdown_text)
        
        # 确保 HTML 是 UTF-8 编码，并清理特殊字符
        # 移除 BOM 标记和零宽字符
        html = html.replace('\ufeff', '').replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
        
        # 清理和优化 HTML，使其适合微信公众号
        # 参考 vscode-markdown-to-wechat 的样式处理
        
        # 1. 处理图片（微信公众号不支持外部图片，但保留 img 标签供用户替换）
        # 不删除图片，而是添加提示样式
        html = re.sub(
            r'<img([^>]+)src=["\'](https?://[^"\']+)["\']([^>]*)>',
            r'<img\1src="\2"\3 style="max-width: 100%; height: auto; display: block; margin: 10px auto;">',
            html
        )
        
        # 2. 为代码块添加样式（参考 vscode-markdown-to-wechat）
        html = re.sub(
            r'<pre><code([^>]*)>',
            r'<pre style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto; font-family: \'Consolas\', \'Monaco\', \'Courier New\', monospace; font-size: 14px; line-height: 1.6; margin: 15px 0;"><code\1 style="color: #333; background: transparent;">',
            html
        )
        html = re.sub(
            r'</code></pre>',
            r'</code></pre>',
            html
        )
        
        # 3. 为表格添加样式（更美观的表格样式）
        html = re.sub(
            r'<table>',
            r'<table style="border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 14px;">',
            html
        )
        html = re.sub(
            r'<th>',
            r'<th style="border: 1px solid #ddd; padding: 10px; background-color: #f8f9fa; text-align: left; font-weight: bold;">',
            html
        )
        html = re.sub(
            r'<td>',
            r'<td style="border: 1px solid #ddd; padding: 10px;">',
            html
        )
        
        # 4. 为段落添加样式（更好的行间距和字体）
        html = re.sub(
            r'<p>',
            r'<p style="line-height: 1.8; margin: 12px 0; color: #333; font-size: 15px; text-align: justify;">',
            html
        )
        
        # 5. 为标题添加样式（不同级别的标题）
        html = re.sub(
            r'<h1>',
            r'<h1 style="font-weight: bold; margin: 25px 0 15px 0; color: #2c3e50; font-size: 24px; border-bottom: 2px solid #eee; padding-bottom: 10px;">',
            html
        )
        html = re.sub(
            r'<h2>',
            r'<h2 style="font-weight: bold; margin: 22px 0 12px 0; color: #34495e; font-size: 20px; border-bottom: 1px solid #eee; padding-bottom: 8px;">',
            html
        )
        html = re.sub(
            r'<h3>',
            r'<h3 style="font-weight: bold; margin: 20px 0 10px 0; color: #34495e; font-size: 18px;">',
            html
        )
        for i in range(4, 7):
            html = re.sub(
                f'<h{i}>',
                f'<h{i} style="font-weight: bold; margin: 18px 0 10px 0; color: #34495e; font-size: {18-i}px;">',
                html
            )
        
        # 6. 为列表添加样式（更好的缩进和间距）
        html = re.sub(
            r'<ul>',
            r'<ul style="padding-left: 25px; margin: 12px 0; list-style-type: disc;">',
            html
        )
        html = re.sub(
            r'<ol>',
            r'<ol style="padding-left: 25px; margin: 12px 0;">',
            html
        )
        html = re.sub(
            r'<li>',
            r'<li style="margin: 6px 0; line-height: 1.8; color: #333;">',
            html
        )
        
        # 7. 为链接添加样式（微信公众号链接样式）
        html = re.sub(
            r'<a([^>]+)href=["\']([^"\']+)["\']([^>]*)>',
            r'<a\1href="\2"\3 style="color: #576b95; text-decoration: none; border-bottom: 1px solid #576b95;">',
            html
        )
        
        # 8. 为引用块添加样式（更美观的引用样式）
        html = re.sub(
            r'<blockquote>',
            r'<blockquote style="border-left: 4px solid #576b95; padding-left: 15px; margin: 15px 0; color: #666; font-style: italic; background-color: #f8f9fa; padding: 10px 15px;">',
            html
        )
        
        # 9. 为强调文本添加样式
        html = re.sub(
            r'<strong>',
            r'<strong style="font-weight: bold; color: #2c3e50;">',
            html
        )
        html = re.sub(
            r'<em>',
            r'<em style="font-style: italic; color: #555;">',
            html
        )
        
        # 10. 为水平线添加样式
        html = re.sub(
            r'<hr>',
            r'<hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">',
            html
        )
        
        # 10. 清理 HTML 实体编码，确保中文字符正确显示
        # 将常见的 HTML 实体转换为实际字符（但保留必要的实体如 &nbsp;）
        try:
            # 先解码 HTML 实体（如 &amp; &lt; &gt; 等），但保留 &nbsp;
            # 因为 &nbsp; 在 HTML 中有特殊意义
            html = html.replace('&nbsp;', '__NBSP__')  # 临时替换
            html = html_lib.unescape(html)  # 解码其他实体
            html = html.replace('__NBSP__', '&nbsp;')  # 恢复
        except Exception:
            pass
        
        # 11. 确保所有文本节点都是 UTF-8 编码
        # 移除可能导致编码问题的字符（BOM、零宽字符等）
        html = html.replace('\ufeff', '')  # BOM
        html = html.replace('\u200b', '')  # 零宽空格
        html = html.replace('\u200c', '')  # 零宽非断字符
        html = html.replace('\u200d', '')  # 零宽断字符
        html = html.replace('\ufeff', '')  # 再次确保移除 BOM
        
        # 确保是有效的 UTF-8 编码
        try:
            html = html.encode('utf-8', errors='ignore').decode('utf-8')
        except Exception:
            pass
        
        # 12. 清理多余的空白字符（但保留必要的空格和换行）
        # 不要在 HTML 标签之间清理，只清理文本内容中的多余空白
        html = re.sub(r'(?<=>)\s+(?=<)', '', html)  # 标签之间的空白
        html = re.sub(r'\n\s*\n\s*\n+', '\n', html)  # 多个换行合并
        
        # 13. 确保 HTML 格式正确，移除可能导致问题的字符
        # 移除控制字符（除了常见的换行、制表符等）
        html = ''.join(char for char in html if ord(char) >= 32 or char in '\n\r\t')
        
        return html
        
    except Exception as e:
        logger.error(f"Markdown 转换失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Markdown 转换失败: {str(e)}")


@router.post("/wechat-publisher/markdown/convert", response_model=MarkdownConvertResponse)
async def convert_markdown(request: MarkdownConvertRequest):
    """
    将 Markdown 转换为微信公众号格式的 HTML
    """
    try:
        # 转换为微信公众号格式的 HTML
        wechat_html = markdown_to_wechat_html(request.markdown)
        
        # 也生成标准 HTML（用于预览）
        try:
            import markdown
            md = markdown.Markdown(extensions=['fenced_code', 'tables', 'nl2br'])
            standard_html = md.convert(request.markdown)
        except Exception:
            standard_html = wechat_html
        
        return MarkdownConvertResponse(
            html=standard_html,
            wechat_html=wechat_html
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转换 Markdown 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


@router.post("/wechat-publisher/publish", response_model=PublishArticleResponse)
async def publish_article(request: PublishArticleRequest):
    """
    发表文章到微信公众号（创建草稿）
    
    注意：此接口会创建草稿，不会直接发布。需要在微信公众号后台手动发布。
    """
    try:
        # 验证必填字段
        if not request.title:
            raise HTTPException(status_code=400, detail="标题不能为空")
        if not request.content:
            raise HTTPException(status_code=400, detail="内容不能为空")
        
        # 验证摘要长度
        if request.digest and len(request.digest) > 54:
            raise HTTPException(status_code=400, detail="摘要不能超过54个字符")
        
        # 验证内容长度（微信公众号限制：少于2万字符，小于1M）
        if len(request.content) >= 20000:
            raise HTTPException(status_code=400, detail="内容不能超过2万字符")
        
        # 创建微信公众号客户端
        client = WeChatMPClient()
        
        # 准备文章数据
        article = {
            "article_type": "news",  # 图文消息
            "title": request.title,
            "author": request.author or "AI-CodeNexus",
            "content": request.content,
            "content_source_url": request.content_source_url or "",
        }
        
        # 添加摘要（如果有）
        if request.digest:
            article["digest"] = request.digest
        
        # 添加封面图（如果有）
        if request.thumb_media_id:
            article["thumb_media_id"] = request.thumb_media_id
        else:
            # 如果没有提供封面图，使用默认封面图
            logger.info("未提供封面图，使用默认封面图")
            default_thumb_id = await client.get_default_thumb_media_id()
            if default_thumb_id:
                article["thumb_media_id"] = default_thumb_id
            else:
                raise HTTPException(
                    status_code=500,
                    detail="无法获取默认封面图，请提供 thumb_media_id"
                )
        
        # 创建草稿
        media_id = await client.create_draft([article])
        
        if media_id:
            logger.info(f"成功创建草稿，media_id: {media_id}")
            return PublishArticleResponse(
                success=True,
                message="草稿创建成功，请在微信公众号后台查看并发布",
                media_id=media_id
            )
        else:
            logger.error("创建草稿失败")
            raise HTTPException(status_code=500, detail="创建草稿失败，请查看日志")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发表文章失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发表文章失败: {str(e)}")


@router.get("/wechat-publisher/drafts")
async def get_drafts(offset: int = 0, count: int = 20):
    """
    获取微信公众号草稿列表
    """
    try:
        client = WeChatMPClient()
        result = await client.get_draft_list(offset=offset, count=count)
        
        if result:
            return {
                "ok": True,
                "data": result
            }
        else:
            raise HTTPException(status_code=500, detail="获取草稿列表失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取草稿列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取草稿列表失败: {str(e)}")


def wechat_html_to_markdown(html_content: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    将微信公众号文章的 HTML 转换为 Markdown 格式
    
    返回: (markdown, title, author)
    """
    # 先尝试导入 html2text
    try:
        import html2text
    except ImportError as e:
        logger.error(f"无法导入 html2text 库: {e}")
        raise HTTPException(
            status_code=500,
            detail="HTML 转 Markdown 功能需要 html2text 库，请安装: pip install html2text"
        )
    
    try:
        
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取标题
        title = None
        title_elem = soup.find('h1') or soup.find('h2') or soup.find('title')
        if title_elem:
            title = title_elem.get_text().strip()
        
        # 提取作者
        author = None
        # 微信公众号文章通常在 meta 标签或特定 class 中
        author_elem = soup.find('meta', {'name': 'author'}) or \
                     soup.find('strong', class_=re.compile('.*author.*', re.I)) or \
                     soup.find('span', class_=re.compile('.*author.*', re.I))
        if author_elem:
            author = author_elem.get('content') or author_elem.get_text().strip()
        
        # 提取文章正文（微信公众号文章通常在 #js_content 或类似的选择器中）
        content_elem = soup.find(id='js_content') or \
                      soup.find(class_=re.compile('.*content.*', re.I)) or \
                      soup.find('article') or \
                      soup.find('div', class_=re.compile('.*article.*', re.I))
        
        if content_elem:
            # 只转换正文部分
            html_to_convert = str(content_elem)
        else:
            # 如果没有找到特定容器，使用整个 HTML
            html_to_convert = html_content
        
        # 在转换前，先处理图片标签
        # 微信公众号的图片可能有以下特点：
        # 1. 懒加载：使用 data-src 而不是 src
        # 2. CDN URL：图片存储在微信 CDN 上（包含 mmbiz、wx_fmt 等标识）
        # 3. 可能缺少 alt 文本
        for img in soup.find_all('img'):
            # 处理懒加载图片：如果 data-src 存在，使用它作为 src
            data_src = img.get('data-src') or img.get('data-original')
            if data_src:
                # 优先使用 data-src（通常是高清原图）
                img['src'] = data_src
            elif not img.get('src'):
                # 如果既没有 src 也没有 data-src，记录警告但继续处理
                logger.warning("发现没有 src 的图片标签")
                continue
            
            # 确保有 alt 属性（用于 Markdown 图片的 alt 文本）
            if not img.get('alt'):
                # 尝试从其他属性获取描述
                alt_text = (img.get('title') or 
                           img.get('data-title') or 
                           img.get('data-alt') or
                           '图片')  # 默认 alt 文本
                img['alt'] = alt_text
        
        # 更新 HTML 内容（包含处理后的图片）
        if content_elem:
            html_to_convert = str(content_elem)
        else:
            html_to_convert = str(soup)
        
        # 配置 html2text 转换器
        h = html2text.HTML2Text()
        h.ignore_links = False  # 保留链接
        h.ignore_images = False  # 保留图片（转换为 Markdown 格式）
        h.body_width = 0  # 不自动换行
        h.unicode_snob = True  # 使用 Unicode 字符
        h.mark_code = True  # 标记代码块
        
        # 转换为 Markdown
        markdown = h.handle(html_to_convert)
        
        # 后处理：优化图片 Markdown 格式
        # html2text 可能生成的格式不统一，统一处理
        # 匹配各种可能的图片格式：![alt](url) 或 ![alt](url "title")
        def normalize_image(match):
            """标准化图片 Markdown 格式"""
            full_match = match.group(0)
            alt = match.group(1) or '图片'
            url = match.group(2)
            # 移除 URL 中的引号和多余空格
            url = url.strip().strip('"').strip("'")
            # 返回标准格式：![alt](url)
            return f'![{alt}]({url})'
        
        # 匹配图片 Markdown 格式
        markdown = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            normalize_image,
            markdown
        )
        
        # 清理多余的空白行
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        markdown = markdown.strip()
        
        return markdown, title, author
        
    except Exception as e:
        logger.error(f"HTML 转 Markdown 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


@router.post("/wechat-publisher/article-to-markdown", response_model=WeChatArticleToMarkdownResponse)
async def wechat_article_to_markdown(request: WeChatArticleToMarkdownRequest):
    """
    将微信公众号文章转换为 Markdown 格式
    
    可以传入文章 URL 或直接传入 HTML 内容
    """
    try:
        html_content = None
        
        # 如果提供了 URL，先获取 HTML 内容
        if request.url:
            if not request.url.startswith(('http://', 'https://')):
                raise HTTPException(status_code=400, detail="URL 格式不正确")
            
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    # 设置 User-Agent 模拟浏览器访问
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    response = await client.get(request.url, headers=headers)
                    response.raise_for_status()
                    html_content = response.text
            except httpx.HTTPError as e:
                logger.error(f"获取文章内容失败: {e}")
                raise HTTPException(status_code=400, detail=f"无法获取文章内容: {str(e)}")
        
        # 如果提供了 HTML 内容，直接使用
        elif request.html:
            html_content = request.html
        else:
            raise HTTPException(status_code=400, detail="请提供 URL 或 HTML 内容")
        
        if not html_content:
            raise HTTPException(status_code=400, detail="无法获取 HTML 内容")
        
        # 转换为 Markdown
        markdown, title, author = wechat_html_to_markdown(html_content)
        
        return WeChatArticleToMarkdownResponse(
            markdown=markdown,
            title=title,
            author=author
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转换微信公众号文章失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


@router.get("/page", response_class=HTMLResponse)
async def ai_assistant_page(assistant_id: str = None):
    """AI助手页面 - 列表页和详情页"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>AI助手集合 - AI-CodeNexus</title>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap" rel="stylesheet">
      <script src="https://cdn.tailwindcss.com"></script>
      <style>
        body { margin: 0; padding: 0; background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%); min-height: 100vh; }
        .tech-font { font-family: 'Orbitron', 'Rajdhani', sans-serif; letter-spacing: 0.05em; }
        .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .neon-glow { box-shadow: 0 0 10px rgba(0, 240, 255, 0.5), 0 0 20px rgba(0, 240, 255, 0.3); }
        .preview-content { max-height: 400px; overflow-y: auto; }
        .preview-content img { max-width: 100%; height: auto; }
        .preview-content pre { background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }
        .preview-content table { border-collapse: collapse; width: 100%; }
        .preview-content th, .preview-content td { border: 1px solid #ddd; padding: 8px; }

        /* 卡片动画 */
        .assistant-card {
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          cursor: pointer;
          position: relative;
          overflow: hidden;
        }
        .assistant-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
          transition: left 0.5s;
        }
        .assistant-card:hover::before {
          left: 100%;
        }
        .assistant-card:hover {
          transform: translateY(-8px) scale(1.02);
          box-shadow: 0 20px 40px rgba(0, 240, 255, 0.3), 0 0 20px rgba(168, 85, 247, 0.2);
          border-color: rgba(0, 240, 255, 0.5);
        }
        .assistant-card:active {
          transform: translateY(-4px) scale(1.01);
        }

        /* 卡片图标动画 */
        .card-icon {
          transition: all 0.3s ease;
        }
        .assistant-card:hover .card-icon {
          transform: scale(1.1) rotate(5deg);
        }

        /* 页面切换动画 */
        .page-section {
          animation: fadeIn 0.4s ease-in;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        /* 卡片网格 */
        .assistant-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 1.5rem;
        }
      </style>
    </head>
    <body class="text-white">
      <div class="container mx-auto px-4 py-8 max-w-7xl">
        <!-- 列表页 -->
        <div id="assistant-list-page" class="page-section">
          <!-- 标题 -->
          <div class="text-center mb-8">
            <h1 class="tech-font text-4xl font-bold mb-2 bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              AI助手集合
            </h1>
            <p class="text-gray-400">智能助手，提升你的工作效率</p>
          </div>

          <!-- AI助手卡片网格 -->
          <div class="assistant-grid">
            <!-- 微信公众号发布助手卡片 -->
            <div class="assistant-card glass rounded-xl p-6" onclick="openAssistant('wechat-publisher')">
              <div class="flex flex-col items-center text-center">
                <div class="card-icon text-6xl mb-4">📝</div>
                <h3 class="text-xl font-bold mb-2 tech-font">微信公众号发布助手</h3>
                <p class="text-gray-400 text-sm mb-4">将 Markdown 格式的文章转换为微信公众号格式，并一键发布到公众号草稿箱</p>
                <div class="flex flex-wrap gap-2 justify-center">
                  <span class="px-3 py-1 bg-blue-600/30 text-blue-300 rounded-full text-xs">内容创作</span>
                  <span class="px-3 py-1 bg-purple-600/30 text-purple-300 rounded-full text-xs">公众号</span>
                </div>
              </div>
            </div>

            <!-- 更多AI助手卡片可以在这里添加 -->
            <!-- 示例：占位卡片（未来添加） -->
            <!--
            <div class="assistant-card glass rounded-xl p-6 opacity-50">
              <div class="flex flex-col items-center text-center">
                <div class="card-icon text-6xl mb-4">🚀</div>
                <h3 class="text-xl font-bold mb-2 tech-font">更多助手</h3>
                <p class="text-gray-400 text-sm">即将推出...</p>
              </div>
            </div>
            -->
          </div>
        </div>

        <!-- 详情页 - 微信公众号发布助手 -->
        <div id="assistant-detail-page" class="page-section hidden">
          <!-- 返回按钮 -->
          <button onclick="backToList()" class="mb-6 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors flex items-center gap-2">
            <span>←</span> 返回助手列表
          </button>

          <!-- 微信公众号发布助手详情 -->
          <div id="assistant-wechat-publisher" class="assistant-detail hidden">
            <div class="glass rounded-lg p-6 mb-6">
            <h2 class="text-2xl font-bold mb-4 tech-font">微信公众号发布助手</h2>
            <p class="text-gray-400 mb-4">Markdown 与微信公众号文章格式互转，一键发布到公众号草稿箱</p>

            <!-- 标签页切换 -->
            <div class="flex gap-2 mb-6 border-b border-gray-700">
              <button onclick="switchTab('md-to-wechat')" id="tab-md-to-wechat" class="px-4 py-2 border-b-2 border-cyan-400 text-cyan-400 font-medium">
                Markdown → 公众号
              </button>
              <button onclick="switchTab('wechat-to-md')" id="tab-wechat-to-md" class="px-4 py-2 border-b-2 border-transparent text-gray-400 hover:text-white">
                公众号 → Markdown
              </button>
            </div>

            <!-- Markdown 转公众号 -->
            <div id="tab-content-md-to-wechat" class="tab-content">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- 左侧：输入区域 -->
              <div>
                <label class="block text-sm font-medium mb-2">Markdown 内容</label>
                <textarea
                  id="markdown-input"
                  class="w-full h-96 p-4 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-cyan-400 focus:outline-none font-mono text-sm"
                  placeholder="在此输入 Markdown 内容...&#10;&#10;例如：&#10;# 标题&#10;&#10;这是一段**粗体**文字和*斜体*文字。&#10;&#10;```python&#10;def hello():&#10;    print('Hello, World!')&#10;```"
                ></textarea>
                <div class="mt-4 flex gap-2">
                  <button onclick="convertMarkdown()" class="px-6 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors neon-glow">
                    转换为公众号格式
                  </button>
                  <button onclick="clearMarkdown()" class="px-6 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors">
                    清空
                  </button>
                </div>
              </div>

              <!-- 右侧：预览区域 -->
              <div>
                <label class="block text-sm font-medium mb-2">预览效果</label>
                <div id="markdown-preview" class="w-full h-96 p-4 bg-white text-gray-800 rounded-lg border border-gray-600 overflow-auto preview-content">
                  <p class="text-gray-500">预览将显示在这里...</p>
                </div>
                <div class="mt-4 flex gap-2 flex-wrap">
                  <button onclick="copyWechatHtml()" class="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors">
                    复制公众号 HTML
                  </button>
                  <button onclick="publishArticle()" class="px-6 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors">
                    发表到公众号
                  </button>
                </div>
                <div class="mt-2 text-xs text-gray-500">
                  💡 提示：复制 HTML 后，在微信公众号编辑器中点击"HTML"按钮（或按 Ctrl+Shift+V）粘贴，而不是直接粘贴
                </div>
              </div>
            </div>

            <!-- 发表文章表单 -->
            <div id="publish-form" class="mt-6 hidden">
              <div class="glass rounded-lg p-4">
                <h3 class="text-xl font-bold mb-4">发表文章到微信公众号</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium mb-2">标题 *</label>
                    <input type="text" id="article-title" class="w-full p-2 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-cyan-400 focus:outline-none" placeholder="文章标题">
                  </div>
                  <div>
                    <label class="block text-sm font-medium mb-2">作者</label>
                    <input type="text" id="article-author" class="w-full p-2 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-cyan-400 focus:outline-none" value="AI-CodeNexus" placeholder="作者名称">
                  </div>
                  <div class="md:col-span-2">
                    <label class="block text-sm font-medium mb-2">摘要（不超过54字符）</label>
                    <input type="text" id="article-digest" class="w-full p-2 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-cyan-400 focus:outline-none" placeholder="文章摘要" maxlength="54">
                  </div>
                  <div class="md:col-span-2">
                    <label class="block text-sm font-medium mb-2">原文链接（可选）</label>
                    <input type="url" id="article-url" class="w-full p-2 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-cyan-400 focus:outline-none" placeholder="https://...">
                  </div>
                </div>
                <div class="mt-4 flex gap-2">
                  <button onclick="submitPublish()" class="px-6 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors">
                    创建草稿
                  </button>
                  <button onclick="hidePublishForm()" class="px-6 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors">
                    取消
                  </button>
                </div>
              </div>
            </div>

            <!-- 草稿箱 -->
            <div class="mt-6">
              <h3 class="text-xl font-bold mb-4">草稿箱管理</h3>
              <button onclick="loadDrafts()" class="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors mb-4">
                刷新草稿列表
              </button>
              <div id="drafts-list" class="space-y-4">
                <p class="text-gray-400">点击"刷新草稿列表"加载草稿...</p>
              </div>
            </div>
            </div>

            <!-- 公众号转 Markdown -->
            <div id="tab-content-wechat-to-md" class="tab-content hidden">
              <div class="space-y-6">
                <div>
                  <label class="block text-sm font-medium mb-2">微信公众号文章 URL</label>
                  <div class="flex gap-2">
                    <input
                      type="url"
                      id="wechat-article-url"
                      class="flex-1 p-3 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-cyan-400 focus:outline-none"
                      placeholder="https://mp.weixin.qq.com/s/..."
                    >
                    <button onclick="convertWechatArticle()" class="px-6 py-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors">
                      转换
                    </button>
                  </div>
                  <p class="text-gray-500 text-xs mt-2">或者直接粘贴文章 HTML 内容到下方</p>
                </div>

                <div>
                  <label class="block text-sm font-medium mb-2">或粘贴 HTML 内容</label>
                  <textarea
                    id="wechat-html-input"
                    class="w-full h-48 p-4 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-cyan-400 focus:outline-none font-mono text-sm"
                    placeholder="在此粘贴微信公众号文章的 HTML 内容..."
                  ></textarea>
                  <div class="mt-2 flex gap-2">
                    <button onclick="convertWechatHtml()" class="px-6 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors">
                      转换为 Markdown
                    </button>
                    <button onclick="clearWechatInput()" class="px-6 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors">
                      清空
                    </button>
                  </div>
                </div>

                <div>
                  <label class="block text-sm font-medium mb-2">转换后的 Markdown</label>
                  <textarea
                    id="wechat-markdown-output"
                    class="w-full h-96 p-4 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-cyan-400 focus:outline-none font-mono text-sm"
                    placeholder="转换后的 Markdown 将显示在这里..."
                    readonly
                  ></textarea>
                  <div class="mt-2 flex gap-2">
                    <button onclick="copyMarkdown()" class="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors">
                      复制 Markdown
                    </button>
                    <button onclick="useAsInput()" class="px-6 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors">
                      用作输入（切换到 Markdown → 公众号）
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          </div>
        </div>

        <!-- 消息提示 -->
        <div id="message" class="fixed top-4 right-4 p-4 rounded-lg shadow-lg hidden z-50">
          <span id="message-text"></span>
        </div>
      </div>

      <script>
        let currentWechatHtml = '';
        let currentMarkdown = '';
        let currentAssistant = null;

        // 初始化：根据 URL 决定显示列表页还是详情页
        function initPage() {
          const path = window.location.pathname;
          const match = path.match(/\/ai-assistant\/(.+)/);
          if (match) {
            openAssistant(match[1], false);
          } else {
            showListPage();
          }
        }

        // 显示列表页
        function showListPage() {
          document.getElementById('assistant-list-page').classList.remove('hidden');
          document.getElementById('assistant-detail-page').classList.add('hidden');
          window.history.pushState({ page: 'list' }, '', '/ai-assistant');
        }

        // 打开助手详情页
        function openAssistant(assistantId, pushState = true) {
          currentAssistant = assistantId;

          // 隐藏列表页，显示详情页
          document.getElementById('assistant-list-page').classList.add('hidden');
          document.getElementById('assistant-detail-page').classList.remove('hidden');

          // 隐藏所有助手详情，显示当前助手
          document.querySelectorAll('.assistant-detail').forEach(el => el.classList.add('hidden'));
          const detailEl = document.getElementById(`assistant-${assistantId}`);
          if (detailEl) {
            detailEl.classList.remove('hidden');
          }

          // 更新 URL
          if (pushState) {
            window.history.pushState({ page: 'detail', assistant: assistantId }, '', `/ai-assistant/${assistantId}`);
          }
        }

        // 返回列表页
        function backToList() {
          showListPage();
        }

        // 处理浏览器前进后退
        window.addEventListener('popstate', function(event) {
          if (event.state && event.state.page === 'detail') {
            openAssistant(event.state.assistant, false);
          } else {
            showListPage();
          }
        });

        // 页面加载时初始化
        initPage();

        // 标签页切换
        function switchTab(tabName) {
          // 隐藏所有标签内容
          document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));

          // 重置所有标签按钮样式
          document.querySelectorAll('[id^="tab-"]').forEach(btn => {
            btn.classList.remove('border-cyan-400', 'text-cyan-400');
            btn.classList.add('border-transparent', 'text-gray-400');
          });

          // 显示选中的标签内容
          document.getElementById(`tab-content-${tabName}`).classList.remove('hidden');

          // 更新选中的标签按钮样式
          const activeTab = document.getElementById(`tab-${tabName}`);
          activeTab.classList.remove('border-transparent', 'text-gray-400');
          activeTab.classList.add('border-cyan-400', 'text-cyan-400');
        }

        // 转换微信公众号文章（通过 URL）
        async function convertWechatArticle() {
          const url = document.getElementById('wechat-article-url').value.trim();
          if (!url) {
            showMessage('请输入文章 URL', 'error');
            return;
          }

          try {
            showMessage('正在获取文章内容...', 'info');
            const response = await fetch('/api/ai-assistant/wechat-publisher/article-to-markdown', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (response.ok) {
              document.getElementById('wechat-markdown-output').value = data.markdown;
              if (data.title) {
                showMessage(`转换成功！标题: ${data.title}`, 'success');
              } else {
                showMessage('转换成功！', 'success');
              }
            } else {
              showMessage(data.detail || '转换失败', 'error');
            }
          } catch (error) {
            showMessage('转换失败: ' + error.message, 'error');
          }
        }

        // 转换微信公众号 HTML（直接粘贴）
        async function convertWechatHtml() {
          const html = document.getElementById('wechat-html-input').value.trim();
          if (!html) {
            showMessage('请输入 HTML 内容', 'error');
            return;
          }

          try {
            showMessage('正在转换...', 'info');
            const response = await fetch('/api/ai-assistant/wechat-publisher/article-to-markdown', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ html: html })
            });

            const data = await response.json();

            if (response.ok) {
              document.getElementById('wechat-markdown-output').value = data.markdown;
              showMessage('转换成功！', 'success');
            } else {
              showMessage(data.detail || '转换失败', 'error');
            }
          } catch (error) {
            showMessage('转换失败: ' + error.message, 'error');
          }
        }

        // 清空公众号输入
        function clearWechatInput() {
          document.getElementById('wechat-article-url').value = '';
          document.getElementById('wechat-html-input').value = '';
          document.getElementById('wechat-markdown-output').value = '';
        }

        // 复制 Markdown
        function copyMarkdown() {
          const markdown = document.getElementById('wechat-markdown-output').value;
          if (!markdown) {
            showMessage('没有可复制的内容', 'error');
            return;
          }

          navigator.clipboard.writeText(markdown).then(() => {
            showMessage('已复制到剪贴板', 'success');
          }).catch(() => {
            showMessage('复制失败', 'error');
          });
        }

        // 用作输入（切换到 Markdown → 公众号）
        function useAsInput() {
          const markdown = document.getElementById('wechat-markdown-output').value;
          if (!markdown) {
            showMessage('没有可用的 Markdown 内容', 'error');
            return;
          }

          // 切换到 Markdown → 公众号 标签页
          switchTab('md-to-wechat');

          // 将 Markdown 填入输入框
          document.getElementById('markdown-input').value = markdown;

          showMessage('已切换到 Markdown → 公众号，内容已填入', 'success');
        }

        // 转换 Markdown
        async function convertMarkdown() {
          const markdown = document.getElementById('markdown-input').value;
          if (!markdown.trim()) {
            showMessage('请输入 Markdown 内容', 'error');
            return;
          }

          currentMarkdown = markdown;

          try {
            const response = await fetch('/api/ai-assistant/wechat-publisher/markdown/convert', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ markdown: markdown })
            });

            const data = await response.json();

            if (response.ok) {
              currentWechatHtml = data.wechat_html;
              document.getElementById('markdown-preview').innerHTML = data.html;
              showMessage('转换成功！', 'success');
            } else {
              showMessage(data.detail || '转换失败', 'error');
            }
          } catch (error) {
            showMessage('转换失败: ' + error.message, 'error');
          }
        }

        // 复制公众号 HTML（使用富文本格式，类似 Ctrl+C 复制网页）
        async function copyWechatHtml() {
          if (!currentWechatHtml) {
            showMessage('请先转换 Markdown', 'error');
            return;
          }

          try {
            // 创建一个临时 div 元素来渲染 HTML（完全隐藏）
            const tempDiv = document.createElement('div');
            tempDiv.style.position = 'fixed';
            tempDiv.style.left = '-9999px';
            tempDiv.style.top = '-9999px';
            tempDiv.style.width = '1px';
            tempDiv.style.height = '1px';
            tempDiv.style.opacity = '0';
            tempDiv.style.pointerEvents = 'none';
            tempDiv.setAttribute('contenteditable', 'true');
            tempDiv.innerHTML = currentWechatHtml;
            document.body.appendChild(tempDiv);

            // 选中所有内容
            const range = document.createRange();
            range.selectNodeContents(tempDiv);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);

            // 先获取文本内容（在移除元素之前）
            const textContent = tempDiv.innerText || tempDiv.textContent || '';

            // 使用 document.execCommand 复制（最接近 Ctrl+C 的行为）
            const success = document.execCommand('copy');

            // 清理
            selection.removeAllRanges();
            document.body.removeChild(tempDiv);

            if (success) {
              showMessage('已复制到剪贴板（富文本格式）', 'success');
            } else {
              // 如果 execCommand 失败，尝试使用 Clipboard API
              if (navigator.clipboard && navigator.clipboard.write) {
                const htmlBlob = new Blob([currentWechatHtml], { type: 'text/html' });
                const textBlob = new Blob([textContent], { type: 'text/plain' });

                const clipboardItem = new ClipboardItem({
                  'text/html': htmlBlob,
                  'text/plain': textBlob
                });

                await navigator.clipboard.write([clipboardItem]);
                showMessage('已复制到剪贴板（富文本格式）', 'success');
              } else {
                throw new Error('浏览器不支持复制功能');
              }
            }
          } catch (error) {
            console.error('复制失败:', error);
            // 如果富文本复制失败，尝试降级到纯文本
            try {
              await navigator.clipboard.writeText(currentWechatHtml);
              showMessage('已复制到剪贴板（纯文本格式）', 'warning');
            } catch (textError) {
              showMessage('复制失败: ' + error.message, 'error');
            }
          }
        }


        // 清空 Markdown
        function clearMarkdown() {
          document.getElementById('markdown-input').value = '';
          document.getElementById('markdown-preview').innerHTML = '<p class="text-gray-500">预览将显示在这里...</p>';
          currentWechatHtml = '';
          currentMarkdown = '';
        }

        // 显示发表表单
        function publishArticle() {
          if (!currentWechatHtml) {
            showMessage('请先转换 Markdown', 'error');
            return;
          }
          document.getElementById('publish-form').classList.remove('hidden');
        }

        // 隐藏发表表单
        function hidePublishForm() {
          document.getElementById('publish-form').classList.add('hidden');
        }

        // 提交发表
        async function submitPublish() {
          const title = document.getElementById('article-title').value.trim();
          const author = document.getElementById('article-author').value.trim() || 'AI-CodeNexus';
          const digest = document.getElementById('article-digest').value.trim();
          const url = document.getElementById('article-url').value.trim();

          if (!title) {
            showMessage('请输入文章标题', 'error');
            return;
          }

          if (!currentWechatHtml) {
            showMessage('请先转换 Markdown', 'error');
            return;
          }

          try {
            const response = await fetch('/api/ai-assistant/wechat-publisher/publish', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: title,
                content: currentWechatHtml,
                author: author,
                digest: digest,
                content_source_url: url || undefined
              })
            });

            const data = await response.json();

            if (response.ok && data.success) {
              showMessage('草稿创建成功！media_id: ' + data.media_id, 'success');
              hidePublishForm();
            } else {
              showMessage(data.message || data.detail || '发表失败', 'error');
            }
          } catch (error) {
            showMessage('发表失败: ' + error.message, 'error');
          }
        }

        // 加载草稿列表
        async function loadDrafts() {
          try {
            const response = await fetch('/api/ai-assistant/wechat-publisher/drafts?offset=0&count=20');
            const result = await response.json();

            if (response.ok && result.ok) {
              const drafts = result.data.item || [];
              const listEl = document.getElementById('drafts-list');

              if (drafts.length === 0) {
                listEl.innerHTML = '<p class="text-gray-400">草稿箱为空</p>';
              } else {
                listEl.innerHTML = drafts.map((draft, idx) => `
                  <div class="glass rounded-lg p-4">
                    <div class="flex justify-between items-start">
                      <div>
                        <h3 class="font-bold text-lg">${draft.news_item?.[0]?.title || '无标题'}</h3>
                        <p class="text-gray-400 text-sm mt-1">media_id: ${draft.media_id}</p>
                        <p class="text-gray-400 text-sm">更新时间: ${new Date(draft.update_time * 1000).toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                `).join('');
              }
              showMessage('草稿列表加载成功', 'success');
            } else {
              showMessage(result.detail || '加载失败', 'error');
            }
          } catch (error) {
            showMessage('加载失败: ' + error.message, 'error');
          }
        }

        // 显示消息
        function showMessage(text, type = 'info') {
          const msgEl = document.getElementById('message');
          const textEl = document.getElementById('message-text');

          msgEl.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-600' :
            type === 'error' ? 'bg-red-600' :
            'bg-blue-600'
          }`;
          msgEl.classList.remove('hidden');
          textEl.textContent = text;

          setTimeout(() => {
            msgEl.classList.add('hidden');
          }, 3000);
        }

      </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html)
