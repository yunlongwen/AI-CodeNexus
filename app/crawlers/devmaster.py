"""DevMaster.cn 工具抓取器"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


# 分类映射：将 devmaster.cn 的分类映射到我们的分类
CATEGORY_MAPPING = {
    "ide": ["IDE", "编辑器", "开发环境"],
    "plugin": ["插件", "扩展", "Extension"],
    "cli": ["命令行", "CLI", "终端", "Terminal"],
    "codeagent": ["AI助手", "CodeAgent", "AI代码", "智能编程"],
    "ai-test": ["AI测试", "测试工具", "自动化测试"],
    "review": ["代码审查", "Code Review", "代码质量"],
    "devops": ["DevOps", "CI/CD", "部署", "运维"],
    "doc": ["文档", "文档工具", "Documentation", "Docs"],
    "design": ["设计", "UI设计", "UX设计"],
    "ui": ["UI生成", "界面生成", "UI工具", "VibeTool"],
    "mcp": ["MCP", "Model Context Protocol"],
    "other": []  # 其他未分类的工具
}

# API分类到我们分类的映射
API_CATEGORY_MAPPING = {
    "VibeTool": "other",  # VibeTool 映射到 other，UI生成只包含 UI-Code
    "UI-Code": "ui",  # UI-Code 映射到 ui（UI生成）
    "Docs": "doc",
    "IDE": "ide",
    "Plugin": "plugin",
    "Extension": "plugin",
    "CLI": "cli",
    "CliAgent": "cli",
    "CodeAgent": "codeagent",
    "AITest": "ai-test",
    "Testing": "ai-test",  # Testing 分类映射到 ai-test
    "Review": "review",
    "CodeReview": "review",
    "DevOps": "devops",
    "Design": "design",
    "MCP": "mcp",
    "McpTool": "mcp",
    "Resource": "other",
    "Other": "other",
}


def _map_api_category(api_category: str) -> str:
    """
    将API返回的分类映射到我们的分类系统
    
    Args:
        api_category: API返回的分类名称
        
    Returns:
        映射后的分类名称
    """
    if not api_category:
        return "other"
    
    # 直接映射
    api_category_clean = api_category.strip()
    if api_category_clean in API_CATEGORY_MAPPING:
        return API_CATEGORY_MAPPING[api_category_clean]
    
    # 模糊匹配
    api_category_lower = api_category_clean.lower()
    for our_category, keywords in CATEGORY_MAPPING.items():
        for keyword in keywords:
            if keyword.lower() in api_category_lower or api_category_lower in keyword.lower():
                return our_category
    
    return "other"


async def fetch_devmaster_tools(
    category: Optional[str] = None,
    max_items: int = 100,
    use_api: bool = True,
    use_playwright: bool = False
) -> List[Dict[str, Any]]:
    """
    从 DevMaster.cn 抓取工具数据
    
    Args:
        category: 工具分类（可选）
        max_items: 最多抓取的工具数量
        use_api: 是否优先使用API（推荐）
        use_playwright: 是否使用 Playwright（当API不可用时）
        
    Returns:
        工具列表，每个工具包含 name, url, description, category, tags, icon 等
    """
    # 优先使用API
    if use_api:
        tools = await fetch_tools_from_api()
        if tools:
            # 如果指定了分类，进行筛选
            if category:
                tools = [t for t in tools if t.get("category") == category]
            # 限制数量
            if max_items:
                tools = tools[:max_items]
            return tools
    
    # API失败时使用Playwright
    if use_playwright:
        return await _fetch_with_playwright(category, max_items)
    else:
        return await _fetch_with_httpx(category, max_items)


async def _fetch_with_playwright(
    category: Optional[str] = None,
    max_items: int = 100
) -> List[Dict[str, Any]]:
    """使用 Playwright 抓取工具数据"""
    base_url = "http://devmaster.cn"
    tools_url = f"{base_url}/tools" if category is None else f"{base_url}/category/{category}"
    
    logger.info(f"使用 Playwright 访问 {tools_url}...")
    tools = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # 访问工具页面
            await page.goto(tools_url, wait_until="networkidle", timeout=30000)
            
            # 等待内容加载
            await page.wait_for_timeout(2000)
            
            # 获取页面内容
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 尝试多种选择器
            tool_elements = []
            selectors = [
                "article",
                "[class*='card']",
                "[class*='item']",
                "[class*='tool']",
                ".tool-card",
                ".product-item"
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements and len(elements) > 3:  # 至少要有几个元素才认为是工具列表
                    logger.info(f"找到 {len(elements)} 个工具元素（选择器: {selector}）")
                    tool_elements = elements
                    break
            
            if not tool_elements:
                logger.warning("未找到工具列表，尝试从API获取...")
                # 尝试查找API调用
                tools = await _try_fetch_from_api(page, base_url)
                if tools:
                    return tools
            
            # 解析工具元素
            logger.info(f"开始解析 {len(tool_elements)} 个工具元素...")
            for idx, element in enumerate(tool_elements[:max_items]):
                try:
                    tool = _parse_tool_element(element, base_url)
                    if tool:
                        if not category:
                            tool["category"] = _auto_categorize_tool(tool)
                        else:
                            tool["category"] = category
                        tools.append(tool)
                        logger.debug(f"解析工具 {idx+1}/{len(tool_elements)}: {tool.get('name', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"解析工具元素失败: {e}")
                    continue
            
            await browser.close()
            
    except PlaywrightTimeoutError:
        logger.error(f"访问 {tools_url} 超时")
    except Exception as e:
        logger.error(f"Playwright 抓取失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
    
    logger.info(f"从 DevMaster.cn 成功抓取到 {len(tools)} 个工具")
    return tools


async def _try_fetch_from_api(page, base_url: str) -> List[Dict[str, Any]]:
    """尝试从API获取工具数据"""
    return await fetch_tools_from_api(base_url=base_url)


async def fetch_tools_from_api(api_url: Optional[str] = None, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    直接从API获取工具数据（推荐方法）
    
    Args:
        api_url: 完整的API URL（优先使用）
        base_url: 网站基础URL（如果未提供api_url，则使用base_url拼接/api/tools）
        
    Returns:
        工具列表
    """
    # 优先使用 api_url，如果没有则使用 base_url 拼接
    if not api_url:
        if base_url:
            api_url = f"{base_url.rstrip('/')}/api/tools"
        else:
            # 兼容旧代码，使用默认值（但不推荐）
            api_url = "http://devmaster.cn/api/tools"
    tools = []
    
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
        ) as client:
            logger.info(f"从API获取工具数据: {api_url}")
            resp = await client.get(api_url)
            resp.raise_for_status()
            
            data = resp.json()
            
            # 处理不同的API响应格式
            items = []
            if isinstance(data, dict):
                # 格式: {"code": 200, "msg": "success", "data": {...}}
                if "data" in data:
                    data_content = data["data"]
                    # data 可能是列表或字典
                    if isinstance(data_content, list):
                        items = data_content
                    elif isinstance(data_content, dict):
                        # 格式: {"items": [...], "total": 100, ...}
                        if "items" in data_content:
                            items = data_content["items"]
                        else:
                            logger.warning(f"data字段是字典但没有items键: {list(data_content.keys())}")
                    else:
                        logger.warning(f"data字段类型未知: {type(data_content)}")
                elif "items" in data:
                    items = data["items"]
                else:
                    logger.warning(f"响应字典中没有data或items键: {list(data.keys())}")
            elif isinstance(data, list):
                items = data
            else:
                logger.warning(f"未知的API响应格式: {type(data)}")
                return []
            
            logger.info(f"API返回 {len(items)} 个工具项")
            
            for item in items:
                try:
                    # 处理时间戳（毫秒）
                    update_time = item.get("updateTime")
                    if update_time:
                        # 将毫秒时间戳转换为ISO格式
                        try:
                            dt = datetime.fromtimestamp(update_time / 1000)
                            created_at = dt.isoformat() + "Z"
                        except (ValueError, TypeError):
                            created_at = datetime.now().isoformat() + "Z"
                    else:
                        created_at = datetime.now().isoformat() + "Z"
                    
                    # 映射分类
                    api_category = item.get("category", "").strip()
                    mapped_category = _map_api_category(api_category)
                    
                    tool = {
                        "name": item.get("name", "").strip(),
                        "url": item.get("url", "").strip(),
                        "description": item.get("description", "").strip(),
                        "category": mapped_category,
                        "tags": item.get("tags", []) or [],
                        "icon": item.get("icon", "🔧"),
                        "view_count": item.get("view_count", 0),
                        "created_at": created_at,
                        "is_featured": item.get("is_featured", False)
                    }
                    
                    # 验证必需字段
                    if tool["name"] and tool["url"]:
                        tools.append(tool)
                    else:
                        logger.debug(f"跳过无效工具: {item}")
                except Exception as e:
                    logger.warning(f"解析工具项失败: {e}, item: {item}")
                    continue
            
            logger.info(f"成功解析 {len(tools)} 个有效工具")
            return tools
            
    except httpx.HTTPStatusError as e:
        logger.error(f"API HTTP 错误: {e.response.status_code} - {e.response.url}")
        return []
    except Exception as e:
        logger.error(f"从API获取工具失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []


async def _fetch_with_httpx(
    category: Optional[str] = None,
    max_items: int = 100
) -> List[Dict[str, Any]]:
    """使用 httpx 抓取工具数据（可能无法获取动态内容）"""
    base_url = "http://devmaster.cn"
    tools_url = f"{base_url}/tools"
    
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            follow_redirects=True
        ) as client:
            resp = await client.get(tools_url)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            tools = []
            
            # 尝试查找工具元素
            tool_elements = []
            selectors = [
                "article",
                "[class*='card']",
                "[class*='item']"
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    tool_elements = elements
                    break
            
            for element in tool_elements[:max_items]:
                tool = _parse_tool_element(element, base_url)
                if tool:
                    if not category:
                        tool["category"] = _auto_categorize_tool(tool)
                    else:
                        tool["category"] = category
                    tools.append(tool)
            
            return tools
            
    except Exception as e:
        logger.error(f"httpx 抓取失败: {e}")
        return []


def _is_tool_link(link) -> bool:
    """判断链接是否是工具链接"""
    href = link.get("href", "")
    text = link.get_text(strip=True)
    
    # 排除一些明显不是工具的链接
    exclude_patterns = [
        "/about", "/contact", "/login", "/register", 
        "/privacy", "/terms", "/help", "/faq"
    ]
    
    if any(pattern in href.lower() for pattern in exclude_patterns):
        return False
    
    # 如果链接文本太短或太长，可能不是工具
    if len(text) < 2 or len(text) > 100:
        return False
    
    return True


def _parse_tool_element(element, base_url: str) -> Optional[Dict[str, Any]]:
    """
    解析单个工具元素
    
    Args:
        element: BeautifulSoup 元素
        base_url: 基础URL
        
    Returns:
        工具字典或 None
    """
    try:
        tool = {
            "name": "",
            "url": "",
            "description": "",
            "category": "other",
            "tags": [],
            "icon": "🔧",
            "view_count": 0,
            "created_at": datetime.now().isoformat() + "Z",
            "is_featured": False
        }
        
        # 查找名称和链接
        name_elem = element.find("a", href=True) or element.find("h1") or element.find("h2") or element.find("h3")
        if name_elem:
            if name_elem.name == "a":
                tool["name"] = name_elem.get_text(strip=True)
                href = name_elem.get("href", "")
                tool["url"] = urljoin(base_url, href)
            else:
                tool["name"] = name_elem.get_text(strip=True)
                # 尝试在父元素中查找链接
                link_elem = element.find("a", href=True)
                if link_elem:
                    href = link_elem.get("href", "")
                    tool["url"] = urljoin(base_url, href)
        
        # 如果没有找到名称，尝试从其他元素获取
        if not tool["name"]:
            title_elem = element.find(class_=lambda x: x and ("title" in x.lower() or "name" in x.lower()))
            if title_elem:
                tool["name"] = title_elem.get_text(strip=True)
        
        # 查找描述
        desc_elem = (
            element.find("p") or 
            element.find(class_=lambda x: x and "desc" in x.lower()) or
            element.find(class_=lambda x: x and "summary" in x.lower())
        )
        if desc_elem:
            tool["description"] = desc_elem.get_text(strip=True)
        
        # 如果没有找到描述，尝试从所有文本中提取
        if not tool["description"]:
            all_text = element.get_text(separator=" ", strip=True)
            # 移除名称部分
            if tool["name"]:
                all_text = all_text.replace(tool["name"], "", 1).strip()
            # 取前200个字符作为描述
            tool["description"] = all_text[:200] if len(all_text) > 200 else all_text
        
        # 查找标签
        tag_elements = element.find_all(class_=lambda x: x and "tag" in x.lower())
        if tag_elements:
            tool["tags"] = [tag.get_text(strip=True) for tag in tag_elements if tag.get_text(strip=True)]
        
        # 查找图标
        icon_elem = element.find("img") or element.find(class_=lambda x: x and "icon" in x.lower())
        if icon_elem:
            if icon_elem.name == "img":
                icon_src = icon_elem.get("src", "")
                if icon_src:
                    tool["icon"] = urljoin(base_url, icon_src)
            else:
                # 可能是 emoji 或字体图标
                icon_text = icon_elem.get_text(strip=True)
                if icon_text:
                    tool["icon"] = icon_text[:1]  # 取第一个字符（可能是emoji）
        
        # 验证必需字段
        if not tool["name"] or not tool["url"]:
            return None
        
        # 清理数据
        tool["name"] = tool["name"].strip()
        tool["url"] = tool["url"].strip()
        tool["description"] = tool["description"].strip()
        
        return tool
        
    except Exception as e:
        logger.warning(f"解析工具元素时出错: {e}")
        return None


def _auto_categorize_tool(tool: Dict[str, Any]) -> str:
    """
    根据工具信息自动分类
    
    Args:
        tool: 工具字典
        
    Returns:
        分类名称
    """
    name_lower = tool.get("name", "").lower()
    desc_lower = tool.get("description", "").lower()
    tags_lower = [tag.lower() for tag in tool.get("tags", [])]
    
    combined_text = f"{name_lower} {desc_lower} {' '.join(tags_lower)}"
    
    # 按优先级检查每个分类
    for category, keywords in CATEGORY_MAPPING.items():
        if category == "other":
            continue
        for keyword in keywords:
            if keyword.lower() in combined_text:
                return category
    
    return "other"


async def fetch_all_devmaster_tools(use_api: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    抓取所有工具并按分类分组
    
    Args:
        use_api: 是否使用API
    
    Returns:
        按分类分组的工具字典
    """
    # 使用API获取所有工具
    if use_api:
        all_tools = await fetch_tools_from_api()
    else:
        all_tools = await fetch_devmaster_tools(max_items=500, use_api=False)
    
    # 按分类分组
    categorized_tools = {}
    for category in CATEGORY_MAPPING.keys():
        categorized_tools[category] = []
    
    for tool in all_tools:
        category = tool.get("category", "other")
        # 如果分类不在映射中，尝试自动分类
        if category not in categorized_tools:
            category = _auto_categorize_tool(tool)
        if category not in categorized_tools:
            category = "other"
        categorized_tools[category].append(tool)
    
    # 统计
    for category, tools in categorized_tools.items():
        if tools:
            logger.info(f"分类 '{category}': {len(tools)} 个工具")
    
    return categorized_tools

