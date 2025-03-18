"""
Domain models for podcast generation.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class SegmentType(str, Enum):
    """Type of podcast segment."""
    INTRO = "intro"
    STORY = "story"
    TRANSITION = "transition"
    OUTRO = "outro"


@dataclass
class PodcastSegment:
    """A segment of a podcast script."""
    segment_type: SegmentType
    content: str
    voice_name: Optional[str] = None
    voice_style: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PodcastStorySegment(PodcastSegment):
    """A story segment of a podcast."""
    title: str
    source_document: Optional[str] = None
    
    def __post_init__(self):
        """Ensure segment type is STORY."""
        self.segment_type = SegmentType.STORY


@dataclass
class Podcast:
    """A complete podcast with all segments."""
    title: str
    segments: List[PodcastSegment]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def full_script(self) -> str:
        """Get the full script as a single string."""
        return "\n\n".join(segment.content for segment in self.segments)


@dataclass
class ExtractTextResult:
    """Result of document text extraction."""
    document_id: str
    original_filename: str
    extracted_text: str
    page_count: int
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceConfig:
    """Configuration for voice synthesis."""
    host_voice: str = "en-US-JennyNeural"
    reporter_voices: List[str] = field(default_factory=lambda: ["en-US-GuyNeural", "en-US-DavisNeural"])
    default_voice: Optional[str] = None
    default_voice_style: Optional[str] = None
    
    def get_recommended_voices(self, gender: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recommended voices, optionally filtered by gender."""
        # This is a simplified implementation
        voices = [
            {
                "name": "en-US-JennyNeural", 
                "gender": "Female", 
                "role": "host", 
                "description": "Clear and professional female voice"
            },
            {
                "name": "en-US-GuyNeural", 
                "gender": "Male", 
                "role": "reporter", 
                "description": "Professional male voice for news segments"
            },
            {
                "name": "en-US-DavisNeural", 
                "gender": "Male", 
                "role": "reporter", 
                "description": "Engaging male voice for feature segments"
            }
        ]
        
        if gender:
            return [v for v in voices if v["gender"].lower() == gender.lower()]
        return voices