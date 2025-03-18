"""
Document tools for MCP server.
"""

import base64
import json
import logging
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP, Context

from ..services.document_processor import MCPDocumentProcessor


def register_document_tools(mcp: FastMCP, document_processor: MCPDocumentProcessor) -> None:
    """Register document tools.
    
    Args:
        mcp: FastMCP instance
        document_processor: Document processor service
    """
    logger = logging.getLogger("mcp-server-podcast.document-tools")
    
    @mcp.tool()
    async def upload_document(
        document_content: str,
        document_name: str,
        document_type: str = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Upload a document for podcast generation.
        
        Args:
            document_content: Base64-encoded document content
            document_name: Original filename
            document_type: MIME type of the document
            ctx: MCP context for progress reporting
            
        Returns:
            Result with document ID and status
        """
        logger.info(f"Uploading document: {document_name}")
        
        try:
            # Decode base64 content
            try:
                content = base64.b64decode(document_content)
            except Exception as e:
                logger.error(f"Error decoding document content: {str(e)}")
                return {
                    "success": False,
                    "error": {
                        "code": "invalid_document",
                        "message": f"Failed to decode document content: {str(e)}"
                    }
                }
            
            # Process document
            document_id, document_resource = await document_processor.process_document(
                document_content=content,
                document_name=document_name,
                document_type=document_type,
                ctx=ctx
            )
            
            # Return success response
            return {
                "success": True,
                "result": {
                    "document_id": document_id,
                    "status": document_resource.status,
                    "uri": document_resource.uri,
                    "metadata_uri": document_resource.metadata_uri
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "processing_failed",
                    "message": f"Document processing failed: {str(e)}"
                }
            }
    
    @mcp.tool()
    async def extract_text(document_id: str, ctx: Context = None) -> Dict[str, Any]:
        """Extract text from an uploaded document.
        
        Args:
            document_id: ID of the uploaded document
            ctx: MCP context for progress reporting
            
        Returns:
            Extraction result with document ID and status
        """
        logger.info(f"Extracting text from document: {document_id}")
        
        # This is just a convenience method since text extraction
        # is automatically done during upload
        metadata = await document_processor.get_document_metadata(document_id)
        
        if not metadata:
            return {
                "success": False,
                "error": {
                    "code": "document_not_found",
                    "message": f"Document not found: {document_id}"
                }
            }
        
        return {
            "success": True,
            "result": {
                "document_id": document_id,
                "status": metadata.get("status", "unknown"),
                "page_count": metadata.get("page_count", 0),
                "uri": f"document://{document_id}"
            }
        }