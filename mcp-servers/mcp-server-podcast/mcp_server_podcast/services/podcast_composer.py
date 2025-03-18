"""
Podcast composer service for creating complete podcasts.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from mcp.server.fastmcp import Context

from ..config import Settings
from ..models.domain import SegmentType, PodcastSegment, PodcastStorySegment, Podcast
from ..models.resource import PodcastResource
from ..utils.progress_reporter import ProgressReporter
from ..utils.resource_id_manager import ResourceIDManager
from .openai_agent import AzureOpenAIAgent


class PodcastComposerService:
    """Implementation of PodcastComposer using OpenAI for transitions, intros, and outros."""
    
    # Prompt templates
    INTRO_PROMPT = """
Create an engaging podcast introduction for a podcast with the following segments:
{segment_summaries}

The podcast title is: {podcast_title}

The introduction should:
1. Welcome listeners to the podcast
2. Briefly mention what the podcast is about
3. Set the tone for the episode
4. Preview what will be covered
5. Be conversational and engaging
6. Be about 30 seconds long when read aloud (about 3-4 sentences)

Return only the introduction text with no additional formatting or explanation.
"""

    TRANSITION_PROMPT = """
Create a smooth transition between these two podcast segments:

SEGMENT 1: {from_segment_title}
Summary: {from_segment_summary}

SEGMENT 2: {to_segment_title}
Summary: {to_segment_summary}

The transition should:
1. Connect the two topics in a natural way
2. Be brief (1-2 sentences)
3. Create a logical flow between the segments
4. Be conversational and engaging

Return only the transition text with no additional formatting or explanation.
"""

    OUTRO_PROMPT = """
Create an outro/conclusion for a podcast that covered the following segments:
{segment_summaries}

The podcast title is: {podcast_title}

The outro should:
1. Summarize the key points discussed
2. Thank the audience for listening
3. Include a brief sign-off message
4. Be conversational and engaging
5. Be about 20-30 seconds long when read aloud (2-3 sentences)

Return only the outro text with no additional formatting or explanation.
"""
    
    def __init__(self, openai_agent: AzureOpenAIAgent, show_transitions: bool = True):
        """Initialize the podcast composer service.
        
        Args:
            openai_agent: Azure OpenAI agent for generating content
            show_transitions: Whether to include transitions between segments
        """
        self.openai_agent = openai_agent
        self.show_transitions = show_transitions
        self.logger = logging.getLogger("mcp-server-podcast.podcast-composer")
    
    async def create_intro(self, story_segments: List[PodcastStorySegment], podcast_title: str) -> PodcastSegment:
        """Create an introduction segment for the podcast.
        
        Args:
            story_segments: List of story segments in the podcast
            podcast_title: Title of the podcast
            
        Returns:
            Introduction segment
        """
        self.logger.info(f"Creating intro for podcast: {podcast_title}")
        
        # Create a summary of segments
        segment_summaries = "\n".join(
            f"- {segment.title}: {segment.content[:100]}..." 
            for segment in story_segments
        )
        
        # Format the prompt
        prompt = self.INTRO_PROMPT.format(
            segment_summaries=segment_summaries,
            podcast_title=podcast_title
        )
        
        # Generate content
        response = await self.openai_agent.client.chat.completions.create(
            model=self.openai_agent.deployment_name,
            messages=[
                {"role": "system", "content": "You are an expert podcast writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Extract content
        content = response.choices[0].message.content.strip()
        
        # Create intro segment
        return PodcastSegment(
            segment_type=SegmentType.INTRO,
            content=content,
            voice_name=None,
            voice_style=None,
            metadata={"podcast_title": podcast_title}
        )
    
    async def create_transition(self, from_segment: PodcastStorySegment, to_segment: PodcastStorySegment) -> PodcastSegment:
        """Create a transition between two story segments.
        
        Args:
            from_segment: Source segment
            to_segment: Destination segment
            
        Returns:
            Transition segment
        """
        self.logger.info(f"Creating transition from '{from_segment.title}' to '{to_segment.title}'")
        
        # Format the prompt
        prompt = self.TRANSITION_PROMPT.format(
            from_segment_title=from_segment.title,
            from_segment_summary=from_segment.content[:200],
            to_segment_title=to_segment.title,
            to_segment_summary=to_segment.content[:200]
        )
        
        # Generate content
        response = await self.openai_agent.client.chat.completions.create(
            model=self.openai_agent.deployment_name,
            messages=[
                {"role": "system", "content": "You are an expert podcast writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        # Extract content
        content = response.choices[0].message.content.strip()
        
        # Create transition segment
        return PodcastSegment(
            segment_type=SegmentType.TRANSITION,
            content=content,
            voice_name=None,
            voice_style=None,
            metadata={
                "from_segment": from_segment.title,
                "to_segment": to_segment.title
            }
        )
    
    async def create_outro(self, story_segments: List[PodcastStorySegment], podcast_title: str) -> PodcastSegment:
        """Create an outro segment for the podcast.
        
        Args:
            story_segments: List of story segments in the podcast
            podcast_title: Title of the podcast
            
        Returns:
            Outro segment
        """
        self.logger.info(f"Creating outro for podcast: {podcast_title}")
        
        # Create a summary of segments
        segment_summaries = "\n".join(
            f"- {segment.title}: {segment.content[:100]}..." 
            for segment in story_segments
        )
        
        # Format the prompt
        prompt = self.OUTRO_PROMPT.format(
            segment_summaries=segment_summaries,
            podcast_title=podcast_title
        )
        
        # Generate content
        response = await self.openai_agent.client.chat.completions.create(
            model=self.openai_agent.deployment_name,
            messages=[
                {"role": "system", "content": "You are an expert podcast writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        # Extract content
        content = response.choices[0].message.content.strip()
        
        # Create outro segment
        return PodcastSegment(
            segment_type=SegmentType.OUTRO,
            content=content,
            voice_name=None,
            voice_style=None,
            metadata={"podcast_title": podcast_title}
        )
    
    async def compose_podcast(self, story_segments: List[PodcastStorySegment], podcast_title: Optional[str] = None) -> Podcast:
        """Compose a complete podcast from story segments.
        
        Args:
            story_segments: List of story segments
            podcast_title: Optional title for the podcast
            
        Returns:
            Complete podcast
        """
        if not story_segments:
            raise ValueError("Cannot compose podcast with no story segments")
            
        if not podcast_title:
            podcast_title = f"Podcast with {len(story_segments)} segments"
            
        self.logger.info(f"Composing podcast: {podcast_title} with {len(story_segments)} segments")
        
        # Create intro
        intro = await self.create_intro(story_segments, podcast_title)
        
        # Create outro
        outro = await self.create_outro(story_segments, podcast_title)
        
        # Arrange segments with transitions if enabled
        all_segments = [intro]
        
        for i, segment in enumerate(story_segments):
            all_segments.append(segment)
            
            # Add transitions between story segments
            if self.show_transitions and i < len(story_segments) - 1:
                transition = await self.create_transition(segment, story_segments[i + 1])
                all_segments.append(transition)
                
        all_segments.append(outro)
        
        # Create podcast
        podcast = Podcast(
            title=podcast_title,
            segments=all_segments,
            metadata={
                "segment_count": len(all_segments),
                "story_segment_count": len(story_segments),
                "has_transitions": self.show_transitions
            }
        )
        
        return podcast


class MCPPodcastComposer:
    """MCP wrapper for the PodcastComposerService."""
    
    def __init__(self, config: Settings, mcp_openai_agent, resource_id_manager: ResourceIDManager):
        """Initialize the MCP podcast composer.
        
        Args:
            config: Application configuration
            mcp_openai_agent: MCP OpenAI agent
            resource_id_manager: Resource ID manager
        """
        self.openai_agent = mcp_openai_agent.openai_agent
        self.podcast_composer = PodcastComposerService(
            self.openai_agent,
            show_transitions=config.show_transitions
        )
        
        self.storage_path = config.mcp_storage_path
        self.podcast_storage_path = self.storage_path / "podcasts"
        self.podcast_storage_path.mkdir(parents=True, exist_ok=True)
        
        self.resource_id_manager = resource_id_manager
        self.logger = logging.getLogger("mcp-server-podcast.mcp-podcast-composer")
    
    async def compose_podcast(self, podcast_id: str, title: Optional[str] = None, ctx: Optional[Context] = None) -> PodcastResource:
        """Compose a complete podcast from stored story segments.
        
        Args:
            podcast_id: ID of the podcast with story segments
            title: Optional custom title
            ctx: MCP context for progress reporting
            
        Returns:
            Podcast resource
        """
        progress = ProgressReporter(ctx)
        await progress.report_progress(0, "Starting podcast composition...")
        
        # Load story segments for the podcast ID
        story_segments = await self._load_story_segments(podcast_id)
        if not story_segments:
            raise ValueError(f"No story segments found for podcast ID: {podcast_id}")
            
        # Get podcast metadata
        metadata = self.resource_id_manager.get_metadata("podcast", podcast_id) or {}
        
        # Use custom title or existing title
        podcast_title = title or metadata.get("title", f"Podcast {podcast_id}")
        
        await progress.report_progress(20, "Loaded story segments, composing podcast...")
        
        # Compose the podcast
        podcast = await self.podcast_composer.compose_podcast(story_segments, podcast_title)
        
        await progress.report_progress(70, "Composed podcast, storing results...")
        
        # Store the composed podcast
        podcast_resource = await self._store_podcast(podcast_id, podcast)
        
        await progress.report_progress(100, "Podcast composition complete")
        
        return podcast_resource
    
    async def _load_story_segments(self, podcast_id: str) -> List[PodcastStorySegment]:
        """Load story segments for a podcast ID.
        
        Args:
            podcast_id: ID of the podcast
            
        Returns:
            List of story segments
        """
        # Get segments path from resource manager
        metadata = self.resource_id_manager.get_metadata("podcast", podcast_id) or {}
        segments_path = metadata.get("segments_path")
        
        if not segments_path:
            # Try default location
            segments_path = self.podcast_storage_path / podcast_id / "segments.json"
        else:
            segments_path = Path(segments_path)
            
        if not segments_path.exists():
            self.logger.error(f"Segments file not found for podcast ID: {podcast_id}")
            return []
            
        # Load segments
        try:
            with open(segments_path, "r") as f:
                data = json.load(f)
                
            segments = []
            for segment_data in data.get("segments", []):
                segment = PodcastStorySegment(
                    title=segment_data.get("title", "Untitled segment"),
                    content=segment_data.get("content", "No content"),
                    source_document=segment_data.get("source_document"),
                    voice_name=segment_data.get("voice_name"),
                    voice_style=segment_data.get("voice_style")
                )
                segments.append(segment)
                
            return segments
            
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            self.logger.error(f"Error loading segments for podcast ID {podcast_id}: {str(e)}")
            return []
    
    async def _store_podcast(self, podcast_id: str, podcast: Podcast) -> PodcastResource:
        """Store a composed podcast.
        
        Args:
            podcast_id: ID of the podcast
            podcast: Composed podcast
            
        Returns:
            Podcast resource
        """
        # Create podcast directory
        podcast_dir = self.podcast_storage_path / podcast_id
        podcast_dir.mkdir(parents=True, exist_ok=True)
        
        # Store script
        script_path = podcast_dir / "script.txt"
        script_path.write_text(podcast.full_script)
        
        # Store segments
        segments_path = podcast_dir / "composed_segments.json"
        segments_data = {
            "podcast_id": podcast_id,
            "title": podcast.title,
            "segments": [
                {
                    "segment_type": segment.segment_type,
                    "content": segment.content,
                    "voice_name": segment.voice_name,
                    "voice_style": segment.voice_style,
                    "metadata": segment.metadata
                } 
                for segment in podcast.segments
            ]
        }
        
        with open(segments_path, "w") as f:
            json.dump(segments_data, indent=2, f)
            
        # Update metadata
        metadata_path = podcast_dir / "metadata.json"
        metadata = {
            "podcast_id": podcast_id,
            "title": podcast.title,
            "segment_count": len(podcast.segments),
            "created_at": os.path.getmtime(script_path),
            "status": "composed"
        }
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, indent=2, f)
            
        # Create resource object
        podcast_resource = PodcastResource(
            podcast_id=podcast_id,
            title=podcast.title,
            script_path=script_path,
            segments_path=segments_path,
            metadata_path=metadata_path,
            status="composed",
            metadata=metadata
        )
        
        # Update resource manager
        self.resource_id_manager.update_metadata(
            resource_type="podcast",
            resource_id=podcast_id,
            metadata={
                "title": podcast.title,
                "segment_count": len(podcast.segments),
                "script_path": str(script_path),
                "composed_segments_path": str(segments_path),
                "metadata_path": str(metadata_path),
                "status": "composed"
            }
        )
        
        return podcast_resource