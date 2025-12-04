# Clean 架构重构说明

## 架构层次

本项目采用 Clean 架构（清洁架构）进行重构，将代码分为以下几个层次：

### 1. Domain Layer (领域层)
**位置**: `app/domain/`

包含业务领域模型和核心业务逻辑：
- `digest/`: 摘要领域模型和渲染
  - `models.py`: 摘要数据模型
  - `render.py`: 摘要渲染逻辑
- `sources/`: 数据源管理
  - `ai_articles.py`: AI文章池管理
  - `ai_candidates.py`: AI文章候选池
  - `tool_candidates.py`: 工具候选池
  - `article_crawler.py`: 文章爬虫
  - `article_sources.py`: 文章源管理

### 2. Infrastructure Layer (基础设施层)
**位置**: `app/infrastructure/`

负责底层技术实现和基础设施：
- `logging.py`: 日志配置
- `file_lock.py`: 跨进程文件锁
- `scheduler.py`: 调度器管理
- `crawlers/`: 外部数据爬虫
  - `sogou_wechat.py`: 搜狗微信搜索
  - `rss.py`: RSS源
  - `github_trending.py`: GitHub趋势
  - `hackernews.py`: HackerNews
  - `devmaster.py`: DevMaster API
- `notifiers/`: 通知服务
  - `wecom.py`: 企业微信通知
  - `wechat_mp.py`: 微信公众号通知
- `db/`: 数据库访问（如需要）

### 3. Service Layer (服务层)
**位置**: `app/services/`

包含业务逻辑服务：
- `digest_service.py`: 推送服务
- `backup_service.py`: 数据备份服务
- `crawler_service.py`: 文章抓取服务
- `data_loader.py`: 数据加载服务
- `weekly_digest.py`: 周报服务

### 4. Presentation Layer (表示层)
**位置**: `app/presentation/`

负责用户界面和展示：
- `templates.py`: HTML模板
- `routes/`: API路由
  - `api.py`: 工具和资讯API
  - `digest.py`: 摘要管理路由
  - `wechat.py`: 微信路由
  - `ai_assistant.py`: AI助手路由
- `static/`: 静态资源文件

### 5. Application Layer (应用层)
**位置**: `app/main.py`

应用入口，负责：
- 应用组装
- 路由注册
- 生命周期管理

## 依赖关系

```
main.py (应用层)
  ├── domain (领域层)
  ├── infrastructure (基础设施层)
  ├── services (服务层)
  │     ├── domain (服务层依赖领域层)
  │     └── infrastructure (服务层依赖基础设施层)
  └── presentation (表示层)
        ├── domain (表示层依赖领域层)
        ├── services (表示层依赖服务层)
        └── infrastructure (表示层依赖基础设施层)
```
