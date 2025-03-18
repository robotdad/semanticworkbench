"""
Domain and resource models for the Podcast MCP Server.
"""

from .domain import (
    SegmentType,
    PodcastSegment, 
    PodcastStorySegment,
    Podcast,
    ExtractTextResult,
    VoiceConfig
)

from .resource import (
    DocumentResource,
    PodcastResource,
    AudioResource,
    ResourceResponse,
    DOCUMENT_SCHEME,
    PODCAST_SCHEME,
    AUDIO_SCHEME,
    VOICES_SCHEME
)

__all__ = [
    "SegmentType",
    "PodcastSegment",
    "PodcastStorySegment",
    "Podcast",
    "ExtractTextResult",
    "VoiceConfig",
    "DocumentResource",
    "PodcastResource",
    "AudioResource",
    "ResourceResponse",
    "DOCUMENT_SCHEME",
    "PODCAST_SCHEME",
    "AUDIO_SCHEME",
    "VOICES_SCHEME"
]