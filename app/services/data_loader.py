"""数据加载服务 - 支持分页加载工具和资讯数据"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger
import os
from urllib.parse import urlparse, parse_qs

# 数据目录路径（指向项目根目录的data文件夹）
# app/services/data_loader.py -> app/services -> app -> 项目根目录 -> data
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TOOLS_DIR = DATA_DIR / "tools"
ARTICLES_DIR = DATA_DIR / "articles"


class DataLoader:
    """数据加载器 - 支持分页和筛选"""
    
    @staticmethod
    def _load_json_file(file_path: Path) -> List[Dict]:
        """加载JSON文件"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"加载文件失败 {file_path}: {e}")
            return []
    
    @staticmethod
    def _save_json_file(file_path: Path, data: List[Dict]) -> bool:
        """保存JSON文件"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")
            return False
    
    @staticmethod
    def get_tools(
        category: Optional[str] = None,
        featured: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: str = "score"
    ) -> Tuple[List[Dict], int]:
        """
        获取工具列表（支持分页）
        
        Args:
            category: 工具分类
            featured: 是否热门（True/False/None）
            page: 页码（从1开始）
            page_size: 每页数量
            search: 搜索关键词（搜索名称和描述）
            sort_by: 排序字段（score, view_count, created_at）
        
        Returns:
            (工具列表, 总数)
        """
        # 加载所有工具文件
        all_tools = []
        
        # 如果只需要热门工具，只加载 featured.json
        if featured is True:
            featured_file = TOOLS_DIR / "featured.json"
            featured_tools = DataLoader._load_json_file(featured_file)
            all_tools.extend(featured_tools)
        else:
            # 加载热门工具
            featured_file = TOOLS_DIR / "featured.json"
            featured_tools = DataLoader._load_json_file(featured_file)
            all_tools.extend(featured_tools)
            
            # 按分类加载工具（如果有分类文件）
            if category:
                category_file = TOOLS_DIR / f"{category}.json"
                category_tools = DataLoader._load_json_file(category_file)
                all_tools.extend(category_tools)
            else:
                # 加载所有分类文件
                for category_file in TOOLS_DIR.glob("*.json"):
                    if category_file.name != "featured.json":
                        category_tools = DataLoader._load_json_file(category_file)
                        all_tools.extend(category_tools)
        
        # 去重（基于id），保留第一次出现的工具（featured.json 中的工具优先）
        seen_ids = set()
        unique_tools = []
        for tool in all_tools:
            tool_id = tool.get("id")
            if tool_id and tool_id not in seen_ids:
                seen_ids.add(tool_id)
                unique_tools.append(tool)
        
        logger.debug(f"加载工具总数: {len(unique_tools)}, featured参数: {featured}")
        
        # 筛选
        filtered_tools = unique_tools
        
        if featured is not None:
            # 确保工具有 is_featured 字段，如果没有则默认为 False
            filtered_tools = [
                t for t in filtered_tools 
                if t.get("is_featured", False) == featured
            ]
            logger.debug(f"筛选后工具数量 (featured={featured}): {len(filtered_tools)}")
        
        if category:
            filtered_tools = [t for t in filtered_tools if t.get("category") == category]
        
        if search:
            # 确保 search 是字符串
            search_str = str(search).strip() if search else ""
            if search_str:
                search_lower = search_str.lower()
                filtered_tools = [
                    t for t in filtered_tools
                    if search_lower in t.get("name", "").lower()
                    or search_lower in t.get("description", "").lower()
                ]
        
        # 排序
        reverse = sort_by in ["score", "view_count", "created_at"]
        logger.debug(f"排序前工具数量: {len(filtered_tools)}, sort_by={sort_by}, reverse={reverse}")
        
        if sort_by == "score":
            filtered_tools.sort(key=lambda x: x.get("score", 0), reverse=reverse)
        elif sort_by == "view_count":
            # 按点击量排序，相同点击量按时间排序
            # 使用元组排序，view_count降序，created_at降序
            filtered_tools.sort(
                key=lambda x: (
                    -x.get("view_count", 0),  # 点击量降序（用负数实现）
                    x.get("created_at", "") or "1970-01-01T00:00:00Z"  # 时间降序（字符串比较）
                ),
                reverse=False  # 因为view_count已经用负数，所以reverse=False
            )
        elif sort_by == "created_at":
            filtered_tools.sort(
                key=lambda x: x.get("created_at", ""),
                reverse=reverse
            )
        
        logger.debug(f"排序后工具数量: {len(filtered_tools)}")
        
        # 分页
        total = len(filtered_tools)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_tools = filtered_tools[start:end]
        
        logger.debug(f"分页后工具数量: {len(paginated_tools)}, total={total}, start={start}, end={end}")
        
        return paginated_tools, total
    
    @staticmethod
    def get_tool_by_id(tool_id: Optional[int] = None, tool_identifier: Optional[str] = None) -> Optional[Dict]:
        """
        根据ID或identifier获取工具详情
        
        Args:
            tool_id: 工具ID（数字）
            tool_identifier: 工具identifier（字符串，优先使用）
        
        Returns:
            工具详情字典，如果未找到则返回None
        """
        # 优先使用 identifier 查找（更可靠，因为 identifier 是唯一的）
        if tool_identifier:
            for tool_file in TOOLS_DIR.glob("*.json"):
                tools = DataLoader._load_json_file(tool_file)
                for tool in tools:
                    if tool.get("identifier") == tool_identifier:
                        return tool
        
        # 如果没有 identifier 或 identifier 未匹配，则使用 ID 查找
        if tool_id is not None:
            for tool_file in TOOLS_DIR.glob("*.json"):
                tools = DataLoader._load_json_file(tool_file)
                for tool in tools:
                    if tool.get("id") == tool_id:
                        return tool
        
        return None
    
    @staticmethod
    def get_articles(
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: str = "published_time"
    ) -> Tuple[List[Dict], int]:
        """
        获取文章列表（支持分页）
        
        Args:
            category: 文章分类（programming, ai_news等）
            page: 页码（从1开始）
            page_size: 每页数量
            search: 搜索关键词
            sort_by: 排序字段（archived_at归档时间默认, published_time, score热度, created_at）
        
        Returns:
            (文章列表, 总数)
        """
        all_articles = []
        
        # 加载所有文章文件（处理分类名称到文件名的映射）
        # 
        # 映射关系说明：
        # - category="programming" -> 文件: programming.json -> UI显示: "编程资讯"
        # - category="ai_news" -> 文件: ai_news.json -> UI显示: "AI资讯"
        if category:
            # ai_news -> ai_news.json, programming -> programming.json
            category_file_name = f"{category}.json"
            category_file = ARTICLES_DIR / category_file_name
            articles = DataLoader._load_json_file(category_file)
            # 为缺少日期字段的文章补充日期（使用文件修改时间作为采纳日期）
            file_mtime = datetime.fromtimestamp(os.path.getmtime(category_file)) if category_file.exists() else datetime.now()
            for article in articles:
                if not article.get("archived_at") and not article.get("created_at") and not article.get("published_time"):
                    # 如果完全没有日期字段，使用文件修改时间
                    article["archived_at"] = file_mtime.isoformat() + "Z"
                    article["created_at"] = file_mtime.isoformat() + "Z"
                elif not article.get("archived_at"):
                    # 如果有其他日期但没有archived_at，使用created_at或published_time作为archived_at
                    article["archived_at"] = article.get("created_at") or article.get("published_time") or file_mtime.isoformat() + "Z"
            all_articles.extend(articles)
        else:
            # 加载所有分类文件
            for article_file in ARTICLES_DIR.glob("*.json"):
                articles = DataLoader._load_json_file(article_file)
                # 为缺少日期字段的文章补充日期（使用文件修改时间作为采纳日期）
                file_mtime = datetime.fromtimestamp(os.path.getmtime(article_file)) if article_file.exists() else datetime.now()
                for article in articles:
                    if not article.get("archived_at") and not article.get("created_at") and not article.get("published_time"):
                        # 如果完全没有日期字段，使用文件修改时间
                        article["archived_at"] = file_mtime.isoformat() + "Z"
                        article["created_at"] = file_mtime.isoformat() + "Z"
                    elif not article.get("archived_at"):
                        # 如果有其他日期但没有archived_at，使用created_at或published_time作为archived_at
                        article["archived_at"] = article.get("created_at") or article.get("published_time") or file_mtime.isoformat() + "Z"
                all_articles.extend(articles)
        
        # 去重（优先使用id，如果没有id则使用url作为唯一标识符）
        seen_ids = set()
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            article_id = article.get("id")
            article_url = article.get("url", "").strip()
            
            # 如果有id，使用id去重
            if article_id:
                if article_id not in seen_ids:
                    seen_ids.add(article_id)
                    unique_articles.append(article)
            # 如果没有id但有url，使用url去重
            elif article_url:
                if article_url not in seen_urls:
                    seen_urls.add(article_url)
                    unique_articles.append(article)
            # 如果既没有id也没有url，直接添加（这种情况应该很少）
            else:
                unique_articles.append(article)
        
        # 筛选
        filtered_articles = unique_articles
        
        # 如果指定了category，筛选匹配的文章
        # 注意：如果文章没有category字段，但从指定分类文件加载的，也应该包含
        # 因为文件本身已经代表了分类（programming.json -> programming分类）
        if category:
            filtered_articles = [
                a for a in filtered_articles 
                # 如果文章有category字段，必须匹配；如果没有category字段，说明是从指定分类文件加载的，应该包含
                if not a.get("category") or a.get("category") == category
            ]
        
        if search:
            # 确保 search 是字符串
            search_str = str(search).strip() if search else ""
            if search_str:
                search_lower = search_str.lower()
                filtered_articles = [
                    a for a in filtered_articles
                    if search_lower in a.get("title", "").lower()
                    or search_lower in a.get("summary", "").lower()
                ]
        
        # 排序
        reverse = True  # 默认倒序
        if sort_by == "archived_at":
            # 按归档时间排序（默认，倒序）
            filtered_articles.sort(
                key=lambda x: x.get("archived_at", x.get("created_at", "")),
                reverse=reverse
            )
        elif sort_by == "published_time":
            filtered_articles.sort(
                key=lambda x: x.get("published_time", ""),
                reverse=reverse
            )
        elif sort_by == "score":
            # 按热度排序，相同热度按时间排序
            filtered_articles.sort(
                key=lambda x: (
                    x.get("view_count", 0),  # 热度（点击次数）
                    x.get("archived_at", x.get("published_time", x.get("created_at", "")))  # 时间作为次要排序
                ),
                reverse=reverse
            )
        elif sort_by == "created_at":
            filtered_articles.sort(
                key=lambda x: x.get("created_at", ""),
                reverse=reverse
            )
        
        # 分页
        total = len(filtered_articles)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_articles = filtered_articles[start:end]
        
        return paginated_articles, total
    
    @staticmethod
    def get_recent_items(
        type_filter: str = "all",
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict], int]:
        """
        获取最近收录的内容
        
        Args:
            type_filter: 类型筛选（all, articles, tools）
            page: 页码
            page_size: 每页数量
        
        Returns:
            (内容列表, 总数)
        """
        all_items = []
        
        if type_filter in ["all", "articles"]:
            # 加载所有文章
            for article_file in ARTICLES_DIR.glob("*.json"):
                articles = DataLoader._load_json_file(article_file)
                for article in articles:
                    article["item_type"] = "article"
                    all_items.append(article)
        
        if type_filter in ["all", "tools"]:
            # 加载所有工具
            for tool_file in TOOLS_DIR.glob("*.json"):
                tools = DataLoader._load_json_file(tool_file)
                for tool in tools:
                    tool["item_type"] = "tool"
                    all_items.append(tool)
        
        # 按归档时间或创建时间排序（优先使用归档时间）
        all_items.sort(
            key=lambda x: x.get("archived_at", x.get("created_at", "")),
            reverse=True
        )
        
        # 分页
        total = len(all_items)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_items = all_items[start:end]
        
        return paginated_items, total
    
    @staticmethod
    def archive_article_to_category(article: Dict, category: str, tool_tags: List[str] = None) -> bool:
        """
        将文章归档到指定分类的JSON文件
        
        Args:
            article: 文章数据字典
            category: 分类名称（如 programming, ai_news）
            tool_tags: 工具标签列表（可选）
        
        Returns:
            是否成功
        """
        try:
            # 生成文章ID（如果没有）
            if "id" not in article:
                # 从现有文件中找到最大ID
                max_id = 0
                for article_file in ARTICLES_DIR.glob("*.json"):
                    articles = DataLoader._load_json_file(article_file)
                    for a in articles:
                        if "id" in a and a["id"] > max_id:
                            max_id = a["id"]
                article["id"] = max_id + 1
            
            # 添加时间戳
            # 注意：archived_at 是必需字段，表示采纳时间，必须设置
            now = datetime.now()
            now_iso = now.isoformat() + "Z"
            
            if "created_at" not in article:
                article["created_at"] = now_iso
            
            if "published_time" not in article:
                article["published_time"] = article["created_at"]
            
            # 记录归档时间（采纳时间）- 必需字段，强制设置
            article["archived_at"] = now_iso
            
            # 初始化热度（点击次数）
            if "view_count" not in article:
                article["view_count"] = 0
            
            # 设置分类
            article["category"] = category
            
            # 设置工具标签
            if tool_tags:
                article["tool_tags"] = tool_tags
                # 同时添加到tags中，方便统一查询
                if "tags" not in article:
                    article["tags"] = []
                article["tags"].extend([tag for tag in tool_tags if tag not in article["tags"]])
            
            # 加载目标文件（处理分类名称到文件名的映射）
            # 
            # 映射关系说明：
            # - category="programming" -> 文件: programming.json -> UI显示: "编程资讯"
            # - category="ai_news" -> 文件: ai_news.json -> UI显示: "AI资讯"
            category_file_name = f"{category}.json"
            category_file = ARTICLES_DIR / category_file_name
            articles = DataLoader._load_json_file(category_file)
            
            # 检查是否已存在（基于URL）
            for existing in articles:
                if existing.get("url") == article.get("url"):
                    logger.warning(f"文章已存在于 {category}.json: {article.get('url')}")
                    return False
            
            # 添加到列表
            articles.append(article)
            
            # 保存文件
            return DataLoader._save_json_file(category_file, articles)
        except Exception as e:
            logger.error(f"归档文章失败: {e}")
            return False
    
    @staticmethod
    def get_articles_by_tool(tool_name: str = None, tool_id: int = None, tool_identifier: str = None, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        """
        根据工具名称、ID或标识符获取相关文章
        
        Args:
            tool_name: 工具名称（可选）
            tool_id: 工具ID（可选）
            tool_identifier: 工具标识符（可选，用于匹配文章的tool_tags）
            page: 页码
            page_size: 每页数量
        
        Returns:
            (文章列表, 总数)
        """
        # 如果提供了tool_identifier，优先使用它来获取工具信息
        if tool_identifier:
            tool = DataLoader.get_tool_by_id(tool_identifier=tool_identifier)
            if tool:
                tool_name = tool.get("name", "") or tool_name
        # 如果没有tool_identifier但提供了tool_id，则通过tool_id获取工具信息
        elif tool_id:
            tool = DataLoader.get_tool_by_id(tool_id=tool_id)
            if tool:
                tool_name = tool.get("name", "") or tool_name
                tool_identifier = tool.get("identifier") or tool_identifier
        
        all_articles = []
        
        # 加载所有文章文件
        for article_file in ARTICLES_DIR.glob("*.json"):
            articles = DataLoader._load_json_file(article_file)
            all_articles.extend(articles)
        
        # 筛选包含该工具标签的文章
        filtered_articles = []
        for article in all_articles:
            matched = False
            
            # 优先使用 identifier 匹配（精确匹配）
            if tool_identifier:
                tool_tags = article.get("tool_tags", []) or []
                if tool_identifier in tool_tags:
                    matched = True
            
            # 如果没有 identifier 或 identifier 未匹配，使用工具名称匹配（模糊匹配）
            if not matched and tool_name:
                tool_name_lower = tool_name.lower()
                tool_tags = article.get("tool_tags", []) or article.get("tags", [])
                if any(tool_name_lower in str(tag).lower() or str(tag).lower() in tool_name_lower for tag in tool_tags):
                    matched = True
            
            if matched:
                filtered_articles.append(article)
        
        # 按发布时间排序
        filtered_articles.sort(
            key=lambda x: x.get("published_time", x.get("created_at", "")),
            reverse=True
        )
        
        # 分页
        total = len(filtered_articles)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_articles = filtered_articles[start:end]
        
        return paginated_articles, total
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        规范化URL，用于比较
        对于微信文章URL，提取基础路径和关键参数进行比较
        
        Args:
            url: 原始URL
        
        Returns:
            规范化后的URL字符串（用于比较）
        """
        if not url or not url.strip():
            return ""
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            # 对于微信文章URL (mp.weixin.qq.com)，提取基础路径
            if "mp.weixin.qq.com" in parsed.netloc:
                # 微信文章URL格式: https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx&idx=xxx&sn=xxx
                # 或者: https://mp.weixin.qq.com/s?src=11&timestamp=xxx&ver=xxx&signature=xxx
                # 提取关键参数进行比较
                query_params = parse_qs(parsed.query)
                # 优先使用 __biz, mid, idx, sn 这些稳定参数（这些是微信文章的稳定标识）
                if "__biz" in query_params or "mid" in query_params:
                    key_params = []
                    for key in ["__biz", "mid", "idx", "sn"]:
                        if key in query_params:
                            key_params.append(f"{key}={query_params[key][0]}")
                    if key_params:
                        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{'&'.join(sorted(key_params))}"
                # 如果只有动态参数（src, timestamp, ver, signature），这些参数会变化
                # 这种情况下，无法通过URL规范化来准确判断是否为同一篇文章
                # 因为timestamp和signature每次抓取都可能不同
                # 所以对于只有动态参数的URL，返回None表示无法规范化，只能进行精确匹配
                if "src" in query_params and "signature" in query_params:
                    # 对于只有动态参数的URL，返回None表示无法规范化
                    # 这样在is_article_archived中只会进行精确匹配，不会进行规范化匹配
                    return None
                # 如果没有稳定参数，使用完整URL（去除可能的尾随空格）
                return url
            else:
                # 对于其他URL，去除尾随斜杠和空格
                normalized = url.rstrip('/').strip()
                return normalized
        except Exception as e:
            logger.warning(f"URL规范化失败: {url}, 错误: {e}")
            # 如果解析失败，返回去除空格后的原始URL
            return url.strip()
    
    @staticmethod
    def is_article_archived(url: str) -> bool:
        """
        检查文章是否已归档
        
        Args:
            url: 文章URL
        
        Returns:
            是否已归档
        """
        try:
            if not url or not url.strip():
                return False
            
            url = url.strip()
            
            # 遍历所有文章文件，检查URL是否存在
            # 注意：只检查正式归档的文章文件，不包括候选池文件
            for article_file in ARTICLES_DIR.glob("*.json"):
                # 排除候选池文件
                if article_file.name in ["ai_candidates.json"]:
                    continue
                
                articles = DataLoader._load_json_file(article_file)
                for article in articles:
                    article_url = article.get("url", "")
                    if not article_url:
                        continue
                    
                    article_url = article_url.strip()
                    
                    # 首先尝试精确匹配（最可靠）
                    if article_url == url:
                        logger.debug(f"文章已归档（精确匹配）: {url[:80]}...")
                        return True
                    
                    # 如果精确匹配失败，尝试规范化后比较
                    # 注意：对于只有动态参数的微信URL，规范化可能返回None，此时跳过规范化匹配
                    normalized_input_url = DataLoader._normalize_url(url)
                    normalized_article_url = DataLoader._normalize_url(article_url)
                    
                    # 只有当两个URL都能成功规范化时，才进行规范化匹配
                    if normalized_input_url is not None and normalized_article_url is not None:
                        if normalized_article_url == normalized_input_url:
                            logger.debug(f"文章已归档（规范化匹配）: {url[:80]}...")
                            return True
                    
            return False
        except Exception as e:
            logger.error(f"检查文章归档状态失败: {e}")
            return False
    
    @staticmethod
    def increment_article_view_count(url: str) -> bool:
        """
        增加文章的点击次数（热度）
        
        Args:
            url: 文章URL
        
        Returns:
            是否成功
        """
        try:
            # 遍历所有文章文件，找到对应的文章
            for article_file in ARTICLES_DIR.glob("*.json"):
                articles = DataLoader._load_json_file(article_file)
                updated = False
                
                for article in articles:
                    if article.get("url", "").strip() == url.strip():
                        # 增加点击次数
                        article["view_count"] = article.get("view_count", 0) + 1
                        updated = True
                        break
                
                # 如果找到并更新了，保存文件
                if updated:
                    return DataLoader._save_json_file(article_file, articles)
            
            logger.warning(f"未找到文章: {url}")
            return False
        except Exception as e:
            logger.error(f"增加文章点击次数失败: {e}")
            return False
    
    @staticmethod
    def increment_tool_view_count(tool_id: Optional[int] = None, tool_identifier: Optional[str] = None) -> bool:
        """
        增加工具的点击次数（热度）
        
        Args:
            tool_id: 工具ID（可选）
            tool_identifier: 工具identifier（可选，优先使用）
        
        Returns:
            是否成功
        """
        try:
            # 优先使用 identifier 查找工具
            if tool_identifier:
                for tool_file in TOOLS_DIR.glob("*.json"):
                    tools = DataLoader._load_json_file(tool_file)
                    updated = False
                    
                    for tool in tools:
                        if tool.get("identifier") == tool_identifier:
                            # 增加点击次数
                            tool["view_count"] = tool.get("view_count", 0) + 1
                            updated = True
                            break
                    
                    # 如果找到并更新了，保存文件
                    if updated:
                        return DataLoader._save_json_file(tool_file, tools)
            
            # 如果没有 identifier 或 identifier 未匹配，使用 ID 查找
            if tool_id is not None:
                for tool_file in TOOLS_DIR.glob("*.json"):
                    tools = DataLoader._load_json_file(tool_file)
                    updated = False
                    
                    for tool in tools:
                        if tool.get("id") == tool_id:
                            # 增加点击次数
                            tool["view_count"] = tool.get("view_count", 0) + 1
                            updated = True
                            break
                    
                    # 如果找到并更新了，保存文件
                    if updated:
                        return DataLoader._save_json_file(tool_file, tools)
            
            logger.warning(f"未找到工具: tool_id={tool_id}, tool_identifier={tool_identifier}")
            return False
        except Exception as e:
            logger.error(f"增加工具点击次数失败: {e}")
            return False
    
    @staticmethod
    def archive_tool_to_category(tool: Dict, category: str) -> bool:
        """
        将工具保存到指定分类的JSON文件中
        
        Args:
            tool: 工具数据字典
            category: 工具分类
        
        Returns:
            是否成功
        """
        try:
            category_file = TOOLS_DIR / f"{category}.json"
            
            # 加载现有工具
            tools = DataLoader._load_json_file(category_file)
            
            # 检查是否已存在（基于URL）
            for existing_tool in tools:
                if existing_tool.get("url") == tool.get("url"):
                    logger.warning(f"工具已存在于 {category}.json: {tool.get('url')}")
                    return False
            
            # 添加到列表
            tools.append(tool)
            
            # 保存文件
            return DataLoader._save_json_file(category_file, tools)
        except Exception as e:
            logger.error(f"保存工具到分类失败: {e}")
            return False
