# Windows 安装与部署指南

本指南适用于需要在 Windows 10/11 桌面或服务器上运行 `100kwhy_wechat_mp` 项目（特别是开发人员调试、验收或小型部署环境）。  
推荐 **PowerShell 7+**，也可以使用 CMD / Windows Terminal。

## 先决条件

1. 安装 Python 3.11/3.13（官网 https://python.org/downloads/ ），并勾选“Add Python to PATH”。
2. 安装 Git 客户端，或确保你有方式把仓库克隆到本地。
3. 安装 Node.js（用于 Playwright 的浏览器下载），可选但推荐。
4. 预先准备好企业微信机器人 Webhook（可稍后在 `.env` 里配置）。

## 克隆项目 & 环境准备

```powershell
cd xxx
git clone https://github.com/yunlongwen/100kwhy_wechat_mp.git
cd 100kwhy_wechat_mp
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
playwright install
```

> 如果 PowerShell 报 `运行脚本已被禁用`，临时执行 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`，然后再 `Activate.ps1`。

## 配置环境变量

在项目根目录创建 `.env`（或通过系统环境变量）：

```powershell
Set-Content .env @"
WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
# 可选：自定义管理员授权码，默认无密码。
# AICODING_ADMIN_CODE="your-admin-code"
"@"
```

你也可以在 PowerShell 中 `setx WECOM_WEBHOOK "..."` 设置系统范围变量。

## 玩转 Playwright

Playwright 依赖 Chromium，安装后可以直接运行，但首次启动可能需要额外依赖。  
如果提示缺少依赖，可尝试：

```powershell
playwright install-deps
```

（在 Windows 上这个命令通常会提示已安装，可忽略）

## 运行服务

激活虚拟环境后：

```powershell
cd D:\study\github\100kwhy_wechat_mp
.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

需要在生产环境使用 `--proxy-headers`、`--log-config` 等可选参数，也可使用 `python -m uvicorn`。

## 管理面板

- 访问 `http://127.0.0.1:8000/` 查看首页；
- 管理面板在 `http://127.0.0.1:8000/digest/panel`；
- 初次使用面板需要填写管理员授权码；若 `.env` 没配置，输入任意值即可；
- 面板包含：文章添加/抓取、候选池、推送、配置管理（关键词/调度/模板）。

## 其他建议

- 如果想后台运行，可用 `schtasks`、`nssm`、`winser` 等工具注册服务。
- 定期检查 `data/articles/ai_articles.json` 与 `data/articles/ai_candidates.json`，确保推送数据准确。
- 推送失败会在日志（console）打印，可以通过 `>> logs/app.log 2>&1` 重定向。

需要把该部署文档加入目录索引/README？反馈我再做。

