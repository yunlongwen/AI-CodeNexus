# 多资讯源功能测试指南

## 方法一：使用测试脚本（推荐）

### 1. 安装依赖

确保已安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 运行测试脚本

```bash
python scripts/test_sources.py
```

测试脚本会依次测试：
- RSS Feed 抓取
- GitHub Trending 抓取
- Hacker News 抓取
- 统一资讯源管理器

### 3. 查看结果

脚本会输出每个资讯源的测试结果，包括：
- 抓取到的文章数量
- 文章标题、来源、链接等信息
- 热度分排序结果

## 方法二：使用 API 接口测试

### 1. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 访问 API 文档

打开浏览器访问：`http://localhost:8000/docs`

### 3. 测试各个资讯源

#### 测试 RSS Feed

```bash
curl -X POST "http://localhost:8000/digest/test/rss" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{"feed_url": "https://rss.cnn.com/rss/edition.rss"}'
```

#### 测试 GitHub Trending

```bash
curl -X POST "http://localhost:8000/digest/test/github-trending" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{"language": "python"}'
```

#### 测试 Hacker News

```bash
curl -X POST "http://localhost:8000/digest/test/hackernews" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{"min_points": 50}'
```

#### 测试所有资讯源

```bash
curl -X POST "http://localhost:8000/digest/test/all-sources" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["AI"],
    "rss_feeds": ["https://rss.cnn.com/rss/edition.rss"],
    "github_languages": ["python"],
    "hackernews_min_points": 50,
    "max_per_source": 3
  }'
```

## 方法三：使用 Python 代码测试

### 测试单个资讯源

```python
import asyncio
from app.crawlers.rss import fetch_rss_articles
from app.crawlers.github_trending import fetch_github_trending
from app.crawlers.hackernews import fetch_hackernews_articles

async def test():
    # 测试 RSS
    articles = await fetch_rss_articles("https://rss.cnn.com/rss/edition.rss", max_items=5)
    print(f"RSS: {len(articles)} 篇文章")
    
    # 测试 GitHub Trending
    articles = await fetch_github_trending("python", max_items=5)
    print(f"GitHub: {len(articles)} 个项目")
    
    # 测试 Hacker News
    articles = await fetch_hackernews_articles(min_points=50, max_items=5)
    print(f"Hacker News: {len(articles)} 篇文章")

asyncio.run(test())
```

### 测试统一资讯源管理器

```python
import asyncio
from app.sources.article_sources import fetch_from_all_sources

async def test():
    articles = await fetch_from_all_sources(
        keywords=["AI"],
        rss_feeds=["https://rss.cnn.com/rss/edition.rss"],
        github_languages=["python"],
        hackernews_min_points=50,
        max_per_source=3,
    )
    
    print(f"总共抓取到 {len(articles)} 篇文章")
    for article in articles[:10]:
        print(f"[{article.get('score', 0):.1f}分] {article.get('title')}")

asyncio.run(test())
```

## 测试数据示例

### RSS Feed URL 示例

- CNN: `https://rss.cnn.com/rss/edition.rss`
- BBC News: `https://feeds.bbci.co.uk/news/rss.xml`
- TechCrunch: `https://techcrunch.com/feed/`
- Hacker News RSS: `https://hnrss.org/frontpage`

### GitHub Trending 语言示例

- `python`
- `javascript`
- `go`
- `rust`
- `java`

### Hacker News 分数阈值

- 低分：`50` points
- 中分：`100` points
- 高分：`200` points

## 常见问题

### 1. RSS Feed 抓取失败

- 检查 Feed URL 是否可访问
- 确认网络连接正常
- 某些 Feed 可能需要特定的 User-Agent

### 2. GitHub Trending 抓取失败

- GitHub 可能会限制频繁请求
- 尝试降低请求频率
- 检查网络连接

### 3. Hacker News 抓取失败

- Hacker News API 是公开的，通常很稳定
- 如果失败，检查网络连接
- 可以降低 `min_points` 阈值获取更多文章

### 4. 热度分计算

热度分综合考虑：
- 来源权重（Hacker News > GitHub > RSS > 其他）
- 时效性（今天发布的文章加分）
- 标题长度（适中长度加分）
- 是否有摘要

## 集成到现有系统

要将多资讯源集成到现有的抓取流程中，可以修改 `app/main.py` 中的抓取逻辑，使用 `fetch_from_all_sources` 函数替代原来的单一来源抓取。

