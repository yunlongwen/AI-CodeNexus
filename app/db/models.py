"""数据库模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Article(Base):
    """文章表"""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False, index=True)
    source = Column(String(200))
    summary = Column(Text)
    score = Column(Float, default=0.0, index=True)  # 热度分
    published_time = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_promoted = Column(Boolean, default=False)  # 是否已提升到正式池
    notes = Column(Text)  # 批注/备注


class Candidate(Base):
    """候选文章表"""
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False, index=True)
    source = Column(String(200))
    summary = Column(Text)
    keyword = Column(String(200), index=True)  # 关键词
    score = Column(Float, default=0.0, index=True)  # 热度分
    published_time = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    notes = Column(Text)  # 批注/备注
    is_ignored = Column(Boolean, default=False)  # 是否已忽略


class Config(Base):
    """配置表"""
    __tablename__ = "configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(JSON)  # 使用 JSON 存储配置值
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Statistic(Base):
    """统计数据表"""
    __tablename__ = "statistics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    keyword = Column(String(200), index=True)
    crawled_count = Column(Integer, default=0)  # 抓取数量
    promoted_count = Column(Integer, default=0)  # 采纳数量
    ignored_count = Column(Integer, default=0)  # 忽略数量

