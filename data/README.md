# 数据目录说明

本目录用于存储工具和资讯的元数据（不存储实际内容，只存储链接和元信息）。

## 目录结构

```
data/
├── tools/          # 工具数据
│   ├── featured.json    # 热门工具
│   ├── cli.json         # 命令行工具
│   ├── ide.json         # 开发IDE
│   └── ...              # 其他分类
└── articles/       # 资讯数据
    ├── programming.json  # 编程资讯
    ├── ai_news.json     # AI资讯
    └── ...              # 其他分类
```

## 数据格式

### 工具数据格式 (tools/*.json)

```json
{
  "id": 1,
  "name": "工具名称",
  "url": "https://tool-url.com",
  "description": "工具描述",
  "category": "cli",
  "tags": ["SaaS", "AI", "终端"],
  "icon": "</>",
  "score": 9.5,
  "view_count": 1250,
  "like_count": 89,
  "is_featured": true,
  "created_at": "2025-01-08T10:00:00Z"
}
```

**字段说明：**
- `id`: 唯一标识符
- `name`: 工具名称
- `url`: 工具官网链接
- `description`: 工具描述
- `category`: 工具分类（cli, ide, ai-test, devops, plugin, review, doc, design, ui, codeagent, mcp, other）
- `tags`: 标签列表
- `icon`: 图标（emoji或字符）
- `score`: 热度分/推荐指数（0-10）
- `view_count`: 访问次数
- `like_count`: 点赞数
- `is_featured`: 是否热门推荐
- `created_at`: 创建时间（ISO 8601格式）

### 资讯数据格式 (articles/*.json)

```json
{
  "id": 1,
  "title": "文章标题",
  "url": "https://article-url.com",
  "source": "来源名称",
  "summary": "文章摘要",
  "category": "programming",
  "archived_at": "2025-01-08T10:00:00Z",
  "created_at": "2025-01-08T10:00:00Z",
  "published_time": "2025-01-08T10:00:00Z",
  "tool_tags": ["工具名称1", "工具名称2"],
  "tags": ["标签1", "标签2"],
  "view_count": 0,
  "score": 8.5
}
```

**字段说明：**
- `id`: 唯一标识符（必需，归档时自动生成）
- `title`: 文章标题（必需）
- `url`: 文章链接（必需，唯一）
- `source`: 来源（可选，公众号名/网站名，为空时显示"未知来源"）
- `summary`: 文章摘要（可选）
- `category`: 文章分类（必需，programming, ai_news等）
- `archived_at`: 采纳/归档时间（必需，ISO 8601格式，归档时自动设置）
- `created_at`: 创建时间（必需，ISO 8601格式，归档时自动设置）
- `published_time`: 原始发布时间（可选，ISO 8601格式）
- `tool_tags`: 工具标签列表（可选，用于工具详情页关联）
- `tags`: 普通标签列表（可选）
- `view_count`: 点击次数（可选，默认0，用于热度计算）
- `score`: 热度分（可选，0-10）

**重要说明：**
- `archived_at` 是必需字段，表示文章被采纳的时间，归档函数会自动设置
- UI显示日期时优先使用 `archived_at`（采纳日期）
- 如果现有数据缺少日期字段，系统会在加载时自动补充（使用文件修改时间）

## 注意事项

1. **不存储实际内容**：本平台只存储链接和元信息，不存储文章或工具的完整内容
2. **数据去重**：系统会自动根据 `id` 字段去重
3. **分页加载**：所有API都支持分页，默认每页20条，最大100条
4. **文件命名**：建议使用分类名称作为文件名（如 `cli.json`, `programming.json`）
5. **数据更新**：可以通过管理面板或直接编辑JSON文件来更新数据

## API使用

### 获取工具列表
```
GET /api/tools?category=cli&page=1&page_size=20
```

### 获取热门工具
```
GET /api/tools/featured?page=1&page_size=20
```

### 获取编程资讯
```
GET /api/news?category=programming&page=1&page_size=20
```

### 获取AI资讯
```
GET /api/ai-news?page=1&page_size=20
```

### 获取最近收录
```
GET /api/recent?type_filter=all&page=1&page_size=20
```

