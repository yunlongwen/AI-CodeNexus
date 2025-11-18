"""
文章爬虫模块：从URL提取文章信息（标题、来源、摘要等）
"""
import re
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import httpx
from loguru import logger


class ArticleInfoParser(HTMLParser):
    """HTML解析器，用于提取文章信息"""

    def __init__(self):
        super().__init__()
        self.title: Optional[str] = None
        # 优先从作者信息中获取来源（例如：阿颖）
        self.author: Optional[str] = None
        # 备用的站点名称（例如：AI产品阿颖）
        self.site_name: Optional[str] = None
        self.summary: Optional[str] = None
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            property_attr = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")
            
            # 提取摘要
            if name == "description" or property_attr == "og:description":
                if content and not self.summary:
                    self.summary = content.strip()
            
            # 提取作者 / 公众号名
            if property_attr == "og:article:author" or name == "author":
                if content and not self.author:
                    self.author = content.strip()

            # 记录站点名称作为备用（例如：AI产品阿颖）
            if property_attr == "og:site_name":
                if content and not self.site_name:
                    self.site_name = content.strip()

    def handle_data(self, data):
        if self.in_title and not self.title:
            self.title = data.strip()

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False


async def fetch_article_info(url: str) -> dict:
    """
    从URL获取文章信息（标题、来源、摘要）
    
    Args:
        url: 文章URL
        
    Returns:
        dict: 包含 title, url, source, summary 的字典
        
    Raises:
        Exception: 当无法获取或解析文章信息时
    """
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError(f"无效的URL: {url}")
    
    # 设置请求头，模拟浏览器访问
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            
    except httpx.HTTPError as e:
        logger.error(f"获取文章失败 {url}: {e}")
        raise Exception(f"无法访问URL: {str(e)}")
    
    # 解析HTML
    parser = ArticleInfoParser()
    try:
        parser.feed(html_content)
    except Exception as e:
        logger.error(f"解析HTML失败 {url}: {e}")
        raise Exception(f"解析文章内容失败: {str(e)}")
    
    # 提取信息
    title = parser.title or ""
    summary = parser.summary or ""

    # 优先使用作者，其次使用站点名
    source = ""
    if getattr(parser, "author", None):
        source = parser.author.strip()
    elif getattr(parser, "site_name", None):
        source = parser.site_name.strip()
    
    # 如果没有提取到标题，尝试从HTML中直接提取
    if not title:
        # 尝试提取 <title> 标签
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        # 尝试提取 og:title
        if not title:
            og_title_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if og_title_match:
                title = og_title_match.group(1).strip()
    
    # 如果没有提取到来源，尝试从URL或域名推断
    if not source:
        # 微信公众号文章
        if "mp.weixin.qq.com" in url:
            # 尝试从HTML中提取公众号名称
            account_match = re.search(r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if account_match:
                source = account_match.group(1).strip()
            else:
                # 尝试从其他meta标签提取
                profile_match = re.search(r'<meta[^>]*property=["\']og:article:author["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
                if profile_match:
                    source = profile_match.group(1).strip()
                else:
                    source = "微信公众号"
        else:
            # 从域名提取
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain:
                source = domain.replace("www.", "")
    
    # 如果没有提取到摘要，尝试从其他meta标签提取
    if not summary:
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if desc_match:
            summary = desc_match.group(1).strip()
        else:
            # 尝试从og:description提取
            og_desc_match = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if og_desc_match:
                summary = og_desc_match.group(1).strip()
    
    # 清理标题和摘要（移除多余的空白字符）
    title = re.sub(r"\s+", " ", title).strip()
    summary = re.sub(r"\s+", " ", summary).strip()
    
    # 如果仍然没有标题，使用URL作为fallback
    if not title:
        title = url
    
    # 如果仍然没有摘要，使用默认值
    if not summary:
        summary = "暂无摘要"
    
    result = {
        "title": title,
        "url": url,
        "source": source or "未知来源",
        "summary": summary,
    }
    
    logger.info(f"成功提取文章信息: {title[:50]}...")
    return result

