# 403 错误排查指南

## 常见原因和解决方案

### 1. Nginx/Apache 配置问题

#### 检查 Nginx 配置
```bash
# 检查 Nginx 配置语法
nginx -t

# 查看 Nginx 错误日志
tail -f /var/log/nginx/error.log
# 或
tail -f /var/log/nginx/aicoding_error.log
```

#### 常见配置错误：
- **缺少 `proxy_set_header Host`**：必须设置，否则 FastAPI 可能无法正确识别域名
- **代理地址错误**：确认 FastAPI 应用实际运行的端口（默认 8000）
- **权限问题**：Nginx 用户需要有权限访问代理目标

### 2. FastAPI 应用未运行

检查应用是否正在运行：
```bash
# 检查端口是否被占用
netstat -tlnp | grep 8000
# 或
ss -tlnp | grep 8000

# 检查进程
ps aux | grep uvicorn
```

### 3. 防火墙或安全组规则

确保防火墙允许访问：
```bash
# 检查防火墙状态
systemctl status firewalld
# 或
ufw status

# 如果需要，开放端口
firewall-cmd --add-port=8000/tcp --permanent
firewall-cmd --reload
```

### 4. SELinux 问题（如果启用）

```bash
# 检查 SELinux 状态
getenforce

# 如果启用，允许 Nginx 代理
setsebool -P httpd_can_network_connect 1
```

### 5. 宝塔面板配置

如果使用宝塔面板：

1. **检查网站配置**
   - 进入「网站」→ 找到 `aicoding.100kwhy.fun`
   - 确认「运行目录」和「网站目录」设置正确
   - 确认「反向代理」配置正确

2. **检查 Python 项目配置**
   - 进入「Python项目」
   - 确认项目运行状态为「运行中」
   - 确认端口号与 Nginx 配置一致

3. **检查文件权限**
   ```bash
   # 确保项目目录权限正确
   chown -R www:www /www/wwwroot/100kwhy_wechat_mp
   chmod -R 755 /www/wwwroot/100kwhy_wechat_mp
   ```

### 6. 测试步骤

1. **直接访问 FastAPI 应用**（绕过 Nginx）
   ```bash
   curl http://127.0.0.1:8000/
   curl http://127.0.0.1:8000/health
   ```

2. **测试 Nginx 代理**
   ```bash
   curl -H "Host: aicoding.100kwhy.fun" http://127.0.0.1/
   ```

3. **查看详细错误信息**
   - 浏览器开发者工具 → Network 标签
   - 查看响应头和响应体
   - 查看服务器日志

### 7. 快速修复命令

```bash
# 重启 Nginx
systemctl restart nginx
# 或
service nginx restart

# 重启 FastAPI 应用（如果使用 systemd）
systemctl restart 100kwhy_wechat_mp
# 或手动重启
cd /www/wwwroot/100kwhy_wechat_mp
# 停止旧进程，启动新进程
```

### 8. 调试模式

在 FastAPI 应用中启用详细日志：
```python
# 在 main.py 中
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 9. 检查域名解析

```bash
# 确认域名解析正确
nslookup aicoding.100kwhy.fun
dig aicoding.100kwhy.fun
```

## 推荐的 Nginx 配置

参考 `docs/nginx_config_example.conf` 文件，确保包含以下关键配置：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## 联系支持

如果以上方法都无法解决问题，请提供：
1. Nginx 错误日志
2. FastAPI 应用日志
3. 完整的 Nginx 配置文件
4. `curl -v http://aicoding.100kwhy.fun/` 的输出

