"""
Podcast generation tools for MCP server.
"""

import logging
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP, Context

from ..services.openai_agent import MCPOpenAIAgent
from ..services.podcast_composer import MCPPodcastComposer


def register_podcast_tools(
    mcp: FastMCP, 
    openai_agent: MCPOpenAIAgent,
    podcast_composer: MCPPodcastComposer
) -> None:
    """Register podcast generation tools.
    
    Args:
        mcp: FastMCP instance
        openai_agent: OpenAI agent service
        podcast_composer: Podcast composer service
    """
    logger = logging.getLogger("mcp-server-podcast.podcast-tools")
    
    @mcp.tool()
    async def generate_podcast(
        document_ids: List[str],
        title: Optional[str] = None,
        length: Optional[int] = None,
        custom_prompt: Optional[str] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Generate a podcast script from documents.
        
        Args:
            document_ids: List of document IDs to process
            title: Optional title for the podcast
            length: Optional target podcast length in minutes
            custom_prompt: Optional custom prompt for script generation
            ctx: MCP context for progress reporting
            
        Returns:
            Result with podcast ID and status
        """
        logger.info(f"Generating podcast from documents: {document_ids}")
        
        try:
            # Generate story segments
            podcast_id, metadata = await openai_agent.generate_podcast(
                document_ids=document_ids,
                podcast_title=title,
                length_minutes=length,
                custom_prompt=custom_prompt,
                ctx=ctx
            )
            
            # Return success response
            return {
                "success": True,
                "result": {
                    "podcast_id": podcast_id,
                    "title": metadata.get("title", f"Podcast {podcast_id}"),
                    "status": metadata.get("status", "segments_generated"),
                    "segment_count": metadata.get("segment_count", 0),
                    "uri": f"podcast://{podcast_id}/segments",
                    "metadata_uri": f"podcast://{podcast_id}/metadata"
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating podcast: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "generation_failed",
                    "message": f"Podcast generation failed: {str(e)}"
                }
            }
    
    @mcp.tool()
    async def compose_podcast(
        podcast_id: str,
        title: Optional[str] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Compose a complete podcast from generated segments.
        
        Args:
            podcast_id: ID of the podcast with generated segments
            title: Optional custom title
            ctx: MCP context for progress reporting
            
        Returns:
            Result with podcast ID and script URI
        """
        logger.info(f"Composing podcast: {podcast_id}")
        
        try:
            # Compose podcast
            podcast_resource = await podcast_composer.compose_podcast(
                podcast_id=podcast_id,
                title=title,
                ctx=ctx
            )
            
            # Return success response
            return {
                "success": True,
                "result": {
                    "podcast_id": podcast_id,
                    "title": podcast_resource.title,
                    "status": podcast_resource.status,
                    "segment_count": podcast_resource.metadata.get("segment_count", 0),
                    "script_uri": podcast_resource.uri,
                    "segments_uri": podcast_resource.segments_uri,
                    "metadata_uri": podcast_resource.metadata_uri
                }
            }
            
        except Exception as e:
            logger.error(f"Error composing podcast: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "composition_failed",
                    "message": f"Podcast composition failed: {str(e)}"
                }
            }
    
    @mcp.tool()
    async def customize_podcast(
        podcast_id: str,
        show_transitions: Optional[bool] = None,
        format: Optional[str] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Customize podcast generation settings.
        
        Args:
            podcast_id: ID of the podcast to customize
            show_transitions: Whether to include transitions between segments
            format: Podcast format (conversational, narrative, etc.)
            ctx: MCP context for progress reporting
            
        Returns:
            Result with podcast ID and status
        """
        logger.info(f"Customizing podcast: {podcast_id}")
        
        try:
            # This is a placeholder for customization functionality
            # In a real implementation, we would store these settings and apply them
            
            # Get current metadata
            metadata = podcast_composer.resource_id_manager.get_metadata("podcast", podcast_id)
            if not metadata:
                return {
                    "success": False,
                    "error": {
                        "code": "podcast_not_found",
                        "message": f"Podcast not found: {podcast_id}"
                    }
                }
                
            # Apply customization
            updated_metadata = {**metadata}
            
            if show_transitions is not None:
                updated_metadata["show_transitions"] = show_transitions
                
            if format is not None:
                updated_metadata["format"] = format
                
            # Update metadata
            podcast_composer.resource_id_manager.update_metadata(
                resource_type="podcast",
                resource_id=podcast_id,
                metadata=updated_metadata
            )
            
            # Return success response
            return {
                "success": True,
                "result": {
                    "podcast_id": podcast_id,
                    "status": "customized",
                    "customizations": {
                        "show_transitions": show_transitions,
                        "format": format
                    },
                    "uri": f"podcast://{podcast_id}/metadata"
                }
            }
            
        except Exception as e:
            logger.error(f"Error customizing podcast: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "customization_failed",
                    "message": f"Podcast customization failed: {str(e)}"
                }
            }