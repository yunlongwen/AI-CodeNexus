# AICoding基地 功能开发计划

## 📋 项目概述

基于现有的文章抓取和管理系统，扩展为"编程资讯与工具聚合平台"，提供资讯浏览、工具发现、内容管理等功能。

---

## 🎯 核心功能模块

### 1. 编程资讯模块 (`#news`)

**功能描述：** 展示编程相关的技术文章和资讯

**后端需求：**
- [ ] 创建 API 端点：`GET /api/news`
  - 支持分页（page, page_size）
  - 支持分类筛选（category: programming, web, mobile, etc.）
  - 支持排序（按时间、热度分）
  - 返回文章列表（标题、链接、来源、摘要、发布时间、标签）

**前端需求：**
- [ ] 实现资讯列表页面
  - 文章卡片展示（标题、摘要、来源、时间、标签）
  - 分页或无限滚动
  - 分类筛选器
  - 搜索功能
- [ ] 文章详情页（可选）
  - 显示完整文章内容或跳转到原文

**数据来源：**
- 复用现有的 `Article` 和 `Candidate` 表
- 根据 `category` 字段筛选编程相关文章

---

### 2. AI资讯模块 (`#ai-news`)

**功能描述：** 展示AI相关的文章和资讯

**后端需求：**
- [ ] 创建 API 端点：`GET /api/ai-news`
  - 与编程资讯类似，但筛选 `category = 'ai_news'` 的文章
  - 支持AI相关标签筛选（如：LLM, GPT, AI工具等）

**前端需求：**
- [ ] 实现AI资讯列表页面
  - 与编程资讯页面类似，但针对AI内容优化
  - AI标签高亮显示

**数据来源：**
- 复用现有的 `Article` 表，筛选 `category = 'ai_news'`

---

### 3. 工具管理模块（核心新功能）

#### 3.1 工具数据模型

**数据库设计：**
```python
class Tool(Base):
    """工具表"""
    __tablename__ = "tools"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)  # 工具名称
    url = Column(String(1000), nullable=False)  # 工具官网
    description = Column(Text)  # 工具描述
    category = Column(String(100), index=True)  # 工具分类
    tags = Column(JSON)  # 标签列表，如 ["SaaS", "开源", "免费"]
    icon = Column(String(500))  # 图标URL或emoji
    score = Column(Float, default=0.0, index=True)  # 热度分/推荐指数
    view_count = Column(Integer, default=0)  # 访问次数
    like_count = Column(Integer, default=0)  # 点赞数
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_featured = Column(Boolean, default=False)  # 是否热门推荐
    notes = Column(Text)  # 备注/评价
```

**工具分类枚举：**
- `start` - 入门工具
- `ide` - 开发IDE
- `cli` - 命令行工具
- `ai-test` - AI测试
- `devops` - DevOps工具
- `plugin` - IDE插件
- `review` - 代码审查
- `doc` - 文档相关
- `design` - 设计工具
- `ui` - UI生成
- `codeagent` - CodeAgent
- `mcp` - MCP工具
- `other` - 其他工具

#### 3.2 热门工具 (`#tools`)

**后端需求：**
- [ ] 创建 API 端点：`GET /api/tools/featured`
  - 返回 `is_featured = True` 的工具
  - 按 `score` 和 `view_count` 排序
  - 支持分页

**前端需求：**
- [ ] 实现热门工具页面（当前已有雏形）
  - 工具卡片网格布局
  - 工具图标、名称、分类、描述
  - "访问工具"按钮
  - 工具详情弹窗或页面
  - 筛选标签（SaaS、开源、免费等）

#### 3.3 全部工具 (`#all-tools`)

**后端需求：**
- [ ] 创建 API 端点：`GET /api/tools`
  - 支持分类筛选（category）
  - 支持标签筛选（tags）
  - 支持搜索（name, description）
  - 支持排序（score, view_count, created_at）
  - 支持分页

**前端需求：**
- [ ] 实现全部工具页面
  - 工具列表/网格视图切换
  - 分类筛选器（复用左侧工具分类）
  - 标签筛选器
  - 搜索框
  - 排序选择器

#### 3.4 工具分类筛选

**后端需求：**
- [ ] 创建 API 端点：`GET /api/tools?category={category}`
  - 根据分类返回工具列表

**前端需求：**
- [ ] 左侧工具分类点击后筛选对应分类的工具
  - 更新URL（如 `#category-ide`）
  - 高亮当前选中的分类
  - 刷新工具列表

#### 3.5 工具详情

**后端需求：**
- [ ] 创建 API 端点：`GET /api/tools/{tool_id}`
  - 返回工具详细信息
  - 返回相关文章列表（通过工具名称或标签关联）

**前端需求：**
- [ ] 实现工具详情页/弹窗
  - 工具完整信息展示
  - 相关资讯列表（复用现有文章数据）
  - 访问统计（可选）

#### 3.6 工具管理（管理员功能）

**后端需求：**
- [ ] 创建工具管理API
  - `POST /api/admin/tools` - 添加工具
  - `PUT /api/admin/tools/{tool_id}` - 更新工具
  - `DELETE /api/admin/tools/{tool_id}` - 删除工具
  - `POST /api/admin/tools/{tool_id}/feature` - 设置/取消热门
  - 需要管理员权限验证

**前端需求：**
- [ ] 在管理面板中添加工具管理页面
  - 工具列表（表格形式）
  - 添加/编辑工具表单
  - 批量操作（设置热门、删除等）

---

### 4. 最近收录模块 (`#recent`)

**功能描述：** 展示最近收录的文章和工具

**后端需求：**
- [ ] 创建 API 端点：`GET /api/recent`
  - 返回最近添加的文章和工具
  - 支持类型筛选（articles, tools, all）
  - 按 `created_at` 倒序排列

**前端需求：**
- [ ] 实现最近收录页面
  - 时间线或列表展示
  - 区分文章和工具
  - 显示收录时间

---

### 5. 入群交流模块 (`#group`)

**功能描述：** 展示微信群二维码和入群信息

**后端需求：**
- [ ] 创建 API 端点：`GET /api/group`
  - 返回群信息（名称、描述、二维码图片URL）
  - 可配置多个群（技术群、AI群等）

**前端需求：**
- [ ] 实现入群交流页面
  - 显示群二维码图片（`/static/wechat_mp_qr.jpg`）
  - 群介绍文字
  - 多个群的切换（如果有）

---

### 6. 工具与文章关联

**功能描述：** 建立工具和文章之间的关联关系

**数据库设计：**
```python
class ToolArticleRelation(Base):
    """工具-文章关联表"""
    __tablename__ = "tool_article_relations"
    
    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey("tools.id"), index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), index=True)
    relation_type = Column(String(50))  # "mention", "review", "tutorial"
    created_at = Column(DateTime, default=func.now())
```

**后端需求：**
- [ ] 自动关联：文章抓取时，检测文章内容中是否提及工具名称，自动建立关联
- [ ] 手动关联：管理员可在管理面板中手动关联
- [ ] API：`GET /api/tools/{tool_id}/articles` - 获取工具相关文章

---

## 🗂️ 技术实现细节

### 后端架构

1. **新增路由模块：** `app/routes/tools.py`
   - 工具相关的所有API端点

2. **新增数据模型：** 在 `app/db/models.py` 中添加 `Tool` 和 `ToolArticleRelation`

3. **工具管理服务：** `app/services/tool_service.py`
   - 工具CRUD操作
   - 工具搜索和筛选逻辑
   - 工具与文章关联逻辑

4. **工具热度分计算：**
   - 基于访问量、点赞数、收录时间等
   - 类似文章的热度分算法

### 前端架构

1. **单页应用（SPA）改造：**
   - 使用 JavaScript 实现路由切换（Hash路由）
   - 动态加载内容，无需刷新页面
   - 统一的API调用函数

2. **组件化：**
   - 文章卡片组件
   - 工具卡片组件
   - 筛选器组件
   - 分页组件

3. **状态管理：**
   - 使用简单的状态管理（localStorage 或全局变量）
   - 或引入轻量级框架（如 Alpine.js）

---

## 📅 开发优先级

### Phase 1: 核心功能（P0）
1. ✅ 工具数据模型设计
2. ✅ 工具管理API（CRUD）
3. ✅ 热门工具页面功能实现
4. ✅ 工具分类筛选功能

### Phase 2: 内容展示（P1）
1. ✅ 编程资讯页面功能实现
2. ✅ AI资讯页面功能实现
3. ✅ 全部工具页面功能实现
4. ✅ 最近收录页面功能实现

### Phase 3: 关联与优化（P2）
1. ✅ 工具与文章关联功能
2. ✅ 工具详情页
3. ✅ 搜索功能
4. ✅ 入群交流页面

### Phase 4: 增强功能（P3）
1. ✅ 工具热度分算法优化
2. ✅ 访问统计
3. ✅ 用户交互（点赞、收藏等，可选）
4. ✅ 数据统计面板

---

## 🔧 开发任务清单

### 数据库迁移
- [ ] 创建 `tools` 表迁移脚本
- [ ] 创建 `tool_article_relations` 表迁移脚本
- [ ] 初始化工具分类数据

### 后端开发
- [ ] 实现 `Tool` 数据模型
- [ ] 实现 `ToolArticleRelation` 数据模型
- [ ] 创建 `app/routes/tools.py` 路由模块
- [ ] 实现工具CRUD API
- [ ] 实现工具搜索和筛选API
- [ ] 实现工具与文章关联API
- [ ] 实现工具热度分计算逻辑
- [ ] 在 `app/main.py` 中注册工具路由

### 前端开发
- [ ] 实现单页应用路由（Hash路由）
- [ ] 实现编程资讯页面
- [ ] 实现AI资讯页面
- [ ] 完善热门工具页面（当前已有雏形）
- [ ] 实现全部工具页面
- [ ] 实现工具分类筛选
- [ ] 实现最近收录页面
- [ ] 实现入群交流页面
- [ ] 实现工具详情弹窗/页面
- [ ] 实现搜索功能
- [ ] 实现分页组件
- [ ] 优化响应式布局

### 管理功能
- [ ] 在管理面板中添加工具管理页面
- [ ] 实现工具添加/编辑表单
- [ ] 实现工具批量操作
- [ ] 实现工具与文章手动关联功能

### 测试
- [ ] 工具API单元测试
- [ ] 工具搜索和筛选测试
- [ ] 前端功能测试

---

## 📝 数据初始化

### 初始工具数据

建议从以下来源获取初始工具数据：
1. 当前页面中已有的示例工具（Warp, Tailwind CSS, GitHub Copilot）
2. 从文章内容中提取提到的工具
3. 手动整理热门开发工具列表

### 工具分类映射

建立工具分类与文章标签的映射关系，便于自动关联。

---

## 🎨 UI/UX 优化建议

1. **加载状态：** 所有API调用显示加载动画
2. **错误处理：** 友好的错误提示
3. **空状态：** 无数据时的提示和引导
4. **响应式：** 移动端适配
5. **性能优化：** 图片懒加载、列表虚拟滚动（如果数据量大）

---

## 📚 相关文档

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Tailwind CSS 文档](https://tailwindcss.com/docs)

---

## 🔄 后续扩展方向

1. **用户系统：** 用户注册、登录、个人收藏
2. **评论系统：** 工具评价、文章评论
3. **推荐算法：** 基于用户行为的个性化推荐
4. **RSS订阅：** 支持RSS订阅功能
5. **API开放：** 提供公开API供第三方使用

