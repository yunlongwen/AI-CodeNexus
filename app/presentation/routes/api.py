"""API路由 - 提供工具和资讯的API接口"""
import json
import os
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pydantic import BaseModel
from loguru import logger
from dotenv import load_dotenv

# 确保加载 .env 文件（如果还没有加载）
try:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"从 {env_path} 加载环境变量")
    else:
        logger.warning(f".env 文件不存在: {env_path}")
except Exception as e:
    logger.warning(f"加载 .env 文件失败: {e}")

from ...services.data_loader import DataLoader

router = APIRouter()

# 配置文件路径
CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "config.json"


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/tools", response_model=PaginatedResponse)
async def get_tools(
    category: Optional[str] = Query(None, description="工具分类"),
    featured: Optional[bool] = Query(None, description="是否热门"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("score", description="排序字段：score, view_count, created_at")
):
    """获取工具列表（支持分页和筛选）"""
    try:
        logger.info(f"获取工具列表: category={category}, featured={featured}, page={page}, sort_by={sort_by}")
        tools, total = DataLoader.get_tools(
            category=category,
            featured=featured,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by
        )
        
        logger.info(f"获取到 {len(tools)} 个工具，总数: {total}")
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            items=tools,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/featured", response_model=PaginatedResponse)
async def get_featured_tools(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("view_count", description="排序字段：score, view_count, created_at")
):
    """获取热门工具列表（按点击量排序）"""
    return await get_tools(
        category=None,  # 热门工具不限制分类
        featured=True,
        page=page,
        page_size=page_size,
        search=None,  # 热门工具不搜索
        sort_by=sort_by  # 按点击量排序
    )


@router.get("/tools/{tool_id_or_identifier}")
async def get_tool_detail(tool_id_or_identifier: str):
    """
    获取工具详情（支持通过ID或identifier查找）
    
    Args:
        tool_id_or_identifier: 工具ID（数字）或identifier（字符串）
    """
    tool = None
    tool_id = None
    
    # 尝试按ID查找（如果是数字）
    try:
        tool_id = int(tool_id_or_identifier)
        tool = DataLoader.get_tool_by_id(tool_id=tool_id)
    except ValueError:
        # 如果不是数字，则按identifier查找
        tool = DataLoader.get_tool_by_id(tool_identifier=tool_id_or_identifier)
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    # 获取实际使用的ID（用于记录点击）
    actual_tool_id = tool.get("id")
    if actual_tool_id:
        tool_id = actual_tool_id
    
    # 获取相关文章（优先使用 identifier，如果没有则使用工具名称）
    tool_name = tool.get("name", "")
    tool_identifier = tool.get("identifier")
    related_articles, total_articles = DataLoader.get_articles_by_tool(
        tool_name=tool_name,
        tool_id=tool_id,
        tool_identifier=tool_identifier,
        page=1,
        page_size=10
    )
    
    return {
        **tool,
        "related_articles": related_articles,
        "related_articles_count": total_articles
    }


@router.get("/news", response_model=PaginatedResponse)
async def get_news(
    category: Optional[str] = Query(None, description="文章分类，不传则获取所有文章。支持的值：programming(编程资讯), ai_news(AI资讯)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("archived_at", description="排序字段：archived_at(归档时间，默认), published_time, score(热度), created_at")
):
    """
    获取资讯列表（不传category则获取所有文章）
    
    分类映射关系：
    - category="programming" -> 文件: programming.json -> UI显示: "编程资讯"
    - category="ai_news" -> 文件: ai_news.json -> UI显示: "AI资讯"
    """
    try:
        articles, total = DataLoader.get_articles(
            category=category,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            items=articles,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取资讯列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-news", response_model=PaginatedResponse)
async def get_ai_news(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("archived_at", description="排序字段：archived_at(归档时间，默认), published_time, score(热度), created_at")
):
    """
    获取AI资讯列表
    
    注意：此端点内部调用 get_news(category="ai_news")
    - category="ai_news" -> 文件: ai_news.json -> UI显示: "AI资讯"
    """
    return await get_news(
        category="ai_news",
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by
    )


@router.get("/recent", response_model=PaginatedResponse)
async def get_recent(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """获取最新资讯（合并编程资讯和AI资讯，按时间排序）"""
    try:
        # 获取所有文章（不分类），按归档时间排序
        articles, total = DataLoader.get_articles(
            category=None,  # 不分类，获取所有文章
            page=page,
            page_size=page_size,
            search=search,
            sort_by="archived_at"  # 按归档时间排序
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            items=articles,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取最新资讯失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config():
    """获取配置文件"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}


@router.post("/articles/click")
async def record_article_click_by_url(url: str = Query(..., description="文章URL")):
    """通过URL记录文章点击，增加热度"""
    try:
        success = DataLoader.increment_article_view_count(url)
        if success:
            return {"ok": True, "message": "点击已记录"}
        else:
            raise HTTPException(status_code=500, detail="记录点击失败")
    except Exception as e:
        logger.error(f"记录文章点击失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/submit")
async def submit_tool(request: dict):
    """提交工具到候选池"""
    try:
        from ...domain.sources.tool_candidates import CandidateTool, load_candidate_pool, save_candidate_pool
        from datetime import datetime
        
        logger.info(f"收到工具提交请求: {request}")
        
        name = request.get("name", "").strip()
        url = request.get("url", "").strip()
        description = request.get("description", "").strip()
        category = request.get("category", "other").strip()
        tags_str = request.get("tags", "").strip()
        icon = request.get("icon", "</>").strip()
        
        if not name or not url:
            raise HTTPException(status_code=400, detail="工具名称和链接不能为空")
        
        # 验证URL格式
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="链接格式不正确，必须以http://或https://开头")
        
        # 加载现有候选池
        candidates = load_candidate_pool()
        logger.info(f"当前工具候选池中有 {len(candidates)} 个工具")
        
        # 检查URL是否已存在
        for candidate in candidates:
            if candidate.url == url:
                logger.warning(f"工具已存在于候选池: {url}")
                return {"ok": False, "message": "该工具已存在于候选池中"}
        
        # 检查是否已在正式工具池中
        all_tools, _ = DataLoader.get_tools(category=None, page=1, page_size=1000)
        for tool in all_tools:
            if tool.get("url") == url:
                logger.warning(f"工具已存在于正式工具池: {url}")
                return {"ok": False, "message": "该工具已存在于工具列表中"}
        
        # 处理标签
        tags = []
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        
        # 创建候选工具
        new_candidate = CandidateTool(
            name=name,
            url=url,
            description=description or name,
            category=category,
            tags=tags,
            icon=icon,
            submitted_by=request.get("submitted_by", "").strip(),
            submitted_at=datetime.now().isoformat() + "Z"
        )
        
        # 添加到候选池
        candidates.append(new_candidate)
        logger.info(f"准备保存候选工具: {name}, URL: {url}, 分类: {category}, 候选池总数: {len(candidates)}")
        
        # 保存候选池
        save_result = save_candidate_pool(candidates)
        logger.info(f"保存工具候选池结果: {save_result}, 候选池大小: {len(candidates)}")
        
        if save_result:
            # 验证文件是否真的保存成功
            from ...domain.sources.tool_candidates import _candidate_data_path
            candidate_path = _candidate_data_path()
            if candidate_path.exists():
                # 重新加载验证
                verify_candidates = load_candidate_pool()
                logger.info(f"验证: 重新加载后工具候选池大小: {len(verify_candidates)} (期望: {len(candidates)})")
                
                # 检查新提交的工具是否在验证列表中
                found = any(c.url == url for c in verify_candidates)
                if found:
                    logger.info("工具已成功保存到候选池")
                    return {"ok": True, "message": "工具已提交成功，等待管理员审核"}
                else:
                    logger.error("工具保存后验证失败：重新加载的候选池中未找到新提交的工具")
                    return {"ok": False, "message": "工具提交失败，请稍后重试"}
            else:
                logger.error(f"工具候选池文件不存在: {candidate_path}")
                return {"ok": False, "message": "工具提交失败，文件保存异常"}
        else:
            logger.error("保存工具候选池失败")
            return {"ok": False, "message": "工具提交失败，请稍后重试"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交工具失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交工具失败: {str(e)}")


@router.get("/admin/verify-code")
async def verify_admin_code(code: str = Query(..., description="授权码")):
    """验证管理员授权码（用于显示管理员入口）"""
    try:
        # 记录接收到的原始编码值
        import urllib.parse
        decoded_code = urllib.parse.unquote(code)
        logger.info(f"授权码验证请求: 原始编码={code}, 解码后={decoded_code}, 长度={len(decoded_code)}")
        
        # 尝试多种方式获取环境变量
        admin_code = os.getenv("AICODING_ADMIN_CODE", "")
        if not admin_code:
            # 尝试从系统环境变量获取
            admin_code = os.environ.get("AICODING_ADMIN_CODE", "")
        
        # 如果还是没有，尝试重新加载 .env 文件
        if not admin_code:
            try:
                env_path = Path(__file__).resolve().parent.parent.parent / ".env"
                if env_path.exists():
                    load_dotenv(env_path, override=True)
                    admin_code = os.getenv("AICODING_ADMIN_CODE", "")
                    logger.info(f"重新加载 .env 文件后，AICODING_ADMIN_CODE={'已设置' if admin_code else '未设置'}")
            except Exception as e:
                logger.error(f"重新加载 .env 文件失败: {e}")
        
        if not admin_code:
            logger.warning("AICODING_ADMIN_CODE 环境变量未配置")
            logger.debug(f"当前所有环境变量中包含ADMIN的: {[k for k in os.environ.keys() if 'ADMIN' in k.upper()]}")
            logger.debug(f"当前所有环境变量: {list(os.environ.keys())[:20]}...")  # 只显示前20个
            # 检查 .env 文件是否存在
            env_path = Path(__file__).resolve().parent.parent.parent / ".env"
            logger.debug(f".env 文件路径: {env_path}, 存在: {env_path.exists()}")
            if env_path.exists():
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        logger.debug(f".env 文件内容（前200字符）: {content[:200]}")
                        if 'AICODING_ADMIN_CODE' in content:
                            logger.warning("检测到 .env 文件中包含 AICODING_ADMIN_CODE，但环境变量未加载，可能需要重启服务器")
                except Exception as e:
                    logger.error(f"读取 .env 文件失败: {e}")
            return {"ok": False, "valid": False}
        
        logger.info(f"环境变量已加载: 配置长度={len(admin_code)}, 配置值前3个字符={admin_code[:3] if len(admin_code) >= 3 else admin_code}")
        
        # 区分大小写比较
        is_valid = decoded_code == admin_code
        logger.info(f"授权码验证结果: 输入='{decoded_code}', 配置='{admin_code}', 匹配={is_valid}")
        logger.info(f"字符对比: 输入长度={len(decoded_code)}, 配置长度={len(admin_code)}")
        if not is_valid and len(decoded_code) == len(admin_code):
            # 如果长度相同但不匹配，逐字符对比
            for i, (c1, c2) in enumerate(zip(decoded_code, admin_code)):
                if c1 != c2:
                    logger.warning(f"第{i+1}个字符不匹配: 输入='{c1}' (ASCII {ord(c1)}), 配置='{c2}' (ASCII {ord(c2)})")
        
        return {"ok": True, "valid": is_valid}
    except Exception as e:
        logger.error(f"验证授权码时发生错误: {e}", exc_info=True)
        return {"ok": False, "valid": False}


@router.post("/tools/{tool_id_or_identifier}/click")
async def record_tool_click(tool_id_or_identifier: str):
    """
    记录工具点击，增加热度（支持通过ID或identifier查找）
    
    Args:
        tool_id_or_identifier: 工具ID（数字）或identifier（字符串）
    """
    try:
        # 尝试按ID查找（如果是数字）
        tool_id = None
        tool_identifier = None
        
        try:
            tool_id = int(tool_id_or_identifier)
        except ValueError:
            # 如果不是数字，则按identifier查找
            tool_identifier = tool_id_or_identifier
        
        success = DataLoader.increment_tool_view_count(tool_id=tool_id, tool_identifier=tool_identifier)
        if success:
            return {"ok": True, "message": "点击已记录"}
        else:
            raise HTTPException(status_code=500, detail="记录点击失败")
    except Exception as e:
        logger.error(f"记录工具点击失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/submit")
async def submit_article(request: dict):
    """提交资讯到候选池"""
    try:
        from ...domain.sources.ai_candidates import CandidateArticle, load_candidate_pool, save_candidate_pool
        from pathlib import Path
        import random
        
        logger.info(f"收到提交请求: {request}")
        
        title = request.get("title", "").strip()
        url = request.get("url", "").strip()
        category = request.get("category", "programming")
        summary = request.get("summary", "").strip()
        
        if not title or not url:
            raise HTTPException(status_code=400, detail="标题和链接不能为空")
        
        # 加载现有候选池
        candidates = load_candidate_pool()
        logger.info(f"当前候选池中有 {len(candidates)} 篇文章")
        
        # 检查URL是否已存在
        for candidate in candidates:
            if candidate.url == url:
                logger.warning(f"文章已存在于候选池: {url}")
                return {"ok": False, "message": "该文章已存在于候选池中"}
        
        # 随机分配关键字（从配置的关键字列表中）
        try:
            from ...config_loader import load_crawler_keywords
            keywords = load_crawler_keywords()
            if not keywords:
                # 如果没有配置关键字，使用默认关键字
                keywords = [
                    "AI编程", "Python", "JavaScript", "开发工具", "技术资讯",
                    "编程技巧", "开源项目", "前端开发", "后端开发", "DevOps",
                    "机器学习", "深度学习", "Web开发", "移动开发", "云原生"
                ]
        except Exception as e:
            logger.warning(f"加载关键字配置失败，使用默认关键字: {e}")
            keywords = [
                "AI编程", "Python", "JavaScript", "开发工具", "技术资讯",
                "编程技巧", "开源项目", "前端开发", "后端开发", "DevOps",
                "机器学习", "深度学习", "Web开发", "移动开发", "云原生"
            ]
        
        keyword = random.choice(keywords) if keywords else "用户提交"
        
        # 创建候选文章
        source = "用户提交"
        if category == "ai_news":
            source = "用户提交-AI资讯"
        elif category == "programming":
            source = "用户提交-编程资讯"
        
        new_candidate = CandidateArticle(
            title=title,
            url=url,
            source=source,
            summary=summary or title,  # 如果没有摘要，使用标题
            crawled_from=f"user_submit:{keyword}"  # 使用关键字作为crawled_from
        )
        
        # 添加到候选池
        candidates.append(new_candidate)
        logger.info(f"准备保存候选文章: {title}, URL: {url}, 关键字: {keyword}, 候选池总数: {len(candidates)}")
        
        # 验证候选文章对象
        try:
            from dataclasses import asdict
            candidate_dict = asdict(new_candidate)
            logger.debug(f"候选文章字典: {candidate_dict}")
        except Exception as e:
            logger.error(f"转换候选文章为字典失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"数据处理失败: {str(e)}")
        
        # 保存候选池
        try:
            save_result = save_candidate_pool(candidates)
            logger.info(f"保存候选池结果: {save_result}, 候选池大小: {len(candidates)}")
            
            if save_result:
                # 验证文件是否真的保存成功
                from ...domain.sources.ai_candidates import _candidate_data_path
                candidate_path = _candidate_data_path()
                if candidate_path.exists():
                    # 重新加载验证
                    verify_candidates = load_candidate_pool()
                    logger.info(f"验证: 重新加载后候选池大小: {len(verify_candidates)} (期望: {len(candidates)})")
                    if len(verify_candidates) >= len(candidates):
                        # 检查新文章是否真的在文件中
                        found = any(c.url == url for c in verify_candidates)
                        if found:
                            logger.info(f"用户提交文章已成功添加到候选池: {title} (关键字: {keyword})")
                            return {
                                "ok": True,
                                "message": "提交成功，文章已进入审核队列",
                                "keyword": keyword
                            }
                        else:
                            logger.error(f"验证失败: 新文章未在重新加载的候选池中找到")
                            raise HTTPException(status_code=500, detail="保存验证失败：文章未找到")
                    else:
                        logger.error(f"验证失败: 保存后重新加载的候选池大小不匹配 (期望: {len(candidates)}, 实际: {len(verify_candidates)})")
                        raise HTTPException(status_code=500, detail="保存验证失败，请稍后重试")
                else:
                    logger.error(f"保存后文件不存在: {candidate_path}")
                    raise HTTPException(status_code=500, detail="保存失败：文件未创建")
            else:
                logger.error(f"保存候选池返回False: {title}")
                raise HTTPException(status_code=500, detail="保存到候选池失败，请稍后重试")
        except HTTPException:
            raise
        except Exception as save_error:
            logger.error(f"保存候选池时发生异常: {save_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"保存失败: {str(save_error)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交文章失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


@router.get("/prompts", response_model=PaginatedResponse)
async def get_prompts(
    category: Optional[str] = Query(None, description="提示词分类"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """获取提示词列表（支持分页和筛选）"""
    try:
        prompts, total = DataLoader.get_prompts(
            category=category,
            page=page,
            page_size=page_size,
            search=search
        )
        total_pages = (total + page_size - 1) // page_size
        return PaginatedResponse(
            items=prompts,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取提示词列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{identifier}")
async def get_prompt_content(identifier: str):
    """获取指定提示词的内容"""
    try:
        content = DataLoader.get_prompt_content(identifier)
        if content is None:
            raise HTTPException(status_code=404, detail="提示词不存在")
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词内容失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", response_model=PaginatedResponse)
async def get_rules(
    category: Optional[str] = Query(None, description="规则分类"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """获取规则列表（支持分页和筛选）"""
    try:
        rules, total = DataLoader.get_rules(
            category=category,
            page=page,
            page_size=page_size,
            search=search
        )
        total_pages = (total + page_size - 1) // page_size
        return PaginatedResponse(
            items=rules,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取规则列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources", response_model=PaginatedResponse)
async def get_resources(
    type: Optional[str] = Query(None, description="资源类型（教程/文章）"),
    category: Optional[str] = Query(None, description="资源分类"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """获取社区资源列表（支持分页和筛选）"""
    try:
        resources, total = DataLoader.get_resources(
            type=type,
            category=category,
            page=page,
            page_size=page_size,
            search=search
        )
        total_pages = (total + page_size - 1) // page_size
        return PaginatedResponse(
            items=resources,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"获取社区资源列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly/{weekly_id}")
async def get_weekly(weekly_id: str):
    """获取每周资讯内容"""
    try:
        # app/presentation/routes/api.py -> app/presentation/routes -> app/presentation -> app -> 项目根目录
        weekly_file = Path(__file__).resolve().parent.parent.parent.parent / "data" / "weekly" / f"{weekly_id}.md"
        
        if not weekly_file.exists():
            raise HTTPException(status_code=404, detail="Weekly not found")
        
        with open(weekly_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        lines = content.split('\n')
        
        # 解析文章信息
        articles = {
            'ai': [],  # AI资讯
            'programming': []  # 编程资讯
        }
        current_category = None
        current_article = {}
        
        title_line = ''
        time_range = ''
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 解析主标题
            if line.startswith('# '):
                title_line = line[2:].strip()
                continue
            
            # 解析时间范围
            if line.startswith('时间范围：'):
                time_range = line.replace('时间范围：', '').strip()
                continue
            
            # 解析分类标题
            if line.startswith('## 🤖 AI资讯'):
                current_category = 'ai'
                continue
            elif line.startswith('## 💻 编程资讯'):
                current_category = 'programming'
                continue
            
            # 解析文章条目（以数字开头，如 "1. 标题"）
            if re.match(r'^\d+\.\s+', line):
                # 保存上一个文章
                if current_article and current_category:
                    articles[current_category].append(current_article)
                
                # 开始新文章
                title = re.sub(r'^\d+\.\s+', '', line).strip()
                current_article = {
                    'title': title,
                    'summary': '',
                    'source': '',
                    'url': ''
                }
                continue
            
            # 解析文章详情
            if current_article:
                if line.startswith('来源：'):
                    current_article['source'] = line.replace('来源：', '').strip()
                elif line.startswith('链接：'):
                    current_article['url'] = line.replace('链接：', '').strip()
                elif line and not line.startswith('---') and not line.startswith('统计信息') and not line.startswith('本报告'):
                    # 摘要（不是来源、链接、分隔符的行）
                    if not current_article['summary']:
                        current_article['summary'] = line
        
        # 保存最后一个文章
        if current_article and current_category:
            articles[current_category].append(current_article)
        
        # 反转列表，使最新的内容在最前面
        articles['ai'].reverse()
        articles['programming'].reverse()
        
        # 生成HTML
        html_parts = []
        
        # 标题和时间
        html_parts.append(f'<h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">{title_line}</h1>')
        if time_range:
            html_parts.append(f'<p class="text-base text-gray-400 tech-font mb-6">{time_range}</p>')
        
        # 先显示编程资讯
        if articles['programming']:
            html_parts.append('<h2 class="text-2xl font-bold text-gray-100 mb-4 mt-8">💻 编程资讯</h2>')
            html_parts.append('<div class="space-y-4 mb-8">')
            for article in articles['programming']:
                article_html = '<div class="glass rounded-lg border border-dark-border p-4 hover:border-neon-cyan transition-all">'
                if article['url']:
                    article_html += f'<a href="{article["url"]}" target="_blank" class="block">'
                    article_html += f'<h3 class="text-lg font-semibold text-neon-cyan hover:text-neon-purple mb-2 transition-colors">{article["title"]}</h3>'
                    article_html += '</a>'
                else:
                    article_html += f'<h3 class="text-lg font-semibold text-gray-100 mb-2">{article["title"]}</h3>'
                
                if article['summary'] and article['summary'] != '暂无摘要':
                    article_html += f'<p class="text-sm text-gray-400 mb-2">{article["summary"]}</p>'
                
                if article['source']:
                    article_html += f'<p class="text-xs text-gray-500">来源：{article["source"]}</p>'
                
                article_html += '</div>'
                html_parts.append(article_html)
            html_parts.append('</div>')
        
        # 再显示AI资讯
        if articles['ai']:
            html_parts.append('<h2 class="text-2xl font-bold text-gray-100 mb-4 mt-8">🤖 AI资讯</h2>')
            html_parts.append('<div class="space-y-4 mb-8">')
            for article in articles['ai']:
                article_html = '<div class="glass rounded-lg border border-dark-border p-4 hover:border-neon-cyan transition-all">'
                if article['url']:
                    article_html += f'<a href="{article["url"]}" target="_blank" class="block">'
                    article_html += f'<h3 class="text-lg font-semibold text-neon-cyan hover:text-neon-purple mb-2 transition-colors">{article["title"]}</h3>'
                    article_html += '</a>'
                else:
                    article_html += f'<h3 class="text-lg font-semibold text-gray-100 mb-2">{article["title"]}</h3>'
                
                if article['summary'] and article['summary'] != '暂无摘要':
                    article_html += f'<p class="text-sm text-gray-400 mb-2">{article["summary"]}</p>'
                
                if article['source']:
                    article_html += f'<p class="text-xs text-gray-500">来源：{article["source"]}</p>'
                
                article_html += '</div>'
                html_parts.append(article_html)
            html_parts.append('</div>')
        
        html_content = '\n'.join(html_parts)
        
        return {
            "title": title_line or weekly_id.replace('weekly', 'Week ').replace('2025', '2025 '),
            "description": time_range or "每周资讯汇总",
            "content": html_content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取每周资讯失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly")
async def list_weekly():
    """获取每周资讯文件列表"""
    try:
        # app/presentation/routes/api.py -> app/presentation/routes -> app/presentation -> app -> 项目根目录
        weekly_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "weekly"
        
        logger.info(f"每周资讯目录路径: {weekly_dir}")
        logger.info(f"目录是否存在: {weekly_dir.exists()}")
        
        if not weekly_dir.exists():
            logger.warning(f"每周资讯目录不存在: {weekly_dir}")
            return {"items": []}
        
        # 获取所有.md文件
        weekly_files = []
        for file_path in weekly_dir.glob("*.md"):
            weekly_id = file_path.stem  # 文件名（不含扩展名）
            # 格式化显示名称：2025weekly49 -> 2025 Week 49
            weekly_files.append({
                "id": weekly_id,
                "name": weekly_id,
                "filename": file_path.name
            })
        
        logger.info(f"找到 {len(weekly_files)} 个每周资讯文件: {[f['id'] for f in weekly_files]}")
        
        # 按文件名倒序排列（最新的在前）
        weekly_files.sort(key=lambda x: x["id"], reverse=True)
        
        result = {"items": weekly_files}
        logger.info(f"返回数据: {result}")
        return result
    except Exception as e:
        logger.error(f"获取每周资讯列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
