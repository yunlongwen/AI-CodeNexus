"""
删除过期微信链接的文章脚本

该脚本会：
1. 扫描所有文章数据文件
2. 识别包含临时参数的微信链接（已过期）
3. 提供选项：删除过期文章或标记为过期
"""
import json
from pathlib import Path
from typing import Dict, List
from loguru import logger


def find_expired_weixin_links(data: List[Dict]) -> List[tuple]:
    """
    查找数据中所有包含临时参数的微信链接
    
    Returns:
        List[tuple]: [(index, article_dict), ...] 包含过期链接的文章
    """
    expired_items = []
    for idx, item in enumerate(data):
        url = item.get("url", "")
        if url and "mp.weixin.qq.com" in url:
            # 检查是否包含临时参数
            if any(param in url for param in ["timestamp=", "signature=", "src=11"]):
                expired_items.append((idx, item))
    return expired_items


def remove_expired_articles(file_path: Path, dry_run: bool = True) -> Dict[str, int]:
    """
    删除文件中的过期文章
    
    Args:
        file_path: 文件路径
        dry_run: 如果为True，只显示将要删除的文章，不实际删除
    
    Returns:
        Dict: 统计信息
    """
    logger.info(f"正在处理文件: {file_path}")
    
    # 读取文件
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"无法读取文件 {file_path}: {e}")
        return {"removed": 0, "total": 0}
    
    if not isinstance(data, list):
        logger.warning(f"文件 {file_path} 不是列表格式，跳过")
        return {"removed": 0, "total": 0}
    
    # 查找过期链接
    expired_items = find_expired_weixin_links(data)
    if not expired_items:
        logger.info(f"文件 {file_path} 中没有找到过期链接")
        return {"removed": 0, "total": 0}
    
    logger.info(f"找到 {len(expired_items)} 个过期链接的文章")
    
    # 显示将要删除的文章
    for idx, item in expired_items:
        title = item.get("title", "未知标题")
        url = item.get("url", "")[:60]
        logger.warning(f"  [{idx}] {title[:50]}... | {url}...")
    
    if dry_run:
        logger.info(f"【预览模式】将会删除 {len(expired_items)} 篇文章")
        return {"removed": 0, "total": len(expired_items)}
    
    # 实际删除过期文章（从后往前删除，避免索引变化）
    expired_indices = sorted([idx for idx, _ in expired_items], reverse=True)
    removed_count = 0
    
    for idx in expired_indices:
        removed_item = data.pop(idx)
        removed_count += 1
        logger.success(f"✓ 已删除: {removed_item.get('title', '')[:50]}...")
    
    # 保存文件
    try:
        # 创建备份（在删除前，保存原始数据）
        backup_path = file_path.with_suffix(f".json.backup")
        if not backup_path.exists():
            # 只有在备份不存在时才创建，避免覆盖之前的备份
            with file_path.open("r", encoding="utf-8") as src, backup_path.open("w", encoding="utf-8") as dst:
                dst.write(src.read())
            logger.info(f"已创建备份: {backup_path}")
        else:
            logger.info(f"备份已存在，跳过创建: {backup_path}")
        
        # 保存更新后的文件
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.success(f"✓ 文件已更新: {file_path}")
    except Exception as e:
        logger.error(f"保存文件失败 {file_path}: {e}")
        return {"removed": 0, "total": len(expired_items)}
    
    return {"removed": removed_count, "total": len(expired_items)}


def main():
    """主函数"""
    import sys
    
    # 项目根目录
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data" / "articles"
    
    # 要处理的文件列表
    files_to_fix = [
        data_dir / "ai_news.json",
        data_dir / "programming.json",
        data_dir / "ai_coding.json",
        data_dir / "ai_articles.json",
    ]
    
    # 检查命令行参数
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    force = "--force" in sys.argv or "-f" in sys.argv
    if dry_run:
        logger.info("=" * 60)
        logger.info("【预览模式】将显示要删除的文章，但不会实际删除")
        logger.info("=" * 60)
    elif force:
        logger.warning("=" * 60)
        logger.warning("【强制执行模式】将删除所有过期链接的文章")
        logger.warning("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("【实际执行模式】将删除所有过期链接的文章")
        logger.warning("输入 'yes' 确认继续，或使用 --dry-run 先预览，或使用 --force 跳过确认")
        logger.warning("=" * 60)
        confirmation = input("确认删除？(yes/no): ")
        if confirmation.lower() != "yes":
            logger.info("已取消操作")
            return
    
    total_stats = {"removed": 0, "total": 0}
    
    for file_path in files_to_fix:
        if not file_path.exists():
            logger.warning(f"文件不存在，跳过: {file_path}")
            continue
        
        stats = remove_expired_articles(file_path, dry_run=dry_run)
        total_stats["removed"] += stats["removed"]
        total_stats["total"] += stats["total"]
        logger.info("")
    
    # 打印总结
    logger.info("=" * 60)
    if dry_run:
        logger.info("预览完成！")
        logger.info(f"总计找到: {total_stats['total']} 个过期链接的文章")
        logger.info(f"运行脚本时不加 --dry-run 参数将删除这些文章")
    else:
        logger.info("删除完成！")
        logger.info(f"总计删除: {total_stats['removed']} 篇文章")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

