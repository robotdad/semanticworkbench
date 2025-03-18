"""
Document processor service for MCP server.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

from mcp.server.fastmcp import Context

from ..config import Settings
from ..models.domain import ExtractTextResult
from ..models.resource import DocumentResource
from ..utils.progress_reporter import ProgressReporter
from ..utils.resource_id_manager import ResourceIDManager


class AzureDocumentProcessor:
    """Implementation of DocumentProcessor using Azure Document Intelligence."""
    
    def __init__(self, endpoint: str, api_key: str, model_id: str, use_managed_identity: bool = False):
        """Initialize the document processor.
        
        Args:
            endpoint: Azure Document Intelligence endpoint
            api_key: Azure Document Intelligence API key
            model_id: Azure Document Intelligence model ID
            use_managed_identity: Whether to use managed identity for authentication
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.model_id = model_id
        self.use_managed_identity = use_managed_identity
        self.logger = logging.getLogger("mcp-server-podcast.azure-document-processor")
        
        # Initialize the client
        if not use_managed_identity:
            self.credential = AzureKeyCredential(api_key)
        else:
            # In a future version, we might need to add DefaultAzureCredential from azure-identity
            self.credential = None
            raise NotImplementedError("Managed identity authentication is not yet implemented")
            
        self.client = DocumentIntelligenceClient(endpoint=endpoint, credential=self.credential)
        
    async def extract_text(self, document_path: Path) -> ExtractTextResult:
        """Extract text from a document.
        
        Args:
            document_path: Path to the document
            
        Returns:
            Result of text extraction
        """
        if not document_path.exists():
            return ExtractTextResult(
                document_id=str(document_path.stem),
                original_filename=document_path.name,
                extracted_text="",
                page_count=0,
                success=False,
                error_message=f"Document not found: {document_path}"
            )
        
        try:
            # Read document content
            with open(document_path, "rb") as f:
                document_content = f.read()
                
            # Process the document
            self.logger.info(f"Extracting text from {document_path}")
            
            # Create an AnalyzeDocumentRequest
            poller = self.client.begin_analyze_document(
                model_id=self.model_id,
                analyze_request=AnalyzeDocumentRequest(
                    base64_source=base64.b64encode(document_content).decode()
                )
            )
            
            # Get the result
            result = poller.result()
            
            # Extract text from the result
            extracted_text = ""
            page_count = 0
            
            if hasattr(result, "pages"):
                page_count = len(result.pages)
                
                # Extract text from pages
                for page in result.pages:
                    if hasattr(page, "lines"):
                        for line in page.lines:
                            extracted_text += line.content + "\n"
                    extracted_text += "\n"
            
            # Create the result
            return ExtractTextResult(
                document_id=str(document_path.stem),
                original_filename=document_path.name,
                extracted_text=extracted_text.strip(),
                page_count=page_count,
                success=True,
                metadata={"mime_type": self._determine_mime_type(document_path)}
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting text from {document_path}: {str(e)}")
            return ExtractTextResult(
                document_id=str(document_path.stem),
                original_filename=document_path.name,
                extracted_text="",
                page_count=0,
                success=False,
                error_message=str(e)
            )
    
    async def extract_text_batch(self, document_paths: List[Path]) -> List[ExtractTextResult]:
        """Extract text from multiple documents.
        
        Args:
            document_paths: Paths to the documents
            
        Returns:
            Results of text extraction for each document
        """
        results = []
        for path in document_paths:
            result = await self.extract_text(path)
            results.append(result)
        return results
    
    def _determine_mime_type(self, file_path: Path) -> str:
        """Determine MIME type based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type string
        """
        extension = file_path.suffix.lower()
        
        # Map common extensions to MIME types
        mime_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".rtf": "application/rtf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".bmp": "image/bmp"
        }
        
        return mime_types.get(extension, "application/octet-stream")


class MCPDocumentProcessor:
    """MCP wrapper for the AzureDocumentProcessor."""
    
    def __init__(self, config: Settings, resource_id_manager: ResourceIDManager):
        """Initialize the MCP document processor.
        
        Args:
            config: Application configuration
            resource_id_manager: Resource ID manager
        """
        # Initialize the Azure document processor
        self.document_processor = AzureDocumentProcessor(
            endpoint=config.document_intelligence_endpoint,
            api_key=config.document_intelligence_api_key,
            model_id=config.document_intelligence_model_id,
            use_managed_identity=config.use_managed_identity
        )
        
        # Set up storage paths
        self.storage_path = config.mcp_storage_path
        self.document_storage_path = self.storage_path / "documents"
        self.document_storage_path.mkdir(parents=True, exist_ok=True)
        
        self.resource_id_manager = resource_id_manager
        self.logger = logging.getLogger("mcp-server-podcast.document-processor")
    
    async def process_document(self, 
                               document_content: bytes, 
                               document_name: str, 
                               document_type: str = None,
                               ctx: Optional[Context] = None) -> Tuple[str, DocumentResource]:
        """Process document content and return a document ID and resource.
        
        Args:
            document_content: Raw document content
            document_name: Original name of the document
            document_type: MIME type of the document
            ctx: MCP context for progress reporting
            
        Returns:
            Tuple of document ID and document resource
        """
        progress = ProgressReporter(ctx)
        await progress.report_progress(0, "Starting document processing...")
        
        # Generate a unique document ID
        document_id = self.resource_id_manager.generate_id("document")
        self.logger.info(f"Processing document {document_name} with ID {document_id}")
        
        # Store the document
        document_path = await self._store_document(document_content, document_name, document_id)
        await progress.report_progress(20, "Document stored, extracting text...")
        
        # Process the document
        result = await self.document_processor.extract_text(document_path)
        
        # Update the document ID in the result
        result.document_id = document_id
        
        # Store the result
        document_resource = await self._store_extraction_result(document_id, document_name, result, document_type)
        await progress.report_progress(100, "Document processing complete")
        
        return document_id, document_resource
    
    async def _store_document(self, content: bytes, name: str, document_id: str) -> Path:
        """Store document content.
        
        Args:
            content: Raw document content
            name: Original document name
            document_id: Unique document ID
            
        Returns:
            Path to the stored document
        """
        # Create storage directory
        document_dir = self.document_storage_path / document_id
        document_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension
        _, extension = os.path.splitext(name)
        if not extension:
            extension = ".bin"  # Default extension if none provided
        
        # Create file path
        document_path = document_dir / f"original{extension}"
        
        # Write content to file
        with open(document_path, "wb") as f:
            f.write(content)
        
        return document_path
    
    async def _store_extraction_result(self, 
                                       document_id: str, 
                                       document_name: str,
                                       result: ExtractTextResult,
                                       document_type: str = None) -> DocumentResource:
        """Store extraction result for resource access.
        
        Args:
            document_id: Unique document ID
            document_name: Original document name
            result: Result of text extraction
            document_type: MIME type of the document
            
        Returns:
            Document resource object
        """
        # Create paths
        document_dir = self.document_storage_path / document_id
        content_path = document_dir / "content.txt"
        metadata_path = document_dir / "metadata.json"
        
        # Determine document type if not provided
        if not document_type:
            document_type = result.metadata.get("mime_type", "application/octet-stream")
        
        # Write content file
        content_path.write_text(result.extracted_text)
        
        # Create metadata
        metadata = {
            "document_id": document_id,
            "original_filename": document_name,
            "page_count": result.page_count,
            "success": result.success,
            "error_message": result.error_message,
            "created_at": os.path.getmtime(content_path),
            "mime_type": document_type
        }
        
        # Write metadata file
        metadata_path.write_text(json.dumps(metadata, indent=2))
        
        # Create document resource
        document_resource = DocumentResource(
            document_id=document_id,
            original_filename=document_name,
            content_path=content_path,
            metadata_path=metadata_path,
            document_type=document_type,
            status="processed" if result.success else "error",
            metadata=metadata
        )
        
        # Add to resource manager
        self.resource_id_manager.add_mapping(
            resource_type="document",
            resource_id=document_id,
            file_path=content_path,
            metadata={
                "original_filename": document_name,
                "page_count": result.page_count,
                "metadata_path": str(metadata_path),
                "content_path": str(content_path),
                "status": "processed" if result.success else "error",
                "mime_type": document_type
            }
        )
        
        return document_resource
    
    async def get_document_content(self, document_id: str) -> Optional[str]:
        """Get document content for a given document ID.
        
        Args:
            document_id: Unique document ID
            
        Returns:
            Extracted text content, or None if not found
        """
        file_path = self.resource_id_manager.get_file_path("document", document_id)
        if not file_path or not file_path.exists():
            return None
            
        return file_path.read_text()
    
    async def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata for a given document ID.
        
        Args:
            document_id: Unique document ID
            
        Returns:
            Metadata dictionary, or None if not found
        """
        return self.resource_id_manager.get_metadata("document", document_id)