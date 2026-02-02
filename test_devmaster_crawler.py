# -*- coding: utf-8 -*-
"""测试 DevMaster 资讯爬虫"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.devmaster_news_service import DevMasterNewsService
from app.infrastructure.db.database import init_db


async def main():
    """测试爬虫"""
    
    print("=" * 80)
    print("测试 DevMaster 资讯爬虫")
    print("=" * 80)
    
    # 初始化数据库
    await init_db()
    
    # 创建服务实例
    service = DevMasterNewsService()
    
    # 执行抓取
    print("\n开始抓取...")
    count = await service.crawl_and_archive_today_news()
    
    print("\n" + "=" * 80)
    print(f"抓取完成！成功归档 {count} 篇资讯")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

