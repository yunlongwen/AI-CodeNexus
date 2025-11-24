# AI-CodeNexus 完整功能文档

## 📋 项目概述

**AI-CodeNexus** 是一个**编程资讯与工具聚合平台**，致力于为开发者提供最新、最优质的技术资讯和开发工具。平台采用现代化的单页应用（SPA）架构，提供流畅的用户体验和强大的内容管理功能。

### 核心定位
- **资讯分发基地**：不存储文章和工具的完整内容，只提供链接和元数据
- **内容聚合平台**：整合多个资讯源，提供统一的内容浏览体验
- **工具发现平台**：帮助开发者发现和分享优秀的开发工具
- **智能推荐系统**：基于点击量和热度的智能排序和推荐

---

## 🎨 用户界面与主题

### 视觉设计
- **科技感主题**：深色背景、霓虹色彩、玻璃态效果
- **现代化UI**：
  - 使用 Tailwind CSS 构建响应式布局
  - 自定义霓虹色彩（cyan、purple、green等）
  - 玻璃态卡片效果（glassmorphism）
  - 流畅的过渡动画和悬停效果
- **字体设计**：
  - 标题使用 Google Fonts - Orbitron（科技感）
  - 导航使用 Google Fonts - Rajdhani（现代感）
  - 优化的字体大小和间距

### 布局结构
- **顶部导航栏**（固定）：
  - 品牌标识：AI-CodeNexus
  - 主要导航：编程资讯、AI资讯、热门资讯、最新资讯、提交资讯、微信公众号
  - 管理员入口（隐藏，需输入授权码显示）
- **左侧边栏**（固定）：
  - 工具分类导航（按研发流程排序）
  - 热门工具、开发IDE、IDE插件、命令行工具、CodeAgent、AI测试、代码审查、DevOps工具、文档相关、设计工具、UI生成、MCP工具、提交工具
- **主内容区**：
  - 动态标题和描述
  - 内容列表/卡片展示
  - 分页控件
- **全局浮动按钮**（右下角固定）：
  - 反馈/联系按钮：点击跳转到提交资讯页面
  - 回到顶部按钮：滚动超过300px时显示，点击平滑滚动到顶部

### 路由系统
- **标准URL路由**：使用 History API，无 `#` 符号
- **路由路径**：
  - `/` 或 `/news` - 编程资讯
  - `/ai-news` - AI资讯
  - `/hot-news` - 热门资讯
  - `/recent` - 最新资讯
  - `/submit` - 提交资讯
  - `/submit-tool` - 提交工具
  - `/wechat-mp` - 微信公众号（包含GitHub仓库宣传）
  - `/tools` - 热门工具
  - `/category/{category}` - 工具分类（如 `/category/ide`）

---

## 📰 资讯模块

### 1. 编程资讯 (`/news`)
**功能描述**：展示编程相关的技术文章和资讯

**数据来源**：
- 存储位置：`data/articles/programming.json`
- 数据格式：JSON数组，每个文章包含标题、URL、摘要、来源、发布时间等

**功能特性**：
- ✅ 分页加载（每页20条，可配置）
- ✅ 按归档时间排序（默认）
- ✅ 文章卡片展示（标题、摘要、来源、时间、标签）
- ✅ 点击文章记录访问量
- ✅ 跳转到原文链接

**API接口**：
- `GET /api/news?category=programming&page=1&page_size=20&sort_by=archived_at`

### 2. AI资讯 (`/ai-news`)
**功能描述**：展示AI相关的文章和资讯

**数据来源**：
- 存储位置：`data/articles/ai_news.json`
- 数据格式：与编程资讯相同

**功能特性**：
- ✅ 分页加载
- ✅ 按归档时间排序
- ✅ AI标签高亮显示
- ✅ 点击统计

**API接口**：
- `GET /api/ai-news?page=1&page_size=20&sort_by=archived_at`

### 3. 热门资讯 (`/hot-news`)
**功能描述**：展示最受欢迎的技术文章，按热度排序

**排序规则**：
- 主要排序：按 `view_count`（访问量）降序
- 次要排序：如果访问量相同，按 `archived_at`（归档时间）降序

**功能特性**：
- ✅ 实时热度统计
- ✅ 点击文章自动增加热度（+1）
- ✅ 点击后自动刷新列表以更新排序
- ✅ 显示访问量统计

**API接口**：
- `GET /api/news?sort_by=score&page=1&page_size=20`
- `POST /api/articles/click?url={encoded_url}` - 记录文章点击

### 4. 最新资讯 (`/recent`)
**功能描述**：合并编程资讯和AI资讯，按时间排序，支持搜索

**功能特性**：
- ✅ 合并两个分类的文章
- ✅ 按 `archived_at` 时间倒序排列
- ✅ 搜索功能（标题、摘要、来源）
- ✅ 显示文章分类标签
- ✅ 显示归档时间
- ✅ 分页加载

**API接口**：
- `GET /api/recent?page=1&page_size=20&search={keyword}`

### 5. 提交资讯 (`/submit`)
**功能描述**：允许用户提交优质的技术文章

**提交流程**：
1. 用户填写表单：
   - 文章标题（必填）
   - 文章URL（必填）
   - 资讯分类（编程资讯/AI资讯，必填）
   - 推荐理由（可选）
2. 系统处理：
   - 检查URL是否重复
   - 随机分配关键词（从 `config/crawler_keywords.json`，用于分类标记）
   - 保存到候选池（`data/articles/ai_candidates.json`）
   - 等待管理员审核
3. 用户提示：
   - 显示"提交成功"消息
   - 说明文章将人工审核，一天内审核完成即可展示

**功能特性**：
- ✅ 表单验证（标题、URL必填）
- ✅ URL重复检测
- ✅ 自动分配关键词
- ✅ 友好的用户提示

**API接口**：
- `POST /api/articles/submit` - 提交文章

---

## 🛠️ 工具模块

### 1. 热门工具 (`/tools`)
**功能描述**：展示访问量最多的开发工具

**排序规则**：
- 主要排序：按 `view_count`（访问量）降序
- 次要排序：如果访问量相同，按 `created_at`（创建时间）降序

**功能特性**：
- ✅ 实时访问量统计
- ✅ 点击工具自动增加访问量（+1）
- ✅ 点击后自动刷新列表
- ✅ 显示访问量（🔥 X 次访问）
- ✅ 工具卡片展示（图标、名称、分类、描述、标签）
- ✅ 显示所有工具（不去重，按访问量排序显示前20个）

**数据来源**：
- 存储位置：`data/tools/featured.json`
- 数据格式：JSON数组，每个工具包含ID、名称、URL、描述、分类、标签、图标、访问量等

**API接口**：
- `GET /api/tools/featured?page=1&page_size=20&sort_by=view_count`
- `POST /api/tools/{tool_id}/click` - 记录工具点击

### 2. 工具分类 (`/category/{category}`)
**功能描述**：按分类展示工具

**工具分类**（按研发流程排序）：
1. **开发IDE** (`/category/ide`) - 集成开发环境
2. **IDE插件** (`/category/plugin`) - 编辑器插件和扩展
3. **命令行工具** (`/category/cli`) - 终端和命令行工具
4. **CodeAgent** (`/category/codeagent`) - AI代码助手和代理
5. **AI测试** (`/category/ai-test`) - AI驱动的测试工具
6. **代码审查** (`/category/review`) - 代码审查和质量检查工具
7. **DevOps工具** (`/category/devops`) - 开发和运维工具
8. **文档相关** (`/category/doc`) - 文档编写和管理工具
9. **设计工具** (`/category/design`) - UI/UX设计工具
10. **UI生成** (`/category/ui`) - AI驱动的UI生成工具
11. **MCP工具** (`/category/mcp`) - Model Context Protocol工具

**数据来源**：
- 存储位置：`data/tools/{category}.json`
- 每个分类有独立的JSON文件

**功能特性**：
- ✅ 分类筛选
- ✅ 分页加载
- ✅ 搜索功能（工具名称、描述）
- ✅ 点击统计
- ✅ 工具详情（显示相关文章）

**API接口**：
- `GET /api/tools?category={category}&page=1&page_size=20&search={keyword}`
- `GET /api/tools/{tool_id}` - 获取工具详情（包含相关文章）

### 3. 工具详情
**功能描述**：展示工具的完整信息和相关文章

**功能特性**：
- ✅ 工具完整信息（名称、URL、描述、分类、标签、图标）
- ✅ 相关文章列表（通过工具标签关联）
- ✅ 访问统计
- ✅ 跳转到工具官网

**关联机制**：
- 文章归档时可添加工具标签（`tool_tags`）
- 点击工具时，系统会查找包含该工具名称的文章
- 支持通过 `tool_tags` 或 `tags` 字段匹配

### 4. 提交工具 (`/submit-tool`)
**功能描述**：允许用户提交新的开发工具

**提交流程**：
1. 用户填写表单：
   - 工具名称（必填）
   - 工具URL（必填）
   - 工具描述（必填）
   - 工具分类（必填，下拉选择）
   - 工具标签（可选，逗号分隔）
   - 工具图标（可选，URL或emoji）
2. 系统处理：
   - 检查URL是否重复（候选池和正式工具池）
   - 保存到工具候选池（`data/tools/tool_candidates.json`）
   - 等待管理员审核
3. 用户提示：
   - 显示"提交成功"消息
   - 说明工具将人工审核

**功能特性**：
- ✅ 表单验证
- ✅ URL重复检测
- ✅ 分类选择器
- ✅ 友好的用户提示

**API接口**：
- `POST /api/tools/submit` - 提交工具

---

## 🔐 管理员功能

### 1. 管理员入口
**访问方式**：
- 默认隐藏，需要"盲敲"授权码才能显示
- 授权码配置在环境变量 `AICODING_ADMIN_CODE` 中
- 授权码验证区分大小写
- 验证成功后，管理员入口显示在右上角
- 验证状态保存在 `localStorage`，刷新后保持显示

**功能特性**：
- ✅ 隐藏式入口（盲敲授权码）
- ✅ 授权码验证（区分大小写）
- ✅ 状态持久化（localStorage）
- ✅ 右上角显示，不影响其他元素布局

**API接口**：
- `GET /api/admin/verify-code?code={admin_code}` - 验证授权码

### 2. 文章候选池管理 (`/digest/panel`)
**功能描述**：管理用户提交和系统获取的文章候选

**操作功能**：

#### 采纳（Accept）
- **功能**：将候选文章添加到正式文章池
- **说明**：文章会被添加到对应分类的JSON文件中，并立即在前端显示
- **操作**：点击"采纳"按钮，文章从候选池移除并添加到正式池

#### 忽略（Ignore）
- **功能**：删除候选文章，不再显示
- **说明**：文章会被永久删除，无法恢复
- **操作**：点击"忽略"按钮，文章从候选池删除

#### 归档（Archive）
- **功能**：将候选文章归档到指定分类，但保留在候选池中
- **说明**：
  - 文章会被添加到指定分类的JSON文件中，并立即在前端显示
  - **文章仍然保留在候选池中**，可以继续被采纳
  - 归档时可以添加工具标签（可选），用于关联工具和文章
  - 已归档的文章会显示"已归档"标签，归档按钮会被禁用
- **操作**：
  1. 点击"归档"按钮
  2. 选择资讯分类（编程资讯/AI资讯）
  3. 输入工具标签（可选，多个标签用逗号分隔）
  4. 点击确认，文章被归档并保留在候选池

**功能特性**：
- ✅ 按关键词分组显示候选文章
- ✅ 显示文章基本信息（标题、URL、来源、摘要、关键词）
- ✅ 显示归档状态（已归档标签）
- ✅ 批量操作支持
- ✅ 归档时间记录（`archived_at`）
- ✅ 工具标签关联

**API接口**：
- `GET /digest/candidates` - 获取候选文章列表
- `POST /digest/accept-candidate` - 采纳文章
- `POST /digest/reject-candidate` - 忽略文章
- `POST /digest/archive-candidate` - 归档文章（包含工具标签）

### 3. 工具候选池管理
**功能描述**：管理用户提交的工具候选

**操作功能**：

#### 采纳工具（Accept）
- **功能**：将候选工具添加到指定分类的正式工具池
- **说明**：工具会被添加到对应分类的JSON文件中，并立即在前端显示
- **操作**：
  1. 点击"采纳"按钮
  2. 选择工具分类（开发IDE、IDE插件等）
  3. 工具被保存到对应分类并显示

#### 忽略工具（Ignore）
- **功能**：删除候选工具，不再显示
- **说明**：工具会被永久删除，无法恢复
- **操作**：点击"忽略"按钮，工具从候选池删除

**功能特性**：
- ✅ 显示工具基本信息（名称、URL、描述、分类、标签、图标）
- ✅ 分类选择器
- ✅ 批量操作支持

**API接口**：
- `GET /digest/tool-candidates` - 获取工具候选列表
- `POST /digest/accept-tool-candidate` - 采纳工具
- `POST /digest/reject-tool-candidate` - 忽略工具

### 4. 工具相关资讯获取
**功能描述**：为每个工具手动触发相关资讯的获取，获取到的资讯会自动关联到对应工具

**核心特性**：
- **工具关键字自动管理**：工具被采纳时，自动将工具名称添加到关键字配置
- **手动触发获取**：支持单个工具或批量获取所有工具的相关资讯
- **当天内容**：只获取当天的资讯内容，确保内容时效性
- **自动标签关联**：获取到的资讯自动带有工具名称标签，归档或采纳时自动提取

**操作功能**：

#### 单个工具获取
- **功能**：选择特定工具关键字，每次获取1篇当天的相关资讯
- **操作**：
  1. 在"工具相关资讯获取"区域选择工具关键字
  2. 点击"获取该工具资讯"按钮
  3. 系统获取1篇当天的相关资讯并进入候选池

#### 批量获取
- **功能**：一次性获取所有工具的相关资讯
- **操作**：点击"获取所有工具资讯"按钮，系统遍历所有工具关键字，每个关键字获取1篇资讯

**功能特性**：
- ✅ 工具关键字自动管理（采纳工具时自动添加）
- ✅ 工具关键字列表显示（显示当前关键字数量）
- ✅ 单个工具获取（每次1篇）
- ✅ 批量获取（所有工具）
- ✅ 自动标签提取（归档/采纳时自动提取工具名称）
- ✅ 工具标签自动填充（归档对话框自动填充）

**数据流程**：
1. 工具采纳 → 自动添加工具名称到关键字配置
2. 手动触发获取 → 使用工具关键字获取相关资讯
3. 资讯进入候选池 → 带有 `tool_keyword:工具名称` 标识
4. 归档/采纳 → 自动提取工具名称作为 `tool_tags`
5. 工具详情页 → 通过 `tool_tags` 匹配显示相关资讯

**API接口**：
- `GET /digest/tool-keywords` - 获取工具关键字列表
- `POST /digest/crawl-tool-articles` - 获取工具相关资讯
  - Body: `{"keyword": "Cursor"}` - 可选，不提供则爬取所有工具

**配置文件**：
- `config/tool_keywords.json` - 工具关键字列表（自动管理）

### 5. 自动推送功能
**功能描述**：系统定时自动推送资讯到企业微信群

**推送流程**：
1. **检查文章池**：首先从文章池（`ai_articles.json`）中选取文章
2. **提升候选池**：如果文章池为空，从候选池（`ai_candidates.json`）中按关键字随机提升文章
3. **自动抓取**：如果文章池和候选池都为空，按关键字自动抓取文章
   - 从 `config/crawler_keywords.json` 读取关键词
   - 对每个关键词抓取文章（每关键词抓取1页）
   - 每个关键词随机选择1篇文章
   - 直接保存到文章列表（不经过候选池）
4. **执行推送**：将选中的文章推送到企业微信群
5. **清理数据**：推送完成后，清空文章池和候选池

**功能特性**：
- ✅ 定时自动推送（可配置Cron表达式或小时+分钟）
- ✅ 智能文章获取（文章池 → 候选池 → 自动抓取）
- ✅ 自动抓取机制（文章池和候选池都为空时触发）
- ✅ 按关键字随机选择（确保内容多样性）
- ✅ 推送后自动清理（避免重复推送）
- ✅ 详细的日志记录（便于排查问题）

**配置说明**：
- **推送时间**：在 `config/digest_schedule.json` 中配置
- **推送数量**：在 `config/digest_schedule.json` 中配置 `count` 字段
- **抓取关键词**：在 `config/crawler_keywords.json` 中配置

**日志标识**：
- `[定时推送]` - 定时推送任务相关日志
- `[自动抓取]` - 自动抓取文章相关日志
- `[调度器]` - 调度器启动和配置相关日志

### 6. 配置管理
**功能描述**：在管理面板中配置系统参数

**配置项**：
- **关键词配置**：设置数据获取关键词，每行一个
- **调度配置**：设置推送时间（Cron表达式或小时+分钟）和数量控制
- **企业微信模板**：自定义推送消息的Markdown格式
- **系统配置**：配置管理员验证码和企业微信推送地址

---

## 📊 数据模型

### 文章数据模型
```json
{
  "id": "article_1234567890",
  "title": "文章标题",
  "url": "https://example.com/article",
  "summary": "文章摘要",
  "source": "来源名称",
  "published_time": "2024-01-01T00:00:00Z",
  "archived_at": "2024-01-01T12:00:00Z",
  "category": "programming",
  "tags": ["tag1", "tag2"],
  "tool_tags": ["ToolName1", "ToolName2"],
  "view_count": 10,
  "score": 0.0,
  "keyword": "关键词"
}
```

### 工具数据模型
```json
{
  "id": 1,
  "name": "工具名称",
  "url": "https://example.com/tool",
  "description": "工具描述",
  "category": "ide",
  "tags": ["开源", "免费", "SaaS"],
  "icon": "🔧",
  "view_count": 100,
  "created_at": "2024-01-01T00:00:00Z",
  "is_featured": true
}
```

### 候选文章模型
```json
{
  "title": "文章标题",
  "url": "https://example.com/article",
  "summary": "文章摘要",
  "source": "来源名称",
  "category": "programming",
  "keyword": "关键词",
  "submitted_at": "2024-01-01T00:00:00Z"
}
```

### 候选工具模型
```json
{
  "name": "工具名称",
  "url": "https://example.com/tool",
  "description": "工具描述",
  "category": "ide",
  "tags": ["开源", "免费"],
  "icon": "🔧",
  "submitted_at": "2024-01-01T00:00:00Z"
}
```

---

## 🔌 API接口文档

### 资讯相关API

#### 获取编程资讯
```
GET /api/news?category=programming&page=1&page_size=20&sort_by=archived_at
```
**响应**：
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

#### 获取AI资讯
```
GET /api/ai-news?page=1&page_size=20&sort_by=archived_at
```

#### 获取热门资讯
```
GET /api/news?sort_by=score&page=1&page_size=20
```

#### 获取最新资讯
```
GET /api/recent?page=1&page_size=20&search={keyword}
```

#### 记录文章点击
```
POST /api/articles/click?url={encoded_url}
```

#### 提交文章
```
POST /api/articles/submit
Content-Type: application/json

{
  "title": "文章标题",
  "url": "https://example.com/article",
  "category": "programming",
  "summary": "推荐理由"
}
```

### 工具相关API

#### 获取工具列表
```
GET /api/tools?category={category}&featured={true|false}&page=1&page_size=20&search={keyword}&sort_by=view_count
```

#### 获取热门工具
```
GET /api/tools/featured?page=1&page_size=20&sort_by=view_count
```

#### 获取工具详情
```
GET /api/tools/{tool_id}
```
**响应**：
```json
{
  "id": 1,
  "name": "工具名称",
  "url": "https://example.com/tool",
  "description": "工具描述",
  "category": "ide",
  "tags": ["开源", "免费"],
  "icon": "🔧",
  "view_count": 100,
  "related_articles": [...]
}
```

#### 记录工具点击
```
POST /api/tools/{tool_id}/click
```

#### 提交工具
```
POST /api/tools/submit
Content-Type: application/json

{
  "name": "工具名称",
  "url": "https://example.com/tool",
  "description": "工具描述",
  "category": "ide",
  "tags": ["开源", "免费"],
  "icon": "🔧"
}
```

### 配置API

#### 获取配置
```
GET /api/config
```
**响应**：返回 `data/config.json` 的内容

### 管理员API

#### 验证授权码
```
GET /api/admin/verify-code?code={admin_code}
```
**响应**：
```json
{
  "ok": true,
  "valid": true
}
```

#### 获取候选文章列表
```
GET /digest/candidates
```

#### 采纳文章
```
POST /digest/accept-candidate
Content-Type: application/json

{
  "url": "https://example.com/article"
}
```

#### 忽略文章
```
POST /digest/reject-candidate
Content-Type: application/json

{
  "url": "https://example.com/article"
}
```

#### 归档文章
```
POST /digest/archive-candidate
Content-Type: application/json

{
  "url": "https://example.com/article",
  "category": "programming",
  "tool_tags": ["ToolName1", "ToolName2"]
}
```

#### 获取工具候选列表
```
GET /digest/tool-candidates
```

#### 采纳工具
```
POST /digest/accept-tool-candidate
Content-Type: application/json

{
  "url": "https://example.com/tool",
  "category": "ide"
}
```

#### 忽略工具
```
POST /digest/reject-tool-candidate
Content-Type: application/json

{
  "url": "https://example.com/tool"
}
```

---

## 📁 数据存储结构

### 目录结构
```
data/
├── config.json              # 页面和分类配置
├── articles/                 # 文章相关
│   ├── ai_candidates.json   # 文章候选池
│   ├── ai_articles.json     # 资讯推送列表
│   ├── programming.json     # 编程资讯
│   └── ai_news.json          # AI资讯
└── tools/                    # 正式工具池
    ├── tool_candidates.json # 工具候选池
    ├── featured.json        # 热门工具
    ├── ide.json             # 开发IDE
    ├── plugin.json          # IDE插件
    ├── cli.json             # 命令行工具
    ├── codeagent.json       # CodeAgent
    ├── ai-test.json         # AI测试
    ├── review.json          # 代码审查
    ├── devops.json          # DevOps工具
    ├── doc.json             # 文档相关
    ├── design.json          # 设计工具
    ├── ui.json              # UI生成
    └── mcp.json             # MCP工具
```

### 配置文件

#### `data/config.json`
包含页面标题、描述和分类元数据：
```json
{
  "pages": {
    "tools": {
      "id": "page-tools",
      "title": "热门工具",
      "description": "发现最优秀的开发工具和资源"
    },
    ...
  },
  "categories": {
    "tools": {...},
    "articles": {...}
  }
}
```

#### `config/crawler_keywords.json`
包含关键词列表，用于随机分配给用户提交的文章进行分类标记。

---

## 🎯 核心功能特性

### 1. 分页加载
- **目的**：防止数据量过大导致页面卡顿
- **实现**：服务器端分页，每页默认20条
- **支持**：所有列表页面（资讯、工具）

### 2. 搜索功能
- **支持范围**：最新资讯页面
- **搜索字段**：标题、摘要、来源
- **实时搜索**：输入关键词即时过滤

### 3. 排序功能
- **文章排序**：
  - 按归档时间（`archived_at`）- 默认
  - 按热度（`score`/`view_count`）- 热门资讯
- **工具排序**：
  - 按访问量（`view_count`）- 热门工具
  - 按创建时间（`created_at`）- 次要排序

### 4. 点击统计
- **文章点击**：每次点击文章链接，`view_count` +1
- **工具点击**：每次点击工具链接，`view_count` +1
- **实时更新**：点击后自动刷新列表（热门资讯/热门工具）

### 5. 文章-工具关联
- **归档时关联**：归档文章时可添加工具标签
- **自动匹配**：点击工具时，自动查找相关文章
- **匹配规则**：通过 `tool_tags` 或 `tags` 字段匹配工具名称

### 6. 动态配置
- **页面标题/描述**：从 `data/config.json` 动态加载
- **分类信息**：从配置文件读取分类名称和描述
- **易于扩展**：新增页面或分类只需修改配置文件

### 7. 响应式设计
- **移动端适配**：使用 Tailwind CSS 响应式类
- **灵活布局**：自适应不同屏幕尺寸

### 8. 全局浮动按钮
- **反馈/联系按钮**：右下角固定，点击跳转到提交资讯页面
- **回到顶部按钮**：滚动超过300px时显示，点击平滑滚动到顶部
- **平滑动画**：使用CSS过渡和JavaScript平滑滚动

### 9. 归档状态检查
- **URL规范化**：改进微信文章URL规范化逻辑，避免动态参数导致的误判
- **精确匹配**：对于只有动态参数的URL，使用精确匹配而非规范化匹配
- **状态显示**：正确显示关键词摘取和工具关键词摘取的资讯归档状态

---

## 🔧 技术架构

### 后端技术栈
- **框架**：FastAPI
- **数据存储**：JSON文件（`data/` 目录）
- **数据加载**：`app/services/data_loader.py` - 统一的数据加载和保存服务
- **路由**：
  - `app/routes/api.py` - 公开API接口
  - `app/routes/digest.py` - 管理员面板和API
- **日志**：loguru

### 前端技术栈
- **框架**：原生JavaScript（SPA架构）
- **样式**：Tailwind CSS + 自定义CSS
- **路由**：History API（标准URL路由，无 `#`）
- **字体**：Google Fonts（Orbitron、Rajdhani）

### 数据服务
- **DataLoader**：统一的数据加载服务
  - 支持分页、筛选、搜索、排序
  - 支持文章归档、工具归档
  - 支持点击统计
  - 支持文章-工具关联查询

---

## 🚀 部署说明

### 环境要求
- Python 3.10+
- 依赖包：见 `requirements.txt`

### 配置环境变量
创建 `.env` 文件：
```bash
AICODING_ADMIN_CODE=your-admin-code-here
WECOM_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

### 启动服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 访问地址
- 首页：`http://localhost:8000/`
- 管理面板：`http://localhost:8000/digest/panel`
- API文档：`http://localhost:8000/docs`

---

## 📝 使用流程

### 用户提交文章流程
1. 用户访问 `/submit` 页面
2. 填写文章信息（标题、URL、分类、推荐理由）
3. 提交后，文章进入候选池
4. 管理员在管理面板审核
5. 管理员可以选择：
   - **采纳**：文章立即显示在前端
   - **归档**：文章显示在前端，但保留在候选池
   - **忽略**：删除文章

### 用户提交工具流程
1. 用户访问 `/submit-tool` 页面
2. 填写工具信息（名称、URL、描述、分类、标签、图标）
3. 提交后，工具进入工具候选池
4. 管理员在管理面板审核
5. 管理员可以选择：
   - **采纳**：选择分类，工具立即显示在前端
   - **忽略**：删除工具

### 管理员审核流程
1. 访问管理面板（需要授权码）
2. 查看文章候选池或工具候选池
3. 对每个候选项进行操作：
   - **文章**：采纳、归档（可添加工具标签）、忽略
   - **工具**：采纳（选择分类）、忽略
4. 已归档的文章会显示"已归档"标签，无法再次归档

---

## 🎯 未来扩展方向

### 计划中的功能
- [ ] 用户系统（注册、登录、个人收藏）
- [ ] 评论系统（工具评价、文章评论）
- [ ] 推荐算法（基于用户行为的个性化推荐）
- [ ] RSS订阅功能
- [ ] 公开API（供第三方使用）
- [ ] 数据统计面板（访问量、提交量、采纳率等）
- [ ] 批量操作（批量采纳/忽略）
- [ ] 文章批注功能

### 技术优化
- [ ] 数据库迁移（从JSON到SQLite/PostgreSQL）
- [ ] 缓存机制（Redis）
- [ ] 图片CDN
- [ ] 搜索优化（全文搜索）
- [ ] 性能优化（虚拟滚动、懒加载）

---

## 📚 相关文档

**功能文档**:
- [功能开发计划](feature_plan.md)
- [多资讯源使用指南](multi_sources_guide.md)
- [测试指南](test_sources.md)
- [工具详情功能](tool_detail_feature.md)
- [工具相关资讯爬取功能](tool_article_crawling_feature.md)

**部署文档**:
- [Python环境部署](../deploy/deploy_python.md)
- [Windows部署](../deploy/deploy_windows.md)
- [宝塔部署](../deploy/deploy_baota.md)
- [微信公众号发布指南](../deploy/wechat_mp_guide.md)

---

## 📄 更新日志

### v3.2（当前版本）
- ✅ 修复归档状态检查问题
  - 改进微信文章URL规范化逻辑，避免动态参数导致的误判
  - 对于只有动态参数的URL，使用精确匹配而非规范化匹配
  - 修复关键词摘取和工具关键词摘取的资讯误判为已归档的问题
- ✅ 修复热门工具显示问题
  - 修复热门工具只显示29个工具的问题（实际有113个工具）
  - 热门工具模式不去重，显示所有工具并按访问量排序
  - 其他模式使用URL去重（比ID更可靠）
- ✅ 改进微信公众号页面
  - 添加GitHub仓库宣传卡片
  - 修复文字对齐问题，GitHub链接和描述文字居中显示
  - 优化页面布局和视觉效果
- ✅ 实现全局浮动按钮功能
  - 反馈/联系按钮：点击跳转到提交资讯页面
  - 回到顶部按钮：滚动超过300px时显示，点击平滑滚动到顶部

### v3.1
- ✅ 自动推送功能增强
  - 文章池和候选池都为空时，自动按关键字抓取文章
  - 每个关键字随机选择1篇文章，直接放入文章列表
  - 推送完成后自动清理文章池和候选池
  - 完善的错误处理和日志记录
- ✅ 推送函数改进
  - 推送函数返回成功/失败状态
  - 详细的日志记录（`[定时推送]`、`[自动抓取]`、`[调度器]`）
  - 统一手动推送和定时推送的逻辑

### v3.0
- ✅ 工具相关资讯获取功能
  - 工具关键字自动管理
  - 手动触发单个或批量获取
  - 自动标签关联
  - 工具详情页展示相关资讯
- ✅ 工具数据录入和整理
  - 完善工具分类体系
  - 工具标识符（identifier）支持
  - 工具详情页功能

### v2.0
- ✅ 完整的资讯和工具聚合平台
- ✅ 用户提交功能
- ✅ 管理员审核功能
- ✅ 点击统计和热度排序
- ✅ 文章-工具关联
- ✅ 现代化UI设计
- ✅ 标准URL路由（无 `#`）

### v1.0
- ✅ 基础的文章抓取和管理系统
- ✅ 多资讯源支持
- ✅ 微信公众号发布

---

**文档最后更新**：2024年11月

