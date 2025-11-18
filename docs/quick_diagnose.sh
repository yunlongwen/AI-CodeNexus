#!/bin/bash
# 快速诊断脚本 - 检查 403 错误的常见原因

echo "=== 403 错误快速诊断 ==="
echo ""

# 1. 检查 FastAPI 应用是否运行
echo "1. 检查 FastAPI 应用状态..."
if netstat -tlnp 2>/dev/null | grep -q ":8000" || ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "   ✅ 端口 8000 正在监听"
    netstat -tlnp 2>/dev/null | grep ":8000" || ss -tlnp 2>/dev/null | grep ":8000"
else
    echo "   ❌ 端口 8000 未监听 - FastAPI 应用可能未运行"
fi
echo ""

# 2. 测试本地访问
echo "2. 测试本地访问..."
if curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "   ✅ 本地访问正常"
    curl -s http://127.0.0.1:8000/health | head -1
else
    echo "   ❌ 本地访问失败 - 应用可能未启动或配置错误"
fi
echo ""

# 3. 检查 Nginx 状态
echo "3. 检查 Nginx 状态..."
if systemctl is-active --quiet nginx; then
    echo "   ✅ Nginx 正在运行"
else
    echo "   ❌ Nginx 未运行"
fi
echo ""

# 4. 检查 Nginx 配置语法
echo "4. 检查 Nginx 配置..."
if command -v nginx &> /dev/null; then
    if nginx -t 2>&1 | grep -q "successful"; then
        echo "   ✅ Nginx 配置语法正确"
    else
        echo "   ❌ Nginx 配置有错误："
        nginx -t 2>&1 | grep -i error
    fi
else
    echo "   ⚠️  未找到 nginx 命令"
fi
echo ""

# 5. 检查防火墙
echo "5. 检查防火墙..."
if command -v firewall-cmd &> /dev/null; then
    if firewall-cmd --list-ports 2>/dev/null | grep -q "8000"; then
        echo "   ✅ 端口 8000 已在防火墙中开放"
    else
        echo "   ⚠️  端口 8000 可能未在防火墙中开放"
    fi
elif command -v ufw &> /dev/null; then
    if ufw status | grep -q "8000"; then
        echo "   ✅ 端口 8000 已在防火墙中开放"
    else
        echo "   ⚠️  端口 8000 可能未在防火墙中开放"
    fi
else
    echo "   ⚠️  未检测到防火墙管理工具"
fi
echo ""

# 6. 检查文件权限
echo "6. 检查项目目录权限..."
PROJECT_DIR="/www/wwwroot/100kwhy_wechat_mp"
if [ -d "$PROJECT_DIR" ]; then
    PERMS=$(stat -c "%a" "$PROJECT_DIR" 2>/dev/null || stat -f "%OLp" "$PROJECT_DIR" 2>/dev/null)
    echo "   项目目录权限: $PERMS"
    if [ "$PERMS" = "755" ] || [ "$PERMS" = "775" ]; then
        echo "   ✅ 目录权限正常"
    else
        echo "   ⚠️  建议权限: 755 或 775"
    fi
else
    echo "   ❌ 项目目录不存在: $PROJECT_DIR"
fi
echo ""

# 7. 检查最近的 Nginx 错误日志
echo "7. 最近的 Nginx 错误日志（最后 5 行）..."
if [ -f /var/log/nginx/error.log ]; then
    tail -5 /var/log/nginx/error.log | grep -i "403\|forbidden\|error" || echo "   无相关错误"
elif [ -f /www/server/nginx/logs/error.log ]; then
    tail -5 /www/server/nginx/logs/error.log | grep -i "403\|forbidden\|error" || echo "   无相关错误"
else
    echo "   ⚠️  未找到 Nginx 错误日志"
fi
echo ""

echo "=== 诊断完成 ==="
echo ""
echo "建议操作："
echo "1. 如果应用未运行，请启动 FastAPI 应用"
echo "2. 检查 Nginx 配置文件中的 proxy_pass 地址"
echo "3. 确认 Nginx 配置中包含正确的 proxy_set_header 设置"
echo "4. 查看详细排查指南: docs/403_error_troubleshooting.md"

