"""
Audio resource handlers for MCP server.
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

from ..models.resource import AUDIO_SCHEME, VOICES_SCHEME, ResourceResponse
from ..services.audio_generator import MCPAudioGenerator
from ..utils.resource_id_manager import ResourceIDManager


class AudioResourceHandler:
    """Handlers for audio resources."""
    
    def __init__(self, resource_id_manager: ResourceIDManager, audio_generator: MCPAudioGenerator, storage_path: Path):
        """Initialize the audio resource handler.
        
        Args:
            resource_id_manager: Resource ID manager
            audio_generator: Audio generator service
            storage_path: Base storage path
        """
        self.resource_id_manager = resource_id_manager
        self.audio_generator = audio_generator
        self.storage_path = storage_path
        self.audio_storage_path = storage_path / "audio"
        self.logger = logging.getLogger("mcp-server-podcast.audio-resources")
        
    async def get_audio(self, audio_id: str) -> Optional[bytes]:
        """Get the audio file.
        
        Args:
            audio_id: Audio ID
            
        Returns:
            Audio file content or None if not found
        """
        # Try to get the audio path from the resource manager
        metadata = self.resource_id_manager.get_metadata("audio", audio_id) or {}
        audio_path = metadata.get("audio_path")
        
        if audio_path:
            audio_path = Path(audio_path)
            if audio_path.exists():
                return audio_path.read_bytes()
        
        # Try the default location
        default_path = self.audio_storage_path / audio_id / "audio.mp3"
        if default_path.exists():
            return default_path.read_bytes()
            
        return None
        
    async def get_audio_segment(self, audio_id: str, segment_id: str) -> Optional[bytes]:
        """Get the audio segment.
        
        Args:
            audio_id: Audio ID
            segment_id: Segment ID
            
        Returns:
            Audio segment content or None if not found
        """
        # Try to get the segment path from the resource manager
        metadata = self.resource_id_manager.get_metadata("audio", audio_id) or {}
        segment_paths = metadata.get("segment_paths", {})
        segment_path = segment_paths.get(segment_id)
        
        if segment_path:
            segment_path = Path(segment_path)
            if segment_path.exists():
                return segment_path.read_bytes()
        
        # Try the default location
        default_path = self.audio_storage_path / audio_id / f"segment_{segment_id}.mp3"
        if default_path.exists():
            return default_path.read_bytes()
            
        return None
        
    async def get_voices_list(self) -> List[Dict[str, Any]]:
        """Get the list of available voices.
        
        Returns:
            List of voice information dictionaries
        """
        return await self.audio_generator.get_voices()
        
    async def get_recommended_voices(self, gender: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recommended voices, optionally filtered by gender.
        
        Args:
            gender: Optional gender to filter by
            
        Returns:
            List of voice information dictionaries
        """
        return await self.audio_generator.get_voices(gender=gender)
        

def register_audio_resources(
    mcp: FastMCP, 
    resource_id_manager: ResourceIDManager, 
    audio_generator: MCPAudioGenerator,
    storage_path: Path
) -> None:
    """Register audio resource handlers.
    
    Args:
        mcp: FastMCP instance
        resource_id_manager: Resource ID manager
        audio_generator: Audio generator service
        storage_path: Base storage path
    """
    # Create audio resource handler
    handler = AudioResourceHandler(resource_id_manager, audio_generator, storage_path)
    logger = logging.getLogger("mcp-server-podcast.audio-resources")
    
    @mcp.resource(f"{AUDIO_SCHEME}{{audio_id}}")
    async def get_audio(audio_id: str) -> Tuple[bytes, str]:
        """Get audio for an audio ID.
        
        Args:
            audio_id: Audio ID
            
        Returns:
            Tuple of content and MIME type
        """
        logger.info(f"Getting audio for {audio_id}")
        content = await handler.get_audio(audio_id)
        
        if content is None:
            response = ResourceResponse(
                content=b"Audio not found",  # Return empty audio
                mime_type="text/plain"
            )
        else:
            response = ResourceResponse(
                content=content,
                mime_type="audio/mpeg"
            )
            
        return response.as_tuple()
    
    @mcp.resource(f"{AUDIO_SCHEME}{{audio_id}}/segment/{{segment_id}}")
    async def get_audio_segment(audio_id: str, segment_id: str) -> Tuple[bytes, str]:
        """Get audio segment for an audio ID and segment ID.
        
        Args:
            audio_id: Audio ID
            segment_id: Segment ID
            
        Returns:
            Tuple of content and MIME type
        """
        logger.info(f"Getting audio segment {segment_id} for audio {audio_id}")
        content = await handler.get_audio_segment(audio_id, segment_id)
        
        if content is None:
            response = ResourceResponse(
                content=b"Audio segment not found",  # Return empty audio
                mime_type="text/plain"
            )
        else:
            response = ResourceResponse(
                content=content,
                mime_type="audio/mpeg"
            )
            
        return response.as_tuple()
    
    @mcp.resource(f"{VOICES_SCHEME}list")
    async def get_voices_list() -> Tuple[str, str]:
        """Get list of available voices.
        
        Returns:
            Tuple of JSON content and MIME type
        """
        logger.info("Getting list of available voices")
        voices = await handler.get_voices_list()
        
        response = ResourceResponse(
            content=json.dumps(voices, indent=2),
            mime_type="application/json"
        )
            
        return response.as_tuple()
    
    @mcp.resource(f"{VOICES_SCHEME}recommended")
    async def get_recommended_voices() -> Tuple[str, str]:
        """Get list of recommended voices.
        
        Returns:
            Tuple of JSON content and MIME type
        """
        logger.info("Getting list of recommended voices")
        voices = await handler.get_recommended_voices()
        
        response = ResourceResponse(
            content=json.dumps(voices, indent=2),
            mime_type="application/json"
        )
            
        return response.as_tuple()