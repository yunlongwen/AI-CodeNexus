# 宝塔面板部署指南

本文档详细说明如何在宝塔面板上部署 AI-CodeNexus 项目。

## 📋 前置条件

- 已安装宝塔面板
- 已安装 Python 项目管理器（Python 版本管理器）
- Python 3.10+ 环境（推荐 3.13.7）
- 已安装 Nginx（用于反向代理）

---

## 🚀 部署步骤

### 1. 准备项目目录

在宝塔面板中，建议将项目放在以下目录：
```bash
/www/wwwroot/aicoding.100kwhy.fun/
```

或者使用您现有的目录：
```bash
/www/wwwroot/100kwhy_wechat_mp/
```

### 2. 上传项目代码

#### 方法一：通过 Git 克隆（推荐）
```bash
cd /www/wwwroot/
git clone https://github.com/yunlongwen/100kwhy_wechat_mp.git
cd 100kwhy_wechat_mp
```

#### 方法二：通过宝塔文件管理器上传
1. 在宝塔面板中进入「文件」管理
2. 上传项目压缩包到 `/www/wwwroot/`
3. 解压文件

### 3. 配置 Python 环境

#### 3.1 确认 Python 环境路径

根据您提供的信息，Python 环境在：
```bash
/www/server/pyporject_evn/versions/3.13.7/bin/python3.13
```

验证 Python 版本：
```bash
/www/server/pyporject_evn/versions/3.13.7/bin/python3.13 --version
```

#### 3.2 创建虚拟环境（可选但推荐）

```bash
cd /www/wwwroot/100kwhy_wechat_mp
/www/server/pyporject_evn/versions/3.13.7/bin/python3.13 -m venv venv
source venv/bin/activate
```

或者直接使用系统 Python：
```bash
# 使用系统 Python，无需创建虚拟环境
```

### 4. 安装项目依赖

#### 4.1 安装 pip 依赖

```bash
cd /www/wwwroot/100kwhy_wechat_mp

# 如果使用虚拟环境
source venv/bin/activate

# 安装依赖
/www/server/pyporject_evn/versions/3.13.7/bin/pip3.13 install -r requirements.txt
```

#### 4.2 安装 Playwright（如果需要数据获取功能）

```bash
/www/server/pyporject_evn/versions/3.13.7/bin/playwright install
```

### 5. 配置环境变量

创建 `.env` 文件：
```bash
cd /www/wwwroot/100kwhy_wechat_mp
nano .env
```

添加以下内容：
```bash
# 管理员授权码（用于显示管理员入口）
AICODING_ADMIN_CODE=your-admin-code-here

# 企业微信推送（可选）
WECOM_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# 微信公众号配置（可选）
WECHAT_MP_APPID=your-appid
WECHAT_MP_SECRET=your-secret
```

保存文件（`Ctrl+O` 保存，`Ctrl+X` 退出）

### 6. 初始化数据目录

确保数据目录存在且权限正确：
```bash
cd /www/wwwroot/100kwhy_wechat_mp
mkdir -p data/articles data/tools
chmod -R 755 data
```

### 7. 测试运行

手动启动服务测试：
```bash
cd /www/wwwroot/100kwhy_wechat_mp

# 如果使用虚拟环境
source venv/bin/activate

# 启动服务
/www/server/pyporject_evn/versions/3.13.7/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 `http://your-server-ip:8000` 测试是否正常。

---

## 🔧 使用宝塔 Python 项目管理器部署

### 方法一：通过宝塔面板 Python 项目管理器

1. **打开宝塔面板** → 「软件商店」→ 搜索「Python项目管理器」→ 安装

2. **添加 Python 项目**：
   - 点击「Python项目管理器」→ 「添加 Python 项目」
   - 项目名称：`aicoding` 或 `100kwhy_wechat_mp`
   - 项目路径：`/www/wwwroot/100kwhy_wechat_mp`
   - Python 版本：选择 `3.13.7` 或您已安装的版本
   - Python 框架：选择「其他」
   - 启动方式：选择「uwsgi」或「gunicorn」
   - 启动文件：`app.main:app`
   - 端口：`8000`（或您自定义的端口）

3. **配置启动命令**（如果使用 uvicorn）：
   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **安装依赖**：
   - 在项目管理器中，点击「模块」→ 安装 `requirements.txt` 中的依赖
   - 或手动执行：
     ```bash
     /www/server/pyporject_evn/versions/3.13.7/bin/pip3.13 install -r /www/wwwroot/100kwhy_wechat_mp/requirements.txt
     ```

5. **启动项目**：
   - 在项目管理器中点击「启动」按钮

### 方法二：使用 Supervisor 进程管理（推荐）

1. **安装 Supervisor**（如果未安装）：
   ```bash
   yum install supervisor -y  # CentOS
   # 或
   apt-get install supervisor -y  # Ubuntu/Debian
   ```

2. **创建 Supervisor 配置文件**：
   ```bash
   nano /etc/supervisor/conf.d/aicoding.conf
   ```

   添加以下内容：
   ```ini
   [program:aicoding]
   directory=/www/wwwroot/100kwhy_wechat_mp
   command=/www/server/pyporject_evn/versions/3.13.7/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
   user=root
   autostart=true
   autorestart=true
   redirect_stderr=true
   stdout_logfile=/www/wwwroot/100kwhy_wechat_mp/logs/app.log
   environment=PATH="/www/server/pyporject_evn/versions/3.13.7/bin:%(ENV_PATH)s"
   ```

3. **创建日志目录**：
   ```bash
   mkdir -p /www/wwwroot/100kwhy_wechat_mp/logs
   ```

4. **启动 Supervisor**：
   ```bash
   supervisorctl reread
   supervisorctl update
   supervisorctl start aicoding
   ```

5. **查看状态**：
   ```bash
   supervisorctl status aicoding
   ```

---

## 🌐 配置 Nginx 反向代理

### 1. 在宝塔面板中配置站点

1. 打开「网站」→ 「添加站点」
2. 域名：`aicoding.100kwhy.fun`（或您的域名）
3. 根目录：`/www/wwwroot/100kwhy_wechat_mp`
4. PHP 版本：纯静态（不需要 PHP）

### 2. 配置反向代理

1. 点击站点「设置」→ 「反向代理」→ 「添加反向代理」
2. 代理名称：`aicoding`
3. 目标URL：`http://127.0.0.1:8000`
4. 发送域名：`$host`
5. 点击「提交」

### 3. 修改 Nginx 配置（可选优化）

点击站点「设置」→ 「配置文件」，在 `location /` 部分添加：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket 支持（如果需要）
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # 超时设置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

### 4. 配置 SSL 证书（推荐）

1. 在站点「设置」→ 「SSL」中
2. 选择「Let's Encrypt」免费证书
3. 点击「申请」并开启「强制 HTTPS」

---

## 🔍 验证部署

### 1. 检查服务状态

```bash
# 检查进程是否运行
ps aux | grep uvicorn

# 检查端口是否监听
netstat -tlnp | grep 8000
```

### 2. 测试访问

- 访问：`https://aicoding.100kwhy.fun/`
- 检查各个页面是否正常加载
- 测试 API：`https://aicoding.100kwhy.fun/api/config`

### 3. 查看日志

```bash
# 应用日志
tail -f /www/wwwroot/100kwhy_wechat_mp/logs/app.log

# Nginx 日志
tail -f /www/wwwroot/logs/aicoding.100kwhy.fun.log

# Supervisor 日志（如果使用）
supervisorctl tail -f aicoding
```

---

## 🛠️ 常用管理命令

### 启动/停止/重启服务

**如果使用 Supervisor**：
```bash
supervisorctl start aicoding    # 启动
supervisorctl stop aicoding     # 停止
supervisorctl restart aicoding  # 重启
supervisorctl status aicoding  # 查看状态
```

**如果使用宝塔 Python 项目管理器**：
- 在面板中直接点击「启动」「停止」「重启」按钮

**如果手动运行**：
```bash
# 启动（后台运行）
nohup /www/server/pyporject_evn/versions/3.13.7/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /www/wwwroot/100kwhy_wechat_mp/logs/app.log 2>&1 &

# 停止
pkill -f "uvicorn app.main:app"
```

### 更新代码

```bash
cd /www/wwwroot/100kwhy_wechat_mp
git pull origin master

# 如果有新依赖
/www/server/pyporject_evn/versions/3.13.7/bin/pip3.13 install -r requirements.txt

# 重启服务
supervisorctl restart aicoding
```

---

## ⚠️ 常见问题

### 1. 端口被占用

如果 8000 端口被占用，可以：
- 修改启动命令中的端口号
- 或使用其他端口，并在 Nginx 配置中相应修改

### 2. 权限问题

确保数据目录有写权限：
```bash
chmod -R 755 /www/wwwroot/100kwhy_wechat_mp/data
chown -R www:www /www/wwwroot/100kwhy_wechat_mp/data
```

### 3. 依赖安装失败

尝试使用国内镜像源：
```bash
/www/server/pyporject_evn/versions/3.13.7/bin/pip3.13 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 静态文件无法访问

确保在 `app/main.py` 中已正确配置静态文件路径：
```python
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

### 5. 环境变量未生效

- 确保 `.env` 文件在项目根目录
- 检查 `.env` 文件权限：`chmod 644 .env`
- 重启服务使环境变量生效

---

## 📝 生产环境优化建议

### 1. 使用 Gunicorn + Uvicorn Workers（推荐）

```bash
/www/server/pyporject_evn/versions/3.13.7/bin/pip3.13 install gunicorn

# 启动命令改为：
/www/server/pyporject_evn/versions/3.13.7/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. 配置日志轮转

创建日志轮转配置：
```bash
nano /etc/logrotate.d/aicoding
```

添加：
```
/www/wwwroot/100kwhy_wechat_mp/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 3. 设置开机自启

如果使用 Supervisor，确保 Supervisor 开机自启：
```bash
systemctl enable supervisor
systemctl start supervisor
```

---

## 🎯 快速部署脚本

创建一键部署脚本 `deploy.sh`：

```bash
#!/bin/bash

PROJECT_DIR="/www/wwwroot/100kwhy_wechat_mp"
PYTHON_BIN="/www/server/pyporject_evn/versions/3.13.7/bin/python3.13"
PIP_BIN="/www/server/pyporject_evn/versions/3.13.7/bin/pip3.13"

cd $PROJECT_DIR

# 更新代码
git pull origin master

# 安装依赖
$PIP_BIN install -r requirements.txt

# 创建必要目录
mkdir -p data/articles data/tools logs

# 设置权限
chmod -R 755 data
chmod 644 .env

# 重启服务
supervisorctl restart aicoding

echo "部署完成！"
```

使用：
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 📚 相关文档

- [完整功能文档](features_complete.md)
- [Python环境部署](deploy_python.md)
- [Windows部署](deploy_windows.md)

---

**部署完成后，访问您的域名即可使用 AI-CodeNexus 平台！** 🎉

