"""
Tests for the audio generator services.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_podcast.models.domain import PodcastSegment, Podcast, SegmentType
from mcp_server_podcast.services.audio_generator import AudioGeneratorService, MCPAudioGenerator
from mcp_server_podcast.utils.resource_id_manager import ResourceIDManager


class TestAudioGeneratorService:
    """Tests for the AudioGeneratorService class."""
    
    @pytest.fixture
    def mock_speech_synthesizer(self):
        """Mock for the speech synthesizer."""
        with patch("mcp_server_podcast.services.audio_generator.SpeechSynthesizer") as mock_synth:
            # Set up the mock result
            mock_result = MagicMock()
            mock_result.reason = MagicMock()
            mock_result.reason.SynthesizingAudioCompleted = 1
            mock_result.reason = 1  # Success
            
            # Set up the speak_ssml_async method
            mock_async_result = MagicMock()
            mock_async_result.get.return_value = mock_result
            mock_synth.return_value.speak_ssml_async.return_value = mock_async_result
            
            yield mock_synth
    
    @pytest.fixture
    def generator(self, mock_speech_synthesizer, tmp_path):
        """Create an audio generator instance."""
        return AudioGeneratorService(
            speech_region="eastus",
            speech_key="test-key",
            host_voice="en-US-JennyNeural",
            reporter_voices=["en-US-GuyNeural"]
        )
    
    @pytest.mark.asyncio
    async def test_generate_audio_for_segment(self, generator, tmp_path):
        """Test generating audio for a segment."""
        # Create a test segment
        segment = PodcastSegment(
            segment_type=SegmentType.INTRO,
            content="This is a test intro.",
            voice_name=None,
            voice_style=None
        )
        
        # Generate audio
        output_file = await generator.generate_audio_for_segment(
            segment=segment,
            output_path=tmp_path,
            output_filename="test_segment.mp3"
        )
        
        # Check result
        assert output_file.name == "test_segment.mp3"
        assert output_file.parent == tmp_path
    
    @pytest.mark.asyncio
    async def test_generate_audio_for_podcast(self, generator, tmp_path):
        """Test generating audio for a podcast."""
        # Create a test podcast
        segments = [
            PodcastSegment(
                segment_type=SegmentType.INTRO,
                content="This is a test intro.",
                voice_name=None,
                voice_style=None
            ),
            PodcastSegment(
                segment_type=SegmentType.STORY,
                content="This is a test story segment.",
                voice_name=None,
                voice_style=None
            ),
            PodcastSegment(
                segment_type=SegmentType.OUTRO,
                content="This is a test outro.",
                voice_name=None,
                voice_style=None
            )
        ]
        
        podcast = Podcast(
            title="Test Podcast",
            segments=segments
        )
        
        # Set progress callback
        generator.set_progress_callback(AsyncMock())
        
        # Generate audio
        output_file, segment_files = await generator.generate_audio_for_podcast(
            podcast=podcast,
            output_path=tmp_path,
            output_filename="test_podcast.mp3",
            generate_segments=True
        )
        
        # Check result
        assert output_file.name == "test_podcast.mp3"
        assert output_file.parent == tmp_path
        assert len(segment_files) == 3
        
    @pytest.mark.asyncio
    async def test_get_available_voices(self, generator):
        """Test getting available voices."""
        voices = await generator.get_available_voices()
        
        # Check result
        assert len(voices) >= 1
        assert "name" in voices[0]
        assert "gender" in voices[0]
        assert "locale" in voices[0]


class TestMCPAudioGenerator:
    """Tests for the MCPAudioGenerator class."""
    
    @pytest.fixture
    def mock_audio_generator(self):
        """Mock for the audio generator."""
        with patch("mcp_server_podcast.services.audio_generator.AudioGeneratorService") as mock_generator:
            # Set up the generate_audio_for_podcast method
            mock_generator.return_value.generate_audio_for_podcast = AsyncMock()
            mock_generator.return_value.generate_audio_for_podcast.return_value = (
                Path("/tmp/test_audio.mp3"),
                {"0": Path("/tmp/segment_0.mp3"), "1": Path("/tmp/segment_1.mp3")}
            )
            
            # Set up the generate_audio_for_segment method
            mock_generator.return_value.generate_audio_for_segment = AsyncMock()
            mock_generator.return_value.generate_audio_for_segment.return_value = Path("/tmp/test_segment.mp3")
            
            # Set up the get_available_voices method
            mock_generator.return_value.get_available_voices = AsyncMock()
            mock_generator.return_value.get_available_voices.return_value = [
                {"name": "en-US-JennyNeural", "gender": "Female", "locale": "en-US"}
            ]
            
            # Return the mock
            yield mock_generator
    
    @pytest.fixture
    def mock_config(self):
        """Mock for the config."""
        mock_config = MagicMock()
        mock_config.mcp_storage_path = Path("/tmp/mcp-test")
        mock_config.speech_region = "eastus"
        mock_config.speech_key = "test-key"
        mock_config.speech_host_voice = "en-US-JennyNeural"
        mock_config.speech_reporter_voices = ["en-US-GuyNeural"]
        return mock_config
    
    @pytest.fixture
    def mock_resource_id_manager(self):
        """Mock for the resource ID manager."""
        mock_manager = MagicMock(spec=ResourceIDManager)
        mock_manager.generate_id.return_value = "test-audio-id"
        return mock_manager
    
    @pytest.fixture
    def mock_podcast_composer(self):
        """Mock for the podcast composer."""
        mock_composer = MagicMock()
        
        # Set up _load_podcast method
        mock_composer._load_podcast = AsyncMock()
        mock_composer._load_podcast.return_value = Podcast(
            title="Test Podcast",
            segments=[
                PodcastSegment(
                    segment_type=SegmentType.INTRO,
                    content="This is a test intro.",
                    voice_name=None,
                    voice_style=None
                ),
                PodcastSegment(
                    segment_type=SegmentType.STORY,
                    content="This is a test story segment.",
                    voice_name=None,
                    voice_style=None
                )
            ]
        )
        
        return mock_composer
    
    @pytest.fixture
    def generator(self, mock_config, mock_resource_id_manager, mock_podcast_composer, mock_audio_generator):
        """Create an MCP audio generator instance."""
        return MCPAudioGenerator(mock_config, mock_resource_id_manager, mock_podcast_composer)
    
    @pytest.mark.asyncio
    async def test_generate_audio(self, generator):
        """Test generating audio for a podcast."""
        # Mock the os.path.getmtime function to return a fixed timestamp
        with patch("os.path.getmtime", return_value=12345):
            # Generate audio
            audio_id, audio_resource = await generator.generate_audio(
                podcast_id="test-podcast-id",
                voice_name="en-US-JennyNeural",
                voice_style="cheerful"
            )
            
            # Check result
            assert audio_id == "test-audio-id"
            assert audio_resource.audio_id == "test-audio-id"
            assert audio_resource.podcast_id == "test-podcast-id"
            assert audio_resource.voice_name == "en-US-JennyNeural"
            assert audio_resource.voice_style == "cheerful"
            assert len(audio_resource.segment_paths) == 2
            
            # Check that resource_id_manager was called
            generator.resource_id_manager.add_mapping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_audio(self, generator):
        """Test generating a test audio."""
        # Mock the os.path.getmtime function to return a fixed timestamp
        with patch("os.path.getmtime", return_value=12345):
            # Generate test audio
            audio_id, audio_resource = await generator.test_audio(
                text="This is a test.",
                voice_name="en-US-JennyNeural",
                voice_style="cheerful"
            )
            
            # Check result
            assert audio_id == "test-audio-id"
            assert audio_resource.audio_id == "test-audio-id"
            assert audio_resource.podcast_id == "test"
            assert audio_resource.voice_name == "en-US-JennyNeural"
            assert audio_resource.voice_style == "cheerful"
            
            # Check that resource_id_manager was called
            generator.resource_id_manager.add_mapping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_voices(self, generator):
        """Test getting voices."""
        # Get voices
        voices = await generator.get_voices()
        
        # Check result
        assert len(voices) >= 1
        assert "name" in voices[0]
        
        # Get voices with gender filter
        voices = await generator.get_voices(gender="Female")
        
        # Check that the voice_config.get_recommended_voices method was called
        generator.voice_config.get_recommended_voices.assert_called_with("Female")