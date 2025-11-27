"""归档功能测试"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_loader import DataLoader


class TestArchiveFeature:
    """归档功能测试类"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_admin_code(self, monkeypatch):
        """模拟管理员授权码"""
        monkeypatch.setenv("AICODING_ADMIN_CODE", "test_admin_code")
    
    def test_list_articles_with_archive_status(self, tmp_path, client, mock_admin_code):
        """测试文章列表API返回归档状态"""
        # 创建临时文章池文件
        articles_dir = tmp_path / "data" / "articles"
        articles_dir.mkdir(parents=True)
        
        article_pool_file = articles_dir / "ai_articles.json"
        article_pool_data = [
            {
                "title": "文章1",
                "url": "https://example.com/article1",
                "source": "来源1",
                "summary": "摘要1"
            },
            {
                "title": "文章2",
                "url": "https://example.com/article2",
                "source": "来源2",
                "summary": "摘要2"
            }
        ]
        with open(article_pool_file, 'w', encoding='utf-8') as f:
            json.dump(article_pool_data, f, ensure_ascii=False)
        
        # 创建归档文件
        archived_file = articles_dir / "programming.json"
        archived_data = [
            {
                "id": 1,
                "title": "已归档文章",
                "url": "https://example.com/article1",  # 与文章池中的文章1相同
                "source": "来源",
                "summary": "摘要",
                "archived_at": "2025-01-01T00:00:00Z"
            }
        ]
        with open(archived_file, 'w', encoding='utf-8') as f:
            json.dump(archived_data, f, ensure_ascii=False)
        
        # Mock文章池路径和归档检查
        with patch('app.sources.ai_articles._articles_path', return_value=article_pool_file):
            with patch('app.services.data_loader.ARTICLES_DIR', articles_dir):
                response = client.get(
                    "/digest/articles",
                    headers={"X-Admin-Code": "test_admin_code"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] == True
                assert len(data["articles"]) == 2
                
                # 检查归档状态
                article1 = next((a for a in data["articles"] if a["url"] == "https://example.com/article1"), None)
                article2 = next((a for a in data["articles"] if a["url"] == "https://example.com/article2"), None)
                
                assert article1 is not None
                assert article1["is_archived"] == True  # 应该已归档
                assert article2 is not None
                assert article2["is_archived"] == False  # 应该未归档
    
    def test_archive_article_from_pool(self, tmp_path, client, mock_admin_code):
        """测试从文章池归档文章"""
        # 创建临时文件
        articles_dir = tmp_path / "data" / "articles"
        articles_dir.mkdir(parents=True)
        
        # 文章池
        article_pool_file = articles_dir / "ai_articles.json"
        article_pool_data = [
            {
                "title": "测试文章",
                "url": "https://example.com/test",
                "source": "来源",
                "summary": "摘要"
            }
        ]
        with open(article_pool_file, 'w', encoding='utf-8') as f:
            json.dump(article_pool_data, f, ensure_ascii=False)
        
        # 归档文件（初始为空）
        archived_file = articles_dir / "programming.json"
        with open(archived_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)
        
        # Mock路径
        with patch('app.sources.ai_articles._articles_path', return_value=article_pool_file):
            with patch('app.services.data_loader.ARTICLES_DIR', articles_dir):
                response = client.post(
                    "/digest/archive-article",
                    headers={"X-Admin-Code": "test_admin_code"},
                    json={
                        "url": "https://example.com/test",
                        "category": "programming",
                        "tool_tags": []
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] == True
                
                # 验证文章已归档
                assert DataLoader.is_article_archived("https://example.com/test") == True
    
    def test_archive_article_already_archived(self, tmp_path, client, mock_admin_code):
        """测试归档已归档的文章"""
        articles_dir = tmp_path / "data" / "articles"
        articles_dir.mkdir(parents=True)
        
        # 文章池
        article_pool_file = articles_dir / "ai_articles.json"
        article_pool_data = [
            {
                "title": "测试文章",
                "url": "https://example.com/test",
                "source": "来源",
                "summary": "摘要"
            }
        ]
        with open(article_pool_file, 'w', encoding='utf-8') as f:
            json.dump(article_pool_data, f, ensure_ascii=False)
        
        # 归档文件（已存在）
        archived_file = articles_dir / "programming.json"
        archived_data = [
            {
                "id": 1,
                "title": "已归档",
                "url": "https://example.com/test",
                "source": "来源",
                "summary": "摘要",
                "archived_at": "2025-01-01T00:00:00Z"
            }
        ]
        with open(archived_file, 'w', encoding='utf-8') as f:
            json.dump(archived_data, f, ensure_ascii=False)
        
        with patch('app.sources.ai_articles._articles_path', return_value=article_pool_file):
            with patch('app.services.data_loader.ARTICLES_DIR', articles_dir):
                response = client.post(
                    "/digest/archive-article",
                    headers={"X-Admin-Code": "test_admin_code"},
                    json={
                        "url": "https://example.com/test",
                        "category": "programming",
                        "tool_tags": []
                    }
                )
                
                assert response.status_code == 400
                data = response.json()
                assert "已归档" in data["detail"]

