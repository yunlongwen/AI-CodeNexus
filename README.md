## AICoding Daily · AI 编程资讯自动聚合与推送

`100kwhy_wechat_mp` 是一个面向「AI 编程」场景的开源项目，用于：

- 通过**爬虫**自动采集 AI 编程 / 工程效率相关资讯；
- 汇总成每日「AI 编程资讯日报」；
- 通过企业微信机器人推送到团队群（后续可扩展为微信公众号图文推送）。

最终目标：**把分散在各个公众号和网站上的优质 AI 编程内容，自动整理并转载到你的公众号/团队渠道。**

---

### 功能概览

- **文章爬取**
  - 在管理面板中粘贴文章 URL（支持微信公众号文章等）
  - 爬虫自动抓取：标题 / 来源（作者或公众号）/ 摘要
  - 一键加入文章池配置（`config/ai_articles.json`）

- **文章池管理**
  - 在 Web 面板查看当前所有文章
  - 支持按 URL 删除文章

- **每日定时推送**
  - 使用 APScheduler + cron 表达式配置每日推送时间
  - 根据配置从文章池中随机抽取 N 篇
  - 生成适配企业微信机器人的 Markdown 消息并推送

- **管理面板**
  - 路径：`/digest/panel`（例如 `http://your-domain/digest/panel`）
  - 功能：
    - 添加文章（粘贴 URL）
    - 查看/删除文章列表
    - 预览当日将推送的日报内容
    - 手动触发一次企业微信推送

---

### 技术栈

- **语言 & 框架**
  - Python 3.10+
  - FastAPI（Web API & 管理页面）
- **调度**
  - APScheduler（基于 cron 表达式的定时任务）
- **HTTP & 爬虫基础**
  - httpx（HTTP 客户端）
  - 标准库 `html.parser` + 正则解析文章标题 / 来源 / 摘要

---

### 目录结构（简要）

```text
app/
  main.py                # 应用入口，包含 scheduler 与根路由
  routes/
    digest.py            # 日报相关 API + 管理面板 HTML
    wechat.py            # 微信公众号接入（占位/待扩展）
  sources/
    ai_articles.py       # 文章池加载/保存/删除
    article_crawler.py   # 通用文章爬虫（通过 URL 获取标题/来源/摘要）
  notifier/
    wecom.py             # 企业微信机器人推送

config/
  digest_schedule.json   # 推送时间 & 篇数配置（支持 cron）
  ai_articles.json       # 文章池（由面板或脚本维护）

docs/
  nginx_config_example.conf      # Nginx 反向代理示例
  403_error_troubleshooting.md   # 403 错误排查指南
  quick_diagnose.sh              # 服务器快速诊断脚本
```

---

## 快速开始（开发环境）

### 1. 克隆仓库

```bash
git clone https://github.com/your-name/100kwhy_wechat_mp.git
cd 100kwhy_wechat_mp
```

### 2. 创建虚拟环境并安装依赖

推荐使用 `venv` 或 `poetry`，这里以 `venv` 为例：

```bash
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install fastapi "uvicorn[standard]" httpx apscheduler loguru python-dotenv
```

> 若使用 `poetry`，直接执行：
> ```bash
> poetry install
> ```

### 3. 配置环境变量

在项目根目录新建 `.env` 或 `env.sh`，至少配置企业微信机器人 Webhook：

```bash
cat > .env << 'EOF'
WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
EOF
```

或使用 `env.sh`：

```bash
cat > env.sh << 'EOF'
#!/usr/bin/env bash
export WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
# 可选：管理面板授权码（如不配置则默认不做鉴权，仅适合本地开发）
# export AICODING_ADMIN_CODE="your-admin-code"
EOF
```

在本地启动前，执行：

```bash
source env.sh  # 如果你使用的是 env.sh
```

### 4. 配置推送时间与篇数

编辑 `config/digest_schedule.json`：

```json
{
  "cron": "0 14 * * *",
  "count": 5
}
```

- `cron`：标准 5 段 cron 表达式（分 时 日 月 周），上例表示每天 14:00 推送
- `count`：每天选取的文章数量

### 5. 启动应用

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

浏览器访问：

- 首页：`http://localhost:8000/`
- 管理面板：`http://localhost:8000/digest/panel`

---

## 生产部署（示例）

这里给出一个基于 **systemd + Nginx** 的通用部署方案（不依赖宝塔）。

### 1. 后端服务（systemd）

创建文件 `/etc/systemd/system/aicoding.service`：

```ini
[Unit]
Description=AICoding Daily Backend (FastAPI)
After=network.target

[Service]
WorkingDirectory=/www/wwwroot/100kwhy_wechat_mp
EnvironmentFile=/www/wwwroot/100kwhy_wechat_mp/env.sh
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl start aicoding.service
sudo systemctl enable aicoding.service
```

### 2. Nginx 反向代理

参考 `docs/nginx_config_example.conf`，核心配置类似：

```nginx
server {
    listen 80;
    server_name aicoding.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

配置完成后：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 如何利用本项目为公众号获取 & 转载 AI 编程资讯

1. **从面板导入文章**
   - 打开 `http://your-domain/digest/panel`
   - 在「添加文章」区域粘贴公众号文章 URL（例如 `https://mp.weixin.qq.com/s/...`）
   - 系统会自动爬取标题 / 来源（作者或公众号）/ 摘要，并写入 `config/ai_articles.json`

2. **筛选与管理文章池**
   - 使用同一面板中的「文章列表」模块查看与删除文章
   - 你可以人工筛选，只保留真正适合你公众号调性的内容

3. **自动生成每日推荐并推送到企业微信群**
   - 根据 `digest_schedule.json` 的 cron 配置，每天自动在文章池中随机抽取若干篇
   - 使用 `app/notifier/wecom.py` 生成 Markdown 并通过机器人推送

4. **在公众号中二次编辑/转载**
   - 你可以手动把当天推荐列表（标题 + 链接 + 摘要）整理为公众号图文
   - 或者基于 `app/digest/render.py` 的示例，扩展出「生成公众号图文内容」的渲染逻辑

> 注意：转载第三方内容时，请遵守各平台/公众号的转载规范，可加上原文链接及出处说明。

---

## 未来规划（与 `todo.md` 对应）

- 真正打通 **微信公众号** 群发接口，一键在公众号后台创建图文消息；
- 引入更多数据源（例如 RSS、Hacker News、GitHub Trending 等）；
- 用 Embedding/Tag 对文章做主题分类，支持智能推荐；
- 支持多频道配置（不同企业微信群/公众号使用不同的文章池与推送策略）。

欢迎 Issue / PR，一起把「AI 编程资讯自动化」这条链路打磨得更好。

---

## 开源协议

本项目采用 **MIT License** 开源协议发布，详情见仓库中的 `LICENSE` 文件。你可以在遵守许可证的前提下自由使用、修改和分发本项目。*** End Patch***}"}еша to=functions.apply_patchорошIEnumerator to=functions.apply_patch ***!
