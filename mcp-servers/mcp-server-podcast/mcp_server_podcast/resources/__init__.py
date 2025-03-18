"""
Resource handlers for MCP resources.
"""

from .document_resources import register_document_resources
from .podcast_resources import register_podcast_resources
from .audio_resources import register_audio_resources

__all__ = [
    "register_document_resources", 
    "register_podcast_resources",
    "register_audio_resources"
]