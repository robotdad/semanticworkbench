"""
Tests for the document processor service.
"""

import base64
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_podcast.models.domain import ExtractTextResult
from mcp_server_podcast.services.document_processor import AzureDocumentProcessor, MCPDocumentProcessor
from mcp_server_podcast.utils.resource_id_manager import ResourceIDManager


class TestAzureDocumentProcessor:
    """Tests for the AzureDocumentProcessor class."""
    
    @pytest.fixture
    def mock_document_intelligence_client(self):
        """Mock for the document intelligence client."""
        with patch("mcp_server_podcast.services.document_processor.DocumentIntelligenceClient") as mock_client:
            # Set up the mock poller
            mock_poller = MagicMock()
            mock_result = MagicMock()
            
            # Set up mock pages with lines
            mock_line1 = MagicMock()
            mock_line1.content = "Line 1 content"
            mock_line2 = MagicMock()
            mock_line2.content = "Line 2 content"
            
            mock_page1 = MagicMock()
            mock_page1.lines = [mock_line1, mock_line2]
            
            mock_page2 = MagicMock()
            mock_page2.lines = [mock_line1]
            
            mock_result.pages = [mock_page1, mock_page2]
            mock_poller.result.return_value = mock_result
            
            # Set up the begin_analyze_document method
            mock_client.return_value.begin_analyze_document.return_value = mock_poller
            
            yield mock_client
    
    @pytest.fixture
    def processor(self, mock_document_intelligence_client):
        """Create a document processor instance."""
        return AzureDocumentProcessor(
            endpoint="https://test-endpoint",
            api_key="test-api-key",
            model_id="test-model-id"
        )
    
    @pytest.mark.asyncio
    async def test_extract_text(self, processor):
        """Test extracting text from a document."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"Test document content")
            temp_path = Path(temp_file.name)
        
        try:
            # Extract text
            result = await processor.extract_text(temp_path)
            
            # Check result
            assert isinstance(result, ExtractTextResult)
            assert result.document_id == temp_path.stem
            assert result.original_filename == temp_path.name
            assert result.extracted_text == "Line 1 content\nLine 2 content\n\nLine 1 content"
            assert result.page_count == 2
            assert result.success is True
            assert result.metadata["mime_type"] == "application/pdf"
        
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_extract_text_file_not_found(self, processor):
        """Test extracting text from a non-existent file."""
        # Create a path that doesn't exist
        non_existent_path = Path("/tmp/non_existent_file.pdf")
        
        # Extract text
        result = await processor.extract_text(non_existent_path)
        
        # Check result
        assert isinstance(result, ExtractTextResult)
        assert result.document_id == non_existent_path.stem
        assert result.original_filename == non_existent_path.name
        assert result.extracted_text == ""
        assert result.page_count == 0
        assert result.success is False
        assert "Document not found" in result.error_message


class TestMCPDocumentProcessor:
    """Tests for the MCPDocumentProcessor class."""
    
    @pytest.fixture
    def mock_azure_document_processor(self):
        """Mock for the Azure document processor."""
        with patch("mcp_server_podcast.services.document_processor.AzureDocumentProcessor") as mock_processor:
            # Set up the extract_text method
            mock_processor.return_value.extract_text = AsyncMock()
            mock_processor.return_value.extract_text.return_value = ExtractTextResult(
                document_id="test-id",
                original_filename="test.pdf",
                extracted_text="Extracted test content",
                page_count=2,
                success=True,
                metadata={"mime_type": "application/pdf"}
            )
            
            yield mock_processor
    
    @pytest.fixture
    def mock_config(self):
        """Mock for the config."""
        mock_config = MagicMock()
        mock_config.mcp_storage_path = Path("/tmp/mcp-test")
        mock_config.document_intelligence_endpoint = "https://test-endpoint"
        mock_config.document_intelligence_api_key = "test-api-key"
        mock_config.document_intelligence_model_id = "test-model-id"
        mock_config.use_managed_identity = False
        return mock_config
    
    @pytest.fixture
    def mock_resource_id_manager(self):
        """Mock for the resource ID manager."""
        mock_manager = MagicMock(spec=ResourceIDManager)
        mock_manager.generate_id.return_value = "test-doc-id"
        return mock_manager
    
    @pytest.fixture
    def processor(self, mock_config, mock_resource_id_manager, mock_azure_document_processor):
        """Create a document processor instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.mcp_storage_path = Path(temp_dir)
            return MCPDocumentProcessor(mock_config, mock_resource_id_manager)
    
    @pytest.mark.asyncio
    async def test_process_document(self, processor):
        """Test processing a document."""
        # Create mock context
        mock_ctx = MagicMock()
        
        # Process document
        document_id, document_resource = await processor.process_document(
            document_content=b"Test document content",
            document_name="test.pdf",
            document_type="application/pdf",
            ctx=mock_ctx
        )
        
        # Check results
        assert document_id == "test-doc-id"
        assert document_resource.document_id == "test-doc-id"
        assert document_resource.original_filename == "test.pdf"
        assert document_resource.document_type == "application/pdf"
        assert document_resource.status == "processed"
        
        # Check that resource_id_manager was called
        processor.resource_id_manager.add_mapping.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_document_content(self, processor):
        """Test getting document content."""
        # Mock get_file_path
        file_path = processor.document_storage_path / "test-doc-id" / "content.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("Test content")
        processor.resource_id_manager.get_file_path.return_value = file_path
        
        # Get content
        content = await processor.get_document_content("test-doc-id")
        
        # Check result
        assert content == "Test content"
        
    @pytest.mark.asyncio
    async def test_get_document_metadata(self, processor):
        """Test getting document metadata."""
        # Mock get_metadata
        metadata = {
            "document_id": "test-doc-id",
            "original_filename": "test.pdf",
            "page_count": 2,
            "status": "processed"
        }
        processor.resource_id_manager.get_metadata.return_value = metadata
        
        # Get metadata
        result = await processor.get_document_metadata("test-doc-id")
        
        # Check result
        assert result == metadata