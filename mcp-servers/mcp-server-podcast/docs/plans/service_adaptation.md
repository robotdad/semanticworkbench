# Podcastly Service Adaptation Plan

This document outlines how the existing Podcastly services will be adapted for use within the MCP server architecture.

## Overview

Podcastly follows a clean architecture with well-defined interfaces and service implementations. We'll leverage this design to adapt the services for MCP while minimizing code duplication and maintaining the core business logic.

## Service Adaptation Strategy

For each Podcastly service, we'll follow this adaptation pattern:

1. Create an MCP-specific wrapper around the existing service
2. Implement MCP-specific concerns (resource management, progress reporting)
3. Bridge between MCP tools/resources and Podcastly interfaces
4. Maintain the core business logic from the original service

## Service-by-Service Adaptation

### 1. Document Processor

#### Original Implementation: `AzureDocumentProcessor`

```python
class AzureDocumentProcessor:
    """Implementation of DocumentProcessor using Azure Document Intelligence."""
    
    def __init__(self, endpoint: str, api_key: str, model_id: str, use_managed_identity: bool = False):
        # Initialization logic
        
    async def extract_text(self, document_path: Path) -> ExtractTextResult:
        # Text extraction logic
        
    async def extract_text_batch(self, document_paths: List[Path]) -> List[ExtractTextResult]:
        # Batch extraction logic
```

#### MCP Adaptation

```python
class MCPDocumentProcessor:
    """MCP wrapper for the AzureDocumentProcessor."""
    
    def __init__(self, config: AppConfig):
        self.document_processor = AzureDocumentProcessor(
            endpoint=config.document_intelligence_endpoint,
            api_key=config.document_intelligence_api_key,
            model_id=config.document_intelligence_model_id,
            use_managed_identity=config.use_managed_identity
        )
        self.storage_path = config.mcp_storage_path
        
    async def process_document(self, document_content: bytes, document_name: str) -> str:
        """Process document content and return a document ID."""
        # Save document to temporary storage
        document_id = self._generate_document_id()
        document_path = self._store_document(document_content, document_name, document_id)
        
        # Process the document
        result = await self.document_processor.extract_text(document_path)
        
        # Store the result for access via resources
        self._store_extraction_result(document_id, result)
        
        return document_id
        
    def _generate_document_id(self) -> str:
        # Generate unique document ID
        
    def _store_document(self, content: bytes, name: str, document_id: str) -> Path:
        # Store document content
        
    def _store_extraction_result(self, document_id: str, result: ExtractTextResult) -> None:
        # Store extraction result for resource access
```

### 2. OpenAI Agent

#### Original Implementation: `AzureOpenAIAgent`

```python
class AzureOpenAIAgent:
    """Implementation of OpenAIAgent using Azure OpenAI."""
    
    def __init__(self, endpoint: str, api_key: str, api_version: str, deployment_name: str,
                 use_managed_identity: bool = False, target_podcast_length_minutes: int = 5,
                 show_prompts: bool = False, custom_prompt_file: Optional[Path] = None):
        # Initialization logic
        
    async def generate_story_segments(self, extraction_result: ExtractTextResult) -> List[PodcastStorySegment]:
        # Story segment generation logic
        
    async def generate_story_segments_batch(self, extraction_results: List[ExtractTextResult]) -> List[PodcastStorySegment]:
        # Batch segment generation logic
```

#### MCP Adaptation

```python
class MCPOpenAIAgent:
    """MCP wrapper for the AzureOpenAIAgent."""
    
    def __init__(self, config: AppConfig):
        self.openai_agent = AzureOpenAIAgent(
            endpoint=config.azure_openai_endpoint,
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version,
            deployment_name=config.azure_openai_deployment,
            use_managed_identity=config.use_managed_identity
        )
        self.storage_path = config.mcp_storage_path
        
    async def generate_podcast(self, document_ids: List[str], podcast_title: Optional[str] = None, 
                               length_minutes: int = 5, custom_prompt: Optional[str] = None) -> str:
        """Generate a podcast from document IDs and return a podcast ID."""
        # Retrieve extraction results for document IDs
        extraction_results = self._load_extraction_results(document_ids)
        
        # Set custom parameters
        self.openai_agent.target_podcast_length_minutes = length_minutes
        if custom_prompt:
            self.openai_agent.set_custom_prompt(custom_prompt)
            
        # Report progress
        await self._report_progress(10, "Generating story segments...")
        
        # Generate story segments
        story_segments = await self.openai_agent.generate_story_segments_batch(extraction_results)
        
        # Store the result for access via resources
        podcast_id = self._generate_podcast_id()
        self._store_story_segments(podcast_id, story_segments)
        
        await self._report_progress(100, "Podcast generation complete")
        
        return podcast_id
        
    def _load_extraction_results(self, document_ids: List[str]) -> List[ExtractTextResult]:
        # Load extraction results from storage
        
    def _generate_podcast_id(self) -> str:
        # Generate unique podcast ID
        
    def _store_story_segments(self, podcast_id: str, segments: List[PodcastStorySegment]) -> None:
        # Store story segments for resource access
        
    async def _report_progress(self, percentage: int, status: str) -> None:
        # Report progress to MCP client
```

### 3. Podcast Composer

#### Original Implementation: `PodcastComposerService`

```python
class PodcastComposerService:
    """Implementation of PodcastComposer using OpenAI for transitions, intros, and outros."""
    
    def __init__(self, openai_agent: AzureOpenAIAgent):
        self.openai_agent = openai_agent
        
    async def create_intro(self, story_segments: List[PodcastStorySegment], podcast_title: str) -> PodcastSegment:
        # Intro creation logic
        
    async def create_transition(self, from_segment: PodcastStorySegment, to_segment: PodcastStorySegment) -> PodcastSegment:
        # Transition creation logic
        
    async def create_outro(self, story_segments: List[PodcastStorySegment], podcast_title: str) -> PodcastSegment:
        # Outro creation logic
        
    async def compose_podcast(self, story_segments: List[PodcastStorySegment], 
                              podcast_title: Optional[str] = None) -> Podcast:
        # Podcast composition logic
```

#### MCP Adaptation

```python
class MCPPodcastComposer:
    """MCP wrapper for the PodcastComposerService."""
    
    def __init__(self, config: AppConfig, mcp_openai_agent: MCPOpenAIAgent):
        self.openai_agent = mcp_openai_agent.openai_agent
        self.podcast_composer = PodcastComposerService(self.openai_agent)
        self.storage_path = config.mcp_storage_path
        
    async def compose_podcast(self, podcast_id: str, title: Optional[str] = None) -> str:
        """Compose a complete podcast from stored story segments."""
        # Load story segments for the podcast ID
        story_segments = self._load_story_segments(podcast_id)
        
        # Report progress
        await self._report_progress(10, "Composing podcast...")
        
        # Compose the podcast
        podcast = await self.podcast_composer.compose_podcast(story_segments, title)
        
        # Store the composed podcast for resource access
        self._store_podcast(podcast_id, podcast)
        
        await self._report_progress(100, "Podcast composition complete")
        
        return podcast_id
        
    def _load_story_segments(self, podcast_id: str) -> List[PodcastStorySegment]:
        # Load story segments from storage
        
    def _store_podcast(self, podcast_id: str, podcast: Podcast) -> None:
        # Store composed podcast for resource access
        
    async def _report_progress(self, percentage: int, status: str) -> None:
        # Report progress to MCP client
```

### 4. Audio Generator

#### Original Implementation: `AudioGeneratorService`

```python
class AudioGeneratorService:
    """Implementation of AudioGenerator using Azure Speech Services."""
    
    def __init__(self, speech_resource_id: str, speech_region: str, speech_key: Optional[str] = None,
                 host_voice: str = "en-US-JennyNeural", reporter_voices: Optional[List[str]] = None,
                 default_voice: Optional[str] = None, default_voice_style: Optional[str] = None,
                 use_managed_identity: bool = False, voice_config: Optional[VoiceConfig] = None):
        # Initialization logic
        
    async def generate_audio_for_segment(self, segment: PodcastSegment, output_path: Path,
                                         voice_name: Optional[str] = None, voice_style: Optional[str] = None) -> Path:
        # Segment audio generation logic
        
    async def generate_audio_for_podcast(self, podcast: Podcast, output_path: Path,
                                         output_filename: Optional[str] = None,
                                         generate_segments: bool = True,
                                         voice_name: Optional[str] = None,
                                         voice_style: Optional[str] = None) -> Path:
        # Podcast audio generation logic
        
    async def get_available_voices(self) -> List[Dict[str, str]]:
        # Voice listing logic
```

#### MCP Adaptation

```python
class MCPAudioGenerator:
    """MCP wrapper for the AudioGeneratorService."""
    
    def __init__(self, config: AppConfig):
        self.voice_config = VoiceConfig()
        self.audio_generator = AudioGeneratorService(
            speech_resource_id=config.speech_resource_id,
            speech_region=config.speech_region,
            speech_key=config.speech_key,
            host_voice=config.speech_host_voice,
            reporter_voices=config.speech_reporter_voices,
            use_managed_identity=config.use_managed_identity,
            voice_config=self.voice_config
        )
        self.storage_path = config.mcp_storage_path
        
    async def generate_audio(self, podcast_id: str, voice_name: Optional[str] = None, 
                            voice_style: Optional[str] = None) -> str:
        """Generate audio for a podcast and return an audio ID."""
        # Load podcast from storage
        podcast = self._load_podcast(podcast_id)
        
        # Set up output path
        output_path = self.storage_path / "audio"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Report initial progress
        await self._report_progress(10, "Generating audio...")
        
        # Generate audio with progress updates
        self._setup_progress_callback()
        audio_file = await self.audio_generator.generate_audio_for_podcast(
            podcast=podcast,
            output_path=output_path,
            generate_segments=True,
            voice_name=voice_name,
            voice_style=voice_style
        )
        
        # Generate audio ID and store mapping
        audio_id = self._generate_audio_id()
        self._store_audio_mapping(audio_id, audio_file)
        
        await self._report_progress(100, "Audio generation complete")
        
        return audio_id
        
    def _load_podcast(self, podcast_id: str) -> Podcast:
        # Load podcast from storage
        
    def _generate_audio_id(self) -> str:
        # Generate unique audio ID
        
    def _store_audio_mapping(self, audio_id: str, audio_file: Path) -> None:
        # Store mapping between audio ID and file path
        
    def _setup_progress_callback(self) -> None:
        # Set up callback for progress reporting from audio generator
        
    async def _report_progress(self, percentage: int, status: str) -> None:
        # Report progress to MCP client
        
    async def get_voices(self, gender: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available or recommended voices."""
        if gender:
            return self.voice_config.get_recommended_voices(gender)
        else:
            return await self.audio_generator.get_available_voices()
```

## MCP Resource Handlers

In addition to the service adaptations, we'll need to implement resource handlers to expose data through MCP resources:

```python
class PodcastMCPResources:
    """Handlers for podcast MCP resources."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        
    async def get_document_content(self, document_id: str) -> Tuple[str, str]:
        """Get document content for document://{document_id} resource."""
        # Load and return document text content with MIME type
        
    async def get_document_metadata(self, document_id: str) -> Tuple[str, str]:
        """Get document metadata for document://{document_id}/metadata resource."""
        # Load and return document metadata with MIME type
        
    async def get_podcast_script(self, podcast_id: str) -> Tuple[str, str]:
        """Get podcast script for podcast://{podcast_id}/script resource."""
        # Load and return podcast script with MIME type
        
    async def get_podcast_segments(self, podcast_id: str) -> Tuple[str, str]:
        """Get podcast segments for podcast://{podcast_id}/segments resource."""
        # Load and return podcast segments with MIME type
        
    async def get_audio_file(self, audio_id: str) -> Tuple[bytes, str]:
        """Get audio file for audio://{audio_id} resource."""
        # Load and return audio file with MIME type
        
    async def get_voice_list(self) -> Tuple[str, str]:
        """Get voice list for voices://list resource."""
        # Load and return voice list with MIME type
```

## Resource ID Management

We'll implement a centralized resource ID management system:

```python
class ResourceIDManager:
    """Manages resource IDs and mappings."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.mappings_file = storage_path / "resource_mappings.json"
        self.mappings = self._load_mappings()
        
    def _load_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Load resource mappings from storage."""
        # Load and return mappings
        
    def _save_mappings(self) -> None:
        """Save resource mappings to storage."""
        # Save mappings
        
    def generate_id(self, resource_type: str) -> str:
        """Generate a unique ID for a resource type."""
        # Generate and return unique ID
        
    def add_mapping(self, resource_type: str, resource_id: str, file_path: Path, metadata: Dict[str, Any] = None) -> None:
        """Add a mapping for a resource ID."""
        # Add mapping and save
        
    def get_file_path(self, resource_type: str, resource_id: str) -> Optional[Path]:
        """Get file path for a resource ID."""
        # Get and return file path
        
    def get_metadata(self, resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a resource ID."""
        # Get and return metadata
```

## Progress Reporting

We'll implement a standardized progress reporting mechanism:

```python
class ProgressReporter:
    """Reports progress for long-running operations."""
    
    def __init__(self, ctx: Context):
        self.ctx = ctx
        
    async def report_progress(self, percentage: int, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Report progress to the MCP client."""
        # Report progress using MCP context
```

## MCP FastMCP Server Integration

Finally, we'll integrate all components into the MCP FastMCP server:

```python
from mcp.server.fastmcp import FastMCP, Context, Image

# Create the MCP server
mcp = FastMCP("Podcast Generator")

# Initialize services
document_processor = MCPDocumentProcessor(config)
openai_agent = MCPOpenAIAgent(config)
podcast_composer = MCPPodcastComposer(config, openai_agent)
audio_generator = MCPAudioGenerator(config)
resource_manager = ResourceIDManager(config.mcp_storage_path)
resources = PodcastMCPResources(config.mcp_storage_path)

# Register resource handlers
@mcp.resource("document://{document_id}")
async def get_document(document_id: str) -> str:
    return await resources.get_document_content(document_id)

# Register tool handlers
@mcp.tool()
async def upload_document(document_content: str, document_name: str, ctx: Context) -> str:
    """Upload a document for podcast generation."""
    progress = ProgressReporter(ctx)
    await progress.report_progress(0, "Starting document upload...")
    
    # Decode base64 content
    content = base64.b64decode(document_content)
    
    # Process document
    document_id = await document_processor.process_document(content, document_name)
    
    await progress.report_progress(100, "Document upload complete")
    return document_id

# Register prompt handlers
@mcp.prompt()
def podcast_creation(title: Optional[str] = None, topic: Optional[str] = None) -> str:
    """Guide through the podcast creation process."""
    # Return prompt template
```

## Conclusion

This adaptation strategy allows us to leverage the existing Podcastly services while properly integrating them into the MCP architecture. By creating thin MCP-specific wrappers around the core services, we maintain the separation of concerns and make future updates to either codebase easier to manage.