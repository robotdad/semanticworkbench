"""
Podcast resource handlers for MCP server.
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

from ..models.resource import PODCAST_SCHEME, ResourceResponse
from ..utils.resource_id_manager import ResourceIDManager


class PodcastResourceHandler:
    """Handlers for podcast resources."""
    
    def __init__(self, resource_id_manager: ResourceIDManager, storage_path: Path):
        """Initialize the podcast resource handler.
        
        Args:
            resource_id_manager: Resource ID manager
            storage_path: Base storage path
        """
        self.resource_id_manager = resource_id_manager
        self.storage_path = storage_path
        self.podcast_storage_path = storage_path / "podcasts"
        self.logger = logging.getLogger("mcp-server-podcast.podcast-resources")
        
    async def get_podcast_script(self, podcast_id: str) -> Optional[str]:
        """Get the podcast script.
        
        Args:
            podcast_id: Podcast ID
            
        Returns:
            Podcast script or None if not found
        """
        # Try to get the script path from the resource manager
        metadata = self.resource_id_manager.get_metadata("podcast", podcast_id) or {}
        script_path = metadata.get("script_path")
        
        if script_path:
            script_path = Path(script_path)
            if script_path.exists():
                return script_path.read_text()
        
        # Try the default location
        default_path = self.podcast_storage_path / podcast_id / "script.txt"
        if default_path.exists():
            return default_path.read_text()
            
        return None
        
    async def get_podcast_segments(self, podcast_id: str) -> Optional[Dict[str, Any]]:
        """Get the podcast segments.
        
        Args:
            podcast_id: Podcast ID
            
        Returns:
            Podcast segments or None if not found
        """
        # Try to get the segments path from the resource manager
        metadata = self.resource_id_manager.get_metadata("podcast", podcast_id) or {}
        
        # First try the composed segments
        segments_path = metadata.get("composed_segments_path")
        
        if segments_path:
            segments_path = Path(segments_path)
            if segments_path.exists():
                try:
                    with open(segments_path, "r") as f:
                        return json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
        
        # Then try the raw segments
        segments_path = metadata.get("segments_path")
        
        if segments_path:
            segments_path = Path(segments_path)
            if segments_path.exists():
                try:
                    with open(segments_path, "r") as f:
                        return json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
        
        # Try the default locations
        default_composed_path = self.podcast_storage_path / podcast_id / "composed_segments.json"
        if default_composed_path.exists():
            try:
                with open(default_composed_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
                
        default_segments_path = self.podcast_storage_path / podcast_id / "segments.json"
        if default_segments_path.exists():
            try:
                with open(default_segments_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
                
        return None
        
    async def get_podcast_metadata(self, podcast_id: str) -> Optional[Dict[str, Any]]:
        """Get the podcast metadata.
        
        Args:
            podcast_id: Podcast ID
            
        Returns:
            Podcast metadata or None if not found
        """
        # Try to get metadata from the resource manager
        metadata = self.resource_id_manager.get_metadata("podcast", podcast_id)
        
        if metadata:
            return metadata
            
        # Try the default location
        metadata_path = self.podcast_storage_path / podcast_id / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
                
        return None
        

def register_podcast_resources(mcp: FastMCP, resource_id_manager: ResourceIDManager, storage_path: Path) -> None:
    """Register podcast resource handlers.
    
    Args:
        mcp: FastMCP instance
        resource_id_manager: Resource ID manager
        storage_path: Base storage path
    """
    # Create podcast resource handler
    handler = PodcastResourceHandler(resource_id_manager, storage_path)
    logger = logging.getLogger("mcp-server-podcast.podcast-resources")
    
    @mcp.resource(f"{PODCAST_SCHEME}{{podcast_id}}/script")
    async def get_podcast_script(podcast_id: str) -> Tuple[str, str]:
        """Get podcast script for a podcast ID.
        
        Args:
            podcast_id: Podcast ID
            
        Returns:
            Tuple of content and MIME type
        """
        logger.info(f"Getting podcast script for {podcast_id}")
        content = await handler.get_podcast_script(podcast_id)
        
        if content is None:
            response = ResourceResponse(
                content=f"Podcast script not found: {podcast_id}",
                mime_type="text/plain"
            )
        else:
            response = ResourceResponse(
                content=content,
                mime_type="text/plain"
            )
            
        return response.as_tuple()
    
    @mcp.resource(f"{PODCAST_SCHEME}{{podcast_id}}/segments")
    async def get_podcast_segments(podcast_id: str) -> Tuple[str, str]:
        """Get podcast segments for a podcast ID.
        
        Args:
            podcast_id: Podcast ID
            
        Returns:
            Tuple of JSON content and MIME type
        """
        logger.info(f"Getting podcast segments for {podcast_id}")
        segments = await handler.get_podcast_segments(podcast_id)
        
        if segments is None:
            error_response = {
                "error": {
                    "code": "podcast_not_found",
                    "message": f"Podcast segments not found: {podcast_id}"
                }
            }
            response = ResourceResponse(
                content=json.dumps(error_response),
                mime_type="application/json"
            )
        else:
            response = ResourceResponse(
                content=json.dumps(segments, indent=2),
                mime_type="application/json"
            )
            
        return response.as_tuple()
    
    @mcp.resource(f"{PODCAST_SCHEME}{{podcast_id}}/metadata")
    async def get_podcast_metadata(podcast_id: str) -> Tuple[str, str]:
        """Get podcast metadata for a podcast ID.
        
        Args:
            podcast_id: Podcast ID
            
        Returns:
            Tuple of JSON content and MIME type
        """
        logger.info(f"Getting podcast metadata for {podcast_id}")
        metadata = await handler.get_podcast_metadata(podcast_id)
        
        if metadata is None:
            error_response = {
                "error": {
                    "code": "podcast_not_found",
                    "message": f"Podcast metadata not found: {podcast_id}"
                }
            }
            response = ResourceResponse(
                content=json.dumps(error_response),
                mime_type="application/json"
            )
        else:
            # Format metadata for response
            formatted_metadata = _format_podcast_metadata(podcast_id, metadata)
            response = ResourceResponse(
                content=json.dumps(formatted_metadata, indent=2),
                mime_type="application/json"
            )
            
        return response.as_tuple()


def _format_podcast_metadata(podcast_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Format podcast metadata for response.
    
    Args:
        podcast_id: Podcast ID
        metadata: Raw metadata
        
    Returns:
        Formatted metadata
    """
    # Extract relevant fields and ensure proper formatting
    return {
        "podcast_id": podcast_id,
        "title": metadata.get("title", f"Podcast {podcast_id}"),
        "status": metadata.get("status", "unknown"),
        "segment_count": metadata.get("segment_count", 0),
        "created_at": metadata.get("created_at", 0),
        "document_ids": metadata.get("document_ids", [])
    }