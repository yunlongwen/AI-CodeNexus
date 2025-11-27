@echo off
chcp 65001 >nul
echo ========================================
echo   100kwhy_wechat_mp 一键启动脚本 (Windows)
echo ========================================
echo.

REM 获取脚本所在目录，然后向上两级到项目根目录
cd /d "%~dp0\..\.."
set PROJECT_ROOT=%CD%

echo [1/4] 检查项目目录...
if not exist "%PROJECT_ROOT%" (
    echo 错误: 项目目录不存在: %PROJECT_ROOT%
    pause
    exit /b 1
)
echo 项目目录: %PROJECT_ROOT%
cd /d "%PROJECT_ROOT%"

echo.
echo [2/4] 检查虚拟环境...
if not exist "venv\Scripts\activate.bat" (
    echo 虚拟环境不存在，正在创建...
    python -m venv venv
    if errorlevel 1 (
        echo 错误: 创建虚拟环境失败，请确保已安装 Python 3.10+
        pause
        exit /b 1
    )
    echo 虚拟环境创建成功
)

echo.
echo [3/4] 激活虚拟环境并检查依赖...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo 错误: 激活虚拟环境失败
    pause
    exit /b 1
)

REM 检查 uvicorn 是否已安装
python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo 检测到依赖未安装，正在安装...
    pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 安装依赖失败
        pause
        exit /b 1
    )
    echo 依赖安装完成
) else (
    echo 依赖检查通过
)

echo.
echo [4/4] 启动应用...
echo 服务地址: http://127.0.0.1:8000
echo 管理面板: http://127.0.0.1:8000/digest/panel
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

REM 启动应用（开发模式，支持热重载）
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause

