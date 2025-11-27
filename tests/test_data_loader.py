"""数据加载器测试"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.services.data_loader import DataLoader


class TestDataLoader:
    """数据加载器测试类"""
    
    def test_is_article_archived_excludes_article_pool(self, tmp_path):
        """测试归档状态检查排除文章池文件"""
        # 创建临时目录结构
        articles_dir = tmp_path / "articles"
        articles_dir.mkdir()
        
        # 创建文章池文件（不应该被检查）
        article_pool_file = articles_dir / "ai_articles.json"
        article_pool_data = [
            {
                "title": "测试文章1",
                "url": "https://example.com/article1",
                "source": "测试来源",
                "summary": "测试摘要"
            }
        ]
        with open(article_pool_file, 'w', encoding='utf-8') as f:
            json.dump(article_pool_data, f, ensure_ascii=False)
        
        # 创建归档文件（应该被检查）
        archived_file = articles_dir / "programming.json"
        archived_data = [
            {
                "id": 1,
                "title": "已归档文章",
                "url": "https://example.com/archived",
                "source": "来源",
                "summary": "摘要",
                "archived_at": "2025-01-01T00:00:00Z"
            }
        ]
        with open(archived_file, 'w', encoding='utf-8') as f:
            json.dump(archived_data, f, ensure_ascii=False)
        
        # 创建候选池文件（不应该被检查）
        candidate_file = articles_dir / "ai_candidates.json"
        candidate_data = [
            {
                "title": "候选文章",
                "url": "https://example.com/candidate",
                "source": "来源",
                "summary": "摘要"
            }
        ]
        with open(candidate_file, 'w', encoding='utf-8') as f:
            json.dump(candidate_data, f, ensure_ascii=False)
        
        # 使用patch替换ARTICLES_DIR
        with patch('app.services.data_loader.ARTICLES_DIR', articles_dir):
            # 测试：文章池中的文章不应该被识别为已归档
            assert DataLoader.is_article_archived("https://example.com/article1") == False
            
            # 测试：归档文件中的文章应该被识别为已归档
            assert DataLoader.is_article_archived("https://example.com/archived") == True
            
            # 测试：候选池中的文章不应该被识别为已归档
            assert DataLoader.is_article_archived("https://example.com/candidate") == False
    
    def test_is_article_archived_exact_match(self, tmp_path):
        """测试归档状态检查的精确匹配"""
        articles_dir = tmp_path / "articles"
        articles_dir.mkdir()
        
        archived_file = articles_dir / "programming.json"
        archived_data = [
            {
                "id": 1,
                "title": "测试文章",
                "url": "https://example.com/test",
                "source": "来源",
                "summary": "摘要",
                "archived_at": "2025-01-01T00:00:00Z"
            }
        ]
        with open(archived_file, 'w', encoding='utf-8') as f:
            json.dump(archived_data, f, ensure_ascii=False)
        
        with patch('app.services.data_loader.ARTICLES_DIR', articles_dir):
            # 精确匹配
            assert DataLoader.is_article_archived("https://example.com/test") == True
            # 不匹配
            assert DataLoader.is_article_archived("https://example.com/other") == False
    
    def test_is_article_archived_empty_url(self):
        """测试空URL的处理"""
        assert DataLoader.is_article_archived("") == False
        assert DataLoader.is_article_archived(None) == False
    
    def test_archive_article_to_category(self, tmp_path):
        """测试归档文章到分类"""
        articles_dir = tmp_path / "articles"
        articles_dir.mkdir()
        
        category_file = articles_dir / "programming.json"
        # 初始为空列表
        with open(category_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)
        
        article = {
            "title": "测试文章",
            "url": "https://example.com/test",
            "source": "来源",
            "summary": "摘要"
        }
        
        with patch('app.services.data_loader.ARTICLES_DIR', articles_dir):
            result = DataLoader.archive_article_to_category(article, "programming", [])
            assert result == True
            
            # 验证文件已更新
            with open(category_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert len(data) == 1
                assert data[0]["url"] == "https://example.com/test"
                assert data[0]["category"] == "programming"
                assert "archived_at" in data[0]
    
    def test_archive_article_duplicate(self, tmp_path):
        """测试归档重复文章"""
        articles_dir = tmp_path / "articles"
        articles_dir.mkdir()
        
        category_file = articles_dir / "programming.json"
        existing_data = [
            {
                "id": 1,
                "title": "已存在",
                "url": "https://example.com/test",
                "source": "来源",
                "summary": "摘要",
                "archived_at": "2025-01-01T00:00:00Z"
            }
        ]
        with open(category_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False)
        
        article = {
            "title": "新文章",
            "url": "https://example.com/test",  # 相同的URL
            "source": "来源",
            "summary": "摘要"
        }
        
        with patch('app.services.data_loader.ARTICLES_DIR', articles_dir):
            result = DataLoader.archive_article_to_category(article, "programming", [])
            assert result == False  # 应该返回False，因为已存在

