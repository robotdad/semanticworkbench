"""
Tests for the podcast generation services.
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_podcast.models.domain import PodcastStorySegment, Podcast
from mcp_server_podcast.services.openai_agent import AzureOpenAIAgent, MCPOpenAIAgent
from mcp_server_podcast.services.podcast_composer import PodcastComposerService, MCPPodcastComposer
from mcp_server_podcast.utils.resource_id_manager import ResourceIDManager


class TestAzureOpenAIAgent:
    """Tests for the AzureOpenAIAgent class."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock for the OpenAI client."""
        with patch("mcp_server_podcast.services.openai_agent.AsyncAzureOpenAI") as mock_client:
            # Set up the mock response
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            mock_message.content = json.dumps({
                "segments": [
                    {
                        "title": "Test Segment 1",
                        "content": "This is test segment 1 content.",
                        "source_document": "test-doc-1"
                    },
                    {
                        "title": "Test Segment 2",
                        "content": "This is test segment 2 content.",
                        "source_document": "test-doc-1"
                    }
                ]
            })
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            
            # Set up the chat.completions.create method
            mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            
            yield mock_client
    
    @pytest.fixture
    def agent(self, mock_openai_client):
        """Create an OpenAI agent instance."""
        return AzureOpenAIAgent(
            endpoint="https://test-endpoint",
            api_key="test-api-key",
            api_version="2023-05-15",
            deployment_name="gpt-4",
            target_podcast_length_minutes=5
        )
    
    @pytest.mark.asyncio
    async def test_generate_story_segments(self, agent):
        """Test generating story segments from a document."""
        from mcp_server_podcast.models.domain import ExtractTextResult
        
        # Create a test extraction result
        extraction_result = ExtractTextResult(
            document_id="test-doc-1",
            original_filename="test.txt",
            extracted_text="This is test document content.",
            page_count=1,
            success=True
        )
        
        # Generate segments
        segments = await agent.generate_story_segments(extraction_result)
        
        # Check result
        assert len(segments) == 2
        assert segments[0].title == "Test Segment 1"
        assert segments[0].content == "This is test segment 1 content."
        assert segments[0].source_document == "test-doc-1"
        assert segments[1].title == "Test Segment 2"


class TestPodcastComposerService:
    """Tests for the PodcastComposerService class."""
    
    @pytest.fixture
    def mock_openai_agent(self):
        """Mock for the OpenAI agent."""
        mock_agent = MagicMock()
        
        # Set up client.chat.completions.create
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # For intro
        intro_response = MagicMock()
        intro_choice = MagicMock()
        intro_message = MagicMock()
        intro_message.content = "This is a test intro."
        intro_choice.message = intro_message
        intro_response.choices = [intro_choice]
        
        # For transition
        transition_response = MagicMock()
        transition_choice = MagicMock()
        transition_message = MagicMock()
        transition_message.content = "This is a test transition."
        transition_choice.message = transition_message
        transition_response.choices = [transition_choice]
        
        # For outro
        outro_response = MagicMock()
        outro_choice = MagicMock()
        outro_message = MagicMock()
        outro_message.content = "This is a test outro."
        outro_choice.message = outro_message
        outro_response.choices = [outro_choice]
        
        # Set up the chat.completions.create method to return different responses
        mock_agent.client.chat.completions.create = AsyncMock(side_effect=[
            intro_response,
            transition_response,
            outro_response
        ])
        
        yield mock_agent
    
    @pytest.fixture
    def composer(self, mock_openai_agent):
        """Create a podcast composer instance."""
        return PodcastComposerService(mock_openai_agent, show_transitions=True)
    
    @pytest.mark.asyncio
    async def test_compose_podcast(self, composer):
        """Test composing a podcast from story segments."""
        # Create test story segments
        segment1 = PodcastStorySegment(
            title="Test Segment 1",
            content="This is test segment 1 content.",
            source_document="test-doc-1"
        )
        
        segment2 = PodcastStorySegment(
            title="Test Segment 2",
            content="This is test segment 2 content.",
            source_document="test-doc-1"
        )
        
        # Compose podcast
        podcast = await composer.compose_podcast([segment1, segment2], "Test Podcast")
        
        # Check result
        assert podcast.title == "Test Podcast"
        assert len(podcast.segments) == 5  # intro + segment1 + transition + segment2 + outro
        assert podcast.segments[0].segment_type == "intro"
        assert podcast.segments[0].content == "This is a test intro."
        assert podcast.segments[1].segment_type == "story"
        assert podcast.segments[1].title == "Test Segment 1"
        assert podcast.segments[2].segment_type == "transition"
        assert podcast.segments[2].content == "This is a test transition."
        assert podcast.segments[3].segment_type == "story"
        assert podcast.segments[3].title == "Test Segment 2"
        assert podcast.segments[4].segment_type == "outro"
        assert podcast.segments[4].content == "This is a test outro."