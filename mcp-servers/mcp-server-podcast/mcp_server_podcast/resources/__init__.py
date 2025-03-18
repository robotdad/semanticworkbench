"""
Resource handlers for MCP resources.
"""

from .document_resources import register_document_resources
from .podcast_resources import register_podcast_resources

__all__ = ["register_document_resources", "register_podcast_resources"]