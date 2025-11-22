import asyncio
import sys

# On Windows, the default asyncio event loop (ProactorEventLoop) does not support
# subprocesses, which Playwright needs to launch browsers.
# We switch to SelectorEventLoop, which does.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 在所有模块导入前，从 .env 文件加载环境变量
# 添加错误处理，避免 .env 文件格式错误导致启动失败
try:
    load_dotenv()
except Exception as e:  # noqa: BLE001
    # logger 还未导入，使用 print 输出警告
    print(f"Warning: Failed to load .env file: {e}. Continuing with environment variables...")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .config_loader import load_digest_schedule
from .notifier.wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from .routes import wechat, digest
from .sources.ai_articles import pick_daily_ai_articles, todays_theme, clear_articles
from .sources.ai_candidates import promote_candidates_to_articles, clear_candidate_pool

# 全局 scheduler 实例
scheduler: Optional[AsyncIOScheduler] = None


async def job_send_daily_ai_digest(digest_count: int) -> None:
    """Send AI coding articles digest to WeCom group."""
    now = datetime.now()
    articles = pick_daily_ai_articles(k=digest_count)
    if not articles:
        logger.info("Article pool is empty before scheduled push, promoting from candidates...")
        promoted = promote_candidates_to_articles(per_keyword=2)
        if promoted:
            articles = pick_daily_ai_articles(k=digest_count)
        else:
            logger.warning("No candidates available to promote, skip sending.")
            return

    theme = todays_theme(now)
    date_str = now.strftime("%Y-%m-%d")
    items = [
        {
            "title": a.title,
            "url": a.url,
            "source": a.source,
            "summary": a.summary,
        }
        for a in articles
    ]

    content = build_wecom_digest_markdown(date_str=date_str, theme=theme, items=items)
    logger.info("Sending daily AI digest to WeCom group...")
    await send_markdown_to_wecom(content)
    clear_articles()
    clear_candidate_pool()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时启动 scheduler，关闭时关闭 scheduler"""
    global scheduler

    # 从配置文件加载定时任务参数
    schedule = load_digest_schedule()
    digest_hour = schedule.hour
    digest_minute = schedule.minute
    digest_count = schedule.count

    # 启动时
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    # 配置触发器：优先使用 cron 表达式
    if schedule.cron:
        trigger = CronTrigger.from_crontab(schedule.cron, timezone="Asia/Shanghai")
        scheduler.add_job(
            job_send_daily_ai_digest,
            trigger=trigger,
            id="daily_ai_digest",
            kwargs={"digest_count": digest_count},
            replace_existing=True,
        )
        logger.info(
            "Scheduler started with cron=%r, count=%d.",
            schedule.cron,
            digest_count,
        )
    else:
        scheduler.add_job(
            job_send_daily_ai_digest,
            "cron",
            hour=digest_hour,
            minute=digest_minute,
            id="daily_ai_digest",
            kwargs={"digest_count": digest_count},
            replace_existing=True,
        )
        logger.info(
            "Scheduler started. Daily digest will be sent at %02d:%02d (Asia/Shanghai), "
            "with up to %d articles.",
            digest_hour,
            digest_minute,
            digest_count,
        )

    scheduler.start()

    yield  # 应用运行期间

    # 关闭时
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Daily Digest API",
        description="每日新闻精选 - 自动抓取、筛选、推送系统",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 挂载静态资源目录，用于提供公众号二维码等图片
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    @app.get("/news", response_class=HTMLResponse)
    @app.get("/ai-news", response_class=HTMLResponse)
    @app.get("/tools", response_class=HTMLResponse)
    @app.get("/hot-news", response_class=HTMLResponse)
    @app.get("/recent", response_class=HTMLResponse)
    @app.get("/submit", response_class=HTMLResponse)
    @app.get("/submit-tool", response_class=HTMLResponse)
    @app.get("/wechat-mp", response_class=HTMLResponse)
    @app.get("/category/{category}", response_class=HTMLResponse)
    @app.get("/tool/{tool_id_or_identifier}", response_class=HTMLResponse)
    async def root(category: str = None, tool_id_or_identifier: str = None):
        """AICoding基地 首页（支持所有前端路由）"""
        html = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>AI-CodeNexus - 编程资讯与工具聚合平台</title>
          <link rel="preconnect" href="https://fonts.googleapis.com">
          <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
          <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap" rel="stylesheet">
          <script src="https://cdn.tailwindcss.com"></script>
          <script>
            // 限制 Tailwind CSS 只影响当前页面，避免全局样式冲突
            tailwind.config = {
              important: true,
              corePlugins: {
                preflight: false,  // 禁用全局重置样式
              },
              theme: {
                extend: {
                  colors: {
                    neon: {
                      cyan: '#00f0ff',
                      purple: '#a855f7',
                      blue: '#3b82f6',
                      pink: '#ec4899',
                    },
                    dark: {
                      bg: '#0a0e27',
                      card: '#111827',
                      border: '#1f2937',
                    }
                  }
                }
              }
            }
          </script>
          <style>
            /* 确保 Tailwind CSS 只影响当前页面 */
            body { margin: 0; padding: 0; }
            
            /* 科技感字体 */
            .tech-font {
              font-family: 'Orbitron', 'Rajdhani', sans-serif;
              letter-spacing: 0.05em;
            }
            
            .tech-font-bold {
              font-family: 'Orbitron', sans-serif;
              font-weight: 700;
              letter-spacing: 0.1em;
            }
            
            .tech-font-nav {
              font-family: 'Rajdhani', sans-serif;
              font-weight: 600;
              letter-spacing: 0.05em;
            }
            
            /* 科技感背景渐变 */
            .tech-bg {
              background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
              position: relative;
            }
            
            .tech-bg::before {
              content: '';
              position: fixed;
              top: 0;
              left: 0;
              right: 0;
              bottom: 0;
              background: 
                radial-gradient(circle at 20% 50%, rgba(0, 240, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(168, 85, 247, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 50%);
              pointer-events: none;
              z-index: 0;
            }
            
            /* 玻璃态效果 */
            .glass {
              background: rgba(17, 24, 39, 0.7);
              backdrop-filter: blur(10px);
              border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            /* 霓虹发光效果 */
            .neon-glow {
              box-shadow: 0 0 10px rgba(0, 240, 255, 0.5),
                          0 0 20px rgba(0, 240, 255, 0.3),
                          0 0 30px rgba(0, 240, 255, 0.2);
            }
            
            .neon-glow-purple {
              box-shadow: 0 0 10px rgba(168, 85, 247, 0.5),
                          0 0 20px rgba(168, 85, 247, 0.3),
                          0 0 30px rgba(168, 85, 247, 0.2);
            }
            
            /* 文字发光效果 */
            .text-glow {
              text-shadow: 0 0 10px rgba(0, 240, 255, 0.8),
                          0 0 20px rgba(0, 240, 255, 0.5),
                          0 0 30px rgba(0, 240, 255, 0.3);
            }
            
            /* 悬停发光动画 */
            @keyframes pulse-glow {
              0%, 100% {
                box-shadow: 0 0 10px rgba(0, 240, 255, 0.5),
                            0 0 20px rgba(0, 240, 255, 0.3);
              }
              50% {
                box-shadow: 0 0 20px rgba(0, 240, 255, 0.8),
                            0 0 40px rgba(0, 240, 255, 0.5);
              }
            }
            
            .hover-glow:hover {
              animation: pulse-glow 2s ease-in-out infinite;
            }
            
            /* 滚动条样式 */
            ::-webkit-scrollbar {
              width: 8px;
            }
            
            ::-webkit-scrollbar-track {
              background: #0a0e27;
            }
            
            ::-webkit-scrollbar-thumb {
              background: rgba(0, 240, 255, 0.5);
              border-radius: 4px;
            }
            
            ::-webkit-scrollbar-thumb:hover {
              background: rgba(0, 240, 255, 0.8);
            }
            
            /* 卡片悬停效果 */
            .card-hover {
              transition: all 0.3s ease;
            }
            
            .card-hover:hover {
              transform: translateY(-4px);
              box-shadow: 0 10px 30px rgba(0, 240, 255, 0.3),
                          0 0 20px rgba(168, 85, 247, 0.2);
              border-color: rgba(0, 240, 255, 0.5);
            }
            
            /* 导航项动画 */
            .nav-item {
              position: relative;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .nav-item::before {
              content: '';
              position: absolute;
              left: 0;
              top: 0;
              bottom: 0;
              width: 3px;
              background: linear-gradient(to bottom, #00f0ff, #a855f7);
              transform: scaleY(0);
              transform-origin: center;
              transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .nav-item.active::before,
            .nav-item:hover::before {
              transform: scaleY(1);
            }
            
            .nav-item.active {
              background: rgba(0, 240, 255, 0.1);
              color: #00f0ff;
              border-left: 3px solid #00f0ff;
            }
            
            /* 顶部导航动画 */
            .top-nav-item {
              position: relative;
              transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .top-nav-item::after {
              content: '';
              position: absolute;
              bottom: 0;
              left: 50%;
              width: 0;
              height: 2px;
              background: linear-gradient(to right, #00f0ff, #a855f7);
              transform: translateX(-50%);
              transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .top-nav-item.active::after,
            .top-nav-item:hover::after {
              width: 80%;
            }
            
            .top-nav-item.active {
              color: #00f0ff;
            }
          </style>
        </head>
        <body class="tech-bg text-gray-100" style="position: relative; z-index: 1;">
          <div class="flex flex-col min-h-screen" style="position: relative; z-index: 1;">
            <!-- 顶部导航栏 -->
            <header class="glass border-b border-dark-border fixed top-0 left-0 right-0" style="z-index: 20; height: 80px;">
              <div class="max-w-7xl mx-auto px-6 h-full">
                <div class="flex items-center justify-between h-full w-full">
              <!-- Logo -->
                  <div class="flex items-center flex-shrink-0">
                    <h1 class="text-2xl tech-font-bold text-neon-cyan text-glow">AI-CodeNexus</h1>
                    <p class="text-sm text-gray-400 ml-4 hidden md:block tech-font">AI · 编程 · 工具聚合</p>
              </div>
              
              <!-- 主导航和管理员入口 -->
              <div class="flex items-center gap-2 flex-1 justify-end">
                  <nav class="flex items-center gap-2 flex-wrap">
                    <a href="/news" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                  📰 编程资讯
                </a>
                    <a href="/ai-news" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple rounded-lg transition-all whitespace-nowrap">
                  🤖 AI资讯
                </a>
                    <a href="/hot-news" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      🔥 热门资讯
                </a>
                    <a href="/recent" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      ⏰ 最新资讯
                </a>
                    <a href="/submit" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple rounded-lg transition-all whitespace-nowrap">
                      ✍️ 提交资讯
                </a>
                    <a href="/wechat-mp" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      📱 微信公众号
                </a>
              </nav>
                  
                  <!-- 管理员入口（隐藏，需要输入授权码后显示，放在最右侧） -->
                  <a href="/digest/panel" id="admin-entry" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple rounded-lg transition-all hidden whitespace-nowrap ml-2" style="display: none;">
                    🔐 管理员入口
                  </a>
              </div>
                </div>
              </div>
            </header>
            
            <div class="flex flex-1" style="margin-top: 80px;">
              <!-- 左侧边栏 -->
              <aside class="w-64 glass border-r border-dark-border flex flex-col fixed" style="top: 80px; height: calc(100vh - 80px); z-index: 10;">
              
              <!-- 工具分类 -->
                <div class="flex-1 p-5 overflow-y-auto">
                  <div class="space-y-2">
                    <a href="/tools" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      🔥 热门工具
                    </a>
                    <a href="/category/ide" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      💻 开发IDE
                  </a>
                    <a href="/category/plugin" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      🔌 IDE插件
                  </a>
                    <a href="/category/cli" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      ⌨️ 命令行工具
                  </a>
                    <a href="/category/codeagent" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      🤖 CodeAgent
                  </a>
                    <a href="/category/ai-test" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      🧪 AI测试
                  </a>
                    <a href="/category/review" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      ✅ 代码审查
                  </a>
                    <a href="/category/devops" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      🚀 DevOps 工具
                  </a>
                    <a href="/category/doc" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      📚 文档相关
                  </a>
                    <a href="/category/design" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      🎨 设计工具
                  </a>
                    <a href="/category/ui" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      🖼️ UI生成
                  </a>
                    <a href="/category/mcp" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-cyan rounded transition-all">
                      🔌 MCP工具
                  </a>
                    <a href="/submit-tool" class="nav-item block px-4 py-3 text-base tech-font-nav text-gray-400 hover:text-neon-purple rounded transition-all">
                      ➕ 提交工具
                  </a>
                </div>
              </div>
              
            </aside>
            
            <!-- 主内容区域 -->
              <main class="flex-1 ml-64 pt-20" style="position: relative; z-index: 1;">
              <div class="max-w-6xl mx-auto p-8">
                <!-- 动态内容区域 -->
                <div id="main-content">
                  <!-- 内容将通过JavaScript动态加载 -->
                  <div class="text-center py-20">
                    <div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div>
                  </div>
                </div>
              </div>
            </main>
                </div>
                
            <script>
              // API基础URL
              const API_BASE = '/api';
              
              // 配置文件
              let pageConfig = {};
              
              // 当前页面状态
              let currentPage = {
                type: 'tools',
                page: 1,
                pageSize: 20,
                category: null,
                loading: false
              };
              
              // 加载配置文件
              async function loadConfig() {
                try {
                  const response = await fetch(`${API_BASE}/config`);
                  pageConfig = await response.json();
                } catch (error) {
                  console.error('加载配置失败:', error);
                }
              }
              
              // 获取页面配置
              function getPageConfig(pageType, category = null) {
                if (!pageConfig.pages) return { title: '', description: '' };
                
                // 如果是分类页面
                if (category && pageConfig.categories && pageConfig.categories.tools) {
                  const catConfig = pageConfig.categories.tools[category];
                  if (catConfig) {
                    return {
                      title: catConfig.name,
                      description: catConfig.description
                    };
                  }
                }
                
                // 普通页面
                const config = pageConfig.pages[pageType];
                return config || { title: '', description: '' };
              }
              
              // 加载工具列表
              async function loadTools(featured = false, category = null, page = 1) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  let url = featured 
                    ? `${API_BASE}/tools/featured?page=${page}&page_size=${currentPage.pageSize}&sort_by=view_count`
                    : `${API_BASE}/tools?page=${page}&page_size=${currentPage.pageSize}`;
                  
                  if (category) {
                    url += `&category=${category}`;
                  }
                  
                  const response = await fetch(url);
                  if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                  }
                  const data = await response.json();
                  
                  console.log('加载工具数据:', { items: data.items?.length, total: data.total, featured });
                  
                  renderTools(data.items, data.total, data.page, data.total_pages, category, featured);
                } catch (error) {
                  console.error('加载工具失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败，请刷新重试</div>';
                }
              }
              
              // 渲染工具列表
              function renderTools(tools, total, page, totalPages, category = null, isFeatured = true) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                // 获取页面配置
                const pageType = isFeatured ? 'tools' : 'all-tools';
                const config = getPageConfig(pageType, category);
                const title = config.title || (isFeatured ? '热门工具' : '全部工具');
                const description = config.description || '发现最优秀的开发工具和资源';
                
                let html = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description} (共 ${total} 个)</p>
                </div>
                
                  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8" id="tools-grid">
                `;
                
                if (tools.length === 0) {
                  html += '<div class="col-span-full text-center py-20 text-gray-400">暂无工具数据</div>';
                } else {
                  tools.forEach(tool => {
                    const iconColor = tool.category === 'codeagent' || tool.category === 'ai-test' 
                      ? 'from-neon-purple to-neon-pink' 
                      : 'from-neon-cyan to-neon-blue';
                    const glowClass = tool.category === 'codeagent' || tool.category === 'ai-test'
                      ? 'neon-glow-purple'
                      : 'neon-glow';
                    const viewCount = tool.view_count || 0;
                    
                    html += `
                      <div class="glass rounded-xl border border-dark-border p-6 card-hover cursor-pointer" onclick="window.location.href='/tool/${tool.identifier || tool.id}'">
                    <div class="flex items-start gap-3 mb-4">
                          <div class="w-10 h-10 rounded-lg bg-gradient-to-br ${iconColor} flex items-center justify-center text-dark-bg text-lg font-bold flex-shrink-0 ${glowClass}">
                            ${tool.icon || '</>'}
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                              <h3 class="text-lg font-bold text-gray-100 truncate">${tool.name}</h3>
                              <span class="text-yellow-400 text-sm">⭐</span>
                        </div>
                            <div class="flex items-center gap-2">
                              <p class="text-xs text-gray-400">${getCategoryName(tool.category)}</p>
                              ${isFeatured ? `<span class="text-xs text-yellow-400">🔥 ${viewCount} 次访问</span>` : ''}
                      </div>
                    </div>
                        </div>
                        <p class="text-sm text-gray-300 line-clamp-3 mb-4">
                          ${tool.description || ''}
                        </p>
                        <a href="${tool.url}" target="_blank" rel="noopener noreferrer" 
                           class="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r ${iconColor} text-dark-bg text-sm rounded-lg hover:from-neon-blue hover:to-neon-cyan transition-all font-medium hover-glow"
                           onclick="event.stopPropagation(); recordToolClick('${tool.identifier || tool.id}');">
                      访问工具
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                    `;
                  });
                }
                
                html += '</div>';
                
                // 分页控件
                if (totalPages > 1) {
                  const categoryParam = category ? `'${category}'` : 'null';
                  html += `
                    <div class="flex items-center justify-center gap-2 mt-8">
                      <button onclick="changePage(${page - 1}, ${categoryParam}, ${isFeatured})" 
                              ${page <= 1 ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        上一页
                      </button>
                      <span class="px-4 py-2 text-gray-400 tech-font">
                        第 ${page} / ${totalPages} 页
                      </span>
                      <button onclick="changePage(${page + 1}, ${categoryParam}, ${isFeatured})" 
                              ${page >= totalPages ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        下一页
                      </button>
                      </div>
                  `;
                }
                
                mainContent.innerHTML = html;
              }
              
              // 加载文章列表
              async function loadArticles(category = 'programming', page = 1) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  const url = category === 'ai_news'
                    ? `${API_BASE}/ai-news?page=${page}&page_size=${currentPage.pageSize}`
                    : `${API_BASE}/news?category=${category}&page=${page}&page_size=${currentPage.pageSize}`;
                  
                  const response = await fetch(url);
                  const data = await response.json();
                  
                  renderArticles(data.items, data.total, data.page, data.total_pages, category);
                } catch (error) {
                  console.error('加载文章失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败，请刷新重试</div>';
                }
              }
              
              // 渲染文章列表
              function renderArticles(articles, total, page, totalPages, category) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                // 获取页面配置
                const pageType = category === 'ai_news' ? 'ai-news' : 'news';
                const config = getPageConfig(pageType);
                const title = config.title || (category === 'ai_news' ? 'AI资讯' : '编程资讯');
                const description = config.description || '最新技术文章和资讯';
                
                let html = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description} (共 ${total} 篇)</p>
                        </div>
                  
                  <div class="space-y-4 mb-8">
                `;
                
                if (articles.length === 0) {
                  html += '<div class="text-center py-20 text-gray-400">暂无文章数据</div>';
                } else {
                  articles.forEach(article => {
                    // 处理日期：优先使用 archived_at（采纳日期），其次 published_time，最后 created_at
                    let dateStr = '未知日期';
                    const dateValue = article.archived_at || article.published_time || article.created_at;
                    if (dateValue) {
                      try {
                        const date = new Date(dateValue);
                        if (!isNaN(date.getTime())) {
                          dateStr = date.toLocaleDateString('zh-CN');
                        }
                      } catch (e) {
                        // 日期解析失败，使用默认值
                      }
                    }
                    
                    // 处理来源：如果source为空字符串，显示"未知来源"
                    const source = (article.source && article.source.trim()) ? article.source : '未知来源';
                    
                    // 合并标签：tool_tags 和 tags
                    const allTags = [];
                    if (article.tool_tags && article.tool_tags.length > 0) {
                      allTags.push(...article.tool_tags.map(tag => ({ tag, isTool: true })));
                    }
                    if (article.tags && article.tags.length > 0) {
                      allTags.push(...article.tags.map(tag => ({ tag, isTool: false })));
                    }
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                        <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                          <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}')">${article.title}</a>
                        </h4>
                        <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                          <span>${source}</span>
                          <span>•</span>
                          <span>${dateStr}</span>
                      </div>
                        <p class="text-sm text-gray-300 leading-relaxed mb-3">
                          ${article.summary || ''}
                        </p>
                        ${allTags.length > 0 ? `
                        <div class="flex items-center gap-2 flex-wrap">
                          ${allTags.map(({ tag, isTool }) => 
                            isTool 
                              ? `<span class="px-2 py-1 glass text-neon-purple text-xs rounded border border-neon-purple/30 flex items-center gap-1">
                                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
                                  </svg>
                                  ${tag}
                                </span>`
                              : `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`
                          ).join('')}
                        </div>
                        ` : ''}
                      </article>
                    `;
                  });
                }
                
                html += '</div>';
                
                // 分页控件
                if (totalPages > 1) {
                  html += `
                    <div class="flex items-center justify-center gap-2 mt-8">
                      <button onclick="changeArticlePage(${page - 1}, '${category}')" 
                              ${page <= 1 ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        上一页
                      </button>
                      <span class="px-4 py-2 text-gray-400 tech-font">
                        第 ${page} / ${totalPages} 页
                      </span>
                      <button onclick="changeArticlePage(${page + 1}, '${category}')" 
                              ${page >= totalPages ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        下一页
                      </button>
                      </div>
                  `;
                }
                
                mainContent.innerHTML = html;
              }
              
              // 工具分类名称映射
              function getCategoryName(category) {
                const map = {
                  'ide': '开发IDE',
                  'plugin': 'IDE插件',
                  'cli': '命令行工具',
                  'codeagent': 'CodeAgent',
                  'ai-test': 'AI测试',
                  'review': '代码审查',
                  'devops': 'DevOps工具',
                  'doc': '文档相关',
                  'design': '设计工具',
                  'ui': 'UI生成',
                  'mcp': 'MCP工具'
                };
                return map[category] || category;
              }
              
              // 切换页面
              function changePage(newPage, category = null, featured = true) {
                if (newPage < 1) return;
                currentPage.page = newPage;
                if (category) currentPage.category = category;
                loadTools(featured, category || currentPage.category, newPage);
              }
              
              // 切换文章页面
              function changeArticlePage(newPage, category) {
                if (newPage < 1) return;
                loadArticles(category, newPage);
              }
              
              // 显示工具详情
              async function showToolDetail(toolIdOrIdentifier) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  const response = await fetch(`${API_BASE}/tools/${toolIdOrIdentifier}`);
                  if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                  }
                  const tool = await response.json();
                  
                  renderToolDetail(tool);
                  
                  // 更新URL（使用 identifier 如果存在，否则使用 ID）
                  const urlIdentifier = tool.identifier || tool.id;
                  window.history.pushState({}, '', `/tool/${urlIdentifier}`);
                } catch (error) {
                  console.error('加载工具详情失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败，请刷新重试</div>';
                }
              }
              
              // 渲染工具详情
              function renderToolDetail(tool) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                const iconColor = tool.category === 'codeagent' || tool.category === 'ai-test' 
                  ? 'from-neon-purple to-neon-pink' 
                  : 'from-neon-cyan to-neon-blue';
                const glowClass = tool.category === 'codeagent' || tool.category === 'ai-test'
                  ? 'neon-glow-purple'
                  : 'neon-glow';
                const viewCount = tool.view_count || 0;
                const relatedArticles = tool.related_articles || [];
                const relatedCount = tool.related_articles_count || 0;
                
                let html = `
                  <div class="mb-6">
                    <a href="javascript:void(0)" onclick="goBack()" class="inline-flex items-center gap-2 text-gray-400 hover:text-neon-cyan transition-colors mb-4">
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                      </svg>
                      <span>返回分类</span>
                    </a>
                    
                    <div class="glass rounded-xl border border-dark-border p-8">
                      <div class="flex items-start gap-6 mb-6">
                        <div class="w-16 h-16 rounded-xl bg-gradient-to-br ${iconColor} flex items-center justify-center text-dark-bg text-2xl font-bold flex-shrink-0 ${glowClass}">
                          ${tool.icon || '</>'}
                        </div>
                        <div class="flex-1">
                          <h1 class="text-3xl tech-font-bold text-neon-cyan text-glow mb-2">${tool.name}</h1>
                          <div class="flex items-center gap-4 text-sm text-gray-400 mb-4">
                            <span>${getCategoryName(tool.category)}</span>
                            <span>•</span>
                            <span>🔥 ${viewCount} 次访问</span>
                          </div>
                          <a href="${tool.url}" target="_blank" rel="noopener noreferrer" 
                             class="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r ${iconColor} text-dark-bg rounded-lg hover:from-neon-blue hover:to-neon-cyan transition-all font-medium hover-glow"
                             onclick="recordToolClick('${tool.identifier || tool.id}')">
                            访问工具
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        </div>
                      </div>
                      
                      <div class="mb-6">
                        <h2 class="text-xl font-semibold text-gray-100 mb-3">工具描述</h2>
                        <p class="text-gray-300 leading-relaxed">${tool.description || '暂无描述'}</p>
                      </div>
                      
                      ${tool.tags && tool.tags.length > 0 ? `
                        <div class="mb-6">
                          <h2 class="text-xl font-semibold text-gray-100 mb-3">标签</h2>
                          <div class="flex items-center gap-2 flex-wrap">
                            ${tool.tags.map(tag => 
                              `<span class="px-3 py-1 glass text-neon-cyan text-sm rounded border border-neon-cyan/30">${tag}</span>`
                            ).join('')}
                          </div>
                        </div>
                      ` : ''}
                    </div>
                    
                    <!-- 相关资讯 -->
                    <div class="mt-8">
                      <div class="flex items-center justify-between mb-4">
                        <h2 class="text-2xl tech-font-bold text-neon-cyan text-glow flex items-center gap-2">
                          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                          </svg>
                          相关资讯
                        </h2>
                        <div class="flex items-center gap-2">
                          <button onclick="refreshRelatedArticles('${tool.identifier || tool.id}')" 
                                  class="px-4 py-2 glass border border-dark-border text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all text-sm">
                            刷新
                          </button>
                          ${relatedCount > 10 ? `
                            <a href="javascript:void(0)" onclick="showMoreArticles('${tool.identifier || tool.id}')" 
                               class="px-4 py-2 glass border border-dark-border text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all text-sm">
                              查看更多 >
                            </a>
                          ` : ''}
                        </div>
                      </div>
                      
                      <div id="related-articles-list" class="space-y-4">
                `;
                
                if (relatedArticles.length === 0) {
                  html += `
                    <div class="glass rounded-xl border border-dark-border p-8 text-center text-gray-400">
                      <p>暂无相关资讯</p>
                    </div>
                  `;
                } else {
                  relatedArticles.forEach(article => {
                    const date = new Date(article.published_time || article.created_at || article.archived_at).toLocaleDateString('zh-CN');
                    const categoryLabel = article.category === 'ai_news' ? 'AI资讯' : '编程资讯';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                        <div class="flex items-start gap-3 mb-2">
                          <span class="text-sm px-2 py-1 glass border border-neon-cyan/30 text-neon-cyan rounded">${categoryLabel}</span>
                          <span class="text-xs text-gray-400">${date}</span>
                        </div>
                        <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                          <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}')">${article.title}</a>
                        </h4>
                        <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                          <span>${article.source || '未知来源'}</span>
                        </div>
                        <p class="text-sm text-gray-300 leading-relaxed mb-3">
                          ${article.summary || ''}
                        </p>
                        ${article.tool_tags && article.tool_tags.length > 0 ? `
                          <div class="flex items-center gap-2 flex-wrap">
                            ${article.tool_tags.map(tag => 
                              `<span class="px-2 py-1 glass text-neon-purple text-xs rounded border border-neon-purple/30 flex items-center gap-1">
                                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                  <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
                                </svg>
                                ${tag}
                              </span>`
                            ).join('')}
                          </div>
                        ` : ''}
                      </article>
                    `;
                  });
                }
                
                html += `
                      </div>
                    </div>
                `;
                
                mainContent.innerHTML = html;
              }
              
              // 返回上一页
              function goBack() {
                const path = window.location.pathname;
                if (path.includes('/tool/')) {
                  // 从工具详情页返回，尝试返回到分类页面
                  const category = localStorage.getItem('last_category') || 'tools';
                  window.history.pushState({}, '', `/${category}`);
                  handleRoute();
                } else {
                  window.history.back();
                }
              }
              
              // 刷新相关文章
              async function refreshRelatedArticles(toolIdOrIdentifier) {
                try {
                  const response = await fetch(`${API_BASE}/tools/${toolIdOrIdentifier}`);
                  if (!response.ok) throw new Error('刷新失败');
                  const tool = await response.json();
                  
                  const relatedArticles = tool.related_articles || [];
                  const relatedList = document.getElementById('related-articles-list');
                  if (!relatedList) return;
                  
                  if (relatedArticles.length === 0) {
                    relatedList.innerHTML = '<div class="glass rounded-xl border border-dark-border p-8 text-center text-gray-400"><p>暂无相关资讯</p></div>';
                    return;
                  }
                  
                  let html = '';
                  relatedArticles.forEach(article => {
                    const date = new Date(article.published_time || article.created_at || article.archived_at).toLocaleDateString('zh-CN');
                    const categoryLabel = article.category === 'ai_news' ? 'AI资讯' : '编程资讯';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                        <div class="flex items-start gap-3 mb-2">
                          <span class="text-sm px-2 py-1 glass border border-neon-cyan/30 text-neon-cyan rounded">${categoryLabel}</span>
                          <span class="text-xs text-gray-400">${date}</span>
                        </div>
                        <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                          <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}')">${article.title}</a>
                        </h4>
                        <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                          <span>${article.source || '未知来源'}</span>
                        </div>
                        <p class="text-sm text-gray-300 leading-relaxed mb-3">
                          ${article.summary || ''}
                        </p>
                        ${article.tool_tags && article.tool_tags.length > 0 ? `
                          <div class="flex items-center gap-2 flex-wrap">
                            ${article.tool_tags.map(tag => 
                              `<span class="px-2 py-1 glass text-neon-purple text-xs rounded border border-neon-purple/30 flex items-center gap-1">
                                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                  <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
                                </svg>
                                ${tag}
                              </span>`
                            ).join('')}
                          </div>
                        ` : ''}
                      </article>
                    `;
                  });
                  
                  relatedList.innerHTML = html;
                } catch (error) {
                  console.error('刷新相关文章失败:', error);
                }
              }
              
              // 显示更多文章
              function showMoreArticles(toolIdOrIdentifier) {
                // TODO: 实现分页加载更多文章
                console.log('显示更多文章:', toolIdOrIdentifier);
              }
              
              // 页面路由
              function handleRoute() {
                const path = window.location.pathname || '/news';
                currentPage.page = 1;
                
                // 移除开头的斜杠并转换为路由标识
                const route = path.startsWith('/') ? path.substring(1) : path;
                currentPage.type = route;
                
                if (route === 'news' || route === '') {
                  currentPage.category = null;
                  loadArticles('programming', 1);
                } else if (route === 'ai-news') {
                  currentPage.category = null;
                  loadArticles('ai_news', 1);
                } else if (route === 'tools') {
                  currentPage.category = null;
                  loadTools(true, null, 1);
                } else if (route === 'hot-news') {
                  currentPage.category = null;
                  loadHotNews(1);
                } else if (route === 'recent') {
                  currentPage.category = null;
                  loadRecent(1);
                } else if (route === 'submit') {
                  currentPage.category = null;
                  showSubmitForm();
                } else if (route === 'submit-tool') {
                  currentPage.category = null;
                  showSubmitToolForm();
                } else if (route === 'wechat-mp') {
                  currentPage.category = null;
                  showWeChatMP();
                } else if (route.startsWith('category/')) {
                  const category = route.substring(9); // 'category/'.length = 9
                  currentPage.category = category;
                  localStorage.setItem('last_category', `category/${category}`);
                  loadTools(false, category, 1);
                } else if (route.startsWith('tool/')) {
                  const toolIdOrIdentifier = route.substring(5); // 'tool/'.length = 5
                  if (toolIdOrIdentifier) {
                    showToolDetail(toolIdOrIdentifier);
                  } else {
                    // 默认显示热门工具
                    currentPage.category = null;
                    loadTools(true, null, 1);
                  }
                } else {
                  // 默认显示热门工具
                  currentPage.category = null;
                  loadTools(true, null, 1);
                }
              }
              
              // 加载最新资讯（合并编程资讯和AI资讯）
              let recentSearchQuery = '';
              
              async function loadRecent(page = 1, search = '') {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  let url = `${API_BASE}/recent?page=${page}&page_size=${currentPage.pageSize}`;
                  if (search) {
                    url += `&search=${encodeURIComponent(search)}`;
                  }
                  
                  const response = await fetch(url);
                  const data = await response.json();
                  
                  // 获取页面配置
                  const config = getPageConfig('recent');
                  const title = config.title || '最新资讯';
                  const description = config.description || '编程资讯和AI资讯的最新文章，按时间排序';
                  
                  let html = `
                    <div class="mb-6">
                      <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                      <p class="text-base text-gray-400 tech-font mb-4">${description} (共 ${data.total} 篇)</p>
                      
                      <!-- 搜索框 -->
                      <div class="flex gap-2 mb-4">
                        <input type="text" id="recent-search-input" 
                               class="flex-1 px-4 py-2 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan" 
                               placeholder="搜索文章标题或摘要..." 
                               value="${search}"
                               onkeypress="if(event.key==='Enter') handleRecentSearch()">
                        <button onclick="handleRecentSearch()" 
                                class="px-6 py-2 bg-gradient-to-r from-neon-cyan to-neon-blue text-dark-bg rounded-lg font-semibold hover:from-neon-blue hover:to-neon-cyan transition-all">
                          搜索
                        </button>
                        ${search ? `<button onclick="clearRecentSearch()" class="px-4 py-2 glass border border-dark-border text-gray-300 rounded-lg hover:bg-dark-card">清除</button>` : ''}
                        </div>
                      </div>
                    
                    <div class="space-y-4 mb-8">
                  `;
                  
                  if (data.items.length === 0) {
                    html += `<div class="text-center py-20 text-gray-400">${search ? '未找到相关文章' : '暂无文章'}</div>`;
                  } else {
                    data.items.forEach(article => {
                      const date = new Date(article.archived_at || article.published_time || article.created_at).toLocaleDateString('zh-CN');
                      const categoryLabel = article.category === 'ai_news' ? 'AI资讯' : '编程资讯';
                      
                      html += `
                        <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                          <div class="flex items-start gap-3 mb-2">
                            <span class="text-sm px-2 py-1 glass border border-neon-cyan/30 text-neon-cyan rounded">${categoryLabel}</span>
                            <span class="text-xs text-gray-400">${date}</span>
                    </div>
                          <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                            <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}'); return true;">${article.title}</a>
                          </h4>
                          <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                            <span>${article.source || '未知来源'}</span>
                          </div>
                          <p class="text-sm text-gray-300 leading-relaxed mb-3">
                            ${article.summary || ''}
                          </p>
                          <div class="flex items-center gap-2 flex-wrap">
                            ${(article.tags || []).map(tag => 
                              `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`
                            ).join('')}
                  </div>
                        </article>
                      `;
                    });
                  }
                  
                  html += '</div>';
                  
                  if (data.total_pages > 1) {
                    html += `
                      <div class="flex items-center justify-center gap-2 mt-8">
                        <button onclick="changeRecentPage(${data.page - 1}, '${search.replace(/'/g, "\\'")}')" 
                                ${data.page <= 1 ? 'disabled' : ''}
                                class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                          上一页
                        </button>
                        <span class="px-4 py-2 text-gray-400 tech-font">第 ${data.page} / ${data.total_pages} 页</span>
                        <button onclick="changeRecentPage(${data.page + 1}, '${search.replace(/'/g, "\\'")}')" 
                                ${data.page >= data.total_pages ? 'disabled' : ''}
                                class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                          下一页
                      </button>
                    </div>
                    `;
                  }
                  
                  mainContent.innerHTML = html;
                } catch (error) {
                  console.error('加载最新资讯失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败</div>';
                }
              }
              
              function changeRecentPage(page, search = '') {
                if (page < 1) return;
                recentSearchQuery = search;
                loadRecent(page, search);
              }
              
              function handleRecentSearch() {
                const searchInput = document.getElementById('recent-search-input');
                const query = searchInput ? searchInput.value.trim() : '';
                recentSearchQuery = query;
                loadRecent(1, query);
              }
              
              function clearRecentSearch() {
                recentSearchQuery = '';
                loadRecent(1, '');
              }
              
              // 加载热门资讯（按点击次数排序）
              async function loadHotNews(page = 1) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  // 获取热门文章（按热度排序，获取所有文章，不传category）
                  const response = await fetch(`${API_BASE}/news?page=${page}&page_size=${currentPage.pageSize}&sort_by=score`);
                  const data = await response.json();
                  
                  renderHotArticles(data.items, data.total, data.page, data.total_pages);
                } catch (error) {
                  console.error('加载热门资讯失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败</div>';
                }
              }
              
              // 渲染热门文章列表
              function renderHotArticles(articles, total, page, totalPages) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                const config = getPageConfig('hot-news');
                const title = config.title || '热门资讯';
                const description = config.description || '最受欢迎的技术文章';
                
                let html = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description} (共 ${total} 篇)</p>
                  </div>
                  
                  <div class="space-y-4 mb-8">
                `;
                
                if (articles.length === 0) {
                  html += '<div class="text-center py-20 text-gray-400">暂无文章数据</div>';
                } else {
                  articles.forEach(article => {
                    const date = new Date(article.archived_at || article.published_time || article.created_at).toLocaleDateString('zh-CN');
                    const viewCount = article.view_count || 0;
                    const categoryLabel = article.category === 'ai_news' ? 'AI资讯' : '编程资讯';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                        <div class="flex items-start gap-3 mb-2">
                          <span class="text-sm px-2 py-1 glass border border-neon-cyan/30 text-neon-cyan rounded">${categoryLabel}</span>
                          <span class="text-xs text-gray-400">${date}</span>
                          <span class="text-xs text-yellow-400">🔥 ${viewCount} 次点击</span>
                        </div>
                        <h4 class="text-lg font-semibold text-gray-100 mb-2 hover:text-neon-cyan cursor-pointer transition-colors">
                          <a href="${article.url}" target="_blank" rel="noopener noreferrer" onclick="recordArticleClick('${article.url.replace(/'/g, "\\'")}')">${article.title}</a>
                      </h4>
                        <div class="flex items-center gap-3 text-sm text-gray-400 mb-2">
                          <span>${article.source || '未知来源'}</span>
                      </div>
                        <p class="text-sm text-gray-300 leading-relaxed mb-3">
                          ${article.summary || ''}
                        </p>
                        <div class="flex items-center gap-2 flex-wrap">
                          ${(article.tags || []).map(tag => 
                            `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`
                          ).join('')}
                      </div>
                    </article>
                    `;
                  });
                }
                
                html += '</div>';
                
                // 分页控件
                if (totalPages > 1) {
                  html += `
                    <div class="flex items-center justify-center gap-2 mt-8">
                      <button onclick="changeHotNewsPage(${page - 1})" 
                              ${page <= 1 ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        上一页
                      </button>
                      <span class="px-4 py-2 text-gray-400 tech-font">
                        第 ${page} / ${totalPages} 页
                      </span>
                      <button onclick="changeHotNewsPage(${page + 1})" 
                              ${page >= totalPages ? 'disabled' : ''}
                              class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">
                        下一页
                      </button>
                      </div>
                  `;
                }
                
                mainContent.innerHTML = html;
              }
              
              function changeHotNewsPage(page) {
                if (page < 1) return;
                loadHotNews(page);
              }
              
              // 记录文章点击
              async function recordArticleClick(url) {
                try {
                  await fetch(`${API_BASE}/articles/click?url=${encodeURIComponent(url)}`, {
                    method: 'POST'
                  });
                  // 如果是热门资讯页面，刷新页面以更新热度显示
                  if (window.location.pathname === '/hot-news') {
                    const currentPage = parseInt(document.querySelector('.tech-font')?.textContent?.match(/\d+/)?.[0]) || 1;
                    setTimeout(() => loadHotNews(currentPage), 500);
                  }
                } catch (error) {
                  console.error('记录点击失败:', error);
                }
              }
              
              // 记录工具点击
              async function recordToolClick(toolId) {
                try {
                  await fetch(`${API_BASE}/tools/${toolId}/click`, {
                    method: 'POST'
                  });
                  // 如果是热门工具页面，刷新页面以更新热度显示
                  if (window.location.pathname === '/tools') {
                    const currentPage = parseInt(document.querySelector('.tech-font')?.textContent?.match(/\d+/)?.[0]) || 1;
                    setTimeout(() => loadTools(true, null, currentPage), 500);
                  }
                } catch (error) {
                  console.error('记录工具点击失败:', error);
                }
              }
              
              // 显示提交资讯表单
              function showSubmitForm() {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                const config = getPageConfig('submit');
                const title = config.title || '提交资讯';
                const description = config.description || '分享优质的技术文章和资讯';
                
                mainContent.innerHTML = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description}</p>
                  </div>
                  
                  <!-- 审核说明 -->
                  <div class="glass rounded-xl border border-neon-cyan/30 p-6 mb-6 max-w-2xl">
                    <div class="flex items-start gap-3">
                      <span class="text-2xl">ℹ️</span>
                      <div>
                        <h3 class="text-lg font-semibold text-neon-cyan mb-2">审核说明</h3>
                        <p class="text-sm text-gray-300 leading-relaxed">
                          您提交的资讯将进入文章候选池，由管理员进行人工审核。我们会在<strong class="text-neon-cyan">一天内</strong>完成审核，审核通过后即可在网站上展示。
                        </p>
                        <p class="text-sm text-gray-400 mt-2">
                          审核期间，您可以在管理员面板查看审核状态。
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div class="glass rounded-xl border border-dark-border p-8 max-w-2xl">
                    <form id="submit-form" class="space-y-6">
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">文章标题 <span class="text-red-400">*</span></label>
                        <input type="text" id="submit-title" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan" placeholder="请输入文章标题" required>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">文章链接 <span class="text-red-400">*</span></label>
                        <input type="url" id="submit-url" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan" placeholder="https://..." required>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">文章分类 <span class="text-red-400">*</span></label>
                        <select id="submit-category" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan">
                          <option value="programming">编程资讯</option>
                          <option value="ai_news">AI资讯</option>
                        </select>
                  </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">推荐理由（可选）</label>
                        <textarea id="submit-reason" rows="4" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-cyan" placeholder="为什么推荐这篇文章..."></textarea>
                </div>
                      <button type="submit" class="w-full px-6 py-3 bg-gradient-to-r from-neon-cyan to-neon-blue text-dark-bg rounded-lg font-semibold hover:from-neon-blue hover:to-neon-cyan transition-all hover-glow">
                        提交资讯
                      </button>
                    </form>
                    <div id="submit-status" class="mt-4 text-sm"></div>
              </div>
                `;
                
                // 绑定表单提交
                document.getElementById('submit-form').addEventListener('submit', async function(e) {
                  e.preventDefault();
                  const title = document.getElementById('submit-title').value.trim();
                  const url = document.getElementById('submit-url').value.trim();
                  const category = document.getElementById('submit-category').value;
                  const reason = document.getElementById('submit-reason').value.trim();
                  
                  if (!title || !url) {
                    const statusEl = document.getElementById('submit-status');
                    statusEl.textContent = '请填写必填项';
                    statusEl.className = 'mt-4 text-sm text-red-400';
                    return;
                  }
                  
                  const statusEl = document.getElementById('submit-status');
                  statusEl.textContent = '提交中...';
                  statusEl.className = 'mt-4 text-sm text-blue-400';
                  
                  try {
                    const response = await fetch(`${API_BASE}/articles/submit`, {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                        title: title,
                        url: url,
                        category: category,
                        summary: reason || ''
                      })
                    });
                    
                    const data = await response.json();
                    
                    if (data.ok) {
                      statusEl.textContent = '提交成功！您的资讯已进入审核队列，我们会在一天内完成审核。';
                      statusEl.className = 'mt-4 text-sm text-green-400';
                      document.getElementById('submit-form').reset();
                    } else {
                      statusEl.textContent = data.message || '提交失败，请稍后重试。';
                      statusEl.className = 'mt-4 text-sm text-red-400';
                    }
                  } catch (error) {
                    console.error('提交失败:', error);
                    statusEl.textContent = '提交失败，请稍后重试。';
                    statusEl.className = 'mt-4 text-sm text-red-400';
                  }
                });
              }
              
              // 显示提交工具表单
              function showSubmitToolForm() {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">提交工具</h1>
                    <p class="text-base text-gray-400 tech-font">分享优质的开发工具和资源</p>
                  </div>
                  
                  <!-- 审核说明 -->
                  <div class="glass rounded-xl border border-neon-purple/30 p-6 mb-6 max-w-2xl">
                    <div class="flex items-start gap-3">
                      <span class="text-2xl">ℹ️</span>
                      <div>
                        <h3 class="text-lg font-semibold text-neon-purple mb-2">审核说明</h3>
                        <p class="text-sm text-gray-300 leading-relaxed">
                          您提交的工具将进入工具候选池，由管理员进行人工审核。我们会在<strong class="text-neon-purple">一天内</strong>完成审核，审核通过后即可在网站上展示。
                        </p>
                        <p class="text-sm text-gray-400 mt-2">
                          审核期间，您可以在管理员面板查看审核状态。
                        </p>
                      </div>
                  </div>
                </div>
                  
                  <div class="glass rounded-xl border border-dark-border p-8 max-w-2xl">
                    <form id="submit-tool-form" class="space-y-6">
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">工具名称 <span class="text-red-400">*</span></label>
                        <input type="text" id="tool-name" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="请输入工具名称" required>
              </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">工具链接 <span class="text-red-400">*</span></label>
                        <input type="url" id="tool-url" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="https://..." required>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">工具描述 <span class="text-red-400">*</span></label>
                        <textarea id="tool-description" rows="3" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="请简要描述工具的功能和特点..." required></textarea>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">工具分类 <span class="text-red-400">*</span></label>
                        <select id="tool-category" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple">
                          <option value="ide">开发IDE</option>
                          <option value="plugin">IDE插件</option>
                          <option value="cli">命令行工具</option>
                          <option value="codeagent">CodeAgent</option>
                          <option value="ai-test">AI测试</option>
                          <option value="review">代码审查</option>
                          <option value="devops">DevOps工具</option>
                          <option value="doc">文档相关</option>
                          <option value="design">设计工具</option>
                          <option value="ui">UI生成</option>
                          <option value="mcp">MCP工具</option>
                          <option value="other">其他工具</option>
                        </select>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">标签（可选，用逗号分隔）</label>
                        <input type="text" id="tool-tags" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="例如：开源, AI, 前端">
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2">图标（可选）</label>
                        <input type="text" id="tool-icon" class="w-full px-4 py-3 glass border border-dark-border rounded-lg text-gray-100 focus:outline-none focus:border-neon-purple" placeholder="例如：</> 或 🚀" value="</>">
                      </div>
                      <button type="submit" class="w-full px-6 py-3 bg-gradient-to-r from-neon-purple to-neon-pink text-dark-bg rounded-lg font-semibold hover:from-neon-pink hover:to-neon-purple transition-all hover-glow">
                        提交工具
                      </button>
                    </form>
                    <div id="submit-tool-status" class="mt-4 text-sm"></div>
                  </div>
                `;
                
                // 绑定表单提交
                document.getElementById('submit-tool-form').addEventListener('submit', async function(e) {
                  e.preventDefault();
                  const name = document.getElementById('tool-name').value.trim();
                  const url = document.getElementById('tool-url').value.trim();
                  const description = document.getElementById('tool-description').value.trim();
                  const category = document.getElementById('tool-category').value;
                  const tags = document.getElementById('tool-tags').value.trim();
                  const icon = document.getElementById('tool-icon').value.trim() || '</>';
                  
                  if (!name || !url || !description) {
                    const statusEl = document.getElementById('submit-tool-status');
                    statusEl.textContent = '请填写必填项';
                    statusEl.className = 'mt-4 text-sm text-red-400';
                    return;
                  }
                  
                  const statusEl = document.getElementById('submit-tool-status');
                  statusEl.textContent = '提交中...';
                  statusEl.className = 'mt-4 text-sm text-blue-400';
                  
                  try {
                    const response = await fetch(`${API_BASE}/tools/submit`, {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                        name: name,
                        url: url,
                        description: description,
                        category: category,
                        tags: tags,
                        icon: icon
                      })
                    });
                    
                    const data = await response.json();
                    
                    if (data.ok) {
                      statusEl.textContent = '提交成功！您的工具已进入审核队列，我们会在一天内完成审核。';
                      statusEl.className = 'mt-4 text-sm text-green-400';
                      document.getElementById('submit-tool-form').reset();
                      document.getElementById('tool-icon').value = '</>';
                    } else {
                      statusEl.textContent = data.message || '提交失败，请稍后重试。';
                      statusEl.className = 'mt-4 text-sm text-red-400';
                    }
                  } catch (error) {
                    console.error('提交失败:', error);
                    statusEl.textContent = '提交失败，请稍后重试。';
                    statusEl.className = 'mt-4 text-sm text-red-400';
                  }
                });
              }
              
              // 显示微信公众号页面
              function showWeChatMP() {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                const config = getPageConfig('wechat-mp');
                const title = config.title || '微信公众号';
                const description = config.description || '关注我们的微信公众号，获取最新技术资讯';
                
                mainContent.innerHTML = `
                  <div class="mb-6">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description}</p>
                  </div>
                  
                  <div class="glass rounded-xl border border-dark-border p-8 max-w-md mx-auto text-center">
                    <div class="mb-6">
                      <img src="/static/wechat_mp_qr.jpg" alt="微信公众号二维码" class="w-64 h-64 mx-auto rounded-lg border border-dark-border" onerror="this.style.display='none'">
                    </div>
                    <p class="text-gray-300 mb-4">扫描二维码关注我们的微信公众号</p>
                    <p class="text-sm text-gray-400">获取最新的编程资讯、AI动态和开发工具推荐</p>
                  </div>
                `;
              }
              
              // 管理员入口授权码验证
              let adminCodeInput = '';
              let adminCodeTimeout = null;
              const ADMIN_CODE_MAX_LENGTH = 50; // 最大长度限制
              
              async function checkAdminCode(input) {
                if (input.length < 3) return; // 至少3个字符才开始验证
                
                try {
                  const response = await fetch(`${API_BASE}/admin/verify-code?code=${encodeURIComponent(input)}`);
                  const data = await response.json();
                  
                  if (data.ok && data.valid) {
                    // 授权码正确，显示管理员入口
                    const adminEntry = document.getElementById('admin-entry');
                    if (adminEntry) {
                      adminEntry.style.display = 'block';
                      adminEntry.classList.remove('hidden');
                      // 保存到localStorage，避免刷新后需要重新输入
                      localStorage.setItem('admin_verified', 'true');
                    }
                    // 清空输入
                    adminCodeInput = '';
                  }
                } catch (error) {
                  console.error('验证授权码失败:', error);
                }
              }
              
              // 监听键盘输入（盲敲）
              document.addEventListener('keydown', function(e) {
                // 排除输入框、文本域等元素
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
                  return;
                }
                
                // 只处理可打印字符
                if (e.key.length === 1) {
                  adminCodeInput += e.key;
                  
                  // 限制长度
                  if (adminCodeInput.length > ADMIN_CODE_MAX_LENGTH) {
                    adminCodeInput = adminCodeInput.slice(-ADMIN_CODE_MAX_LENGTH);
                  }
                  
                  // 清除之前的定时器
                  if (adminCodeTimeout) {
                    clearTimeout(adminCodeTimeout);
                  }
                  
                  // 延迟验证，避免频繁请求
                  adminCodeTimeout = setTimeout(() => {
                    checkAdminCode(adminCodeInput);
                  }, 500);
                } else if (e.key === 'Backspace' || e.key === 'Delete') {
                  // 允许退格删除
                  adminCodeInput = adminCodeInput.slice(0, -1);
                } else if (e.key === 'Escape') {
                  // ESC键清空输入
                  adminCodeInput = '';
                }
              });
              
              // 初始化
              document.addEventListener('DOMContentLoaded', async function() {
                // 先加载配置文件
                await loadConfig();
                
                // 检查是否已经验证过（从localStorage）
                if (localStorage.getItem('admin_verified') === 'true') {
                  const adminEntry = document.getElementById('admin-entry');
                  if (adminEntry) {
                    adminEntry.style.display = 'block';
                    adminEntry.classList.remove('hidden');
                  }
                }
                
                // 顶部导航激活状态管理
                const topNavItems = document.querySelectorAll('.top-nav-item');
                const currentPath = window.location.pathname || '/news';
                
                function updateActiveNav() {
                  topNavItems.forEach(item => {
                    const href = item.getAttribute('href');
                    if (href === currentPath || (currentPath === '/' && href === '/news')) {
                      item.classList.add('active');
                    } else {
                      item.classList.remove('active');
                    }
                  });
                }
                
                updateActiveNav();
                
                // 监听popstate事件（浏览器前进/后退）
                window.addEventListener('popstate', function() {
                  handleRoute();
                  updateActiveNav();
                });
                
                // 点击导航项
                topNavItems.forEach(item => {
                  item.addEventListener('click', function(e) {
                    const href = this.getAttribute('href');
                    // 如果链接是外部链接（如管理员入口），直接跳转
                    if (href.startsWith('http') || href.startsWith('/digest')) {
                      return; // 允许默认行为，直接跳转
                    }
                    e.preventDefault();
                    // 使用 history API 更新 URL
                    window.history.pushState({}, '', href);
                    handleRoute();
                    updateActiveNav();
                  });
                });
                
                // 左侧分类点击
                document.querySelectorAll('.nav-item').forEach(item => {
                  item.addEventListener('click', function(e) {
                    const href = this.getAttribute('href');
                    // 如果是外部链接，直接跳转
                    if (href.startsWith('http') || href.startsWith('/digest')) {
                      return;
                    }
                    e.preventDefault();
                    // 使用 history API 更新 URL
                    window.history.pushState({}, '', href);
                    handleRoute();
                    updateActiveNav();
                  });
                });
                
                // 初始加载
                handleRoute();
              });
            </script>
          </div>
          
          <!-- 浮动按钮 -->
          <div class="fixed bottom-8 right-8 flex flex-col gap-3" style="z-index: 100;">
            <button class="w-14 h-14 bg-gradient-to-br from-neon-cyan to-neon-blue text-dark-bg rounded-full shadow-lg hover:from-neon-blue hover:to-neon-cyan transition-all flex items-center justify-center neon-glow hover-glow">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </button>
            <button class="w-14 h-14 glass border border-dark-border text-neon-cyan rounded-full shadow-lg hover:bg-dark-card transition-all flex items-center justify-center hover:border-neon-cyan">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </button>
          </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)

    @app.get("/health")
    async def health_check():
        """健康检查接口"""
        return {"status": "ok", "service": "100kwhy-wechat-mp"}

    app.include_router(wechat.router, prefix="/wechat", tags=["wechat"])
    app.include_router(digest.router, prefix="/digest", tags=["digest"])
    
    # 注册API路由
    from .routes import api
    app.include_router(api.router, prefix="/api", tags=["api"])

    return app


app = create_app()


