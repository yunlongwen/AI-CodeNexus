## Daily Digest · 把热度新闻“秒变”你的内容资产

`100kwhy_wechat_mp` 是一个聚焦热闻捕捉与分发的项目。只要配置好关键词和企业微信群机器人，它就能帮你：

 - **自动发现热点**：Playwright 驱动关键词抓取，过滤掉旧闻，只保留当天新内容；
 - **一眼看完候选池**：抓到的文章会按关键词分组，方便人工筛选、快速采纳；
 - **定点推送 + 自动补位**：APScheduler 定时任务在推送前自动抽样文章，如遇空池会临时从候选池补齐；
 - **推送即清空**：手动/自动推送成功后，文章池与候选池自动清空，下一轮继续抓取，实现“无人值守”。

> 目标：把“找内容 → 组日报 → 推送”整个链路自动化，让运营同学专注观点与读者，而不是到处找素材。

---

### 亮点能力

| 能力 | 描述 |
| --- | --- |
| 关键词抓取 | 每个关键词可配置最多抓取多少篇文章，自动计算翻页并限量存储 |
| 候选池分组 | 面板中按关键词展示候选文章，可随时采纳/忽略 |
| 自动补位推送 | 推送前若文章池为空，会按关键词随机抽取候选文章填充主池 |
| 推送即清空 | 推送成功后自动清空文章池 & 候选池，防止旧内容重复推送 |
| 管理面板 | `/digest/panel` 集成添加文章、候选池分组、预览日报、手动推送等操作 |
| 可视化配置 | 支持在管理面板中配置关键词、调度策略、企业微信模板、系统环境变量等 |

---

### 技术栈一览

- Python 3.10+
- FastAPI + Uvicorn
- Playwright（搜狗微信或其他网页）
- APScheduler（cron 定时任务）
- 企业微信机器人 Markdown 推送

---

### 目录速览

```text
app/
  main.py                # 应用入口 + 定时任务
  routes/digest.py       # API & 管理面板
  sources/               # 文章池 / 候选池工具 & 爬虫
  notifier/wecom.py      # 企业微信推送
config/
  digest_schedule.json   # 推送策略
  wecom_template.json    # 企业微信推送样式
data/
  ai_articles.json       # 正式文章池（运行期数据）
  ai_candidates.json     # 候选池（运行期数据）
requirements.txt         # 依赖清单
docs/
  deploy_python.md       # Python 环境一键部署
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

创建 `.env`（或直接以环境变量形式注入）：

```bash
cat > .env <<'EOF'
WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
# 可选：管理面板授权码
# AICODING_ADMIN_CODE="your-admin-code"
EOF
```

设置推送策略 `config/digest_schedule.json`：

```json
{
  "cron": "0 14 * * *",
  "count": 5,
  "max_articles_per_keyword": 3
}
```

启动：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- 首页：`http://localhost:8000/`
- 管理面板：`http://localhost:8000/digest/panel`

> 生产环境部署？请参考 [docs/deploy_python.md](docs/deploy_python.md) 的 Python 环境一键部署指南，桌面/本地调试可参照 [docs/deploy_windows.md](docs/deploy_windows.md)。

### 配置管理

所有配置都可以在管理面板的"配置管理"中完成，无需手动编辑配置文件：

- **关键词配置**：设置抓取关键词，每行一个
- **调度配置**：设置推送时间（支持 Cron 表达式或小时+分钟）和数量控制
- **企业微信模板**：自定义推送消息的 Markdown 格式，支持占位符 `{date}`、`{theme}`、`{idx}`、`{title}`、`{url}`、`{source}`、`{summary}`
- **系统配置**：配置管理员验证码和企业微信推送地址

> 提示：配置修改后会自动保存，系统配置（环境变量）需要重启服务后生效。

---

## 使用场景

1. **自动抓取热点**：定时任务根据关键词抓取最新文章，候选池自动按关键词分组。
2. **人工质检**：在面板上按分组浏览，决定采纳或忽略；也可手动粘贴 URL 增补精品内容。
3. **定时推送**：APScheduler 在设定时间构建日报 → 调用企业微信机器人，一次搞定。
4. **循环往复**：推送成功后自动清空两个池子，下一轮继续抓取，实现“日更模式”。

> 转载第三方内容请遵守对应平台协议，保持原文链接和署名。

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
