"""
修复过期微信链接的脚本

该脚本会：
1. 扫描所有文章数据文件
2. 识别包含临时参数的微信链接
3. 尝试访问每个链接并提取永久链接
4. 更新数据文件
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
from loguru import logger

# 添加项目根目录到路径
import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.sources.article_crawler import (
    normalize_weixin_url,
    extract_weixin_permanent_url,
)


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


async def fetch_permanent_url(url: str) -> Optional[str]:
    """
    尝试获取微信文章的永久链接
    
    Args:
        url: 原始URL（可能包含临时参数）
        
    Returns:
        永久链接，如果无法获取则返回None
    """
    if "mp.weixin.qq.com" not in url:
        return None
    
    # 先尝试规范化URL（移除临时参数）
    normalized = normalize_weixin_url(url)
    if normalized != url and not any(param in normalized for param in ["timestamp=", "signature="]):
        # 规范化成功，返回规范化后的URL
        return normalized
    
    # 如果规范化后仍有临时参数，需要访问链接获取永久链接
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
            
            # 从HTML中提取永久链接
            permanent_url = extract_weixin_permanent_url(html_content, url)
            if permanent_url:
                return permanent_url
            
            # 如果无法提取永久链接，尝试规范化响应URL
            if response.url and "mp.weixin.qq.com" in str(response.url):
                normalized_response = normalize_weixin_url(str(response.url))
                if not any(param in normalized_response for param in ["timestamp=", "signature="]):
                    return normalized_response
            
            # 最后尝试规范化原始URL
            return normalize_weixin_url(url)
            
    except httpx.HTTPError as e:
        logger.warning(f"无法访问链接 {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"处理链接 {url} 时出错: {e}")
        return None


async def fix_file(file_path: Path) -> Dict[str, int]:
    """
    修复单个文件中的过期链接
    
    Returns:
        Dict: 统计信息 {"fixed": 修复数量, "failed": 失败数量, "total": 总数}
    """
    logger.info(f"正在处理文件: {file_path}")
    
    # 读取文件
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"无法读取文件 {file_path}: {e}")
        return {"fixed": 0, "failed": 0, "total": 0, "skipped": 0}
    
    if not isinstance(data, list):
        logger.warning(f"文件 {file_path} 不是列表格式，跳过")
        return {"fixed": 0, "failed": 0, "total": 0, "skipped": 1}
    
    # 查找过期链接
    expired_items = find_expired_weixin_links(data)
    if not expired_items:
        logger.info(f"文件 {file_path} 中没有找到过期链接")
        return {"fixed": 0, "failed": 0, "total": 0, "skipped": 0}
    
    logger.info(f"找到 {len(expired_items)} 个过期链接")
    
    # 修复每个过期链接
    stats = {"fixed": 0, "failed": 0, "total": len(expired_items)}
    updated = False
    
    for idx, item in expired_items:
        old_url = item.get("url", "")
        logger.info(f"处理链接 [{idx}]: {item.get('title', '')[:50]}...")
        
        # 尝试获取永久链接
        permanent_url = await fetch_permanent_url(old_url)
        
        if permanent_url and permanent_url != old_url:
            # 检查是否是真正的永久链接（不包含临时参数）
            if not any(param in permanent_url for param in ["timestamp=", "signature="]):
                item["url"] = permanent_url
                stats["fixed"] += 1
                updated = True
                logger.success(f"✓ 修复成功: {old_url[:60]}... -> {permanent_url[:60]}...")
            else:
                stats["failed"] += 1
                logger.warning(f"✗ 获取的链接仍包含临时参数: {permanent_url[:60]}...")
        else:
            stats["failed"] += 1
            logger.warning(f"✗ 无法获取永久链接: {old_url[:60]}...")
        
        # 添加延迟，避免请求过快
        await asyncio.sleep(1)
    
    # 如果修复了链接，保存文件
    if updated:
        try:
            # 创建备份
            backup_path = file_path.with_suffix(f".json.backup")
            with file_path.open("r", encoding="utf-8") as src, backup_path.open("w", encoding="utf-8") as dst:
                dst.write(src.read())
            logger.info(f"已创建备份: {backup_path}")
            
            # 保存修复后的文件
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.success(f"✓ 文件已更新: {file_path}")
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")
            stats["failed"] = stats["total"]
    
    return stats


async def main():
    """主函数"""
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
    
    logger.info("=" * 60)
    logger.info("开始修复过期微信链接")
    logger.info("=" * 60)
    
    total_stats = {"fixed": 0, "failed": 0, "total": 0, "skipped": 0}
    
    for file_path in files_to_fix:
        if not file_path.exists():
            logger.warning(f"文件不存在，跳过: {file_path}")
            continue
        
        stats = await fix_file(file_path)
        total_stats["fixed"] += stats["fixed"]
        total_stats["failed"] += stats["failed"]
        total_stats["total"] += stats["total"]
        total_stats["skipped"] += stats.get("skipped", 0)
        
        logger.info("")
    
    # 打印总结
    logger.info("=" * 60)
    logger.info("修复完成！")
    logger.info(f"总计: {total_stats['total']} 个过期链接")
    logger.info(f"修复成功: {total_stats['fixed']} 个")
    logger.info(f"修复失败: {total_stats['failed']} 个")
    logger.info(f"跳过文件: {total_stats['skipped']} 个")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

