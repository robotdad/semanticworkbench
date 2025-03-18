"""
Audio generator service for text-to-speech conversion.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable, Awaitable

import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import SpeechSynthesisOutputFormat, SpeechSynthesizer
from azure.cognitiveservices.speech.audio import AudioOutputConfig

from mcp.server.fastmcp import Context

from ..config import Settings
from ..models.domain import Podcast, PodcastSegment, VoiceConfig
from ..models.resource import AudioResource
from ..utils.progress_reporter import ProgressReporter
from ..utils.resource_id_manager import ResourceIDManager


class AudioGeneratorService:
    """Implementation of audio generator using Azure Speech Services."""
    
    def __init__(self, 
                 speech_region: str, 
                 speech_key: str,
                 host_voice: str = "en-US-JennyNeural", 
                 reporter_voices: Optional[List[str]] = None,
                 default_voice: Optional[str] = None, 
                 default_voice_style: Optional[str] = None,
                 voice_config: Optional[VoiceConfig] = None):
        """Initialize the audio generator service.
        
        Args:
            speech_region: Azure Speech Services region
            speech_key: Azure Speech Services key
            host_voice: Voice to use for host segments (intro/outro)
            reporter_voices: List of voices to use for reporter segments (stories)
            default_voice: Default voice to use if not specified
            default_voice_style: Default voice style to use if not specified
            voice_config: Voice configuration
        """
        self.speech_region = speech_region
        self.speech_key = speech_key
        self.host_voice = host_voice
        self.reporter_voices = reporter_voices or ["en-US-GuyNeural", "en-US-DavisNeural"]
        self.default_voice = default_voice or host_voice
        self.default_voice_style = default_voice_style
        self.voice_config = voice_config or VoiceConfig(
            host_voice=host_voice, 
            reporter_voices=self.reporter_voices,
            default_voice=self.default_voice,
            default_voice_style=self.default_voice_style
        )
        
        # Create speech config
        self.speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=speech_region
        )
        self.speech_config.set_speech_synthesis_output_format(
            SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )
        
        self.logger = logging.getLogger("mcp-server-podcast.audio-generator")
        self.progress_callback = None
        
    def set_progress_callback(self, callback: Callable[[int, str, Optional[Dict[str, Any]]], Awaitable[None]]) -> None:
        """Set a callback for progress reporting.
        
        Args:
            callback: Progress callback function
        """
        self.progress_callback = callback
    
    async def _report_progress(self, percentage: int, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Report progress using the callback if set.
        
        Args:
            percentage: Progress percentage (0-100)
            status: Status message
            details: Optional details
        """
        if self.progress_callback:
            await self.progress_callback(percentage, status, details)
        else:
            self.logger.debug(f"Progress: {percentage}% - {status}")
    
    async def generate_audio_for_segment(self, 
                                        segment: PodcastSegment, 
                                        output_path: Path,
                                        output_filename: Optional[str] = None,
                                        voice_name: Optional[str] = None, 
                                        voice_style: Optional[str] = None) -> Path:
        """Generate audio for a single podcast segment.
        
        Args:
            segment: Podcast segment to generate audio for
            output_path: Directory to save the audio file
            output_filename: Optional filename for the audio file
            voice_name: Optional voice name to override segment voice
            voice_style: Optional voice style to override segment style
            
        Returns:
            Path to the generated audio file
        """
        # Determine voice name and style
        selected_voice = voice_name or segment.voice_name or self._get_voice_for_segment(segment)
        selected_style = voice_style or segment.voice_style or self._get_style_for_voice(selected_voice)
        
        # Determine output filename
        if not output_filename:
            segment_type = segment.segment_type
            timestamp = int(time.time())
            output_filename = f"{segment_type}_{timestamp}.mp3"
            
        # Create output file path
        output_file = output_path / output_filename
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create audio config
        audio_config = AudioOutputConfig(filename=str(output_file))
        
        # Create synthesizer
        synthesizer = SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Create SSML
        ssml = self._create_ssml(segment.content, selected_voice, selected_style)
        
        # Synthesize speech
        self.logger.info(f"Generating audio for segment with voice {selected_voice}, style {selected_style}")
        result = synthesizer.speak_ssml_async(ssml).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            self.logger.info(f"Audio generated successfully: {output_file}")
            return output_file
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = speechsdk.SpeechSynthesisCancellationDetails(result)
            self.logger.error(f"Audio generation canceled: {cancellation.reason}")
            self.logger.error(f"Error details: {cancellation.error_details}")
            raise Exception(f"Audio generation failed: {cancellation.error_details}")
        else:
            self.logger.error(f"Audio generation failed with reason: {result.reason}")
            raise Exception(f"Audio generation failed with reason: {result.reason}")
    
    async def generate_audio_for_podcast(self, 
                                        podcast: Podcast, 
                                        output_path: Path,
                                        output_filename: Optional[str] = None,
                                        generate_segments: bool = True,
                                        voice_name: Optional[str] = None,
                                        voice_style: Optional[str] = None) -> Tuple[Path, Dict[str, Path]]:
        """Generate audio for a complete podcast.
        
        Args:
            podcast: Podcast to generate audio for
            output_path: Directory to save the audio files
            output_filename: Optional filename for the main audio file
            generate_segments: Whether to generate separate files for each segment
            voice_name: Optional voice name to override podcast voices
            voice_style: Optional voice style to override podcast styles
            
        Returns:
            Tuple of path to the main audio file and dictionary mapping segment indices to segment audio files
        """
        # Determine output filename
        if not output_filename:
            sanitized_title = podcast.title.replace(" ", "_").lower()
            timestamp = int(time.time())
            output_filename = f"{sanitized_title}_{timestamp}.mp3"
            
        # Create output path
        output_path.mkdir(parents=True, exist_ok=True)
        output_file = output_path / output_filename
        
        # Generate audio for each segment if requested
        segment_files = {}
        total_segments = len(podcast.segments)
        
        if generate_segments:
            for i, segment in enumerate(podcast.segments):
                # Report progress
                progress_pct = int(i / total_segments * 90)
                await self._report_progress(
                    progress_pct, 
                    f"Generating audio for segment {i+1}/{total_segments}",
                    {"segment_index": i, "segment_type": segment.segment_type}
                )
                
                # Generate audio for segment
                segment_filename = f"segment_{i}_{segment.segment_type}.mp3"
                segment_file = await self.generate_audio_for_segment(
                    segment=segment,
                    output_path=output_path,
                    output_filename=segment_filename,
                    voice_name=voice_name,
                    voice_style=voice_style
                )
                
                segment_files[str(i)] = segment_file
        
        # In a real implementation, we would combine all the segment files into one
        # For simplicity, we'll just copy the first segment file as the complete podcast
        if segment_files:
            # This is a placeholder implementation - a real implementation would concatenate the audio files
            # For now, we'll use the first segment as the main file
            first_segment_file = segment_files.get("0")
            if first_segment_file and first_segment_file.exists():
                # Copy the first segment file to the output file
                with open(first_segment_file, "rb") as src, open(output_file, "wb") as dst:
                    dst.write(src.read())
        else:
            # Generate a full podcast audio if segments weren't generated
            # This is not implemented in this simplified version
            self.logger.warning("Generating full podcast audio without segments is not implemented")
            # Create an empty file as a placeholder
            output_file.touch()
            
        await self._report_progress(100, "Audio generation complete")
        
        return output_file, segment_files
    
    async def get_available_voices(self, locale: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get a list of available voices.
        
        Args:
            locale: Optional locale to filter voices by
            
        Returns:
            List of voice information dictionaries
        """
        # In a real implementation, this would query the Azure Speech Services API
        # For simplicity, we'll return a hardcoded list
        voices = [
            {
                "name": "en-US-JennyNeural", 
                "gender": "Female", 
                "locale": "en-US",
                "styles": ["chat", "cheerful", "empathetic"]
            },
            {
                "name": "en-US-GuyNeural", 
                "gender": "Male", 
                "locale": "en-US",
                "styles": ["newscast", "calm"]
            },
            {
                "name": "en-US-DavisNeural", 
                "gender": "Male", 
                "locale": "en-US",
                "styles": ["chat", "narration-professional"]
            },
            {
                "name": "en-US-AriaNeural", 
                "gender": "Female", 
                "locale": "en-US",
                "styles": ["newscast", "narration-professional", "customerservice"]
            }
        ]
        
        if locale:
            return [v for v in voices if v["locale"] == locale]
        return voices
    
    def _get_voice_for_segment(self, segment: PodcastSegment) -> str:
        """Determine the appropriate voice for a segment based on its type.
        
        Args:
            segment: Podcast segment
            
        Returns:
            Voice name
        """
        segment_type = segment.segment_type
        
        if segment_type in ("intro", "outro"):
            return self.voice_config.host_voice
        elif segment_type == "story":
            # Rotate through reporter voices if multiple segments
            # This is a simple implementation; a more sophisticated one would ensure
            # consistent voice assignment
            return self.reporter_voices[0]
        else:
            return self.default_voice
    
    def _get_style_for_voice(self, voice_name: str) -> Optional[str]:
        """Get an appropriate style for a voice.
        
        Args:
            voice_name: Voice name
            
        Returns:
            Voice style or None if no specific style
        """
        # Map voices to default styles
        style_map = {
            "en-US-JennyNeural": "cheerful",
            "en-US-GuyNeural": "newscast",
            "en-US-DavisNeural": "narration-professional",
            "en-US-AriaNeural": "newscast"
        }
        
        return style_map.get(voice_name, self.default_voice_style)
    
    def _create_ssml(self, text: str, voice_name: str, voice_style: Optional[str] = None) -> str:
        """Create SSML markup for text-to-speech.
        
        Args:
            text: Text to convert to speech
            voice_name: Voice to use
            voice_style: Optional voice style
            
        Returns:
            SSML markup
        """
        # Basic sanitization
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Create SSML with or without style
        if voice_style:
            ssml = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
                <voice name="{voice_name}">
                    <mstts:express-as style="{voice_style}">
                        {text}
                    </mstts:express-as>
                </voice>
            </speak>
            """
        else:
            ssml = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
                <voice name="{voice_name}">
                    {text}
                </voice>
            </speak>
            """
            
        return ssml


class MCPAudioGenerator:
    """MCP wrapper for the AudioGeneratorService."""
    
    def __init__(self, config: Settings, resource_id_manager: ResourceIDManager, podcast_composer):
        """Initialize the MCP audio generator.
        
        Args:
            config: Application configuration
            resource_id_manager: Resource ID manager
            podcast_composer: Podcast composer service for loading podcasts
        """
        self.voice_config = VoiceConfig(
            host_voice=config.speech_host_voice,
            reporter_voices=config.speech_reporter_voices
        )
        
        self.audio_generator = AudioGeneratorService(
            speech_region=config.speech_region,
            speech_key=config.speech_key,
            host_voice=config.speech_host_voice,
            reporter_voices=config.speech_reporter_voices,
            voice_config=self.voice_config
        )
        
        self.storage_path = config.mcp_storage_path
        self.audio_storage_path = self.storage_path / "audio"
        self.audio_storage_path.mkdir(parents=True, exist_ok=True)
        
        self.resource_id_manager = resource_id_manager
        self.podcast_composer = podcast_composer
        self.logger = logging.getLogger("mcp-server-podcast.mcp-audio-generator")
    
    async def generate_audio(self, 
                           podcast_id: str, 
                           voice_name: Optional[str] = None, 
                           voice_style: Optional[str] = None,
                           ctx: Optional[Context] = None) -> Tuple[str, AudioResource]:
        """Generate audio for a podcast and return an audio ID.
        
        Args:
            podcast_id: ID of the podcast to generate audio for
            voice_name: Optional voice name to override podcast voices
            voice_style: Optional voice style to override podcast styles
            ctx: MCP context for progress reporting
            
        Returns:
            Tuple of audio ID and audio resource
        """
        progress = ProgressReporter(ctx)
        await progress.report_progress(0, "Starting audio generation...")
        
        # Set up progress callback
        self.audio_generator.set_progress_callback(progress.report_progress)
        
        # Load podcast
        podcast = await self._load_podcast(podcast_id)
        if not podcast:
            raise ValueError(f"Podcast not found with ID: {podcast_id}")
            
        await progress.report_progress(10, "Loaded podcast, generating audio...")
        
        # Set up output path
        audio_id = self.resource_id_manager.generate_id("audio")
        output_path = self.audio_storage_path / audio_id
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate audio
        main_audio_file, segment_files = await self.audio_generator.generate_audio_for_podcast(
            podcast=podcast,
            output_path=output_path,
            generate_segments=True,
            voice_name=voice_name,
            voice_style=voice_style
        )
        
        await progress.report_progress(95, "Audio generated, storing results...")
        
        # Convert segment files dict to use proper paths
        segment_paths = {segment_id: path for segment_id, path in segment_files.items()}
        
        # Create audio resource
        audio_resource = AudioResource(
            audio_id=audio_id,
            podcast_id=podcast_id,
            audio_path=main_audio_file,
            segment_paths=segment_paths,
            voice_name=voice_name,
            voice_style=voice_style,
            metadata={
                "podcast_id": podcast_id,
                "voice_name": voice_name,
                "voice_style": voice_style,
                "segment_count": len(segment_paths),
                "created_at": os.path.getmtime(main_audio_file),
                "format": "mp3"
            }
        )
        
        # Register with resource manager
        self.resource_id_manager.add_mapping(
            resource_type="audio",
            resource_id=audio_id,
            file_path=main_audio_file,
            metadata={
                "podcast_id": podcast_id,
                "voice_name": voice_name,
                "voice_style": voice_style,
                "segment_paths": {segment_id: str(path) for segment_id, path in segment_paths.items()},
                "audio_path": str(main_audio_file),
                "created_at": os.path.getmtime(main_audio_file),
                "format": "mp3"
            }
        )
        
        await progress.report_progress(100, "Audio generation complete")
        
        return audio_id, audio_resource
    
    async def test_audio(self, 
                       text: str, 
                       voice_name: Optional[str] = None, 
                       voice_style: Optional[str] = None,
                       ctx: Optional[Context] = None) -> Tuple[str, AudioResource]:
        """Generate a test audio sample from text.
        
        Args:
            text: Text to convert to speech
            voice_name: Optional voice name
            voice_style: Optional voice style
            ctx: MCP context for progress reporting
            
        Returns:
            Tuple of audio ID and audio resource
        """
        progress = ProgressReporter(ctx)
        await progress.report_progress(0, "Starting test audio generation...")
        
        # Create a test segment
        from ..models.domain import PodcastSegment, SegmentType
        test_segment = PodcastSegment(
            segment_type=SegmentType.STORY,
            content=text,
            voice_name=voice_name,
            voice_style=voice_style
        )
        
        # Set up output path
        audio_id = self.resource_id_manager.generate_id("audio")
        output_path = self.audio_storage_path / audio_id
        output_path.mkdir(parents=True, exist_ok=True)
        
        await progress.report_progress(20, "Generating test audio...")
        
        # Generate audio for the segment
        audio_file = await self.audio_generator.generate_audio_for_segment(
            segment=test_segment,
            output_path=output_path,
            output_filename="test_audio.mp3",
            voice_name=voice_name,
            voice_style=voice_style
        )
        
        # Create audio resource
        audio_resource = AudioResource(
            audio_id=audio_id,
            podcast_id="test",
            audio_path=audio_file,
            segment_paths={"0": audio_file},
            voice_name=voice_name,
            voice_style=voice_style,
            metadata={
                "test": True,
                "text": text,
                "voice_name": voice_name,
                "voice_style": voice_style,
                "created_at": os.path.getmtime(audio_file),
                "format": "mp3"
            }
        )
        
        # Register with resource manager
        self.resource_id_manager.add_mapping(
            resource_type="audio",
            resource_id=audio_id,
            file_path=audio_file,
            metadata={
                "test": True,
                "text": text,
                "voice_name": voice_name,
                "voice_style": voice_style,
                "audio_path": str(audio_file),
                "created_at": os.path.getmtime(audio_file),
                "format": "mp3"
            }
        )
        
        await progress.report_progress(100, "Test audio generation complete")
        
        return audio_id, audio_resource
    
    async def get_voices(self, gender: Optional[str] = None, locale: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available or recommended voices.
        
        Args:
            gender: Optional gender to filter by
            locale: Optional locale to filter by
            
        Returns:
            List of voice information dictionaries
        """
        if gender:
            return self.voice_config.get_recommended_voices(gender)
        else:
            voices = await self.audio_generator.get_available_voices(locale)
            return voices
    
    async def _load_podcast(self, podcast_id: str) -> Optional[Podcast]:
        """Load a podcast from storage.
        
        Args:
            podcast_id: ID of the podcast
            
        Returns:
            Podcast object or None if not found
        """
        try:
            # Use the podcast composer to load the podcast
            return await self.podcast_composer._load_podcast(podcast_id)
        except Exception as e:
            self.logger.error(f"Error loading podcast {podcast_id}: {str(e)}")
            return None