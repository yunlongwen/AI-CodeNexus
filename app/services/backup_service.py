"""数据备份服务模块"""

import asyncio
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Tuple

from loguru import logger


class BackupService:
    """数据备份服务"""
    
    def __init__(self):
        """初始化备份服务"""
        self.project_root = Path(__file__).resolve().parent.parent.parent
    
    def _run_git_command(self, cmd: list, env: dict = None) -> Tuple[str, str, int]:
        """
        执行 Git 命令
        
        Args:
            cmd: Git命令列表
            env: 环境变量字典
            
        Returns:
            (stdout, stderr, returncode)
        """
        try:
            cmd_env = os.environ.copy()
            if env:
                cmd_env.update(env)
            # 禁用交互式提示
            cmd_env['GIT_TERMINAL_PROMPT'] = '0'
            
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=60,
                env=cmd_env
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            logger.error("[数据备份] Git 命令执行超时")
            return "", "Timeout", -1
        except Exception as e:
            logger.error(f"[数据备份] Git 命令执行失败: {e}")
            return "", str(e), -1
    
    async def backup_data_to_github(self) -> None:
        """
        定时任务：将 data/ 和 config/ 目录的数据提交到 GitHub
        每天 23:00 执行
        """
        try:
            now = datetime.now()
            logger.info(
                f"[数据备份] 开始执行数据备份任务，时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # 检查是否是 Git 仓库
            git_dir = self.project_root / ".git"
            if not git_dir.exists():
                logger.warning("[数据备份] 当前目录不是 Git 仓库，跳过备份")
                return
            
            # 1. 检查是否有变更
            stdout, stderr, code = await asyncio.to_thread(
                self._run_git_command,
                ["git", "status", "--porcelain", "data/", "config/"]
            )
            
            if code != 0:
                logger.error(f"[数据备份] 检查 Git 状态失败: {stderr}")
                return
            
            if not stdout.strip():
                logger.info("[数据备份] data/ 和 config/ 目录没有变更，跳过提交")
                return
            
            # 2. 添加变更的文件
            logger.info("[数据备份] 添加变更的文件...")
            stdout, stderr, code = await asyncio.to_thread(
                self._run_git_command,
                ["git", "add", "data/", "config/"]
            )
            
            if code != 0:
                logger.error(f"[数据备份] 添加文件失败: {stderr}")
                return
            
            # 3. 提交变更
            commit_message = f"chore: auto backup data and config - {now.strftime('%Y-%m-%d %H:%M:%S')}"
            logger.info(f"[数据备份] 提交变更: {commit_message}")
            stdout, stderr, code = await asyncio.to_thread(
                self._run_git_command,
                ["git", "commit", "-m", commit_message]
            )
            
            if code != 0:
                if "nothing to commit" in stderr.lower() or "nothing to commit" in stdout.lower():
                    logger.info("[数据备份] 没有需要提交的变更")
                    return
                logger.error(f"[数据备份] 提交失败: {stderr}")
                return
            
            logger.info(f"[数据备份] 提交成功: {stdout.strip()}")
            
            # 4. 推送到远程仓库
            logger.info("[数据备份] 推送到远程仓库...")
            # 获取远程仓库 URL，支持 SSH 和 HTTPS
            stdout, stderr, code = await asyncio.to_thread(
                self._run_git_command,
                ["git", "config", "--get", "remote.origin.url"]
            )
            remote_url = stdout.strip() if code == 0 else ""
            if remote_url:
                logger.info(f"[数据备份] 使用远程仓库 URL: {remote_url}")
            
            stdout, stderr, code = await asyncio.to_thread(
                self._run_git_command,
                ["git", "push", "origin", "master"]
            )
            
            if code != 0:
                # 检查是否是 SSH host key 验证错误
                if "Host key verification failed" in stderr or "host key" in stderr.lower():
                    logger.error(f"[数据备份] 推送失败: SSH host key 验证失败")
                    logger.error(f"[数据备份] 错误详情: {stderr}")
                    logger.warning("[数据备份] 提示: 请确保 SSH 密钥已添加到 GitHub，或配置 SSH host key")
                    logger.warning("[数据备份] 解决方案: 访问 https://github.com/settings/keys 添加 SSH 公钥")
                else:
                    logger.error(f"[数据备份] 推送失败: {stderr}")
                
                # 如果推送失败，尝试拉取最新代码后再推送
                logger.info("[数据备份] 尝试拉取最新代码...")
                stdout, stderr, code = await asyncio.to_thread(
                    self._run_git_command,
                    ["git", "pull", "origin", "master", "--rebase"]
                )
                if code == 0:
                    logger.info("[数据备份] 拉取成功，重新推送...")
                    stdout, stderr, code = await asyncio.to_thread(
                        self._run_git_command,
                        ["git", "push", "origin", "master"]
                    )
                    if code == 0:
                        logger.info("[数据备份] 推送成功")
                    else:
                        if "Host key verification failed" in stderr or "host key" in stderr.lower():
                            logger.error(f"[数据备份] 重新推送失败: SSH host key 验证失败")
                            logger.error(f"[数据备份] 错误详情: {stderr}")
                            logger.warning("[数据备份] 提示: 请确保 SSH 密钥已添加到 GitHub")
                        else:
                            logger.error(f"[数据备份] 重新推送失败: {stderr}")
                else:
                    if "Host key verification failed" in stderr or "host key" in stderr.lower():
                        logger.error(f"[数据备份] 拉取失败: SSH host key 验证失败")
                        logger.error(f"[数据备份] 错误详情: {stderr}")
                        logger.warning("[数据备份] 提示: 请确保 SSH 密钥已添加到 GitHub")
                    else:
                        logger.error(f"[数据备份] 拉取失败: {stderr}")
                return
            
            logger.info(f"[数据备份] 推送成功: {stdout.strip()}")
            logger.info("[数据备份] 数据备份任务执行成功")
            
        except Exception as e:
            logger.error(f"[数据备份] 数据备份任务执行失败: {e}", exc_info=True)

