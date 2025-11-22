# 微信公众号发布功能使用指南

## 功能说明

微信公众号发布功能允许你将抓取的文章自动发布到微信公众号，支持：

1. **创建草稿**：将文章创建为微信公众号草稿
2. **发布草稿**：将草稿发布到公众号
3. **一键发布日报**：直接将当前日报发布到公众号

## 当前状态

✅ **代码已实现**：微信公众号客户端代码已完成  
⚠️ **需要配置**：需要配置 AppID 和 Secret  
⚠️ **需要测试**：功能已实现但需要实际测试验证

## 配置步骤

### 1. 获取微信公众号 AppID 和 Secret

1. 登录[微信公众平台](https://mp.weixin.qq.com/)
2. 进入"开发" -> "基本配置"
3. 获取 `AppID` 和 `AppSecret`

### 2. 配置环境变量

在 `.env` 文件中添加：

```bash
WECHAT_MP_APPID="your_appid"
WECHAT_MP_SECRET="your_secret"
```

或者在系统配置面板中配置（需要重启服务生效）。

### 3. 设置 IP 白名单（可选）

如果使用 IP 白名单，需要在微信公众平台添加服务器 IP。

## 使用方法

### 方法一：通过 API 接口

#### 1. 创建草稿

```bash
curl -X POST "http://localhost:8000/digest/wechat-mp/create-draft" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{
    "articles": [
      {
        "title": "文章标题",
        "author": "作者",
        "digest": "摘要",
        "content": "<p>文章内容</p>",
        "content_source_url": "https://example.com/article",
        "thumb_media_id": "",
        "show_cover_pic": 1
      }
    ]
  }'
```

#### 2. 发布草稿

```bash
curl -X POST "http://localhost:8000/digest/wechat-mp/publish" \
  -H "X-Admin-Code: your-admin-code" \
  -H "Content-Type: application/json" \
  -d '{
    "media_id": "your_media_id"
  }'
```

#### 3. 一键发布日报

```bash
curl -X POST "http://localhost:8000/digest/wechat-mp/publish-digest" \
  -H "X-Admin-Code: your-admin-code"
```

### 方法二：通过 Swagger UI

1. 启动服务：`uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. 访问：`http://localhost:8000/docs`
3. 找到微信公众号相关接口：
   - `POST /digest/wechat-mp/create-draft` - 创建草稿
   - `POST /digest/wechat-mp/publish` - 发布草稿
   - `POST /digest/wechat-mp/publish-digest` - 一键发布日报
4. 点击 "Try it out"，填写参数，执行测试

### 方法三：在代码中使用

```python
from app.notifier.wechat_mp import WeChatMPClient

# 创建客户端
client = WeChatMPClient()

# 准备文章数据
articles = [
    {
        "title": "文章标题",
        "author": "作者",
        "digest": "摘要（120字以内）",
        "content": "<p>文章内容 HTML</p>",
        "content_source_url": "https://example.com/article",
        "thumb_media_id": "",  # 可选：封面图 media_id
        "show_cover_pic": 1,  # 是否显示封面
    }
]

# 创建草稿
media_id = await client.create_draft(articles)
if media_id:
    print(f"草稿创建成功，media_id: {media_id}")
    
    # 发布草稿
    success = await client.publish(media_id)
    if success:
        print("发布成功！")
```

## 文章格式说明

微信公众号文章需要以下字段：

- **title** (必填): 文章标题
- **author** (必填): 作者
- **digest** (可选): 摘要，最多120字
- **content** (必填): 文章内容，HTML 格式
- **content_source_url** (必填): 原文链接
- **thumb_media_id** (可选): 封面图 media_id（需要先上传）
- **show_cover_pic** (可选): 是否显示封面，0/1

## 注意事项

### 1. Access Token 管理

- Access Token 有效期为 7200 秒（2小时）
- 系统会自动刷新 Token（提前5分钟）
- 如果 Token 过期，会自动重新获取

### 2. 文章数量限制

- 单次最多创建 8 篇文章
- 如果文章过多，建议分批创建

### 3. 封面图

- 如果需要封面图，需要先使用 `upload_media` 上传图片
- 上传后获得 `media_id`，在创建文章时使用

### 4. 发布限制

- 每天有发布次数限制（根据公众号类型不同）
- 建议先创建草稿，确认后再发布

### 5. 内容格式

- 内容必须是 HTML 格式
- 支持基本的 HTML 标签（p, a, img, strong 等）
- 不支持 JavaScript 和外部 CSS

## 测试步骤

### 1. 测试 Access Token 获取

```python
from app.notifier.wechat_mp import WeChatMPClient

client = WeChatMPClient()
token = await client.get_access_token()
print(f"Access Token: {token}")
```

### 2. 测试创建草稿

使用 Swagger UI 或 curl 测试创建草稿接口，检查返回的 `media_id`。

### 3. 测试发布

在微信公众平台查看草稿，确认无误后再发布。

## 常见问题

### Q: 获取 Access Token 失败？

A: 检查：
1. AppID 和 Secret 是否正确
2. 网络连接是否正常
3. IP 是否在白名单中（如果设置了）

### Q: 创建草稿失败？

A: 检查：
1. 文章格式是否正确
2. 必填字段是否都有
3. 内容是否符合微信公众号规范

### Q: 发布失败？

A: 检查：
1. media_id 是否正确
2. 草稿是否已存在
3. 是否达到每日发布限制

## 集成到现有流程

可以将微信公众号发布集成到定时推送任务中：

```python
from app.notifier.wechat_mp import WeChatMPClient
from app.sources.ai_articles import get_all_articles

async def publish_to_wechat_mp():
    """将日报发布到微信公众号"""
    # 获取文章
    articles_data = get_all_articles()
    
    # 转换为微信公众号格式
    wechat_articles = convert_to_wechat_format(articles_data["articles"])
    
    # 创建并发布
    client = WeChatMPClient()
    media_id = await client.create_draft(wechat_articles)
    if media_id:
        await client.publish(media_id)
```

## 相关文档

- [微信公众平台开发文档](https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html)
- [素材管理 API](https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/New_temporary_materials.html)
- [草稿箱 API](https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Add_draft.html)

