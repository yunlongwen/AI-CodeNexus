"""测试微信公众号功能"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.notifier.wechat_mp import WeChatMPClient


async def test_access_token():
    """测试获取 Access Token"""
    print("\n" + "="*60)
    print("测试获取 Access Token")
    print("="*60)
    
    client = WeChatMPClient()
    
    if not client.appid or not client.secret:
        print("❌ 错误：未配置 WECHAT_MP_APPID 或 WECHAT_MP_SECRET")
        print("\n请在 .env 文件中配置：")
        print("WECHAT_MP_APPID=your_appid")
        print("WECHAT_MP_SECRET=your_secret")
        return False
    
    print(f"AppID: {client.appid[:10]}...")
    print("正在获取 Access Token...")
    
    token = await client.get_access_token()
    
    if token:
        print(f"✅ Access Token 获取成功: {token[:20]}...")
        return True
    else:
        print("❌ Access Token 获取失败")
        print("请检查：")
        print("1. AppID 和 Secret 是否正确")
        print("2. 网络连接是否正常")
        print("3. IP 是否在白名单中（如果设置了）")
        return False


async def test_create_draft():
    """测试创建草稿"""
    print("\n" + "="*60)
    print("测试创建草稿")
    print("="*60)
    
    client = WeChatMPClient()
    
    # 测试文章数据
    test_articles = [
        {
            "title": "测试文章标题",
            "author": "测试作者",
            "digest": "这是一篇测试文章的摘要",
            "content": "<p>这是测试文章的内容。</p><p><a href='https://example.com'>阅读原文</a></p>",
            "content_source_url": "https://example.com",
            "thumb_media_id": "",  # 可选
            "show_cover_pic": 1,
        }
    ]
    
    print("正在创建草稿...")
    media_id = await client.create_draft(test_articles)
    
    if media_id:
        print(f"✅ 草稿创建成功，media_id: {media_id}")
        print("\n注意：这只是测试，不会真正发布。")
        print("你可以在微信公众平台的草稿箱中查看。")
        return media_id
    else:
        print("❌ 草稿创建失败")
        print("请检查文章格式和配置")
        return None


async def main():
    """主函数"""
    print("开始测试微信公众号功能...")
    print("\n注意：需要先配置 WECHAT_MP_APPID 和 WECHAT_MP_SECRET")
    
    # 测试 Access Token
    token_ok = await test_access_token()
    
    if not token_ok:
        print("\n⚠️  Access Token 获取失败，无法继续测试")
        return
    
    # 测试创建草稿（可选）
    print("\n是否测试创建草稿？(y/n): ", end="")
    # 在脚本中默认跳过，避免误操作
    # choice = input().strip().lower()
    # if choice == 'y':
    #     await test_create_draft()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    print("\n下一步：")
    print("1. 使用 API 接口测试创建草稿和发布")
    print("2. 访问 http://localhost:8000/docs 查看 API 文档")
    print("3. 参考 docs/deploy/wechat_mp_guide.md 了解详细使用方法")


if __name__ == "__main__":
    asyncio.run(main())

