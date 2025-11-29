"""
清理周报文件中的过期微信链接

该脚本会：
1. 扫描所有周报文件（data/weekly/*.md）
2. 识别包含临时参数的微信链接
3. 删除包含过期链接的文章条目
"""
import re
from pathlib import Path
from typing import List, Tuple
from loguru import logger


def find_expired_links_in_md(content: str) -> List[Tuple[int, str, str]]:
    """
    在Markdown内容中查找包含过期链接的文章条目
    
    Returns:
        List[Tuple[int, str, str]]: [(line_number, title, url), ...]
    """
    expired_items = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检查是否包含过期链接
        if '链接：' in line and 'mp.weixin.qq.com' in line:
            if any(param in line for param in ["timestamp=", "signature=", "src=11"]):
                # 查找对应的标题（向上查找几行）
                title = "未知标题"
                title_line_idx = i
                
                # 向上查找标题（通常是数字开头的行，如 "1. 标题"）
                for j in range(max(0, i - 3), i):
                    if re.match(r'^\d+\.\s+', lines[j]):
                        title = lines[j].strip()
                        title_line_idx = j
                        break
                
                expired_items.append((title_line_idx, title, line.strip()))
        
        i += 1
    
    return expired_items


def remove_expired_articles_from_md(file_path: Path, dry_run: bool = True) -> dict:
    """
    从Markdown文件中删除包含过期链接的文章条目
    
    Args:
        file_path: Markdown文件路径
        dry_run: 如果为True，只显示将要删除的内容，不实际删除
    
    Returns:
        Dict: 统计信息
    """
    logger.info(f"正在处理文件: {file_path}")
    
    try:
        with file_path.open("r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"无法读取文件 {file_path}: {e}")
        return {"removed": 0, "total": 0}
    
    # 查找过期链接
    expired_items = find_expired_links_in_md(content)
    if not expired_items:
        logger.info(f"文件 {file_path} 中没有找到过期链接")
        return {"removed": 0, "total": 0}
    
    logger.info(f"找到 {len(expired_items)} 个过期链接的条目")
    
    # 显示将要删除的条目
    for title_line_idx, title, url_line in expired_items:
        logger.warning(f"  [{title_line_idx}] {title[:50]}... | {url_line[:60]}...")
    
    if dry_run:
        logger.info(f"【预览模式】将会删除 {len(expired_items)} 个条目")
        return {"removed": 0, "total": len(expired_items)}
    
    # 实际删除过期条目
    lines = content.split('\n')
    lines_to_remove = set()
    
    for title_line_idx, title, url_line in expired_items:
        # 找到需要删除的行范围（从标题行开始，到下一个条目或空行结束）
        start_idx = title_line_idx
        
        # 找到结束位置（下一个数字开头的行或空行）
        end_idx = len(lines)
        for i in range(title_line_idx + 1, len(lines)):
            line = lines[i].strip()
            # 如果遇到空行，检查下一行是否为下一个条目
            if line == '':
                # 检查下一行是否是新条目（数字开头）或新分类
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^\d+\.\s+', next_line) or next_line.startswith('## '):
                        end_idx = i + 1
                        break
            # 如果遇到下一个数字开头的行（同一分类内）
            elif re.match(r'^\d+\.\s+', line):
                end_idx = i
                break
            # 如果遇到新的分类标题
            elif line.startswith('## '):
                end_idx = i
                break
        
        # 标记要删除的行（包括标题行到链接行及之后的空行）
        for i in range(start_idx, min(end_idx, len(lines))):
            lines_to_remove.add(i)
    
    # 删除标记的行
    lines_list = [line for i, line in enumerate(lines) if i not in lines_to_remove]
    
    # 重新编号AI资讯和编程资讯部分的条目
    current_category = None
    item_num = 0
    
    new_lines = []
    for i, line in enumerate(lines_list):
        # 检测分类标题
        if '## 🤖 AI资讯' in line or '## 💻 编程资讯' in line:
            current_category = line
            item_num = 0
            new_lines.append(line)
            continue
        
        # 如果是数字开头的条目，重新编号
        match = re.match(r'^(\d+)\.\s+(.+)', line)
        if match:
            item_num += 1
            new_lines.append(f"{item_num}. {match.group(2)}")
        else:
            new_lines.append(line)
    
    # 更新统计信息
    content_new = '\n'.join(new_lines)
    
    # 更新统计信息行
    stats_match = re.search(r'本周共推荐\s+(\d+)\s+篇优质资讯', content_new)
    if stats_match:
        current_count = int(stats_match.group(1))
        removed_count = len(expired_items)
        new_count = current_count - removed_count
        
        # 更新总数
        content_new = re.sub(
            r'本周共推荐\s+\d+\s+篇优质资讯',
            f'本周共推荐 {new_count} 篇优质资讯',
            content_new
        )
        
        # 统计实际剩余的文章数量
        # 提取AI资讯部分
        ai_section_match = re.search(r'## 🤖 AI资讯\n\n(.*?)(?=\n\n---|\n\n##)', content_new, re.DOTALL)
        ai_section = ai_section_match.group(1) if ai_section_match else ""
        ai_count = len(re.findall(r'^\d+\.\s+', ai_section, re.MULTILINE))
        
        # 提取编程资讯部分
        programming_section_match = re.search(r'## 💻 编程资讯\n\n(.*?)(?=\n\n---|\n\n统计)', content_new, re.DOTALL)
        programming_section = programming_section_match.group(1) if programming_section_match else ""
        programming_count = len(re.findall(r'^\d+\.\s+', programming_section, re.MULTILINE))
        
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
    
    # 保存文件
    try:
        # 创建备份
        backup_path = file_path.with_suffix(f".md.backup")
        with file_path.open("r", encoding="utf-8") as src, backup_path.open("w", encoding="utf-8") as dst:
            dst.write(src.read())
        logger.info(f"已创建备份: {backup_path}")
        
        # 保存更新后的文件
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content_new)
        logger.success(f"✓ 文件已更新: {file_path}")
    except Exception as e:
        logger.error(f"保存文件失败 {file_path}: {e}")
        return {"removed": 0, "total": len(expired_items)}
    
    return {"removed": len(expired_items), "total": len(expired_items)}


def main():
    """主函数"""
    import sys
    
    # 项目根目录
    project_root = Path(__file__).resolve().parents[1]
    weekly_dir = project_root / "data" / "weekly"
    
    # 查找所有周报文件
    weekly_files = list(weekly_dir.glob("*.md"))
    
    if not weekly_files:
        logger.warning(f"在 {weekly_dir} 中没有找到周报文件")
        return
    
    # 检查命令行参数
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    force = "--force" in sys.argv or "-f" in sys.argv
    
    if dry_run:
        logger.info("=" * 60)
        logger.info("【预览模式】将显示要删除的条目，但不会实际删除")
        logger.info("=" * 60)
    elif force:
        logger.warning("=" * 60)
        logger.warning("【强制执行模式】将删除所有过期链接的条目")
        logger.warning("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("【实际执行模式】将删除所有过期链接的条目")
        logger.warning("输入 'yes' 确认继续，或使用 --dry-run 先预览，或使用 --force 跳过确认")
        logger.warning("=" * 60)
        confirmation = input("确认删除？(yes/no): ")
        if confirmation.lower() != "yes":
            logger.info("已取消操作")
            return
    
    total_stats = {"removed": 0, "total": 0}
    
    for file_path in weekly_files:
        stats = remove_expired_articles_from_md(file_path, dry_run=dry_run)
        total_stats["removed"] += stats["removed"]
        total_stats["total"] += stats["total"]
        logger.info("")
    
    # 打印总结
    logger.info("=" * 60)
    if dry_run:
        logger.info("预览完成！")
        logger.info(f"总计找到: {total_stats['total']} 个过期链接的条目")
        logger.info(f"运行脚本时不加 --dry-run 参数将删除这些条目")
    else:
        logger.info("删除完成！")
        logger.info(f"总计删除: {total_stats['removed']} 个条目")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

