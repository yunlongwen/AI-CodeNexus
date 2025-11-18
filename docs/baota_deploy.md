## 宝塔面板部署说明（企业微信每日 AI 编程推荐）

本说明帮助你在宝塔面板中部署 `100kwhy_wechat_mp`，并通过企业微信群机器人每天 14:00 推送 5 篇 AI 编程文章。

> 假设项目路径为：`/www/wwwroot/100kwhy_wechat_mp`

---

### 一、环境变量文件（推荐）

1. 在服务器上创建环境变量文件 `env.sh`：

```bash
cd /www/wwwroot/100kwhy_wechat_mp
cat > env.sh << 'EOF'
#!/usr/bin/env bash

# 企业微信群机器人 Webhook 地址
export WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=替换成你的key"

# 如果后续接入微信公众号，可在这里一起配置
# export WECHAT_TOKEN="your_wechat_token"
EOF

chmod +x env.sh
```

2. 在宝塔「Python项目」中配置环境变量：

- 选择项目 → 「添加 Python 项目」弹窗中：
  - `环境变量` 选择：**从文件加载**
  - 右侧选择文件：指向 `/www/wwwroot/100kwhy_wechat_mp/env.sh`

---

### 二、启动方式与启动命令

在宝塔「添加 Python 项目」中按如下填写：

- **项目名称**：`100kwhy_wechat_mp`
- **Python环境**：选择 **Python 3.13.7**（或你安装的其他 Python 3.x，**不要选 2.7**）
- **启动方式**：选择 **命令行启动**
- **项目路径**：`/www/wwwroot/100kwhy_wechat_mp`
- **当前框架**：选择 `fastapi` / `asgi`（不同版本文案略有差异，选 ASGI 类型即可）
- **环境变量**：选择「从文件加载」，并选中上面创建的 `env.sh`
- **启动命令**（**关键：使用宝塔配置的 Python 环境**）：

```bash
cd /www/wwwroot/100kwhy_wechat_mp && \
if [ ! -d "venv" ]; then python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install fastapi "uvicorn[standard]" httpx apscheduler loguru; fi && \
source venv/bin/activate && \
source env.sh && \
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**重要说明**：

1. **宝塔会自动使用你选择的 Python 环境**（3.13.7），所以命令里的 `python3` 会指向正确的版本。
2. 上面的启动命令会：
   - 检查 `venv` 是否存在，不存在则自动创建并安装依赖（只需一次）
   - 激活虚拟环境
   - 加载环境变量文件 `env.sh`
   - 启动 uvicorn 服务
3. 如果启动失败，请检查：
   - 宝塔「项目日志」里的错误信息
   - 确认 `env.sh` 文件存在且 `WECOM_WEBHOOK` 已正确配置
4. FastAPI 监听 `8000` 端口，宝塔会自动使用 Nginx 做反向代理。

---

### 三、首次测试建议

1. 为了验证定时任务，可在 `app/main.py` 中临时把：

```python
@scheduler.scheduled_job("cron", hour=14, minute=0)
```

改为当前时间之后几分钟对应的小时，例如：

```python
@scheduler.scheduled_job("cron", hour=16, minute=5)
```

2. 在宝塔中重启 Python 项目，观察企业微信群是否在指定时间收到一条「AI 编程优质文章推荐」消息。

3. 测试通过后，再改回 `hour=14, minute=0`，重新部署。


