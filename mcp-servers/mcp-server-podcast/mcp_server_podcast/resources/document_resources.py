"""
Document resource handlers for MCP server.
"""

import json
import logging
from typing import Tuple, Dict, Any

from mcp.server.fastmcp import FastMCP

from ..models.resource import DOCUMENT_SCHEME, ResourceResponse
from ..services.document_processor import MCPDocumentProcessor


def register_document_resources(mcp: FastMCP, document_processor: MCPDocumentProcessor) -> None:
    """Register document resource handlers.
    
    Args:
        mcp: FastMCP instance
        document_processor: Document processor service
    """
    logger = logging.getLogger("mcp-server-podcast.document-resources")
    
    @mcp.resource(f"{DOCUMENT_SCHEME}{{document_id}}")
    async def get_document(document_id: str) -> Tuple[str, str]:
        """Get document content for a document ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Tuple of content and MIME type
        """
        logger.info(f"Getting document content for {document_id}")
        content = await document_processor.get_document_content(document_id)
        
        if content is None:
            response = ResourceResponse(
                content=f"Document not found: {document_id}",
                mime_type="text/plain"
            )
        else:
            response = ResourceResponse(
                content=content,
                mime_type="text/plain"
            )
            
        return response.as_tuple()
    
    @mcp.resource(f"{DOCUMENT_SCHEME}{{document_id}}/metadata")
    async def get_document_metadata(document_id: str) -> Tuple[str, str]:
        """Get document metadata for a document ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Tuple of metadata JSON and MIME type
        """
        logger.info(f"Getting document metadata for {document_id}")
        metadata = await document_processor.get_document_metadata(document_id)
        
        if metadata is None:
            error_response = {
                "error": {
                    "code": "document_not_found",
                    "message": f"Document not found: {document_id}"
                }
            }
            response = ResourceResponse(
                content=json.dumps(error_response),
                mime_type="application/json"
            )
        else:
            # Format metadata for response
            formatted_metadata = _format_document_metadata(document_id, metadata)
            response = ResourceResponse(
                content=json.dumps(formatted_metadata, indent=2),
                mime_type="application/json"
            )
            
        return response.as_tuple()
    
    
def _format_document_metadata(document_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Format document metadata for response.
    
    Args:
        document_id: Document ID
        metadata: Raw metadata
        
    Returns:
        Formatted metadata
    """
    # Extract relevant fields and ensure proper formatting
    return {
        "document_id": document_id,
        "original_filename": metadata.get("original_filename", "unknown"),
        "page_count": metadata.get("page_count", 0),
        "status": metadata.get("status", "unknown"),
        "mime_type": metadata.get("mime_type", "application/octet-stream"),
        "created_at": metadata.get("created_at", 0),
        "success": metadata.get("success", False),
        "error_message": metadata.get("error_message", None)
    }