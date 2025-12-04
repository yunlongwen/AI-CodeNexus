"""数据库模块"""
# 如果数据库文件存在，导入它们
try:
    from .database import get_db, init_db
    from .models import Article, Candidate, Config, Statistic
    __all__ = ["get_db", "init_db", "Article", "Candidate", "Config", "Statistic"]
except ImportError:
    # 如果文件不存在，提供空导出
    __all__ = []

