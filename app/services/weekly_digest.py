"""
每周资讯推荐功能
当有资讯被采纳或归档时，自动更新本周的Markdown文件
"""
import json
import re
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


def delete_article_from_weekly(url: str) -> bool:
    """
    从当前周报中删除指定URL的文章
    
    Args:
        url: 要删除的文章URL
        
    Returns:
        是否成功删除
    """
    try:
        year, week = get_week_number()
        filepath = get_weekly_filepath(year, week)
        
        if not filepath.exists():
            logger.warning(f"周报文件不存在: {filepath}")
            return False
        
        # 读取周报内容
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        url_to_delete = url.strip()
        
        # 查找并删除包含该URL的行
        new_lines = []
        skip_until_number = False
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检查是否包含要删除的URL
            if url_to_delete in line:
                # 找到包含URL的行，需要删除整个条目
                # 向上查找条目开始（数字开头的行）
                start_idx = i
                for j in range(i - 1, -1, -1):
                    if re.match(r'^\d+\.\s+', lines[j]):
                        start_idx = j
                        break
                    # 如果遇到空行，停止
                    if lines[j].strip() == '' and j < i - 1:
                        break
                
                # 向下查找条目结束（下一个数字开头的行或空行后的数字行）
                end_idx = i + 1
                for j in range(i + 1, len(lines)):
                    if re.match(r'^\d+\.\s+', lines[j]):
                        end_idx = j
                        break
                    # 如果遇到空行后跟数字行，也停止
                    if lines[j].strip() == '' and j + 1 < len(lines):
                        if re.match(r'^\d+\.\s+', lines[j + 1]):
                            end_idx = j + 1
                            break
                    # 如果遇到分隔符或统计信息，也停止
                    if lines[j].strip().startswith('---') or lines[j].strip().startswith('统计信息'):
                        end_idx = j
                        break
                
                # 跳过要删除的条目
                i = end_idx
                continue
            
            new_lines.append(line)
            i += 1
        
        # 重新编号剩余的条目
        current_category = None
        item_num = 0
        final_lines = []
        
        for line in new_lines:
            # 检测分类标题
            if '## 🤖 AI资讯' in line or '## 💻 编程资讯' in line:
                current_category = line
                item_num = 0
                final_lines.append(line)
                continue
            
            # 如果是数字开头的条目，重新编号
            match = re.match(r'^(\d+)\.\s+(.+)', line)
            if match:
                item_num += 1
                final_lines.append(f"{item_num}. {match.group(2)}")
            else:
                final_lines.append(line)
        
        # 更新统计信息
        content_new = '\n'.join(final_lines)
        
        # 统计实际剩余的文章数量
        ai_section_match = re.search(r'## 🤖 AI资讯\n\n(.*?)(?=\n\n---|\n\n##)', content_new, re.DOTALL)
        programming_section_match = re.search(r'## 💻 编程资讯\n\n(.*?)(?=\n\n---|\n\n统计)', content_new, re.DOTALL)
        
        ai_count = len(re.findall(r'^\d+\.\s+', ai_section_match.group(1) if ai_section_match else "", re.MULTILINE))
        programming_count = len(re.findall(r'^\d+\.\s+', programming_section_match.group(1) if programming_section_match else "", re.MULTILINE))
        total_count = ai_count + programming_count
        
        # 更新总数
        content_new = re.sub(
            r'本周共推荐\s+\d+\s+篇优质资讯',
            f'本周共推荐 {total_count} 篇优质资讯',
            content_new
        )
        
        # 更新分类统计
        content_new = re.sub(
            r'-\s+AI资讯：\d+\s+篇',
            f'- AI资讯：{ai_count} 篇',
            content_new
        )
        content_new = re.sub(
            r'-\s+编程资讯：\d+\s+篇',
            f'- 编程资讯：{programming_count} 篇',
            content_new
        )
        
        # 保存更新后的周报
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_new)
        
        logger.info(f"从周报中删除文章: {url_to_delete[:60]}...")
        return True
        
    except Exception as e:
        logger.error(f"从周报删除文章失败: {e}", exc_info=True)
        return False


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

