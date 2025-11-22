from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ArticleItem:
    title: str
    url: str
    source: str  # 公众号名 / 网站名
    category: str  # ai_news / team_management / other
    pub_time: Optional[datetime] = None
    summary: Optional[str] = None  # 1-2 句摘要
    comment: Optional[str] = None  # 你的点评


@dataclass
class DailyDigest:
    date: datetime
    theme: str  # 今日主题一句话
    items: List[ArticleItem]
    extra_note: Optional[str] = None  # 结尾备注 / 招呼


