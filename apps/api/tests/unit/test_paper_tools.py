"""Unit tests for paper tool implementations.

Tests cover:
- upload_paper: Upload papers from external sources
- delete_paper: Delete papers (if implemented)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.paper_tools import execute_upload_paper, execute_delete_paper


@pytest.mark.asyncio
class TestUploadPaper:
    """Tests for upload_paper tool."""
    
    async def test_upload_paper_arxiv_url(self):
        """Test uploading from arXiv URL."""
        params = {
            "paper_url": "https://arxiv.org/pdf/2301.12345.pdf",
            "metadata": {
                "title": "Test Paper",
                "authors": ["Author A", "Author B"],
                "year": 2023,
                "source": "arxiv",
                "arxiv_id": "2301.12345"
            }
        }
        
        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.core.storage.ObjectStorage") as mock_storage, \
             patch("app.tools.paper_tools.get_db_connection") as mock_db, \
             patch("app.workers.pdf_coordinator.get_pdf_coordinator") as mock_coordinator, \
             patch("asyncio.create_task"):
            
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.content = b"%PDF-1.4 fake pdf content"
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            # Mock storage
            mock_storage_instance = MagicMock()
            mock_storage_instance.upload_file = AsyncMock()
            mock_storage.return_value = mock_storage_instance
            
            # Mock database
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn
            
            # Mock coordinator
            mock_coord_instance = MagicMock()
            mock_coordinator.return_value = mock_coord_instance
            
            result = await execute_upload_paper(params, user_id="user-123")
            
            assert result["success"] is True
            assert "paper_id" in result["data"]
            assert result["data"]["status"] == "processing"
    
    async def test_upload_paper_semantic_scholar_url(self):
        """Test uploading from Semantic Scholar URL."""
        params = {
            "paper_url": "https://pdfs.semanticscholar.org/abc123.pdf",
            "metadata": {
                "title": "S2 Paper",
                "authors": ["Author C"],
                "year": 2024,
                "source": "semantic_scholar",
                "doi": "10.1234/test"
            }
        }
        
        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.core.storage.ObjectStorage") as mock_storage, \
             patch("app.tools.paper_tools.get_db_connection") as mock_db, \
             patch("app.workers.pdf_coordinator.get_pdf_coordinator") as mock_coordinator, \
             patch("asyncio.create_task"):
            
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.content = b"%PDF-1.4 fake pdf content"
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            # Mock storage
            mock_storage_instance = MagicMock()
            mock_storage_instance.upload_file = AsyncMock()
            mock_storage.return_value = mock_storage_instance
            
            # Mock database
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn
            
            # Mock coordinator
            mock_coord_instance = MagicMock()
            mock_coordinator.return_value = mock_coord_instance
            
            result = await execute_upload_paper(params, user_id="user-123")
            
            assert result["success"] is True
    
    async def test_upload_paper_missing_url(self):
        """Test missing URL returns error."""
        params = {
            "paper_url": None,
            "metadata": {"title": "Test"}
        }
        
        result = await execute_upload_paper(params, user_id="user-123")
        
        assert result["success"] is False
        assert "required" in result["error"].lower()
    
    async def test_upload_paper_empty_url(self):
        """Test empty URL returns error."""
        params = {
            "paper_url": "",
            "metadata": {}
        }
        
        result = await execute_upload_paper(params, user_id="user-123")
        
        assert result["success"] is False
    
    async def test_upload_paper_database_error(self):
        """Test database error handling."""
        params = {
            "paper_url": "https://arxiv.org/pdf/test.pdf",
            "metadata": {}
        }
        
        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.core.storage.ObjectStorage") as mock_storage, \
             patch("app.tools.paper_tools.get_db_connection") as mock_db:
            
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.content = b"%PDF-1.4 fake pdf content"
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            # Mock storage
            mock_storage_instance = MagicMock()
            mock_storage_instance.upload_file = AsyncMock()
            mock_storage.return_value = mock_storage_instance
            
            # Mock database error
            mock_db.return_value.__aenter__.side_effect = Exception("DB error")
            
            result = await execute_upload_paper(params, user_id="user-123")
            
            assert result["success"] is False
    
    async def test_upload_paper_processing_error(self):
        """Test PDF processing error handling."""
        params = {
            "paper_url": "https://arxiv.org/pdf/test.pdf",
            "metadata": {}
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            
            # Mock HTTP error
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=Exception("PDF error"))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            result = await execute_upload_paper(params, user_id="user-123")
            
            assert result["success"] is False
    
    async def test_upload_paper_with_minimal_metadata(self):
        """Test upload with minimal metadata."""
        params = {
            "paper_url": "https://example.com/paper.pdf",
            "metadata": {}
        }
        
        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.core.storage.ObjectStorage") as mock_storage, \
             patch("app.tools.paper_tools.get_db_connection") as mock_db, \
             patch("app.workers.pdf_coordinator.get_pdf_coordinator") as mock_coordinator, \
             patch("asyncio.create_task"):
            
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.content = b"%PDF-1.4 fake pdf content"
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            # Mock storage
            mock_storage_instance = MagicMock()
            mock_storage_instance.upload_file = AsyncMock()
            mock_storage.return_value = mock_storage_instance
            
            # Mock database
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn
            
            # Mock coordinator
            mock_coord_instance = MagicMock()
            mock_coordinator.return_value = mock_coord_instance
            
            result = await execute_upload_paper(params, user_id="user-123")
            
            assert result["success"] is True


@pytest.mark.asyncio
class TestDeletePaper:
    """Tests for delete_paper tool."""
    
    async def test_delete_paper_success(self):
        """Test successful paper deletion."""
        params = {"paper_id": "paper-123"}
        
        with patch("app.tools.paper_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value="UPDATE 1")
            mock_db.return_value.__aenter__.return_value = mock_conn
            
            result = await execute_delete_paper(params, user_id="user-123")
            
            assert result["success"] is True
            assert result["data"]["deleted"] is True
    
    async def test_delete_paper_not_found(self):
        """Test deleting non-existent paper."""
        params = {"paper_id": "non-existent"}
        
        with patch("app.tools.paper_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value="UPDATE 0")
            mock_db.return_value.__aenter__.return_value = mock_conn
            
            result = await execute_delete_paper(params, user_id="user-123")
            
            assert result["success"] is False
            assert "not found" in result["error"].lower()
    
    async def test_delete_paper_missing_id(self):
        """Test missing paper_id returns error."""
        params = {"paper_id": None}
        
        result = await execute_delete_paper(params, user_id="user-123")
        
        assert result["success"] is False
        assert "required" in result["error"].lower()