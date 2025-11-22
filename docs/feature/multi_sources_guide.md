# 多资讯源支持使用指南

## 什么是多资讯源支持？

多资讯源支持允许系统从**多个不同的资讯来源**自动抓取文章，而不仅仅局限于搜狗微信搜索。这样可以：

1. **扩大内容覆盖面**：从更多渠道获取资讯
2. **提高内容质量**：不同来源的文章质量不同，可以筛选优质内容
3. **减少单一依赖**：不依赖单一平台，提高系统稳定性
4. **智能排序**：根据热度分自动排序，优先展示高质量内容

## 支持的资讯源

### 1. 搜狗微信搜索（原有功能）
- **用途**：搜索微信公众号文章
- **配置**：在"关键词配置"中设置关键词
- **特点**：中文内容为主，适合国内资讯

### 2. RSS/Atom Feed
- **用途**：抓取 RSS 订阅源的文章
- **配置**：添加 RSS Feed URL
- **特点**：支持各种新闻网站、博客、技术网站
- **示例**：
  - CNN: `https://rss.cnn.com/rss/edition.rss`
  - BBC News: `https://feeds.bbci.co.uk/news/rss.xml`
  - TechCrunch: `https://techcrunch.com/feed/`

### 3. GitHub Trending
- **用途**：抓取 GitHub 热门项目
- **配置**：指定编程语言（如 python, javascript, go）
- **特点**：技术项目为主，适合开发者
- **示例语言**：python, javascript, go, rust, java

### 4. Hacker News
- **用途**：抓取 Hacker News 高分文章
- **配置**：设置最低分数阈值
- **特点**：高质量技术文章和新闻
- **推荐阈值**：50-200 points

## 如何使用

### 方法一：通过代码直接使用（推荐用于集成）

在代码中调用统一资讯源管理器：

```python
from app.sources.article_sources import fetch_from_all_sources

# 从所有配置的资讯源抓取文章
articles = await fetch_from_all_sources(
    keywords=["AI", "Python"],  # 搜狗微信搜索关键词
    rss_feeds=[
        "https://rss.cnn.com/rss/edition.rss",
        "https://techcrunch.com/feed/",
    ],
    github_languages=["python", "javascript"],
    hackernews_min_points=100,
    max_per_source=5,  # 每个源最多抓取5篇
)

# 文章已按热度分自动排序
for article in articles:
    print(f"[{article['score']:.1f}分] {article['title']}")
    print(f"  来源: {article['source']}")
    print(f"  链接: {article['url']}")
```

### 方法二：通过 API 接口使用

#### 1. 测试单个资讯源

```bash
# 测试 RSS Feed
curl -X POST "http://localhost:8000/digest/test/rss" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{"feed_url": "https://rss.cnn.com/rss/edition.rss"}'

# 测试 GitHub Trending
curl -X POST "http://localhost:8000/digest/test/github-trending" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{"language": "python"}'

# 测试 Hacker News
curl -X POST "http://localhost:8000/digest/test/hackernews" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{"min_points": 100}'
```

#### 2. 测试所有资讯源

```bash
curl -X POST "http://localhost:8000/digest/test/all-sources" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["AI", "Python"],
    "rss_feeds": [
      "https://rss.cnn.com/rss/edition.rss",
      "https://techcrunch.com/feed/"
    ],
    "github_languages": ["python", "javascript"],
    "hackernews_min_points": 100,
    "max_per_source": 5
  }'
```

### 方法三：集成到现有抓取流程

修改 `app/main.py` 或抓取任务，使用多资讯源：

```python
from app.sources.article_sources import fetch_from_all_sources
from app.config_loader import load_crawler_keywords

async def crawl_articles():
    # 获取配置的关键词
    keywords = load_crawler_keywords()
    
    # 从所有资讯源抓取
    articles = await fetch_from_all_sources(
        keywords=keywords,
        rss_feeds=[
            "https://rss.cnn.com/rss/edition.rss",
            # 添加更多 RSS Feed
        ],
        github_languages=["python"],
        hackernews_min_points=100,
        max_per_source=5,
    )
    
    # 将抓取的文章添加到候选池
    for article in articles:
        # 添加到候选池的逻辑
        add_to_candidate_pool(article)
```

## 热度分计算说明

系统会自动为每篇文章计算热度分，考虑因素：

1. **来源权重**：
   - Hacker News: 分数 × 0.1（高分文章得分更高）
   - GitHub Trending: +50 基础分
   - RSS Feed: +30 基础分
   - 其他来源: +20 基础分

2. **时效性**：
   - 今天发布的文章: +30 分

3. **内容质量**：
   - 标题长度适中（20-60字符）: +10 分
   - 有摘要: +5 分

文章会按热度分从高到低自动排序。

## 实际应用场景

### 场景一：技术资讯聚合

```python
articles = await fetch_from_all_sources(
    keywords=["AI", "机器学习"],
    rss_feeds=[
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    github_languages=["python", "javascript", "go"],
    hackernews_min_points=100,
    max_per_source=5,
)
```

**效果**：从技术网站、GitHub 热门项目、Hacker News 高分文章等多个来源抓取，获得全面的技术资讯。

### 场景二：新闻资讯聚合

```python
articles = await fetch_from_all_sources(
    keywords=["科技", "AI"],
    rss_feeds=[
        "https://rss.cnn.com/rss/edition.rss",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://www.reuters.com/rssFeed/technologyNews",
    ],
    max_per_source=10,
)
```

**效果**：从多个新闻源抓取，获得更全面的新闻覆盖。

### 场景三：开发者日报

```python
articles = await fetch_from_all_sources(
    github_languages=["python", "javascript", "rust", "go"],
    hackernews_min_points=50,
    max_per_source=10,
)
```

**效果**：专注于技术内容，从 GitHub 和 Hacker News 获取高质量技术文章。

## 配置建议

### RSS Feed 推荐

**技术类**：
- TechCrunch: `https://techcrunch.com/feed/`
- The Verge: `https://www.theverge.com/rss/index.xml`
- Hacker News RSS: `https://hnrss.org/frontpage`

**新闻类**：
- CNN: `https://rss.cnn.com/rss/edition.rss`
- BBC News: `https://feeds.bbci.co.uk/news/rss.xml`
- Reuters: `https://www.reuters.com/rssFeed/technologyNews`

**中文类**：
- 36氪: `https://36kr.com/feed`
- 虎嗅: `https://www.huxiu.com/rss/0.xml`

### GitHub Trending 语言推荐

- `python` - Python 项目
- `javascript` - JavaScript 项目
- `go` - Go 语言项目
- `rust` - Rust 项目
- `java` - Java 项目

### Hacker News 分数阈值

- **低阈值（50）**：获取更多文章，但质量可能参差不齐
- **中阈值（100）**：平衡质量和数量（推荐）
- **高阈值（200）**：只获取高质量文章，但数量较少

## 注意事项

1. **请求频率**：避免过于频繁的请求，建议在抓取之间添加延迟
2. **网络稳定性**：某些 Feed 可能需要稳定的网络连接
3. **内容过滤**：抓取的文章可能需要进一步过滤，确保符合你的需求
4. **存储空间**：多资讯源可能产生大量文章，注意存储空间

## 下一步

1. **配置 RSS Feed**：在代码或配置文件中添加你感兴趣的 RSS Feed
2. **测试抓取**：使用测试脚本或 API 测试各个资讯源
3. **集成到系统**：将多资讯源集成到现有的抓取和推送流程中
4. **调整参数**：根据实际效果调整各源的抓取数量和分数阈值

## 相关文档

- [测试指南](test_sources.md) - 如何测试多资讯源功能
- [API 文档](../README.md) - 完整的 API 使用说明

