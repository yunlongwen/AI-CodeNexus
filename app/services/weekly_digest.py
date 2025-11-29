"""
每周资讯推荐功能
当有资讯被采纳或归档时，自动更新本周的Markdown文件
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger

# 数据目录路径
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
WEEKLY_DIR = DATA_DIR / "weekly"
ARTICLES_DIR = DATA_DIR / "articles"


def get_week_number(date: Optional[datetime] = None) -> tuple[int, int]:
    """
    获取指定日期所在的年份和第几周
    
    Args:
        date: 日期，如果为None则使用当前日期
    
    Returns:
        (年份, 周数) 元组，例如 (2025, 47)
    """
    if date is None:
        date = datetime.now()
    
    # 使用 ISO 8601 标准计算周数
    # ISO 8601: 周一为一周的开始，第一周是包含1月4日的那一周
    year, week, _ = date.isocalendar()
    return year, week


def get_weekly_filename(year: int, week: int) -> str:
    """
    获取周报文件名
    
    Args:
        year: 年份
        week: 周数
    
    Returns:
        文件名，例如 "2025weekly47.md"
    """
    return f"{year}weekly{week}.md"


def get_weekly_filepath(year: int, week: int) -> Path:
    """
    获取周报文件路径
    
    Args:
        year: 年份
        week: 周数
    
    Returns:
        文件路径
    """
    WEEKLY_DIR.mkdir(exist_ok=True)
    filename = get_weekly_filename(year, week)
    return WEEKLY_DIR / filename


def get_this_week_articles() -> Dict[str, List[Dict]]:
    """
    获取本周新增的资讯（AI资讯和编程资讯）
    
    Returns:
        {
            "ai_news": [...],  # AI资讯列表
            "programming": [...]  # 编程资讯列表
        }
    """
    year, week = get_week_number()
    
    # 计算本周的开始时间（周一 00:00:00）
    today = datetime.now()
    days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
    week_start = today - timedelta(days=days_since_monday)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 计算本周的结束时间（周日 23:59:59）
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    logger.debug(f"[周报] 本周时间范围: {week_start} 到 {week_end}")
    
    # 加载AI资讯
    ai_news_file = ARTICLES_DIR / "ai_news.json"
    ai_news = []
    if ai_news_file.exists():
        with open(ai_news_file, 'r', encoding='utf-8') as f:
            ai_news = json.load(f)
    
    # 加载编程资讯
    programming_file = ARTICLES_DIR / "programming.json"
    programming = []
    if programming_file.exists():
        with open(programming_file, 'r', encoding='utf-8') as f:
            programming = json.load(f)
    
    # 筛选本周新增的资讯
    def is_this_week(article: Dict) -> bool:
        """判断文章是否在本周"""
        archived_at = article.get("archived_at")
        if not archived_at:
            return False
        
        try:
            # 解析时间戳
            if isinstance(archived_at, str):
                # 尝试解析 ISO 格式
                try:
                    # 处理带Z的ISO格式
                    if archived_at.endswith('Z'):
                        archived_at_clean = archived_at[:-1]
                    else:
                        archived_at_clean = archived_at
                    article_time = datetime.fromisoformat(archived_at_clean)
                except ValueError:
                    # 如果解析失败，尝试其他格式
                    try:
                        article_time = datetime.strptime(archived_at, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        logger.warning(f"[周报] 无法解析时间格式: {archived_at}")
                        return False
            else:
                # 假设是时间戳
                article_time = datetime.fromtimestamp(archived_at)
            
            # 转换为本地时间（如果需要）
            if article_time.tzinfo:
                article_time = article_time.replace(tzinfo=None)
            
            return week_start <= article_time <= week_end
        except Exception as e:
            logger.warning(f"[周报] 解析文章时间失败: {archived_at}, 错误: {e}")
            return False
    
    ai_news_this_week = [a for a in ai_news if is_this_week(a)]
    programming_this_week = [a for a in programming if is_this_week(a)]
    
    logger.info(f"[周报] 本周新增资讯: AI资讯 {len(ai_news_this_week)} 篇, 编程资讯 {len(programming_this_week)} 篇")
    
    return {
        "ai_news": ai_news_this_week,
        "programming": programming_this_week,
    }


def format_article_for_wechat(article: Dict, index: int) -> str:
    """
    格式化单篇文章为微信公众号格式
    
    Args:
        article: 文章数据
        index: 序号
    
    Returns:
        格式化后的Markdown字符串
    """
    title = article.get("title", "无标题")
    url = article.get("url", "")
    source = article.get("source", "未知来源")
    summary = article.get("summary", "")
    
    # 微信公众号格式：使用数字序号和链接
    # 注意：微信公众号不支持Markdown链接，所以使用纯文本格式
    result = f"{index}. {title}\n"
    if summary:
        # 限制摘要长度，避免过长
        summary_short = summary[:100] + "..." if len(summary) > 100 else summary
        result += f"   {summary_short}\n"
    result += f"   来源：{source}\n"
    result += f"   链接：{url}\n"
    
    return result


def generate_weekly_markdown(year: int, week: int) -> str:
    """
    生成周报Markdown内容
    
    Args:
        year: 年份
        week: 周数
    
    Returns:
        Markdown内容
    """
    articles = get_this_week_articles()
    ai_news = articles["ai_news"]
    programming = articles["programming"]
    
    # 计算本周的日期范围
    today = datetime.now()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    week_start_str = week_start.strftime("%Y年%m月%d日")
    week_end_str = week_end.strftime("%Y年%m月%d日")
    
    # 生成Markdown内容（适合微信公众号格式）
    markdown = f"""# 第{week}周资讯推荐

时间范围：{week_start_str} - {week_end_str}

---

## 🤖 AI资讯

"""
    
    if ai_news:
        for i, article in enumerate(ai_news, 1):
            markdown += format_article_for_wechat(article, i) + "\n"
    else:
        markdown += "本周暂无AI资讯。\n\n"
    
    markdown += "\n---\n\n## 💻 编程资讯\n\n"
    
    if programming:
        for i, article in enumerate(programming, 1):
            markdown += format_article_for_wechat(article, i) + "\n"
    else:
        markdown += "本周暂无编程资讯。\n\n"
    
    markdown += f"""
---

统计信息：
本周共推荐 {len(ai_news) + len(programming)} 篇优质资讯
- AI资讯：{len(ai_news)} 篇
- 编程资讯：{len(programming)} 篇

---
本报告由 [AI-CodeNexus](https://aicoding.100kwhy.fun) 自动生成
"""
    
    return markdown


def update_weekly_digest() -> bool:
    """
    更新本周的周报Markdown文件
    当有资讯被采纳或归档时调用此函数
    
    Returns:
        是否成功更新
    """
    try:
        year, week = get_week_number()
        filepath = get_weekly_filepath(year, week)
        
        logger.info(f"[周报] 开始更新周报: {get_weekly_filename(year, week)}")
        
        # 生成Markdown内容
        markdown = generate_weekly_markdown(year, week)
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        logger.info(f"[周报] 周报已更新: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"[周报] 更新周报失败: {e}", exc_info=True)
        return False

