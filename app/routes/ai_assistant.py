"""AI助手路由 - 提供AI相关助手功能"""
import re
import html as html_lib
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger
import httpx
from bs4 import BeautifulSoup

from ..notifier.wechat_mp import WeChatMPClient

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

