"""
文章爬虫模块：从URL提取文章信息（标题、来源、摘要等）
"""
import re
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode

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


def normalize_weixin_url(url: str) -> str:
    """
    规范化微信公众号文章链接，移除临时参数，保留永久链接格式
    
    微信链接格式：
    1. 路径格式（永久链接）：https://mp.weixin.qq.com/s/JRSjbfTduWAYl1ig2uGpUw
    2. 查询参数格式（可能带临时参数）：https://mp.weixin.qq.com/s?src=11&timestamp=...&signature=...
    3. 查询参数格式（稳定参数）：https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx&idx=xxx&sn=xxx
    
    临时参数（会过期）：src, timestamp, ver, signature
    稳定参数（不会过期）：__biz, mid, idx, sn
    
    Args:
        url: 原始微信文章URL
        
    Returns:
        规范化后的URL，移除临时参数
    """
    if not url or "mp.weixin.qq.com" not in url:
        return url
    
    try:
        parsed = urlparse(url)
        
        # 如果是路径格式（/s/xxx），直接返回路径部分，移除所有查询参数
        # 路径格式：https://mp.weixin.qq.com/s/JRSjbfTduWAYl1ig2uGpUw
        # 这是最稳定的格式，不需要查询参数
        if parsed.path.startswith("/s/") and len(parsed.path) > 3:
            # 移除所有查询参数，只保留路径部分
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # 如果是查询参数格式
        if parsed.path == "/s" or parsed.path == "/s/":
            query_params = parse_qs(parsed.query, keep_blank_values=False)
            
            # 提取稳定参数（不会过期的参数）
            stable_params = {}
            stable_keys = ["__biz", "mid", "idx", "sn"]
            for key in stable_keys:
                if key in query_params:
                    value = query_params[key][0] if query_params[key] else None
                    if value:
                        stable_params[key] = value
            
            # 如果有稳定参数，使用稳定参数构建URL
            if stable_params:
                normalized_query = urlencode(stable_params, doseq=False)
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{normalized_query}"
            
            # 如果没有稳定参数，但有临时参数，尝试提取路径格式
            # 微信的临时链接可能包含路径信息在某个参数中
            # 对于这种情况，我们需要从HTML中提取，但这里先返回原始URL去掉临时参数
            # 移除临时参数
            temp_keys = ["src", "timestamp", "ver", "signature", "new"]
            cleaned_params = {k: v[0] for k, v in query_params.items() 
                            if k not in temp_keys and v}
            
            if cleaned_params:
                cleaned_query = urlencode(cleaned_params, doseq=False)
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{cleaned_query}"
        
        # 如果无法规范化，返回原始URL（去掉临时参数）
        return url
        
    except Exception as e:
        logger.warning(f"规范化微信链接失败: {url}, 错误: {e}")
        return url


def extract_weixin_permanent_url(html_content: str, original_url: str) -> Optional[str]:
    """
    从HTML内容中提取微信公众号的永久链接
    
    尝试从以下位置提取：
    1. og:url meta标签
    2. canonical link标签
    3. 从HTML中查找路径格式的链接
    
    Args:
        html_content: HTML内容
        original_url: 原始URL
        
    Returns:
        永久链接，如果找不到则返回None
    """
    if "mp.weixin.qq.com" not in original_url:
        return None
    
    try:
        # 1. 尝试从 og:url 提取
        og_url_match = re.search(
            r'<meta[^>]*property=["\']og:url["\'][^>]*content=["\']([^"\']+)["\']',
            html_content,
            re.IGNORECASE
        )
        if og_url_match:
            og_url = og_url_match.group(1).strip()
            if "mp.weixin.qq.com/s/" in og_url:
                # 提取路径格式的链接
                match = re.search(r'https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]+', og_url)
                if match:
                    return match.group(0)
        
        # 2. 尝试从 canonical link 提取
        canonical_match = re.search(
            r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
            html_content,
            re.IGNORECASE
        )
        if canonical_match:
            canonical_url = canonical_match.group(1).strip()
            if "mp.weixin.qq.com/s/" in canonical_url:
                match = re.search(r'https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]+', canonical_url)
                if match:
                    return match.group(0)
        
        # 3. 从HTML中搜索路径格式的链接
        path_match = re.search(
            r'https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]+',
            html_content
        )
        if path_match:
            return path_match.group(0)
            
    except Exception as e:
        logger.warning(f"从HTML提取永久链接失败: {e}")
    
    return None


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
    
    # 规范化微信链接，移除临时参数，保留永久链接格式
    normalized_url = url
    if "mp.weixin.qq.com" in url:
        # 首先尝试从HTML中提取永久链接（路径格式）
        permanent_url = extract_weixin_permanent_url(html_content, url)
        if permanent_url:
            normalized_url = permanent_url
            logger.debug(f"从HTML提取到永久链接: {permanent_url}")
        else:
            # 如果无法提取永久链接，则规范化URL，移除临时参数
            normalized_url = normalize_weixin_url(url)
            if normalized_url != url:
                logger.debug(f"规范化微信链接: {url} -> {normalized_url}")
    
    result = {
        "title": title,
        "url": normalized_url,  # 使用规范化后的URL
        "source": source or "未知来源",
        "summary": summary,
    }
    
    logger.info(f"成功提取文章信息: {title[:50]}...")
    return result

