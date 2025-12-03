## AI-CodeNexus · 编程资讯与工具聚合平台

`AI-CodeNexus` 是一个**编程资讯与工具聚合平台**，致力于为开发者提供最新、最优质的技术资讯和开发工具。

### 🌐 在线访问

**🎯 立即体验**：[https://aicoding.100kwhy.fun/](https://aicoding.100kwhy.fun/)

访问我们的在线平台，浏览最新技术资讯、发现优质开发工具！

### 📱 关注微信公众号

<div align="center">
  <img src="app/static/wechat_mp_qr.jpg" alt="微信公众号二维码" width="200" />
  <br/>
  <p>扫描二维码关注公众号，获取最新技术资讯和工具推荐</p>
</div>

---

### 核心功能

- **📰 资讯聚合**：整合编程资讯和AI资讯，提供统一的内容浏览体验
- **🛠️ 工具发现**：帮助开发者发现和分享优秀的开发工具
- **🔥 智能推荐**：基于点击量和热度的智能排序和推荐
- **👥 用户参与**：支持用户提交优质文章和工具
- **🔐 内容管理**：完善的管理员审核和管理系统
- **📊 数据统计**：实时访问量统计和热度排序

> **定位**：我们是一个**分发基地**，不存储文章和工具的完整内容，只提供链接和元数据，帮助开发者快速发现优质资源。

---

### 核心特性

| 特性 | 描述 |
| --- | --- |
| **资讯浏览** | 编程资讯、AI资讯、热门资讯、最新资讯，支持搜索和分页 |
| **工具发现** | 热门工具、工具分类浏览，支持搜索和点击统计 |
| **用户提交** | 支持用户提交优质文章和工具，等待管理员审核 |
| **智能排序** | 基于访问量的热度排序，实时更新 |
| **文章-工具关联** | 归档文章时可添加工具标签，点击工具时显示相关文章 |
| **管理员审核** | 完善的审核系统，支持采纳、归档、忽略、删除操作 |
| **现代化UI** | 科技感主题，玻璃态效果，流畅动画 |
| **标准路由** | 使用History API，无 `#` 符号的标准URL路由 |
| **分页加载** | 所有列表支持分页，防止数据量过大导致卡顿 |
| **点击统计** | 实时记录文章和工具的访问量，用于热度排序 |

---

### 技术栈

**后端**：
- Python 3.10+
- FastAPI + Uvicorn
- JSON文件存储（`data/` 目录）
- loguru（日志）

**前端**：
- 原生JavaScript（SPA架构）
- Tailwind CSS + 自定义CSS
- History API（路由）
- Google Fonts（Orbitron、Rajdhani）

**数据服务**：
- `DataLoader` - 统一的数据加载和保存服务
- 支持分页、筛选、搜索、排序
- 支持点击统计和文章-工具关联

---

### 目录结构

```text
app/
  main.py                # 应用入口 + 前端HTML
  routes/
    api.py              # 公开API接口
    digest.py           # 管理员面板和API
  services/
    data_loader.py      # 数据加载和保存服务
  sources/              # 文章池 / 候选池工具 & 爬虫
  notifier/             # 推送服务
config/
  crawler_keywords.json # 抓取关键词
data/
  config.json           # 页面和分类配置
  articles/             # 正式文章池
    programming.json   # 编程资讯
    ai_news.json       # AI资讯
  tools/                # 正式工具池## 📄 更新日志
    featured.json      # 热门工具
    {category}.json   # 各分类工具
  articles/ai_candidates.json    # 文章候选池
  articles/ai_articles.json      # 资讯推送列表
  tools/tool_candidates.json  # 工具候选池
docs/
  deploy/               # 部署相关文档
  feature/              # 功能描述文档
  ADR/                  # 技术决策文档
requirements.txt        # 依赖清单
```

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
- **API文档**：`http://localhost:8000/docs`

> 🌐 **在线体验**：访问 [https://aicoding.100kwhy.fun/](https://aicoding.100kwhy.fun/) 立即使用我们的平台  
> 📖 **详细文档**：请查看 [完整功能文档](docs/feature/features_complete.md)  
> 🚀 **部署指南**：请参考 [Python环境部署](docs/deploy/deploy_python.md) 或 [Windows部署](docs/deploy/deploy_windows.md)

### 快速开始

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
   - 点击工具查看详情和相关文章

3. **提交内容**：
   - 访问 `/submit` 提交优质文章
   - 访问 `/submit-tool` 提交开发工具
   - 提交后等待管理员审核

4. **管理员审核**：
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

### 工具模块
- ✅ 热门工具（按访问量排序）
- ✅ 11个工具分类（按研发流程排序）
- ✅ 工具详情和相关文章
- ✅ 用户提交工具功能
- ✅ 点击统计和热度排序

### 管理员功能
- ✅ 隐藏式管理员入口（盲敲授权码）
- ✅ 文章候选池管理（采纳、归档、忽略）
- ✅ 工具候选池管理（采纳、忽略）
- ✅ 文章-工具关联（归档时添加工具标签）
- ✅ 归档状态显示（已归档标签）
- ✅ 文章删除功能（管理员登录后，前端页面每个文章右侧显示删除按钮，支持从所有数据源删除）

### 技术特性
- ✅ 标准URL路由（无 `#` 符号）
- ✅ 分页加载（防止卡顿）
- ✅ 搜索功能（最新资讯）
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
4. **内容贡献**：提交优质文章和工具，帮助社区成长
5. **内容管理**：管理员审核和分类管理用户提交的内容

---

## 📚 文档

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

### 最近更新（v4.0）
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
