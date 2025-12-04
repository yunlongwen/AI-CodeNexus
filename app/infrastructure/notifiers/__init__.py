"""通知服务模块"""
from .wecom import build_wecom_digest_markdown, send_markdown_to_wecom
from .wechat_mp import WeChatMPClient

__all__ = ["build_wecom_digest_markdown", "send_markdown_to_wecom", "WeChatMPClient"]
