"""HTML模板模块"""

INDEX_HTML = """
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

            /* 下拉菜单样式 - 完全透明，与提示词菜单保持一致 */
            .news-dropdown-menu,
            .weekly-dropdown-menu,
            .resources-dropdown-menu {
              background: transparent !important;
              backdrop-filter: none !important;
              border: none !important;
              box-shadow: none !important;
              padding: 0 !important;
            }
            
            .news-dropdown-menu a,
            .weekly-dropdown-menu a,
            .resources-dropdown-menu a {
              background: transparent !important;
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
            
            /* 移除下拉菜单按钮的背景色、边框和轮廓 */
            button.top-nav-item {
              background: transparent !important;
              border: none !important;
              outline: none !important;
              box-shadow: none !important;
            }
            
            button.top-nav-item:hover {
              background: transparent !important;
              border: none !important;
              outline: none !important;
              box-shadow: none !important;
            }
            
            button.top-nav-item:focus {
              background: transparent !important;
              border: none !important;
              outline: none !important;
              box-shadow: none !important;
            }
            
            button.top-nav-item:active {
              background: transparent !important;
              border: none !important;
              outline: none !important;
              box-shadow: none !important;
            }
            
            /* 移动端响应式样式 */
            @media (max-width: 768px) {
              /* 移动端隐藏顶部导航的所有链接 */
              .top-nav-item {
                display: none !important;
              }
              
              /* 移动端隐藏主导航容器 */
              nav.flex.items-center {
                display: none !important;
              }
              
              /* 移动端显示汉堡菜单按钮 */
              .mobile-menu-btn {
                display: block !important;
                margin-right: 0.75rem;
              }
              
              /* 移动端侧边栏默认隐藏，可以滑动显示 */
              .sidebar {
                transform: translateX(-100%);
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                width: 280px;
                max-width: 80vw;
                box-shadow: 2px 0 10px rgba(0, 0, 0, 0.3);
              }
              
              .sidebar.open {
                transform: translateX(0);
              }
              
              /* 移动端侧边栏内容区域 */
              .sidebar .flex-1 {
                padding: 1rem;
              }
              
              /* 移动端导航项样式优化 */
              .sidebar .nav-item {
                padding: 0.875rem 1rem;
                font-size: 0.9375rem;
                margin-bottom: 0.25rem;
              }
              
              /* 移动端主内容区域不需要左边距 - 使用更具体的选择器覆盖Tailwind类 */
              main.main-content {
                margin-left: 0 !important;
                width: 100% !important;
                max-width: 100% !important;
              }
              
              main.main-content > div {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 1rem !important;
                padding-bottom: 1rem !important;
              }
              
              /* 移动端顶部导航栏调整 */
              header {
                padding: 0 1rem;
                height: 70px !important;
              }
              
              header .max-w-7xl {
                padding-left: 1rem;
                padding-right: 1rem;
              }
              
              /* Logo区域调整 */
              .logo-area {
                flex: 1;
                min-width: 0;
              }
              
              .logo-area h1 {
                font-size: 1.25rem;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
              }
              
              .logo-area p {
                display: none !important;
              }
              
              /* 遮罩层 */
              .sidebar-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.6);
                z-index: 15;
                display: none;
                backdrop-filter: blur(2px);
              }
              
              .sidebar-overlay.show {
                display: block;
              }
              
              /* 移动端内容区域顶部间距调整 */
              main.main-content {
                margin-top: 70px !important;
                padding-top: 0 !important;
              }
              
              /* 确保侧边栏在移动端不占据布局空间 */
              .sidebar {
                position: fixed !important;
              }
              
              /* 移动端主容器不需要为侧边栏留空间 */
              .main-container {
                margin-left: 0 !important;
              }
              
              /* 确保主内容区域在移动端占满宽度 */
              main.main-content {
                left: 0 !important;
                right: 0 !important;
              }
              
              /* 移动端侧边栏顶部位置调整 */
              .sidebar {
                top: 70px !important;
                height: calc(100vh - 70px) !important;
              }
            }
            
            /* 桌面端样式 */
            @media (min-width: 769px) {
              .mobile-menu-btn {
                display: none !important;
              }
              
              .sidebar {
                transform: translateX(0) !important;
              }
              
              .sidebar-overlay {
                display: none !important;
              }
            }
            
            /* 汉堡菜单按钮样式 */
            .mobile-menu-btn {
              display: none;
              background: transparent;
              border: none;
              color: #00f0ff;
              font-size: 1.5rem;
              cursor: pointer;
              padding: 0.5rem;
              transition: all 0.3s ease;
              line-height: 1;
            }
            
            .mobile-menu-btn:hover {
              color: #a855f7;
              transform: scale(1.1);
            }
            
            .mobile-menu-btn:active {
              transform: scale(0.95);
            }
            
            /* 移动端关闭按钮样式 */
            .mobile-close-btn {
              background: transparent;
              border: none;
              cursor: pointer;
              padding: 0.25rem 0.5rem;
              transition: all 0.3s ease;
              line-height: 1;
            }
            
            .mobile-close-btn:hover {
              transform: scale(1.1);
            }
            
            .mobile-close-btn:active {
              transform: scale(0.95);
            }
            
            /* 移动端顶部导航菜单按钮 */
            .mobile-top-nav-btn {
              display: none;
              background: transparent;
              border: none;
              color: #00f0ff;
              font-size: 1.25rem;
              cursor: pointer;
              padding: 0.5rem;
              transition: all 0.3s ease;
              line-height: 1;
            }
            
            .mobile-top-nav-btn:hover {
              color: #a855f7;
              transform: scale(1.1);
            }
            
            /* 移动端顶部导航下拉菜单 */
            .mobile-top-nav-menu {
              position: fixed;
              top: 70px;
              left: 0;
              right: 0;
              background: rgba(17, 24, 39, 0.95);
              backdrop-filter: blur(10px);
              border-bottom: 1px solid rgba(255, 255, 255, 0.1);
              z-index: 19;
              max-height: 0;
              overflow: hidden;
              transition: max-height 0.3s ease-in-out;
              box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            }
            
            .mobile-top-nav-menu.open {
              max-height: 500px;
            }
            
            .mobile-top-nav-menu .mobile-nav-link {
              display: block;
              padding: 1rem 1.5rem;
              color: #d1d5db;
              text-decoration: none;
              border-bottom: 1px solid rgba(255, 255, 255, 0.05);
              transition: all 0.3s ease;
              font-size: 0.9375rem;
            }
            
            .mobile-top-nav-menu .mobile-nav-link:hover {
              background: rgba(0, 240, 255, 0.1);
              color: #00f0ff;
              padding-left: 2rem;
            }
            
            .mobile-top-nav-menu .mobile-nav-link:active {
              background: rgba(0, 240, 255, 0.15);
            }
            
            @media (max-width: 768px) {
              .mobile-top-nav-btn {
                display: block !important;
              }
            }

            /* 移动端子菜单样式 */
            .mobile-nav-submenu-header {
              display: block;
              padding: 1rem 1.5rem;
              color: #d1d5db;
              text-decoration: none;
              font-size: 0.9375rem;
              transition: all 0.3s ease;
              cursor: pointer;
              border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }

            .mobile-nav-submenu-header:hover {
              background: rgba(0, 240, 255, 0.1);
              color: #00f0ff;
              padding-left: 2rem;
            }

            .mobile-nav-submenu-content {
              transition: all 0.2s ease;
              max-height: 0;
              overflow: hidden;
            }

            .mobile-nav-submenu-content.open {
              max-height: 200px;
              display: block !important;
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
                  <div class="flex items-center flex-shrink-0 logo-area">
                    <!-- 移动端汉堡菜单按钮 -->
                    <button class="mobile-menu-btn" id="mobile-menu-btn" aria-label="打开菜单">
                      ☰
                    </button>
                    <h1 class="text-2xl tech-font-bold text-neon-cyan text-glow">AI-CodeNexus</h1>
                    <p class="text-sm text-gray-400 ml-4 hidden md:block tech-font">AI · 编程 · 工具聚合</p>
              </div>
              
              <!-- 主导航和管理员入口 -->
              <div class="flex items-center gap-2 flex-1 justify-end">
                  <nav class="flex items-center gap-2 flex-wrap">
                    <!-- 最新资讯下拉菜单 -->
                    <div class="relative">
                      <button class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap flex items-center gap-2" onclick="toggleNewsDropdown()">
                        📰 最新资讯
                        <svg class="w-4 h-4 transition-transform duration-200" id="news-dropdown-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                      </button>
                      <div class="news-dropdown-menu absolute top-full left-0 mt-1 w-48 hidden z-50" id="news-dropdown-menu">
                        <a href="/news" class="block px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan transition-all">
                          💻 编程资讯
                        </a>
                        <a href="/ai-news" class="block px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                          🤖 AI资讯
                        </a>
                      </div>
                    </div>
                    <!-- 每周资讯下拉菜单 -->
                    <div class="relative">
                      <button class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap flex items-center gap-2" onclick="toggleWeeklyDropdown()">
                        📅 每周资讯
                        <svg class="w-4 h-4 transition-transform duration-200" id="weekly-dropdown-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                      </button>
                      <div class="weekly-dropdown-menu absolute top-full left-0 mt-1 w-48 hidden z-50" id="weekly-dropdown-menu">
                        <!-- 动态加载的weekly列表 -->
                      </div>
                    </div>
                    <a href="/prompts" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      💡 提示词
                </a>
                    <a href="/rules" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      📋 规则
                </a>
                    <!-- 社区资源下拉菜单 -->
                    <div class="relative">
                      <button class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple rounded-lg transition-all whitespace-nowrap flex items-center gap-2" onclick="toggleResourcesDropdown()">
                        🌐 社区资源
                        <svg class="w-4 h-4 transition-transform duration-200" id="resources-dropdown-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                      </button>
                      <div class="resources-dropdown-menu absolute top-full left-0 mt-1 w-48 hidden z-50" id="resources-dropdown-menu">
                        <a href="/resources?category=飞书知识库" class="block px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                          📚 飞书知识库
                        </a>
                        <a href="/resources?category=技术社区" class="block px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                          👥 技术社区
                        </a>
                        <a href="/resources?category=Cursor资源" class="block px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                          🎯 Cursor资源
                        </a>
                        <div class="relative group">
                          <a href="/resources?category=Claude Code 资源" class="block px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                            🤖 Claude Code 资源
                            <svg class="w-3 h-3 inline ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                            </svg>
                          </a>
                          <div class="absolute left-full top-0 ml-1 w-48 hidden group-hover:block z-50">
                            <div class="glass rounded-lg border border-dark-border shadow-lg">
                              <a href="/resources?category=Claude Code 资源&subcategory=插件市场" class="block px-5 py-3 text-sm tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                                🔌 插件市场
                              </a>
                              <a href="/resources?category=Claude Code 资源&subcategory=模型服务" class="block px-5 py-3 text-sm tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                                🌐 模型服务
                              </a>
                              <a href="/resources?category=Claude Code 资源&subcategory=Skill" class="block px-5 py-3 text-sm tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                                🎯 Skill
                              </a>
                              <a href="/resources?category=Claude Code 资源&subcategory=其他" class="block px-5 py-3 text-sm tech-font-nav text-gray-300 hover:text-neon-purple transition-all">
                                📦 其他
                              </a>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <a href="/wechat-mp" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan rounded-lg transition-all whitespace-nowrap">
                      📱 微信公众号
                </a>
              </nav>
                  
                  <!-- 管理员入口（隐藏，需要输入授权码后显示，放在最右侧） -->
                  <a href="/digest/panel" id="admin-entry" class="top-nav-item px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-purple rounded-lg transition-all hidden whitespace-nowrap ml-2" style="display: none;">
                    🔐 管理员入口
                  </a>
                  
                  <!-- 移动端顶部导航菜单按钮 -->
                  <button class="mobile-top-nav-btn" id="mobile-top-nav-btn" aria-label="打开导航菜单">
                    ⋮
                  </button>
              </div>
                </div>
              </div>
            </header>
            
            <!-- 移动端顶部导航下拉菜单 -->
            <div class="mobile-top-nav-menu" id="mobile-top-nav-menu">
              <!-- 最新资讯子菜单 -->
              <div class="mobile-nav-submenu">
                <div class="mobile-nav-submenu-header" onclick="toggleMobileNewsSubmenu()">
                  📰 最新资讯
                  <svg class="w-4 h-4 transition-transform duration-200 inline ml-1" id="mobile-news-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                  </svg>
                </div>
                <div class="mobile-nav-submenu-content hidden pl-4" id="mobile-news-submenu">
                  <a href="/news" class="mobile-nav-link">💻 编程资讯</a>
                  <a href="/ai-news" class="mobile-nav-link">🤖 AI资讯</a>
                </div>
              </div>
              <!-- 每周资讯子菜单 -->
              <div class="mobile-nav-submenu">
                <div class="mobile-nav-submenu-header" onclick="toggleMobileWeeklySubmenu()">
                  📅 每周资讯
                  <svg class="w-4 h-4 transition-transform duration-200 inline ml-1" id="mobile-weekly-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                  </svg>
                </div>
                <div class="mobile-nav-submenu-content hidden pl-4" id="mobile-weekly-submenu">
                  <!-- 动态加载的weekly列表 -->
                </div>
              </div>
              <a href="/prompts" class="mobile-nav-link">💡 提示词</a>
              <a href="/rules" class="mobile-nav-link">📋 规则</a>
              <!-- 社区资源子菜单 -->
              <div class="mobile-nav-submenu">
                <div class="mobile-nav-submenu-header" onclick="toggleMobileResourcesSubmenu()">
                  🌐 社区资源
                  <svg class="w-4 h-4 transition-transform duration-200 inline ml-1" id="mobile-resources-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                  </svg>
                </div>
                <div class="mobile-nav-submenu-content hidden pl-4" id="mobile-resources-submenu">
                  <a href="/resources?category=飞书知识库" class="mobile-nav-link">📚 飞书知识库</a>
                  <a href="/resources?category=技术社区" class="mobile-nav-link">👥 技术社区</a>
                  <a href="/resources?category=Cursor资源" class="mobile-nav-link">🎯 Cursor资源</a>
                  <div class="mobile-nav-submenu">
                    <div class="mobile-nav-submenu-header" onclick="toggleMobileClaudeCodeSubmenu()">
                      🤖 Claude Code 资源
                      <svg class="w-4 h-4 transition-transform duration-200 inline ml-1" id="mobile-claude-code-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                      </svg>
                    </div>
                    <div class="mobile-nav-submenu-content hidden pl-4" id="mobile-claude-code-submenu">
                      <a href="/resources?category=Claude Code 资源&subcategory=插件市场" class="mobile-nav-link">🔌 插件市场</a>
                      <a href="/resources?category=Claude Code 资源&subcategory=模型服务" class="mobile-nav-link">🌐 模型服务</a>
                      <a href="/resources?category=Claude Code 资源&subcategory=Skill" class="mobile-nav-link">🎯 Skill</a>
                      <a href="/resources?category=Claude Code 资源&subcategory=其他" class="mobile-nav-link">📦 其他</a>
                    </div>
                  </div>
                </div>
              </div>
              <a href="/wechat-mp" class="mobile-nav-link">📱 微信公众号</a>
              <a href="/digest/panel" id="mobile-admin-entry" class="mobile-nav-link hidden" style="display: none;">🔐 管理员入口</a>
            </div>
            
            <!-- 移动端遮罩层 -->
            <div class="sidebar-overlay" id="sidebar-overlay"></div>
            
            <div class="flex flex-1 main-container" style="margin-top: 80px;">
              <!-- 左侧边栏 -->
              <aside class="sidebar w-64 glass border-r border-dark-border flex flex-col fixed" style="top: 80px; height: calc(100vh - 80px); z-index: 16;">
              
              <!-- 移动端侧边栏关闭按钮 -->
              <div class="md:hidden flex justify-end p-4 border-b border-dark-border">
                <button class="mobile-close-btn text-gray-400 hover:text-neon-cyan text-2xl transition-colors" id="mobile-close-btn" aria-label="关闭菜单">
                  ✕
                </button>
              </div>
              
              <!-- 工具分类 -->
                <div class="flex-1 p-5 overflow-y-auto">
                  <div class="space-y-2">
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
              <main class="main-content flex-1 ml-64 pt-20" style="position: relative; z-index: 1;">
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
                    
                    const isAdminUser = isAdmin();
                    const urlEscaped = article.url.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover relative">
                        ${isAdminUser ? `
                        <button onclick="deleteArticle('${urlEscaped}', '${category}')" class="absolute top-4 right-4 px-2 py-1 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded transition-colors" title="删除文章">
                          删除
                        </button>
                        ` : ''}
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
                    const isAdminUser = isAdmin();
                    const urlEscaped = article.url.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                    const categoryValue = article.category || '';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover relative">
                        ${isAdminUser ? `
                        <button onclick="deleteArticle('${urlEscaped}', '${categoryValue}')" class="absolute top-4 right-4 px-2 py-1 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded transition-colors" title="删除文章">
                          删除
                        </button>
                        ` : ''}
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
                    const isAdminUser = isAdmin();
                    const urlEscaped = article.url.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                    const categoryValue = article.category || '';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover relative">
                        ${isAdminUser ? `
                        <button onclick="deleteArticle('${urlEscaped}', '${categoryValue}')" class="absolute top-4 right-4 px-2 py-1 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded transition-colors" title="删除文章">
                          删除
                        </button>
                        ` : ''}
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
              
              // 顶部导航激活状态管理函数（必须在 handleRoute 之前定义）
              function updateActiveNav() {
                // 每次调用时都读取最新的路径
                const currentPath = window.location.pathname || '/news';
                const topNavItems = document.querySelectorAll('.top-nav-item');
                
                if (!topNavItems || topNavItems.length === 0) {
                  // DOM 还没加载完成，稍后重试
                  setTimeout(updateActiveNav, 100);
                  return;
                }
                
                // 路由映射：将当前路径映射到对应的导航项
                const routeMap = {
                  '/': '/news',
                  '/news': '/news',
                  '/ai-news': '/ai-news',
                  '/tools': '/tools',
                  '/prompts': '/prompts',
                  '/rules': '/rules',
                  '/resources': '/resources',
                  '/wechat-mp': '/wechat-mp'
                };
                
                // 处理动态路由
                let targetRoute = currentPath;
                if (currentPath.startsWith('/category/') || currentPath.startsWith('/tool/')) {
                  targetRoute = '/tools';
                } else if (routeMap[currentPath]) {
                  targetRoute = routeMap[currentPath];
                } else if (currentPath === '/') {
                  targetRoute = '/news';
                }
                
                topNavItems.forEach(item => {
                  const href = item.getAttribute('href');
                  // 先移除所有 active 类
                  item.classList.remove('active');
                  
                  // 检查是否应该激活
                  if (href === targetRoute || href === currentPath) {
                    item.classList.add('active');
                  }
                });
              }
              
              // 页面路由
              function handleRoute() {
                const path = window.location.pathname || '/news';
                currentPage.page = 1;
                
                // 移除开头的斜杠并转换为路由标识
                const route = path.startsWith('/') ? path.substring(1) : path;
                currentPage.type = route;
                
                // 更新导航激活状态
                setTimeout(updateActiveNav, 50);
                
                if (route === 'news' || route === '') {
                  currentPage.category = null;
                  loadArticles('programming', 1);
                } else if (route === 'ai-news') {
                  currentPage.category = null;
                  loadArticles('ai_news', 1);
                } else if (route === 'tools') {
                  currentPage.category = null;
                  loadTools(true, null, 1);
                } else if (route === 'prompts') {
                  currentPage.category = null;
                  loadPrompts(1);
                } else if (route === 'rules') {
                  currentPage.category = null;
                  loadRules(1);
                } else if (route === 'resources') {
                  currentPage.category = null;
                  loadResources(1);
                } else if (route === 'submit') {
                  currentPage.category = null;
                  showSubmitForm();
                } else if (route === 'submit-tool') {
                  currentPage.category = null;
                  showSubmitToolForm();
                } else if (route === 'wechat-mp') {
                  currentPage.category = null;
                  showWeChatMP();
                } else if (route.startsWith('weekly/')) {
                  const weeklyId = route.substring(7); // 'weekly/'.length = 7
                  currentPage.category = null;
                  loadWeekly(weeklyId);
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
                  // 默认显示编程资讯
                  currentPage.category = null;
                  loadArticles('programming', 1);
                }
                
                // 再次更新导航状态（确保在内容加载后）
                if (typeof updateActiveNav === 'function') {
                  setTimeout(updateActiveNav, 200);
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
                      const isAdminUser = isAdmin();
                      const urlEscaped = article.url.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                      const categoryValue = article.category || '';
                      
                      html += `
                        <article class="glass rounded-xl border border-dark-border p-6 card-hover relative">
                          ${isAdminUser ? `
                          <button onclick="deleteArticle('${urlEscaped}', '${categoryValue}')" class="absolute top-4 right-4 px-2 py-1 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded transition-colors" title="删除文章">
                            删除
                          </button>
                          ` : ''}
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
                    const isAdminUser = isAdmin();
                    const urlEscaped = article.url.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                    const categoryValue = article.category || '';
                    
                    html += `
                      <article class="glass rounded-xl border border-dark-border p-6 card-hover relative">
                        ${isAdminUser ? `
                        <button onclick="deleteArticle('${urlEscaped}', '${categoryValue}')" class="absolute top-4 right-4 px-2 py-1 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded transition-colors" title="删除文章">
                          删除
                        </button>
                        ` : ''}
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
                    const currentPage = parseInt(document.querySelector('.tech-font')?.textContent?.match(/\\d+/)?.[0]) || 1;
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
                    const currentPage = parseInt(document.querySelector('.tech-font')?.textContent?.match(/\\d+/)?.[0]) || 1;
                    setTimeout(() => loadTools(true, null, currentPage), 500);
                  }
                } catch (error) {
                  console.error('记录工具点击失败:', error);
                }
              }
              
              // 复制提示词到剪贴板
              async function copyPromptToClipboard(button, promptId) {
                try {
                  // 从 data 属性获取编码的内容
                  const encodedContent = button.getAttribute('data-content');
                  if (!encodedContent) {
                    console.error('未找到内容');
                    return;
                  }
                  
                  // 解码 base64 内容
                  const textContent = decodeURIComponent(escape(atob(encodedContent)));
                  
                  if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(textContent);
                  } else {
                    // 降级方案：使用 execCommand
                    const textArea = document.createElement('textarea');
                    textArea.value = textContent;
                    textArea.style.position = 'fixed';
                    textArea.style.opacity = '0';
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                  }
                  
                  // 显示成功提示
                  const originalText = button.innerHTML;
                  button.innerHTML = '✓ 已复制';
                  button.classList.add('bg-green-600');
                  button.classList.remove('bg-neon-cyan');
                  setTimeout(() => {
                    button.innerHTML = originalText;
                    button.classList.remove('bg-green-600');
                    button.classList.add('bg-neon-cyan');
                  }, 2000);
                } catch (error) {
                  console.error('复制失败:', error);
                  alert('复制失败，请手动选择文本复制');
                }
              }



              // 加载提示词
              async function loadPrompts(page = 1) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  const response = await fetch(`${API_BASE}/prompts?page=${page}&page_size=${currentPage.pageSize}`);
                  const data = await response.json();
                  
                  const config = getPageConfig('prompts');
                  const title = config.title || '提示词';
                  const description = config.description || '精选AI编程提示词，提升开发效率';
                  
                  let html = `
                    <div class="mb-6">
                      <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                      <p class="text-base text-gray-400 tech-font">${description} (共 ${data.total} 个)</p>
                    </div>
                    <div class="space-y-6 mb-8">
                  `;
                  
                  if (data.items.length === 0) {
                    html += '<div class="text-center py-20 text-gray-400">暂无提示词</div>';
                  } else {
                    data.items.forEach((prompt, index) => {
                      const promptId = prompt.id || index;
                      const identifier = prompt.identifier || '';
                      const hasContent = identifier; // 如果有identifier，就认为有内容

                      html += `
                        <article class="glass rounded-xl border border-dark-border p-6 card-hover relative">
                          <div class="flex items-start justify-between mb-4">
                            <div class="flex-1">
                              <h3 class="text-xl font-semibold text-gray-100 mb-2">${prompt.name}</h3>
                              <p class="text-sm text-gray-400 mb-3">${prompt.description}</p>
                            </div>
                            ${prompt.url ? `
                            <a href="${prompt.url}"
                                    target="_blank"
                                    class="ml-4 px-4 py-2 bg-neon-cyan hover:bg-neon-blue text-dark-bg rounded-lg font-medium transition-all hover-glow flex items-center gap-2 whitespace-nowrap">
                              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                              查看详情
                            </a>
                            ` : ''}
                          </div>
                          <div class="flex items-center justify-between mt-4 pt-4 border-t border-dark-border">
                            <div class="flex items-center gap-2 flex-wrap">
                              ${(prompt.tags || []).map(tag => `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`).join('')}
                            </div>
                            ${prompt.url ? `<a href="${prompt.url}" target="_blank" class="text-xs text-gray-400 hover:text-neon-cyan transition-colors">查看原文 →</a>` : ''}
                          </div>
                        </article>
                      `;
                    });
                  }
                  
                  html += '</div>';
                  
                  if (data.total_pages > 1) {
                    html += `
                      <div class="flex items-center justify-center gap-2 mt-8">
                        <button onclick="changePromptsPage(${data.page - 1})" ${data.page <= 1 ? 'disabled' : ''} class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">上一页</button>
                        <span class="px-4 py-2 text-gray-400 tech-font">第 ${data.page} / ${data.total_pages} 页</span>
                        <button onclick="changePromptsPage(${data.page + 1})" ${data.page >= data.total_pages ? 'disabled' : ''} class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">下一页</button>
                      </div>
                    `;
                  }

                  mainContent.innerHTML = html;

                  // 更新导航激活状态
                  setTimeout(updateActiveNav, 100);
                } catch (error) {
                  console.error('加载提示词失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败</div>';
                }
              }
              
              function changePromptsPage(page) {
                if (page < 1) return;
                loadPrompts(page);
              }
              
              // 加载规则
              async function loadRules(page = 1) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  // 规则页面一次性加载所有规则，不使用分页
                  const response = await fetch(`${API_BASE}/rules?page=1&page_size=100`);
                  const data = await response.json();
                  
                  const config = getPageConfig('rules');
                  const title = config.title || '规则';
                  const description = config.description || 'Cursor Rules和其他AI编程规则';
                  
                  let html = `
                    <div class="mb-6">
                      <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                      <p class="text-base text-gray-400 tech-font">${description} (共 ${data.total} 个)</p>
                    </div>
                    <div class="space-y-6 mb-8">
                  `;
                  
                  if (data.items.length === 0) {
                    html += '<div class="text-center py-20 text-gray-400">暂无规则</div>';
                  } else {
                    data.items.forEach((rule, index) => {
                      html += `
                        <article class="glass rounded-xl border border-dark-border p-6 card-hover relative">
                          <div class="flex items-start justify-between mb-4">
                            <div class="flex-1">
                              <h3 class="text-xl font-semibold text-gray-100 mb-2">${rule.name}</h3>
                              <p class="text-sm text-gray-400 mb-3">${rule.description}</p>
                            </div>
                            ${rule.url ? `
                            <a href="${rule.url}"
                                    target="_blank"
                                    class="ml-4 px-4 py-2 bg-neon-cyan hover:bg-neon-blue text-dark-bg rounded-lg font-medium transition-all hover-glow flex items-center gap-2 whitespace-nowrap">
                              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                              查看详情
                            </a>
                            ` : ''}
                          </div>
                          <div class="flex items-center justify-between mt-4 pt-4 border-t border-dark-border">
                            <div class="flex items-center gap-2 flex-wrap">
                              ${(rule.tags || []).map(tag => `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`).join('')}
                            </div>
                            ${rule.url ? `<a href="${rule.url}" target="_blank" class="text-xs text-gray-400 hover:text-neon-cyan transition-colors">查看原文 →</a>` : ''}
                          </div>
                        </article>
                      `;
                    });
                  }
                  
                  html += '</div>';
                  
                  if (data.total_pages > 1) {
                    html += `
                      <div class="flex items-center justify-center gap-2 mt-8">
                        <button onclick="changeRulesPage(${data.page - 1})" ${data.page <= 1 ? 'disabled' : ''} class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">上一页</button>
                        <span class="px-4 py-2 text-gray-400 tech-font">第 ${data.page} / ${data.total_pages} 页</span>
                        <button onclick="changeRulesPage(${data.page + 1})" ${data.page >= data.total_pages ? 'disabled' : ''} class="px-4 py-2 glass text-gray-300 rounded-lg hover:bg-dark-card hover:text-neon-cyan transition-all border border-dark-border disabled:opacity-50 disabled:cursor-not-allowed">下一页</button>
                      </div>
                    `;
                  }
                  
                  mainContent.innerHTML = html;
                  // 更新导航激活状态
                  setTimeout(updateActiveNav, 100);
                } catch (error) {
                  console.error('加载规则失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败</div>';
                }
              }
              
              function changeRulesPage(page) {
                if (page < 1) return;
                loadRules(page);
              }
              
              // 加载社区资源（按分类模块化显示）
              async function loadResources(page = 1, category = null) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;
                
                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';
                
                try {
                  // 从URL参数获取category和subcategory
                  const urlParams = new URLSearchParams(window.location.search);
                  const urlCategory = urlParams.get('category');
                  const urlSubcategory = urlParams.get('subcategory');
                  if (urlCategory) {
                    category = urlCategory;
                  }
                  
                  // 构建API URL
                  let apiUrl = `${API_BASE}/resources?page=1&page_size=100`;
                  if (category) {
                    apiUrl += `&category=${encodeURIComponent(category)}`;
                  }
                  if (urlSubcategory) {
                    apiUrl += `&subcategory=${encodeURIComponent(urlSubcategory)}`;
                  }
                  
                  const response = await fetch(apiUrl);
                  const data = await response.json();
                  
                  const config = getPageConfig('resources');
                  let title = config.title || '社区资源';
                  if (category) {
                    title = category;
                  }
                  const description = config.description || 'AI编程教程、文章和社区资源';
                  
                  // 如果有category参数，只显示该分类的资源
                  let displayItems = data.items;
                  if (category) {
                    displayItems = data.items.filter(resource => resource.category === category);
                    // 如果有subcategory参数，进一步过滤
                    if (urlSubcategory) {
                      displayItems = displayItems.filter(resource => resource.subcategory === urlSubcategory);
                    }
                  }
                  
                  let html = `
                    <div class="mb-6">
                      <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                      <p class="text-base text-gray-400 tech-font">${description} (共 ${displayItems.length} 个)</p>
                    </div>
                  `;
                  
                  if (displayItems.length === 0) {
                    html += '<div class="text-center py-20 text-gray-400">暂无资源</div>';
                  } else {
                    if (category) {
                      // 如果指定了分类，直接显示该分类的资源
                      const categoryIcon = category === '飞书知识库' ? '📚' : category === '技术社区' ? '👥' : category === 'Cursor资源' ? '🎯' : category === 'Claude Code 资源' ? '🤖' : '📦';
                      
                      // 如果是Claude Code资源且有subcategory，显示子分类标题
                      let categoryTitle = category;
                      if (category === 'Claude Code 资源' && urlSubcategory) {
                        const subcategoryIcon = urlSubcategory === '插件市场' ? '🔌' : urlSubcategory === '模型服务' ? '🌐' : urlSubcategory === 'Skill' ? '🎯' : '📦';
                        categoryTitle = `${category} - ${subcategoryIcon} ${urlSubcategory}`;
                      }
                      
                      html += `
                        <div class="mb-8">
                          <h2 class="text-2xl font-bold text-neon-cyan mb-4 flex items-center gap-2">
                            ${categoryIcon} ${categoryTitle}
                          </h2>
                          <div class="space-y-4">
                      `;
                      
                      displayItems.forEach(resource => {
                        html += `
                          <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                            <div class="flex items-start gap-3 mb-2">
                              <span class="text-sm px-2 py-1 glass border border-neon-purple/30 text-neon-purple rounded">${resource.type || '资源'}</span>
                            </div>
                            <h3 class="text-xl font-semibold text-gray-100 mb-2">
                              <a href="${resource.url}" target="_blank" class="hover:text-neon-cyan transition-colors">${resource.title}</a>
                            </h3>
                            <p class="text-sm text-gray-300 mb-3">${resource.description}</p>
                            ${resource.author ? `<p class="text-xs text-gray-400 mb-3">作者: ${resource.author}</p>` : ''}
                            <div class="flex items-center gap-2 flex-wrap">
                              ${(resource.tags || []).map(tag => `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`).join('')}
                            </div>
                          </article>
                        `;
                      });
                      
                      html += `
                          </div>
                        </div>
                      `;
                    } else {
                      // 按分类分组显示
                      const resourcesByCategory = {};
                      displayItems.forEach(resource => {
                        const cat = resource.category || '其他';
                        if (!resourcesByCategory[cat]) {
                          resourcesByCategory[cat] = [];
                        }
                        resourcesByCategory[cat].push(resource);
                      });
                      
                      const categoryOrder = ['飞书知识库', '技术社区', 'Cursor资源', 'Claude Code 资源', '其他'];
                      const sortedCategories = Object.keys(resourcesByCategory).sort((a, b) => {
                        const indexA = categoryOrder.indexOf(a);
                        const indexB = categoryOrder.indexOf(b);
                        if (indexA === -1 && indexB === -1) return a.localeCompare(b);
                        if (indexA === -1) return 1;
                        if (indexB === -1) return -1;
                        return indexA - indexB;
                      });
                      
                      sortedCategories.forEach(cat => {
                        const resources = resourcesByCategory[cat];
                        const categoryIcon = cat === '飞书知识库' ? '📚' : cat === '技术社区' ? '👥' : cat === 'Cursor资源' ? '🎯' : cat === 'Claude Code 资源' ? '🤖' : '📦';
                        
                        // 如果是Claude Code资源，按subcategory分组
                        if (cat === 'Claude Code 资源') {
                          const subcategories = {};
                          resources.forEach(resource => {
                            const subcat = resource.subcategory || '其他';
                            if (!subcategories[subcat]) {
                              subcategories[subcat] = [];
                            }
                            subcategories[subcat].push(resource);
                          });
                          
                          const subcategoryOrder = ['插件市场', '模型服务', 'Skill', '其他'];
                          const sortedSubcategories = Object.keys(subcategories).sort((a, b) => {
                            const indexA = subcategoryOrder.indexOf(a);
                            const indexB = subcategoryOrder.indexOf(b);
                            if (indexA === -1 && indexB === -1) return a.localeCompare(b);
                            if (indexA === -1) return 1;
                            if (indexB === -1) return -1;
                            return indexA - indexB;
                          });
                          
                          sortedSubcategories.forEach(subcat => {
                            const subcatResources = subcategories[subcat];
                            const subcategoryIcon = subcat === '插件市场' ? '🔌' : subcat === '模型服务' ? '🌐' : subcat === 'Skill' ? '🎯' : '📦';
                            
                            html += `
                              <div class="mb-8">
                                <h3 class="text-xl font-bold text-neon-purple mb-4 flex items-center gap-2">
                                  ${subcategoryIcon} ${subcat}
                                </h3>
                                <div class="space-y-4">
                            `;
                            
                            subcatResources.forEach(resource => {
                              html += `
                                <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                                  <div class="flex items-start gap-3 mb-2">
                                    <span class="text-sm px-2 py-1 glass border border-neon-purple/30 text-neon-purple rounded">${resource.type || '资源'}</span>
                                  </div>
                                  <h3 class="text-xl font-semibold text-gray-100 mb-2">
                                    <a href="${resource.url}" target="_blank" class="hover:text-neon-cyan transition-colors">${resource.title}</a>
                                  </h3>
                                  <p class="text-sm text-gray-300 mb-3">${resource.description}</p>
                                  ${resource.author ? `<p class="text-xs text-gray-400 mb-3">作者: ${resource.author}</p>` : ''}
                                  <div class="flex items-center gap-2 flex-wrap">
                                    ${(resource.tags || []).map(tag => `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`).join('')}
                                  </div>
                                </article>
                              `;
                            });
                            
                            html += `
                                </div>
                              </div>
                            `;
                          });
                        } else {
                          html += `
                            <div class="mb-8">
                              <h2 class="text-2xl font-bold text-neon-cyan mb-4 flex items-center gap-2">
                                ${categoryIcon} ${cat}
                              </h2>
                              <div class="space-y-4">
                          `;
                          
                          resources.forEach(resource => {
                            html += `
                              <article class="glass rounded-xl border border-dark-border p-6 card-hover">
                                <div class="flex items-start gap-3 mb-2">
                                  <span class="text-sm px-2 py-1 glass border border-neon-purple/30 text-neon-purple rounded">${resource.type || '资源'}</span>
                                </div>
                                <h3 class="text-xl font-semibold text-gray-100 mb-2">
                                  <a href="${resource.url}" target="_blank" class="hover:text-neon-cyan transition-colors">${resource.title}</a>
                                </h3>
                                <p class="text-sm text-gray-300 mb-3">${resource.description}</p>
                                ${resource.author ? `<p class="text-xs text-gray-400 mb-3">作者: ${resource.author}</p>` : ''}
                                <div class="flex items-center gap-2 flex-wrap">
                                  ${(resource.tags || []).map(tag => `<span class="px-2 py-1 glass text-neon-cyan text-xs rounded border border-neon-cyan/30">${tag}</span>`).join('')}
                                </div>
                              </article>
                            `;
                          });
                          
                          html += `
                              </div>
                            </div>
                          `;
                        }
                      });
                    }
                  }
                  
                  mainContent.innerHTML = html;
                  // 更新导航激活状态
                  setTimeout(updateActiveNav, 100);
                } catch (error) {
                  console.error('加载社区资源失败:', error);
                  mainContent.innerHTML = '<div class="text-center py-20 text-red-400">加载失败</div>';
                }
              }
              
              function changeResourcesPage(page) {
                if (page < 1) return;
                loadResources(page);
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
                  <div class="mb-6 text-center">
                    <h1 class="text-4xl tech-font-bold text-neon-cyan text-glow mb-2">${title}</h1>
                    <p class="text-base text-gray-400 tech-font">${description}</p>
                  </div>
                  
                  <div class="flex flex-col items-center gap-6">
                    <div class="glass rounded-xl border border-dark-border p-8 w-full max-w-md text-center">
                      <div class="mb-6">
                        <img src="/static/wechat_mp_qr.jpg" alt="微信公众号二维码" class="w-64 h-64 mx-auto rounded-lg border border-dark-border" onerror="this.style.display='none'">
                      </div>
                      <p class="text-gray-300 mb-4">扫描二维码关注我们的微信公众号</p>
                      <p class="text-sm text-gray-400">获取最新的编程资讯、AI动态和开发工具推荐</p>
                    </div>
                    
                    <div class="glass rounded-xl border border-dark-border p-8 w-full max-w-2xl">
                      <div class="flex items-center justify-center mb-4">
                        <svg class="w-8 h-8 mr-3 text-gray-300" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"></path>
                        </svg>
                        <h2 class="text-2xl tech-font-bold text-neon-purple text-glow">开源项目</h2>
                      </div>
                      <p class="text-gray-300 mb-4 text-center">这个平台是开源的！欢迎访问我们的 GitHub 仓库</p>
                      <div class="bg-dark-secondary rounded-lg p-4 mb-4 border border-dark-border">
                        <div class="text-center">
                          <a href="https://github.com/yunlongwen/AI-CodeNexus" target="_blank" rel="noopener noreferrer" class="text-neon-cyan hover:text-neon-green transition-colors text-lg font-medium inline-flex items-center justify-center">
                            <svg class="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                              <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"></path>
                            </svg>
                            <span>yunlongwen/AI-CodeNexus</span>
                            <svg class="w-4 h-4 ml-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                            </svg>
                          </a>
                          <p class="text-sm text-gray-400 mt-1">编程资讯与工具聚合平台</p>
                        </div>
                      </div>
                      <div class="text-center">
                        <p class="text-gray-300 mb-3">⭐ 如果这个项目对你有帮助，欢迎给个 Star！</p>
                        <a href="https://github.com/yunlongwen/AI-CodeNexus" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-6 py-3 bg-gradient-to-r from-neon-purple to-neon-cyan text-white rounded-lg font-medium hover:from-neon-cyan hover:to-neon-purple transition-all transform hover:scale-105 shadow-lg shadow-neon-purple/50">
                          <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.29-1.552 3.297-1.23 3.297-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"></path>
                          </svg>
                          前往 GitHub 点 Star
                        </a>
                      </div>
                    </div>
                  </div>
                `;
              }

              // 加载每周资讯
              async function loadWeekly(weeklyId) {
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return;

                mainContent.innerHTML = '<div class="text-center py-20"><div class="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-neon-cyan"></div></div>';

                try {
                  const response = await fetch(`${API_BASE}/weekly/${weeklyId}`);
                  if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: '加载失败' }));
                    throw new Error(errorData.detail || `HTTP ${response.status}`);
                  }
                  const data = await response.json();

                  let html = `
                    <div class="glass rounded-xl border border-dark-border p-8">
                      <div class="prose prose-invert max-w-none">
                        ${data.content || '<p class="text-gray-400">暂无内容</p>'}
                      </div>
                    </div>
                  `;

                  mainContent.innerHTML = html;
                  // 更新导航激活状态
                  setTimeout(updateActiveNav, 100);
                } catch (error) {
                  console.error('加载每周资讯失败:', error);
                  mainContent.innerHTML = `<div class="text-center py-20 text-red-400">加载失败: ${error.message}</div>`;
                }
              }
              
              // 管理员入口授权码验证
              let adminCodeInput = '';
              let adminCodeTimeout = null;
              const ADMIN_CODE_MAX_LENGTH = 50; // 最大长度限制
              
              // 检查是否为管理员
              function isAdmin() {
                return localStorage.getItem('admin_verified') === 'true';
              }
              
              // 获取管理员授权码（从digest面板）
              function getAdminCode() {
                return localStorage.getItem('aicoding_admin_code') || '';
              }
              
              // 删除文章函数
              async function deleteArticle(url, category) {
                if (!confirm('确定要删除这篇文章吗？删除后将从所有相关数据源（文章池、归档分类、周报）中移除。')) {
                  return;
                }
                
                try {
                  const adminCode = getAdminCode();
                  // 删除API路径是 /digest/delete-article（不使用API_BASE前缀）
                  const response = await fetch('/digest/delete-article', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'X-Admin-Code': adminCode || ''
                    },
                    body: JSON.stringify({ url: url })
                  });
                  
                  if (response.status === 401 || response.status === 403) {
                    alert('删除失败：需要管理员权限');
                    return;
                  }
                  
                  const data = await response.json();
                  if (data.ok) {
                    alert(data.message || '文章已成功删除');
                    // 重新加载当前页面
                    if (category) {
                      loadArticles(category, 1);
                    } else {
                      // 根据当前路由重新加载
                      handleRoute();
                    }
                  } else {
                    alert(data.message || '删除失败');
                  }
                } catch (error) {
                  console.error('删除文章失败:', error);
                  alert('删除失败，请查看浏览器控制台');
                }
              }
              
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
              
              // 移动端顶部导航菜单控制
              function initMobileTopNav() {
                const topNavBtn = document.getElementById('mobile-top-nav-btn');
                const topNavMenu = document.getElementById('mobile-top-nav-menu');
                const adminEntry = document.getElementById('admin-entry');
                const mobileAdminEntry = document.getElementById('mobile-admin-entry');
                
                if (!topNavBtn || !topNavMenu) return;
                
                // 同步管理员入口的显示状态
                function syncAdminEntry() {
                  if (adminEntry && mobileAdminEntry) {
                    if (adminEntry.style.display !== 'none' && !adminEntry.classList.contains('hidden')) {
                      mobileAdminEntry.style.display = 'block';
                      mobileAdminEntry.classList.remove('hidden');
                    } else {
                      mobileAdminEntry.style.display = 'none';
                      mobileAdminEntry.classList.add('hidden');
                    }
                  }
                }
                
                // 打开/关闭顶部导航菜单
                topNavBtn.addEventListener('click', function(e) {
                  e.stopPropagation();
                  topNavMenu.classList.toggle('open');
                });
                
                // 点击菜单项后关闭菜单
                const navLinks = topNavMenu.querySelectorAll('.mobile-nav-link');
                navLinks.forEach(link => {
                  link.addEventListener('click', function() {
                    topNavMenu.classList.remove('open');
                  });
                });
                
                // 点击外部区域关闭菜单
                document.addEventListener('click', function(e) {
                  if (!topNavMenu.contains(e.target) && !topNavBtn.contains(e.target)) {
                    topNavMenu.classList.remove('open');
                  }
                });
                
                // 窗口大小改变时关闭菜单
                window.addEventListener('resize', function() {
                  if (window.innerWidth > 768) {
                    topNavMenu.classList.remove('open');
                  }
                });
                
                // 初始化时同步管理员入口
                syncAdminEntry();
                
                // 监听管理员入口的变化（使用MutationObserver）
                if (adminEntry) {
                  const observer = new MutationObserver(syncAdminEntry);
                  observer.observe(adminEntry, {
                    attributes: true,
                    attributeFilter: ['style', 'class']
                  });
                }
              }

              // 最新资讯下拉菜单控制
              function toggleNewsDropdown() {
                const menu = document.getElementById('news-dropdown-menu');
                const arrow = document.getElementById('news-dropdown-arrow');

                if (menu.classList.contains('hidden')) {
                  menu.classList.remove('hidden');
                  arrow.style.transform = 'rotate(180deg)';
                } else {
                  menu.classList.add('hidden');
                  arrow.style.transform = 'rotate(0deg)';
                }
              }

              // 移动端最新资讯子菜单控制
              function toggleMobileNewsSubmenu() {
                const submenu = document.getElementById('mobile-news-submenu');
                const arrow = document.getElementById('mobile-news-arrow');

                if (submenu.classList.contains('open')) {
                  submenu.classList.remove('open');
                  submenu.classList.add('hidden');
                  arrow.style.transform = 'rotate(0deg)';
                } else {
                  submenu.classList.remove('hidden');
                  submenu.classList.add('open');
                  arrow.style.transform = 'rotate(90deg)';
                }
              }

              // 社区资源下拉菜单控制
              function toggleResourcesDropdown() {
                const menu = document.getElementById('resources-dropdown-menu');
                const arrow = document.getElementById('resources-dropdown-arrow');

                if (menu.classList.contains('hidden')) {
                  menu.classList.remove('hidden');
                  arrow.style.transform = 'rotate(180deg)';
                } else {
                  menu.classList.add('hidden');
                  arrow.style.transform = 'rotate(0deg)';
                }
              }

              // 每周资讯下拉菜单控制
              function toggleWeeklyDropdown() {
                const menu = document.getElementById('weekly-dropdown-menu');
                const arrow = document.getElementById('weekly-dropdown-arrow');

                if (!menu || !arrow) {
                  console.error('每周资讯下拉菜单元素未找到');
                  return;
                }

                if (menu.classList.contains('hidden')) {
                  menu.classList.remove('hidden');
                  arrow.style.transform = 'rotate(180deg)';
                  // 如果菜单内容为空，尝试重新加载
                  if (!menu.innerHTML || menu.innerHTML.trim() === '<!-- 动态加载的weekly列表 -->') {
                    loadWeeklyList();
                  }
                } else {
                  menu.classList.add('hidden');
                  arrow.style.transform = 'rotate(0deg)';
                }
              }

              // 移动端社区资源子菜单控制
              function toggleMobileResourcesSubmenu() {
                const submenu = document.getElementById('mobile-resources-submenu');
                const arrow = document.getElementById('mobile-resources-arrow');

                if (submenu.classList.contains('open')) {
                  submenu.classList.remove('open');
                  submenu.classList.add('hidden');
                  arrow.style.transform = 'rotate(0deg)';
                } else {
                  submenu.classList.remove('hidden');
                  submenu.classList.add('open');
                  arrow.style.transform = 'rotate(90deg)';
                }
              }
              
              function toggleMobileClaudeCodeSubmenu() {
                const submenu = document.getElementById('mobile-claude-code-submenu');
                const arrow = document.getElementById('mobile-claude-code-arrow');

                if (submenu.classList.contains('open')) {
                  submenu.classList.remove('open');
                  submenu.classList.add('hidden');
                  arrow.style.transform = 'rotate(0deg)';
                } else {
                  submenu.classList.remove('hidden');
                  submenu.classList.add('open');
                  arrow.style.transform = 'rotate(90deg)';
                }
              }

              // 移动端每周资讯子菜单控制
              function toggleMobileWeeklySubmenu() {
                const submenu = document.getElementById('mobile-weekly-submenu');
                const arrow = document.getElementById('mobile-weekly-arrow');

                if (submenu.classList.contains('open')) {
                  submenu.classList.remove('open');
                  submenu.classList.add('hidden');
                  arrow.style.transform = 'rotate(0deg)';
                } else {
                  submenu.classList.remove('hidden');
                  submenu.classList.add('open');
                  arrow.style.transform = 'rotate(90deg)';
                }
              }

              // 点击外部区域关闭下拉菜单
              document.addEventListener('click', function(e) {
                const newsDropdown = document.getElementById('news-dropdown-menu');
                const newsBtn = document.querySelector('[onclick="toggleNewsDropdown()"]');
                const resourcesDropdown = document.getElementById('resources-dropdown-menu');
                const resourcesBtn = document.querySelector('[onclick="toggleResourcesDropdown()"]');
                const weeklyDropdown = document.getElementById('weekly-dropdown-menu');
                const weeklyBtn = document.querySelector('[onclick="toggleWeeklyDropdown()"]');

                if (newsDropdown && !newsDropdown.contains(e.target) && !newsBtn.contains(e.target)) {
                  newsDropdown.classList.add('hidden');
                  const arrow = document.getElementById('news-dropdown-arrow');
                  if (arrow) arrow.style.transform = 'rotate(0deg)';
                }

                if (resourcesDropdown && !resourcesDropdown.contains(e.target) && !resourcesBtn.contains(e.target)) {
                  resourcesDropdown.classList.add('hidden');
                  const arrow = document.getElementById('resources-dropdown-arrow');
                  if (arrow) arrow.style.transform = 'rotate(0deg)';
                }

                if (weeklyDropdown && !weeklyDropdown.contains(e.target) && !weeklyBtn.contains(e.target)) {
                  weeklyDropdown.classList.add('hidden');
                  const arrow = document.getElementById('weekly-dropdown-arrow');
                  if (arrow) arrow.style.transform = 'rotate(0deg)';
                }
              });

              // 移动端侧边栏菜单控制
              function initMobileMenu() {
                const menuBtn = document.getElementById('mobile-menu-btn');
                const closeBtn = document.getElementById('mobile-close-btn');
                const sidebar = document.querySelector('.sidebar');
                const overlay = document.getElementById('sidebar-overlay');
                
                if (!menuBtn || !sidebar || !overlay) return;
                
                // 打开菜单
                function openMenu() {
                  sidebar.classList.add('open');
                  overlay.classList.add('show');
                  document.body.style.overflow = 'hidden'; // 防止背景滚动
                }
                
                // 关闭菜单
                function closeMenu() {
                  sidebar.classList.remove('open');
                  overlay.classList.remove('show');
                  document.body.style.overflow = ''; // 恢复滚动
                }
                
                // 点击汉堡菜单按钮
                menuBtn.addEventListener('click', function(e) {
                  e.stopPropagation();
                  if (sidebar.classList.contains('open')) {
                    closeMenu();
                  } else {
                    openMenu();
                  }
                });
                
                // 点击关闭按钮
                if (closeBtn) {
                  closeBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    closeMenu();
                  });
                }
                
                // 点击遮罩层关闭菜单
                overlay.addEventListener('click', closeMenu);
                
                // 点击侧边栏内的链接后关闭菜单（移动端）
                const sidebarLinks = sidebar.querySelectorAll('a');
                sidebarLinks.forEach(link => {
                  link.addEventListener('click', function() {
                    if (window.innerWidth <= 768) {
                      closeMenu();
                    }
                  });
                });
                
                // 窗口大小改变时，如果是桌面端则关闭菜单
                window.addEventListener('resize', function() {
                  if (window.innerWidth > 768) {
                    closeMenu();
                  }
                });
                
                // ESC键关闭菜单
                document.addEventListener('keydown', function(e) {
                  if (e.key === 'Escape' && sidebar.classList.contains('open')) {
                    closeMenu();
                  }
                });
              }
              
              // 加载每周资讯列表
              async function loadWeeklyList() {
                try {
                  const response = await fetch(`${API_BASE}/weekly`);
                  if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                  }
                  const data = await response.json();
                  
                  const weeklyMenu = document.getElementById('weekly-dropdown-menu');
                  const mobileWeeklySubmenu = document.getElementById('mobile-weekly-submenu');
                  
                  if (weeklyMenu) {
                    if (data.items && data.items.length > 0) {
                      let html = '';
                      data.items.forEach((item) => {
                        html += `<a href="/weekly/${item.id}" class="block px-5 py-3 text-base tech-font-nav text-gray-300 hover:text-neon-cyan transition-all">
                          📅 ${item.name}
                        </a>`;
                      });
                      weeklyMenu.innerHTML = html;
                    } else {
                      weeklyMenu.innerHTML = '<div class="px-5 py-3 text-sm text-gray-400">暂无每周资讯</div>';
                    }
                  }
                  
                  if (mobileWeeklySubmenu) {
                    if (data.items && data.items.length > 0) {
                      let html = '';
                      data.items.forEach(item => {
                        html += `<a href="/weekly/${item.id}" class="mobile-nav-link">📅 ${item.name}</a>`;
                      });
                      mobileWeeklySubmenu.innerHTML = html;
                    } else {
                      mobileWeeklySubmenu.innerHTML = '<div class="mobile-nav-link text-gray-400">暂无每周资讯</div>';
                    }
                  }
                } catch (error) {
                  console.error('加载每周资讯列表失败:', error);
                  const weeklyMenu = document.getElementById('weekly-dropdown-menu');
                  const mobileWeeklySubmenu = document.getElementById('mobile-weekly-submenu');
                  if (weeklyMenu) {
                    weeklyMenu.innerHTML = '<div class="px-5 py-3 text-sm text-red-400">加载失败</div>';
                  }
                  if (mobileWeeklySubmenu) {
                    mobileWeeklySubmenu.innerHTML = '<div class="mobile-nav-link text-red-400">加载失败</div>';
                  }
                }
              }

              // 初始化
              document.addEventListener('DOMContentLoaded', async function() {
                // 初始化移动端顶部导航菜单
                initMobileTopNav();
                
                // 初始化移动端侧边栏菜单
                initMobileMenu();
                
                // 先加载配置文件
                await loadConfig();
                
                // 加载每周资讯列表
                await loadWeeklyList();
                
                // 检查是否已经验证过（从localStorage）
                if (localStorage.getItem('admin_verified') === 'true') {
                  const adminEntry = document.getElementById('admin-entry');
                  if (adminEntry) {
                    adminEntry.style.display = 'block';
                    adminEntry.classList.remove('hidden');
                  }
                }
                
                // 初始化导航激活状态
                updateActiveNav();
                
                // 监听popstate事件（浏览器前进/后退）
                window.addEventListener('popstate', function() {
                  handleRoute();
                  setTimeout(updateActiveNav, 100);
                });
                
                // 点击导航项
                const topNavItems = document.querySelectorAll('.top-nav-item');
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
                    setTimeout(updateActiveNav, 100);
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
            <!-- 反馈/联系按钮 -->
            <button id="feedback-btn" class="w-14 h-14 bg-gradient-to-br from-neon-cyan to-neon-blue text-dark-bg rounded-full shadow-lg hover:from-neon-blue hover:to-neon-cyan transition-all flex items-center justify-center neon-glow hover-glow" title="反馈/联系">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </button>
            <!-- 回到顶部按钮 -->
            <button id="scroll-top-btn" class="w-14 h-14 glass border border-dark-border text-neon-cyan rounded-full shadow-lg hover:bg-dark-card transition-all flex items-center justify-center hover:border-neon-cyan opacity-0 pointer-events-none" title="回到顶部">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </button>
          </div>
          
          <script>
            // 反馈/联系按钮功能
            document.getElementById('feedback-btn')?.addEventListener('click', function() {
              // 跳转到社区资源页面
              window.location.href = '/resources';
            });
            
            // 回到顶部按钮功能
            const scrollTopBtn = document.getElementById('scroll-top-btn');
            if (scrollTopBtn) {
              // 监听滚动，显示/隐藏按钮
              window.addEventListener('scroll', function() {
                if (window.pageYOffset > 300) {
                  scrollTopBtn.classList.remove('opacity-0', 'pointer-events-none');
                  scrollTopBtn.classList.add('opacity-100');
                } else {
                  scrollTopBtn.classList.add('opacity-0', 'pointer-events-none');
                  scrollTopBtn.classList.remove('opacity-100');
                }
              });
              
              // 点击回到顶部
              scrollTopBtn.addEventListener('click', function() {
                window.scrollTo({
                  top: 0,
                  behavior: 'smooth'
                });
              });
            }
          </script>
        </body>
        </html>
        """

def get_index_html() -> str:
    """获取首页HTML"""
    return INDEX_HTML
