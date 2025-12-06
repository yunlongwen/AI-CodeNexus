## AI-CodeNexus · AI编程资讯与工具聚合平台

`AI-CodeNexus` 是一个**AI编程资讯与工具聚合平台**，致力于为开发者提供最新、最优质的技术资讯、开发工具、AI编程提示词、规则和社区资源。

### 🌐 在线访问

**🎯 立即体验**：[https://aicoding.100kwhy.fun/](https://aicoding.100kwhy.fun/)

访问我们的在线平台，浏览最新技术资讯、发现优质开发工具！

### 📱 关注微信公众号

<div align="center">
  <img src="app/presentation/static/wechat_mp_qr.jpg" alt="微信公众号二维码" width="200" />
  <br/>
  <p>扫描二维码关注公众号，获取最新技术资讯和工具推荐</p>
</div>

---

### 核心功能

- **📰 资讯聚合**：整合编程资讯和AI资讯，提供统一的内容浏览体验
- **🛠️ 工具发现**：帮助开发者发现和分享优秀的开发工具
- **💡 提示词库**：精选AI编程提示词，支持分类浏览和搜索
- **📋 规则集合**：Cursor Rules和其他AI编程规则（31个规则）
- **📚 社区资源**：AI编程教程、文章和社区资源聚合
- **📅 周报生成**：自动生成每周资讯汇总，适合微信公众号发布
- **🤖 AI助手**：微信公众号发布助手，Markdown与公众号格式互转
- **🔥 智能推荐**：基于点击量和热度的智能排序和推荐
- **👥 用户参与**：支持用户提交优质文章和工具
- **🔐 内容管理**：完善的管理员审核和管理系统
- **📊 数据统计**：实时访问量统计和热度排序
- **⏰ 自动推送**：定时抓取、筛选和推送优质内容到企业微信

> **定位**：我们是一个**分发基地**，不存储文章和工具的完整内容，只提供链接和元数据，帮助开发者快速发现优质资源。同时提供AI编程相关的提示词、规则和社区资源，以及实用的AI助手工具。

---

### 核心特性

| 特性 | 描述 |
| --- | --- |
| **资讯浏览** | 编程资讯、AI资讯、热门资讯、最新资讯，支持搜索和分页 |
| **工具发现** | 热门工具、工具分类浏览，支持搜索和点击统计 |
| **提示词库** | 精选AI编程提示词，支持分类浏览、搜索和一键复制 |
| **规则集合** | Cursor Rules和其他AI编程规则（31个规则），支持分类浏览和搜索 |
| **社区资源** | AI编程教程、文章和社区资源，支持类型和分类筛选 |
| **周报生成** | 自动生成每周资讯汇总，支持Markdown格式，适合微信公众号发布 |
| **AI助手** | 微信公众号发布助手，Markdown与公众号格式互转，一键发布草稿 |
| **用户提交** | 支持用户提交优质文章和工具，等待管理员审核 |
| **智能排序** | 基于访问量的热度排序，实时更新 |
| **文章-工具关联** | 归档文章时可添加工具标签，点击工具时显示相关文章 |
| **管理员审核** | 完善的审核系统，支持采纳、归档、忽略、删除操作 |
| **自动推送** | 定时抓取、筛选和推送优质内容到企业微信 |
| **数据备份** | 每天自动备份数据到GitHub |
| **现代化UI** | 科技感主题，玻璃态效果，流畅动画 |
| **标准路由** | 使用History API，无 `#` 符号的标准URL路由 |
| **分页加载** | 所有列表支持分页，防止数据量过大导致卡顿 |
| **点击统计** | 实时记录文章和工具的访问量，用于热度排序 |

---

### 技术栈

**后端**：
- Python 3.10+
- FastAPI + Uvicorn
- SQLite数据库（SQLAlchemy + aiosqlite）
- APScheduler（定时任务调度）
- loguru（日志）
- Playwright（网页爬虫）
- BeautifulSoup4 + lxml（HTML解析）
- feedparser（RSS解析）
- markdown + html2text（Markdown处理）

**前端**：
- 原生JavaScript（SPA架构）
- Tailwind CSS + 自定义CSS
- History API（路由）
- Google Fonts（Orbitron、Rajdhani）

**数据服务**：
- `DatabaseDataService` - 从数据库读取数据
- `DatabaseWriteService` - 将数据写入数据库
- 支持分页、筛选、搜索、排序
- 支持点击统计和文章-工具关联
- 支持提示词、规则、社区资源等新数据类型

---

### 目录结构

```text
app/
  main.py                # 应用入口
  domain/                # 领域层（业务模型）
    digest/             # 摘要模型
    sources/            # 数据源管理
  infrastructure/        # 基础设施层
    crawlers/           # 爬虫（RSS、GitHub、HackerNews等）
    notifiers/          # 通知服务（企业微信、微信公众号）
    db/                 # 数据库
  services/             # 服务层（业务服务）
    database_data_service.py  # 数据库读取服务
    database_write_service.py # 数据库写入服务
    data_loader.py      # 数据加载服务（仅用于候选池等临时数据）
    digest_service.py   # 推送服务
    backup_service.py   # 备份服务
    weekly_backup_service.py  # 手动备份服务（从数据库导出JSON）
    weekly_digest.py    # 周报生成服务
    crawler_service.py  # 爬虫服务
  presentation/          # 表示层
    routes/             # API路由
      api.py           # 主要API路由
      digest.py        # 推送管理路由
      wechat.py        # 微信相关路由
      ai_assistant.py  # AI助手路由
    templates.py        # HTML模板
    static/             # 静态资源
config/
  crawler_keywords.json # 抓取关键词
  digest_schedule.json  # 推送调度配置
data/
  config.json           # 页面和分类配置（仅用于前端展示配置）
  articles/             # 文章候选池和推送列表（JSON文件，仅用于候选数据）
    ai_candidates.json # 文章候选池
    ai_articles.json   # 资讯推送列表
  tools/                # 工具候选池（JSON文件，仅用于候选数据）
    tool_candidates.json  # 工具候选池
  prompts/              # 提示词备份文件（从数据库导出）
    prompts.json       # 提示词备份
  rules.json            # 规则备份文件（从数据库导出）
  resources.json        # 社区资源备份文件（从数据库导出）
  weekly/               # 周报文件
    {year}weekly{week}.md  # 每周资讯汇总
data.db                 # SQLite数据库（主要数据存储）
docs/
  technical/            # 技术文档
    ARCHITECTURE.md    # 架构设计文档
  deploy/               # 部署相关文档
  feature/              # 功能描述文档
requirements.txt        # 依赖清单
```

> 📖 **架构说明**：项目采用 Clean 架构设计，详细说明请查看 [架构设计文档](docs/technical/ARCHITECTURE.md)

---

## 快速开始

```bash
git clone https://github.com/your-name/100kwhy_wechat_mp.git
cd 100kwhy_wechat_mp

python -m venv venv
# Windows: .\venv\Scripts\activate
source venv/bin/activate

pip install -r requirements.txt
playwright install  # 首次安装需要下载浏览器内核
```

创建 `.env` 文件：

```bash
# 管理员授权码（用于显示管理员入口）
AICODING_ADMIN_CODE="your-admin-code-here"

# 企业微信推送（可选）
WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
```

安装依赖并启动：

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问地址：
- **在线平台**：**[https://aicoding.100kwhy.fun/](https://aicoding.100kwhy.fun/)** ⭐
- **本地开发**：`http://localhost:8000/`
- **管理面板**：`http://localhost:8000/digest/panel`（需要授权码）
- **AI助手**：`http://localhost:8000/ai-assistant`（微信公众号发布助手）
- **API文档**：`http://localhost:8000/docs`

> 🌐 **在线体验**：访问 [https://aicoding.100kwhy.fun/](https://aicoding.100kwhy.fun/) 立即使用我们的平台  
> 📖 **详细文档**：请查看 [完整功能文档](docs/feature/features_complete.md)  
> 🚀 **部署指南**：请参考 [Python环境部署](docs/deploy/deploy_python.md) 或 [Windows部署](docs/deploy/deploy_windows.md)

#### 🌐 在线使用（推荐）

直接访问 **[https://aicoding.100kwhy.fun/](https://aicoding.100kwhy.fun/)** 开始使用，无需安装！

#### 💻 本地开发

1. **浏览资讯**：
   - 访问 `/news` 查看编程资讯
   - 访问 `/ai-news` 查看AI资讯
   - 访问 `/hot-news` 查看热门资讯（按访问量排序）
   - 访问 `/recent` 查看最新资讯（支持搜索）

2. **发现工具**：
   - 访问 `/tools` 查看热门工具（按访问量排序）
   - 访问 `/category/{category}` 查看分类工具
   - 访问 `/tool/{tool_id_or_identifier}` 查看工具详情和相关文章

3. **提示词和规则**：
   - 访问 `/prompts` 浏览AI编程提示词，支持分类和搜索
   - 访问 `/rules` 浏览Cursor Rules和其他AI编程规则
   - 访问 `/resources` 浏览AI编程教程和社区资源

4. **周报和AI助手**：
   - 访问 `/weekly/{weekly_id}` 查看每周资讯汇总
   - 访问 `/ai-assistant` 使用微信公众号发布助手

5. **提交内容**：
   - 访问 `/submit` 提交优质文章
   - 访问 `/submit-tool` 提交开发工具
   - 提交后等待管理员审核

6. **管理员审核**：
   - 在网页上"盲敲"授权码显示管理员入口
   - 访问管理面板审核用户提交的内容
   - 对文章进行采纳、归档（可添加工具标签）、忽略操作
   - 对工具进行采纳（选择分类）、忽略操作
   - **删除文章**：管理员登录后，在前端页面的每个文章右侧会显示删除按钮，点击可删除文章（会从文章池、归档分类、周报等所有数据源中删除）

---

## 功能特性

### 资讯模块
- ✅ 编程资讯、AI资讯分类浏览
- ✅ 热门资讯（按访问量排序）
- ✅ 最新资讯（合并分类，支持搜索）
- ✅ 用户提交文章功能
- ✅ 点击统计和热度排序
- ✅ 周报自动生成（每周资讯汇总）

### 工具模块
- ✅ 热门工具（按访问量排序）
- ✅ 11个工具分类（按研发流程排序）
- ✅ 工具详情和相关文章
- ✅ 用户提交工具功能
- ✅ 点击统计和热度排序
- ✅ 工具标识符（identifier）支持

### 提示词模块（v4.0新增）
- ✅ 精选AI编程提示词
- ✅ 支持分类浏览和搜索
- ✅ 一键复制提示词内容
- ✅ 优化排版，完整显示提示词内容

### 规则模块（v4.0新增）
- ✅ Cursor Rules和其他AI编程规则
- ✅ 31个精选规则
- ✅ 支持分类浏览和搜索
- ✅ 参考 cursor.directory 和 dotcursorrules.com

### 社区资源模块（v4.0新增）
- ✅ AI编程教程、文章和社区资源
- ✅ 支持类型和分类筛选
- ✅ 按分类模块化显示
- ✅ 参考 cursor101.com 的资源内容
- ✅ **Claude Code 资源**（v4.1新增）
  - 新增 Claude Code 资源分类，包含17个精选资源
  - 支持四个子分类：插件市场、模型服务、Skill、其他
  - 自动分类和智能筛选功能

### AI助手模块
- ✅ 微信公众号发布助手
- ✅ Markdown转微信公众号格式
- ✅ 微信公众号文章转Markdown
- ✅ 一键发布到公众号草稿箱
- ✅ 草稿箱管理

### 管理员功能
- ✅ 隐藏式管理员入口（盲敲授权码）
- ✅ 文章候选池管理（采纳、归档、忽略）
- ✅ 工具候选池管理（采纳、忽略）
- ✅ 文章-工具关联（归档时添加工具标签）
- ✅ 归档状态显示（已归档标签）
- ✅ 文章删除功能（管理员登录后，前端页面每个文章右侧显示删除按钮，支持从所有数据源删除）

### 自动化功能
- ✅ 定时抓取文章（支持RSS、GitHub Trending、Hacker News等）
- ✅ 自动推送到企业微信
- ✅ 自动生成周报
- ✅ 手动备份数据到GitHub（管理员面板操作）

### 技术特性
- ✅ 标准URL路由（无 `#` 符号）
- ✅ 分页加载（防止卡顿）
- ✅ 搜索功能（最新资讯、提示词、规则、资源）
- ✅ 动态配置（页面标题/描述）
- ✅ 响应式设计（移动端完美适配）
  - 移动端侧边栏抽屉式菜单，支持滑动显示/隐藏
  - 移动端顶部导航下拉菜单，方便访问所有功能
  - 主内容区域自动占满屏幕，充分利用移动端空间
  - 优化的触摸交互和动画效果

---

## 使用场景

1. **开发者日常浏览**：快速浏览最新技术资讯和热门工具
2. **内容发现**：通过热门排序发现最受欢迎的内容
3. **工具推荐**：发现和分享优秀的开发工具
4. **AI编程学习**：浏览提示词、规则和社区资源，提升AI编程效率
5. **内容创作**：使用AI助手将Markdown转换为微信公众号格式并发布
6. **周报生成**：自动生成每周资讯汇总，适合复制到微信公众号
7. **内容贡献**：提交优质文章和工具，帮助社区成长
8. **内容管理**：管理员审核和分类管理用户提交的内容
9. **自动化运营**：定时抓取、筛选和推送优质内容

---

## 📚 文档

**技术文档** (docs/technical/):
- **[架构设计文档](docs/technical/ARCHITECTURE.md)** ⭐ - Clean架构重构说明，包含各层次职责和依赖关系

**功能文档** (docs/feature/):
- **[完整功能文档](docs/feature/features_complete.md)** ⭐ - 详细的功能说明和使用指南
- [功能开发计划](docs/feature/feature_plan.md) - 功能规划文档
- [多资讯源使用指南](docs/feature/multi_sources_guide.md) - 多资讯源配置
- [测试指南](docs/feature/test_sources.md) - 测试方法
- [工具详情功能](docs/feature/tool_detail_feature.md) - 工具详情页功能说明

**部署文档** (docs/deploy/):
- [Python环境部署](docs/deploy/deploy_python.md) - 生产环境部署
- [Windows部署](docs/deploy/deploy_windows.md) - Windows本地部署
- [宝塔部署](docs/deploy/deploy_baota.md) - 宝塔面板部署
- [微信公众号发布指南](docs/deploy/wechat_mp_guide.md) - 公众号发布配置

---

## 🔄 更新日志

详细的更新日志请查看 [CHANGELOG.md](CHANGELOG.md)。

### 最近更新

#### v4.1（最新）
- ✅ **Claude Code 资源模块** - 新增 Claude Code 资源分类
  - 从 devmaster.cn 自动抓取 Claude Code 相关资源
  - 支持四个子分类：插件市场、模型服务、Skill、其他
  - 智能分类算法，根据资源内容自动归类
  - 桌面端和移动端均支持子分类浏览
- ✅ 修复每周资讯页面重复显示标题的问题
- ✅ 修复资源显示代码的语法错误，解决菜单点击无响应问题

#### v4.0
- ✅ **全新导航菜单** - 聚焦AI编程核心：最新资讯、提示词、规则、社区资源
- ✅ **提示词模块** - 精选AI编程提示词，支持分类浏览、搜索和一键复制
- ✅ **规则模块** - Cursor Rules和其他AI编程规则集合（31个规则）
- ✅ **社区资源模块** - AI编程教程、文章和社区资源聚合，按分类模块化显示
- ✅ 添加16个AI编程工具到工具库（Rosebud、Clacky、GPT Engineer等）
- ✅ 修复导航菜单激活状态问题
- ✅ 修复社区资源加载失败问题
- ✅ 优化提示词复制功能和排版

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

## 路线图

详细任务都写在 [TODO.md](TODO.md)，包括：

- 引入更多资讯源（RSS、GitHub Trending、Hacker News…）
- 文章打标签 + 智能排序，支持多频道策略
- 打通微信公众号草稿 / 发布接口，真正做到“抓 → 发”全自动
- 管理面板批注、协作与更细粒度的权限控制

欢迎 Issue / PR，一起来把 AI 资讯的“自动驾驶模式”做稳。

---

## 开源协议

MIT License — 在遵守协议前提下可自由使用、修改、分发。若 AICoding Daily 帮到了你，欢迎 ⭐️ 支持，并分享给更多需要自动化内容生产的团队！
