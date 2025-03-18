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
    
    # Initialize services
    document_processor = MCPDocumentProcessor(settings, resource_manager)
    openai_agent = MCPOpenAIAgent(settings, resource_manager, document_processor)
    podcast_composer = MCPPodcastComposer(settings, openai_agent, resource_manager)
    audio_generator = MCPAudioGenerator(settings, resource_manager, podcast_composer)
    
    # Register resources and tools
    register_document_resources(mcp, document_processor)
    register_document_tools(mcp, document_processor)
    register_podcast_resources(mcp, resource_manager, settings.mcp_storage_path)
    register_podcast_tools(mcp, openai_agent, podcast_composer)
    register_audio_resources(mcp, resource_manager, audio_generator, settings.mcp_storage_path)
    register_audio_tools(mcp, audio_generator)
    
    logger.info(f"Initialized MCP server with storage at {settings.mcp_storage_path}")
    
    # Note: Podcast resources are now registered via register_podcast_resources() above
    
    # Note: Audio resources are now registered via register_audio_resources() above
    
    # Tool implementations
    
    # Note: Document tools are now registered via register_document_tools() above
    
    # Placeholder for other tools that will be implemented in later phases
    
    # Example of a simple echo tool to verify server functionality
    @mcp.tool()    
    async def echo(value: str) -> str:
        """Returns whatever is passed to it. Used for testing."""
        return value

    return mcp
