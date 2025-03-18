import asyncio
import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from mcp.server.fastmcp import FastMCP, Context

from . import settings
from .config import Settings
from .models import (
    DocumentResource, PodcastResource, AudioResource, ResourceResponse,
    DOCUMENT_SCHEME, PODCAST_SCHEME, AUDIO_SCHEME, VOICES_SCHEME
)
from .resources import register_document_resources
from .services import MCPDocumentProcessor
from .tools import register_document_tools
from .utils import ResourceIDManager, ProgressReporter

# Set up logger
logger = logging.getLogger("mcp-server-podcast")

# Set the name of the MCP server
server_name = "Podcast MCP Server"


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with resources, tools, and prompts."""
    # Initialize FastMCP with configured logging level
    mcp = FastMCP(name=server_name, log_level=settings.log_level)
    
    # Ensure storage directories exist
    documents_dir = settings.mcp_storage_path / "documents"
    podcasts_dir = settings.mcp_storage_path / "podcasts"
    audio_dir = settings.mcp_storage_path / "audio"
    
    documents_dir.mkdir(exist_ok=True, parents=True)
    podcasts_dir.mkdir(exist_ok=True, parents=True)
    audio_dir.mkdir(exist_ok=True, parents=True)
    
    # Initialize resource ID manager
    resource_manager = ResourceIDManager(settings.mcp_storage_path)
    
    # Initialize document processor service
    document_processor = MCPDocumentProcessor(settings, resource_manager)
    
    # Register document resources and tools
    register_document_resources(mcp, document_processor)
    register_document_tools(mcp, document_processor)
    
    logger.info(f"Initialized MCP server with storage at {settings.mcp_storage_path}")
    
    @mcp.resource("podcast://{podcast_id}/script")
    async def get_podcast_script(podcast_id: str) -> Tuple[str, str]:
        """Retrieve the full text of a generated podcast script."""
        # This is a placeholder implementation
        script_path = podcasts_dir / f"{podcast_id}.txt"
        
        if not script_path.exists():
            raise FileNotFoundError(f"Podcast script with ID {podcast_id} not found")
            
        script = script_path.read_text()
        return script, "text/plain"
    
    @mcp.resource("podcast://{podcast_id}/segments")
    async def get_podcast_segments(podcast_id: str) -> Tuple[str, str]:
        """Retrieve the individual segments of a podcast."""
        # This is a placeholder implementation
        segments_path = podcasts_dir / f"{podcast_id}.segments.json"
        
        if not segments_path.exists():
            raise FileNotFoundError(f"Podcast segments with ID {podcast_id} not found")
            
        segments = segments_path.read_text()
        return segments, "application/json"
    
    @mcp.resource("podcast://{podcast_id}/metadata")
    async def get_podcast_metadata(podcast_id: str) -> Tuple[str, str]:
        """Retrieve metadata about a generated podcast."""
        # This is a placeholder implementation
        metadata_path = podcasts_dir / f"{podcast_id}.metadata.json"
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata for podcast with ID {podcast_id} not found")
            
        metadata = metadata_path.read_text()
        return metadata, "application/json"
    
    @mcp.resource("audio://{audio_id}")
    async def get_audio(audio_id: str) -> Tuple[bytes, str]:
        """Retrieve a generated audio file."""
        # This is a placeholder implementation
        audio_path = audio_dir / f"{audio_id}.mp3"
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file with ID {audio_id} not found")
            
        audio_content = audio_path.read_bytes()
        return audio_content, "audio/mpeg"
    
    @mcp.resource("audio://{audio_id}/segment/{segment_id}")
    async def get_audio_segment(audio_id: str, segment_id: str) -> Tuple[bytes, str]:
        """Retrieve audio for a specific podcast segment."""
        # This is a placeholder implementation
        segment_path = audio_dir / f"{audio_id}_segment_{segment_id}.mp3"
        
        if not segment_path.exists():
            raise FileNotFoundError(f"Audio segment {segment_id} for audio ID {audio_id} not found")
            
        segment_content = segment_path.read_bytes()
        return segment_content, "audio/mpeg"
    
    @mcp.resource("voices://list")
    async def get_voice_list() -> Tuple[str, str]:
        """List all available voices."""
        # This is a placeholder implementation
        voices = [
            {"name": "en-US-JennyNeural", "gender": "Female", "locale": "en-US", "styles": ["chat", "newscast"]},
            {"name": "en-US-GuyNeural", "gender": "Male", "locale": "en-US", "styles": ["newscast", "narration-professional"]},
            {"name": "en-US-DavisNeural", "gender": "Male", "locale": "en-US", "styles": ["chat", "narration-professional"]}
        ]
        return json.dumps(voices), "application/json"
    
    @mcp.resource("voices://recommended")
    async def get_recommended_voices() -> Tuple[str, str]:
        """List recommended voices for podcasts."""
        # This is a placeholder implementation
        recommended = [
            {"name": "en-US-JennyNeural", "role": "host", "description": "Clear and professional female voice"},
            {"name": "en-US-GuyNeural", "role": "reporter", "description": "Professional male voice for news segments"},
            {"name": "en-US-DavisNeural", "role": "reporter", "description": "Engaging male voice for feature segments"}
        ]
        return json.dumps(recommended), "application/json"
    
    # Tool implementations
    
    # Note: Document tools are now registered via register_document_tools() above
    
    # Placeholder for other tools that will be implemented in later phases
    
    # Example of a simple echo tool to verify server functionality
    @mcp.tool()    
    async def echo(value: str) -> str:
        """Returns whatever is passed to it. Used for testing."""
        return value

    return mcp
