"""
Audio generation tools for MCP server.
"""

import logging
from typing import Dict, Any, Optional, List

from mcp.server.fastmcp import FastMCP, Context

from ..services.audio_generator import MCPAudioGenerator


def register_audio_tools(
    mcp: FastMCP, 
    audio_generator: MCPAudioGenerator
) -> None:
    """Register audio generation tools.
    
    Args:
        mcp: FastMCP instance
        audio_generator: Audio generator service
    """
    logger = logging.getLogger("mcp-server-podcast.audio-tools")
    
    @mcp.tool()
    async def generate_audio(
        podcast_id: str,
        voice_name: Optional[str] = None,
        voice_style: Optional[str] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Generate audio for a podcast script.
        
        Args:
            podcast_id: ID of the podcast
            voice_name: Optional voice name (e.g., "en-US-JennyNeural" or "female")
            voice_style: Optional voice style (e.g., "cheerful", "newscast")
            ctx: MCP context for progress reporting
            
        Returns:
            Result with audio ID and URIs
        """
        logger.info(f"Generating audio for podcast: {podcast_id}")
        
        try:
            # Generate audio
            audio_id, audio_resource = await audio_generator.generate_audio(
                podcast_id=podcast_id,
                voice_name=voice_name,
                voice_style=voice_style,
                ctx=ctx
            )
            
            # Return success response
            return {
                "success": True,
                "result": {
                    "audio_id": audio_id,
                    "podcast_id": podcast_id,
                    "voice_name": voice_name or "default",
                    "voice_style": voice_style,
                    "segment_count": len(audio_resource.segment_paths),
                    "uri": audio_resource.uri,
                    "format": "mp3"
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "audio_generation_failed",
                    "message": f"Audio generation failed: {str(e)}"
                }
            }
    
    @mcp.tool()
    async def test_audio(
        text: str,
        voice_name: Optional[str] = None,
        voice_style: Optional[str] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Test audio generation with sample text.
        
        Args:
            text: Text to synthesize
            voice_name: Optional voice to use
            voice_style: Optional voice style to use
            ctx: MCP context for progress reporting
            
        Returns:
            Result with audio ID and URI
        """
        logger.info(f"Testing audio generation with voice: {voice_name}, style: {voice_style}")
        
        try:
            # Generate test audio
            audio_id, audio_resource = await audio_generator.test_audio(
                text=text,
                voice_name=voice_name,
                voice_style=voice_style,
                ctx=ctx
            )
            
            # Return success response
            return {
                "success": True,
                "result": {
                    "audio_id": audio_id,
                    "voice_name": voice_name or "default",
                    "voice_style": voice_style,
                    "text": text,
                    "uri": audio_resource.uri,
                    "format": "mp3"
                }
            }
            
        except Exception as e:
            logger.error(f"Error testing audio: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "audio_test_failed",
                    "message": f"Audio test failed: {str(e)}"
                }
            }
    
    @mcp.tool()
    async def list_voices(
        gender: Optional[str] = None,
        locale: Optional[str] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """List available voices and their properties.
        
        Args:
            gender: Optional filter by gender ("Male" or "Female")
            locale: Optional filter by language/locale (e.g., "en-US")
            ctx: MCP context for progress reporting
            
        Returns:
            Result with list of matching voice details
        """
        logger.info(f"Listing voices with filters - gender: {gender}, locale: {locale}")
        
        try:
            # Get voices
            voices = await audio_generator.get_voices(gender=gender, locale=locale)
            
            # Return success response
            return {
                "success": True,
                "result": {
                    "voices": voices,
                    "count": len(voices),
                    "filters": {
                        "gender": gender,
                        "locale": locale
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing voices: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "voice_listing_failed",
                    "message": f"Voice listing failed: {str(e)}"
                }
            }
    
    @mcp.tool()
    async def get_voice_details(
        voice_name: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Get detailed information about a specific voice.
        
        Args:
            voice_name: Name of the voice to query
            ctx: MCP context for progress reporting
            
        Returns:
            Result with detailed voice information
        """
        logger.info(f"Getting details for voice: {voice_name}")
        
        try:
            # Get all voices
            voices = await audio_generator.get_voices()
            
            # Find the requested voice
            voice_details = next((v for v in voices if v["name"] == voice_name), None)
            
            if not voice_details:
                return {
                    "success": False,
                    "error": {
                        "code": "voice_not_found",
                        "message": f"Voice not found: {voice_name}"
                    }
                }
                
            # Return success response
            return {
                "success": True,
                "result": {
                    "voice": voice_details
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting voice details: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "voice_details_failed",
                    "message": f"Getting voice details failed: {str(e)}"
                }
            }