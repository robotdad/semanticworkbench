"""
Tool implementations for the MCP server.
"""

from .document_tools import register_document_tools
from .podcast_tools import register_podcast_tools

__all__ = ["register_document_tools", "register_podcast_tools"]