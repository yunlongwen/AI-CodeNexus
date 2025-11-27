#!/bin/bash

# 设置脚本在遇到错误时退出
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  100kwhy_wechat_mp 一键启动脚本 (Linux)"
echo "========================================"
echo ""

# 获取脚本所在目录，然后向上两级到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "[1/4] 检查项目目录..."
if [ ! -d "$PROJECT_ROOT" ]; then
    echo -e "${RED}错误: 项目目录不存在: $PROJECT_ROOT${NC}"
    exit 1
fi
echo "项目目录: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

echo ""
echo "[2/4] 检查虚拟环境..."
if [ ! -f "venv/bin/activate" ]; then
    echo "虚拟环境不存在，正在创建..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}错误: 创建虚拟环境失败，请确保已安装 Python 3.10+${NC}"
        exit 1
    fi
    echo -e "${GREEN}虚拟环境创建成功${NC}"
fi

echo ""
echo "[3/4] 激活虚拟环境并检查依赖..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 激活虚拟环境失败${NC}"
    exit 1
fi

# 检查 uvicorn 是否已安装
python -c "import uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "检测到依赖未安装，正在安装..."
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}错误: 安装依赖失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}依赖安装完成${NC}"
else
    echo -e "${GREEN}依赖检查通过${NC}"
fi

echo ""
echo "[4/4] 启动应用..."
echo -e "${GREEN}服务地址: http://127.0.0.1:8000${NC}"
echo -e "${GREEN}管理面板: http://127.0.0.1:8000/digest/panel${NC}"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================"
echo ""

# 启动应用（开发模式，支持热重载）
# 如果需要生产模式，可以去掉 --reload 参数，并修改 --host 为 0.0.0.0
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

