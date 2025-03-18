"""
Resource models for MCP resources.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple

# Resource URI schemes
DOCUMENT_SCHEME = "document://"
PODCAST_SCHEME = "podcast://"
AUDIO_SCHEME = "audio://"
VOICES_SCHEME = "voices://"


@dataclass
class DocumentResource:
    """Resource model for a document."""
    document_id: str
    original_filename: str
    content_path: Path
    metadata_path: Path
    document_type: str = "application/octet-stream"
    status: str = "uploaded"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def uri(self) -> str:
        """Get the URI for this resource."""
        return f"{DOCUMENT_SCHEME}{self.document_id}"
    
    @property
    def metadata_uri(self) -> str:
        """Get the metadata URI for this resource."""
        return f"{DOCUMENT_SCHEME}{self.document_id}/metadata"


@dataclass
class PodcastResource:
    """Resource model for a podcast."""
    podcast_id: str
    title: str
    script_path: Path
    segments_path: Path
    metadata_path: Path
    status: str = "generated"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def uri(self) -> str:
        """Get the URI for this resource."""
        return f"{PODCAST_SCHEME}{self.podcast_id}/script"
    
    @property
    def segments_uri(self) -> str:
        """Get the segments URI for this resource."""
        return f"{PODCAST_SCHEME}{self.podcast_id}/segments"
    
    @property
    def metadata_uri(self) -> str:
        """Get the metadata URI for this resource."""
        return f"{PODCAST_SCHEME}{self.podcast_id}/metadata"


@dataclass
class AudioResource:
    """Resource model for audio."""
    audio_id: str
    podcast_id: str
    audio_path: Path
    segment_paths: Dict[str, Path]
    voice_name: Optional[str] = None
    voice_style: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def uri(self) -> str:
        """Get the URI for this resource."""
        return f"{AUDIO_SCHEME}{self.audio_id}"
    
    def segment_uri(self, segment_id: str) -> str:
        """Get the URI for a segment."""
        return f"{AUDIO_SCHEME}{self.audio_id}/segment/{segment_id}"


@dataclass
class ResourceResponse:
    """Response data for MCP resources."""
    content: Union[str, bytes]
    mime_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def as_tuple(self) -> Tuple[Union[str, bytes], str]:
        """Return as a tuple for MCP resource handlers."""
        return self.content, self.mime_type