# Python 环境一键部署指南

本指南将引导你如何在一个标准的 Linux 服务器上，通过 Python 环境（而非 Docker 或其他 PaaS 平台）部署 AICoding Daily 项目。

### 前提条件

- 一台已安装 Python 3.10+ 和 `git` 的服务器。
- 对 `systemd`（或你偏好的进程管理工具）有基本了解。
- （可选但强烈推荐）一个域名，用于配置 Nginx 反向代理。

--- 

### 步骤 1：克隆仓库与安装依赖

首先，将项目代码克隆到你的服务器上，例如 `/var/www/aicoding` 目录：

```bash
sudo mkdir -p /var/www
sudo chown $USER:$USER /var/www

git clone https://github.com/your-name/100kwhy_wechat_mp.git /var/www/aicoding
cd /var/www/aicoding
```

创建 Python 虚拟环境并安装所有依赖：

```bash
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

最后，安装 Playwright 所需的浏览器内核（通常是 Chromium）：

```bash
playwright install
```

--- 

### 步骤 2：配置环境变量

在项目根目录 `/var/www/aicoding` 下创建一个 `.env` 文件，用于存放敏感信息：

```bash
cat > .env <<'EOF'
# 必填：你的企业微信群机器人 Webhook URL
WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"

# 必填：用于保护管理面板的授权码
AICODING_ADMIN_CODE="a-very-strong-and-secret-password"
EOF
```

> **重要**：请务必将 `AICODING_ADMIN_CODE` 设置为一个强密码，以防未授权访问。

--- 

### 步骤 3：配置应用

根据你的需求，调整 `config/` 目录下的配置文件：

1.  **推送策略 (`config/digest_schedule.json`)**

    ```json
    {
      "cron": "0 14 * * *",
      "count": 5,
      "max_articles_per_keyword": 3
    }
    ```
    - `cron`：每日推送时间，格式为标准的 5 段 cron 表达式。
    - `count`：每次推送的文章数量。
    - `max_articles_per_keyword`：每个关键词最多抓取并保留的文章数。

2.  **抓取关键词 (`config/crawler_keywords.json`)**

    ```json
    [
      "AI 编程",
      "Cursor.sh",
      "Devin",
      "代码大模型"
    ]
    ```
    - 在此列表中添加或修改你关心的公众号文章关键词。

--- 

### 步骤 4：使用 systemd 运行应用

为了让应用能在后台稳定运行并实现开机自启，我们使用 `systemd` 来管理它。

创建 systemd 服务文件：

```bash
sudo nano /etc/systemd/system/aicoding.service
```

将以下内容粘贴进去，并根据你的实际情况修改 `User` 和 `Group`（通常是 `www-data` 或你的用户名）：

```ini
[Unit]
Description=AICoding Daily Backend Service
After=network.target

[Service]
# 运行服务的用户和组
User=www-data
Group=www-data

# 项目根目录
WorkingDirectory=/var/www/aicoding

# 环境变量文件路径
EnvironmentFile=/var/www/aicoding/.env

# 启动命令：使用虚拟环境中的 uvicorn
ExecStart=/var/www/aicoding/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 失败后自动重启
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

保存并退出后，启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl start aicoding.service
sudo systemctl enable aicoding.service
```

检查服务状态，确保它正在运行：

```bash
sudo systemctl status aicoding.service
```

--- 

### 步骤 5（可选）：配置 Nginx 反向代理

直接暴露 8000 端口不安全且不方便。推荐使用 Nginx 作为反向代理，并通过域名访问。

安装 Nginx（如果尚未安装）：

```bash
sudo apt update
sudo apt install nginx
```

创建一个新的 Nginx 站点配置：

```bash
sudo nano /etc/nginx/sites-available/aicoding
```

粘贴以下配置，并将 `your-domain.com` 替换为你的域名：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用该站点并测试配置：

```bash
sudo ln -s /etc/nginx/sites-available/aicoding /etc/nginx/sites-enabled/
sudo nginx -t
```

如果测试通过，重启 Nginx 使配置生效：

```bash
sudo systemctl restart nginx
```

现在，你可以通过 `http://your-domain.com/digest/panel` 访问你的管理面板了。

> **提示**：为了安全，建议后续为你的域名配置 SSL 证书（HTTPS），可以使用 Let's Encrypt 免费实现。

