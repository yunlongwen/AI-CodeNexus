"""微信公众号发布接口"""
import os
from typing import Dict, Any, Optional

import httpx
from loguru import logger

from ..config_loader import load_env_var


class WeChatMPClient:
    """微信公众号客户端"""
    
    def __init__(self):
        # 优先从 .env 文件读取，如果不存在则从环境变量读取
        self.appid = load_env_var("WECHAT_MP_APPID") or os.getenv("WECHAT_MP_APPID")
        self.secret = load_env_var("WECHAT_MP_SECRET") or os.getenv("WECHAT_MP_SECRET")
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        
        # 如果配置了，记录日志（不记录敏感信息）
        if self.appid and self.secret:
            logger.info("微信公众号配置已加载")
        else:
            logger.warning("微信公众号 AppID 或 Secret 未配置，相关功能将不可用")
    
    async def get_access_token(self) -> Optional[str]:
        """获取 access_token"""
        if self.access_token and self.token_expires_at and self.token_expires_at > __import__("time").time():
            return self.access_token
        
        if not self.appid or not self.secret:
            logger.error("微信公众号 AppID 或 Secret 未配置")
            return None
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.appid}&secret={self.secret}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                data = resp.json()
                
                if "access_token" in data:
                    self.access_token = data["access_token"]
                    expires_in = data.get("expires_in", 7200)
                    self.token_expires_at = __import__("time").time() + expires_in - 300  # 提前5分钟刷新
                    return self.access_token
                else:
                    logger.error(f"获取 access_token 失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"获取 access_token 异常: {e}")
            return None
    
    async def upload_media(self, media_type: str, media_path: str) -> Optional[str]:
        """上传素材"""
        token = await self.get_access_token()
        if not token:
            return None
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type={media_type}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(media_path, "rb") as f:
                    files = {"media": f}
                    resp = await client.post(url, files=files)
                    data = resp.json()
                    
                    if "media_id" in data:
                        return data["media_id"]
                    else:
                        logger.error(f"上传素材失败: {data}")
                        return None
        except Exception as e:
            logger.error(f"上传素材异常: {e}")
            return None
    
    async def upload_media_from_bytes(self, media_type: str, media_data: bytes, filename: str = "image.jpg") -> Optional[str]:
        """从字节数据上传素材（草稿箱需要使用永久素材的 media_id）"""
        token = await self.get_access_token()
        if not token:
            return None
        
        try:
            # 草稿箱需要使用永久素材，而不是临时素材
            # 永久素材接口：/cgi-bin/material/add_material
            # 注意：对于图片类型的永久素材，description 参数是可选的，但如果不提供可能会使用默认值导致错误
            # 我们提供一个简短的 description，确保不会超出长度限制
            url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type={media_type}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"media": (filename, media_data, "image/jpeg")}
                # 对于图片类型，description 参数是可选的，但提供一个简短的描述更安全
                # description 长度限制通常是 120 字符，我们使用很短的描述
                if media_type == "image":
                    # 图片类型：提供简短的 description（不超过 120 字符）
                    data_fields = {"description": "封面图"}  # 简短描述，确保不会超出限制
                else:
                    # 其他类型：不提供 description
                    data_fields = {}
                
                logger.info(f"上传永久素材，type={media_type}, description={data_fields.get('description', '无')}")
                resp = await client.post(url, files=files, data=data_fields)
                result = resp.json()
                
                if "media_id" in result:
                    media_id = result["media_id"]
                    logger.info(f"成功上传永久素材，media_id: {media_id} (类型: {type(media_id)}, 长度: {len(str(media_id))})")
                    if not isinstance(media_id, str):
                        media_id = str(media_id)
                    return media_id
                else:
                    logger.error(f"上传永久素材失败: {result}")
                    # 如果永久素材失败，尝试使用临时素材（作为备用方案）
                    logger.info("永久素材上传失败，尝试使用临时素材接口...")
                    return await self._upload_temp_media_from_bytes(media_type, media_data, filename)
        except Exception as e:
            logger.error(f"上传素材异常: {e}")
            return None
    
    async def _upload_temp_media_from_bytes(self, media_type: str, media_data: bytes, filename: str = "image.jpg") -> Optional[str]:
        """从字节数据上传临时素材（备用方案）"""
        token = await self.get_access_token()
        if not token:
            return None
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type={media_type}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"media": (filename, media_data, "image/jpeg")}
                resp = await client.post(url, files=files)
                data = resp.json()
                
                if "media_id" in data:
                    media_id = data["media_id"]
                    logger.info(f"成功上传临时素材，media_id: {media_id} (类型: {type(media_id)}, 长度: {len(str(media_id))})")
                    # 确保返回的是字符串类型
                    if not isinstance(media_id, str):
                        logger.warning(f"media_id 不是字符串类型，转换为字符串: {type(media_id)}")
                        media_id = str(media_id)
                    return media_id
                else:
                    logger.error(f"上传临时素材失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"上传临时素材异常: {e}")
            return None
    
    async def get_default_thumb_media_id(self) -> Optional[str]:
        """获取默认封面图的 media_id（如果不存在则创建一个简单的占位图）"""
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        try:
            # 创建一个简单的默认封面图（640x360，微信公众号推荐尺寸）
            width, height = 640, 360
            img = Image.new("RGB", (width, height), color=(74, 144, 226))  # 蓝色背景
            
            # 在图片上添加文字
            draw = ImageDraw.Draw(img)
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                # 如果找不到字体，使用默认字体
                font = ImageFont.load_default()
            
            text = "每日新闻精选"
            # 计算文字位置（居中）
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            position = ((width - text_width) // 2, (height - text_height) // 2)
            
            draw.text(position, text, fill=(255, 255, 255), font=font)
            
            # 将图片转换为字节
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG", quality=85)
            img_bytes.seek(0)
            
            # 上传图片
            media_id = await self.upload_media_from_bytes("image", img_bytes.getvalue(), "default_thumb.jpg")
            if media_id:
                logger.info("成功上传默认封面图")
            return media_id
        except ImportError:
            logger.warning("PIL 未安装，无法生成默认封面图。请安装 Pillow: pip install Pillow")
            return None
        except Exception as e:
            logger.error(f"创建默认封面图失败: {e}")
            return None
    
    async def create_draft(self, articles: list) -> Optional[str]:
        """创建草稿"""
        token = await self.get_access_token()
        if not token:
            return None
        
        try:
            # 验证文章数据格式
            if not articles or len(articles) == 0:
                logger.error("文章列表为空")
                return None
            
            if len(articles) > 8:
                logger.error(f"文章数量超过限制（最多8篇），当前：{len(articles)}")
                return None
            
            # 验证每篇文章的必填字段（根据官方文档）
            for idx, article in enumerate(articles):
                if not article.get("title"):
                    logger.error(f"第 {idx + 1} 篇文章缺少 title 字段（必填）")
                    return None
                if not article.get("author"):
                    logger.error(f"第 {idx + 1} 篇文章缺少 author 字段（必填）")
                    return None
                # digest 字段是可选的，如果提供则长度不能超过 54 字符
                if article.get("digest"):
                    digest_len = len(article.get("digest", ""))
                    if digest_len > 54:
                        logger.error(f"第 {idx + 1} 篇文章的 digest 字段长度超过限制（54字符），当前: {digest_len}")
                        return None
                if not article.get("content"):
                    logger.error(f"第 {idx + 1} 篇文章缺少 content 字段（必填）")
                    return None
                # 验证 content 字段长度（必须少于2万字符，小于1M）
                content = article.get("content", "")
                content_len = len(content)
                if content_len >= 20000:
                    logger.error(f"第 {idx + 1} 篇文章的 content 字段长度超过限制（2万字符），当前: {content_len}")
                    return None
                # 检查是否包含外部图片URL（会被过滤，可能导致问题）
                if "http://" in content or "https://" in content:
                    # 检查是否是图片URL
                    import re
                    img_url_pattern = r'<img[^>]+src=["\'](https?://[^"\']+)["\']'
                    if re.search(img_url_pattern, content):
                        logger.warning(f"第 {idx + 1} 篇文章的 content 包含外部图片URL，将被微信过滤")
                # 检查是否包含JS（会被去除）
                if "<script" in content.lower() or "javascript:" in content.lower():
                    logger.warning(f"第 {idx + 1} 篇文章的 content 包含JS，将被微信去除")
                # 暂时不验证 content_source_url，逐个排查问题
                # if not article.get("content_source_url"):
                #     logger.error(f"第 {idx + 1} 篇文章缺少 content_source_url 字段（必填）")
                #     return None
                # # 验证 URL 格式
                # url = article.get("content_source_url", "")
                # if not url.startswith(("http://", "https://")):
                #     logger.error(f"第 {idx + 1} 篇文章的 content_source_url 格式不正确: {url}")
                #     return None
                # 验证 article_type 字段（必填）
                if not article.get("article_type"):
                    logger.warning(f"第 {idx + 1} 篇文章缺少 article_type 字段，默认设置为 'news'")
                    article["article_type"] = "news"
                # 检查 thumb_media_id，如果没有则使用默认封面图
                if not article.get("thumb_media_id"):
                    logger.info(f"第 {idx + 1} 篇文章缺少 thumb_media_id，使用默认封面图")
                    default_thumb_id = await self.get_default_thumb_media_id()
                    if not default_thumb_id:
                        logger.error("无法获取默认封面图 media_id")
                        return None
                    logger.info(f"获取到默认封面图 media_id: {default_thumb_id} (长度: {len(default_thumb_id)})")
                    article["thumb_media_id"] = default_thumb_id
                # 确保 thumb_media_id 不为空且格式正确
                thumb_media_id = article.get("thumb_media_id", "")
                if not thumb_media_id:
                    logger.error(f"第 {idx + 1} 篇文章的 thumb_media_id 为空（必填）")
                    return None
                if not isinstance(thumb_media_id, str) or len(thumb_media_id) == 0:
                    logger.error(f"第 {idx + 1} 篇文章的 thumb_media_id 格式不正确: {type(thumb_media_id)}, 值: {thumb_media_id}")
                    return None
                logger.info(f"第 {idx + 1} 篇文章使用 thumb_media_id: {thumb_media_id[:50]}... (完整长度: {len(thumb_media_id)})")
                # 移除 show_cover_pic 字段（官方文档示例中没有此字段）
                if "show_cover_pic" in article:
                    del article["show_cover_pic"]
            
            url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
            payload = {"articles": articles}
            
            # 详细记录请求数据，用于调试
            logger.info(f"========== 创建草稿请求开始 ==========")
            logger.info(f"请求 URL: {url}")
            logger.info(f"文章数量: {len(articles)}")
            
            for idx, article in enumerate(articles):
                logger.info(f"--- 文章 {idx + 1} 详细信息 ---")
                logger.info(f"  字段列表: {sorted(article.keys())}")
                logger.info(f"  article_type: {article.get('article_type', 'MISSING')}")
                logger.info(f"  title: {article.get('title', 'MISSING')[:50]}")
                logger.info(f"  author: {article.get('author', 'MISSING')}")
                logger.info(f"  digest: {article.get('digest', 'MISSING')[:50]} (长度: {len(article.get('digest', ''))})")
                logger.info(f"  content: {article.get('content', 'MISSING')[:100]}... (总长度: {len(article.get('content', ''))})")
                logger.info(f"  content_source_url: {article.get('content_source_url', 'MISSING')}")
                logger.info(f"  thumb_media_id: {article.get('thumb_media_id', 'MISSING')[:30]}... (长度: {len(article.get('thumb_media_id', ''))})")
                logger.info(f"  need_open_comment: {article.get('need_open_comment', 'MISSING')}")
                logger.info(f"  only_fans_can_comment: {article.get('only_fans_can_comment', 'MISSING')}")
                
                # 检查是否有官方文档中没有的字段
                official_fields = {
                    "article_type", "title", "author", "digest", "content", 
                    "content_source_url", "thumb_media_id", "need_open_comment", 
                    "only_fans_can_comment", "pic_crop_235_1", "pic_crop_1_1"
                }
                extra_fields = set(article.keys()) - official_fields
                if extra_fields:
                    logger.warning(f"  额外字段（官方文档中没有）: {extra_fields}")
                missing_fields = official_fields - set(article.keys())
                required_fields = {"article_type", "title", "author", "digest", "content", "content_source_url", "thumb_media_id"}
                missing_required = required_fields - set(article.keys())
                if missing_required:
                    logger.error(f"  缺少必填字段: {missing_required}")
            
            # 打印完整的 JSON payload（用于调试）
            import json
            payload_str = json.dumps(payload, ensure_ascii=False, indent=2)
            logger.info(f"完整请求 payload:\n{payload_str}")
            logger.info(f"========== 创建草稿请求结束 ==========")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                
                # 检查响应状态
                logger.info(f"响应状态码: {resp.status_code}")
                logger.info(f"响应头 Content-Type: {resp.headers.get('content-type', 'unknown')}")
                
                # 获取响应文本（用于调试）
                response_text = resp.text
                logger.info(f"响应内容（前500字符）: {response_text[:500]}")
                
                # 尝试解析 JSON
                try:
                    data = resp.json()
                except Exception as json_error:
                    logger.error(f"JSON 解析失败: {json_error}")
                    logger.error(f"完整响应内容: {response_text}")
                    logger.error(f"响应状态码: {resp.status_code}")
                    return None
                
                if "media_id" in data:
                    logger.info(f"成功创建草稿，media_id: {data['media_id']}")
                    return data["media_id"]
                else:
                    logger.error(f"创建草稿失败: {data}")
                    # 记录请求数据以便调试（只记录关键字段）
                    logger.error(f"请求的文章数量: {len(articles)}")
                    for idx, article in enumerate(articles):
                        logger.error(f"文章 {idx + 1} 字段: {list(article.keys())}")
                        # 检查是否有 thumb_media_id 字段
                        if "thumb_media_id" in article:
                            logger.error(f"文章 {idx + 1} 包含 thumb_media_id: {article.get('thumb_media_id')}")
                    return None
        except Exception as e:
            logger.error(f"创建草稿异常: {e}")
            return None
    
    async def publish(self, media_id: str) -> bool:
        """发布草稿"""
        token = await self.get_access_token()
        if not token:
            return False
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={"media_id": media_id})
                data = resp.json()
                
                if data.get("errcode") == 0:
                    return True
                else:
                    logger.error(f"发布失败: {data}")
                    return False
        except Exception as e:
            logger.error(f"发布异常: {e}")
            return False
    
    async def get_draft_list(self, offset: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取草稿箱列表"""
        token = await self.get_access_token()
        if not token:
            return None
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token={token}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={
                    "offset": offset,
                    "count": count,
                    "no_content": 0  # 返回内容
                })
                data = resp.json()
                
                if "item" in data:
                    return data
                else:
                    logger.error(f"获取草稿列表失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"获取草稿列表异常: {e}")
            return None
    
    async def get_draft(self, media_id: str) -> Optional[Dict[str, Any]]:
        """获取草稿详情"""
        token = await self.get_access_token()
        if not token:
            return None
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={"media_id": media_id})
                data = resp.json()
                
                if "news_item" in data:
                    return data
                else:
                    logger.error(f"获取草稿详情失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"获取草稿详情异常: {e}")
            return None
    
    async def update_draft(self, media_id: str, index: int, article: Dict[str, Any]) -> bool:
        """更新草稿中的单篇文章"""
        token = await self.get_access_token()
        if not token:
            return False
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/draft/update?access_token={token}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={
                    "media_id": media_id,
                    "index": index,
                    "articles": article
                })
                data = resp.json()
                
                if data.get("errcode") == 0:
                    return True
                else:
                    logger.error(f"更新草稿失败: {data}")
                    return False
        except Exception as e:
            logger.error(f"更新草稿异常: {e}")
            return False
    
    async def delete_draft(self, media_id: str) -> bool:
        """删除草稿"""
        token = await self.get_access_token()
        if not token:
            return False
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/draft/delete?access_token={token}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={"media_id": media_id})
                data = resp.json()
                
                if data.get("errcode") == 0:
                    return True
                else:
                    logger.error(f"删除草稿失败: {data}")
                    return False
        except Exception as e:
            logger.error(f"删除草稿异常: {e}")
            return False

