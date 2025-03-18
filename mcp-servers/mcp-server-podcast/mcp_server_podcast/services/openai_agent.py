"""
OpenAI agent service for podcast generation.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import azure.core.credentials
from openai import AsyncAzureOpenAI

from mcp.server.fastmcp import Context

from ..config import Settings
from ..models.domain import ExtractTextResult, PodcastStorySegment
from ..models.resource import PodcastResource
from ..utils.progress_reporter import ProgressReporter
from ..utils.resource_id_manager import ResourceIDManager


class AzureOpenAIAgent:
    """Implementation of OpenAI Agent using Azure OpenAI."""
    
    DEFAULT_PROMPT = """
You are a podcast writer. Your task is to create engaging and informative podcast segments based on the provided document content.
The segments should be conversational, engaging, and suitable for a podcast format.

Document content:
{document_content}

Create {num_segments} distinct segments with the following properties:
1. Each segment should be 1-2 paragraphs long.
2. Each segment should cover a specific topic or point from the document.
3. Each segment should have a clear title that summarizes its content.
4. Write in a conversational tone suitable for a podcast.
5. Each segment should be standalone but related to the overall theme.

Return your response in the following JSON format:
{
  "segments": [
    {
      "title": "Segment Title",
      "content": "Segment content...",
      "source_document": "Document name or ID"
    },
    ...
  ]
}
"""
    
    def __init__(self, 
                 endpoint: str, 
                 api_key: str, 
                 api_version: str, 
                 deployment_name: str,
                 use_managed_identity: bool = False, 
                 target_podcast_length_minutes: int = 5,
                 show_prompts: bool = False, 
                 custom_prompt_file: Optional[Path] = None):
        """Initialize the Azure OpenAI agent.
        
        Args:
            endpoint: Azure OpenAI API endpoint
            api_key: Azure OpenAI API key
            api_version: Azure OpenAI API version
            deployment_name: Azure OpenAI deployment name
            use_managed_identity: Whether to use managed identity for authentication
            target_podcast_length_minutes: Target length of the podcast in minutes
            show_prompts: Whether to show prompts in the logs
            custom_prompt_file: Path to a custom prompt file
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.deployment_name = deployment_name
        self.use_managed_identity = use_managed_identity
        self.target_podcast_length_minutes = target_podcast_length_minutes
        self.show_prompts = show_prompts
        self.logger = logging.getLogger("mcp-server-podcast.azure-openai-agent")
        
        # Set up prompt
        self.prompt_template = self.DEFAULT_PROMPT
        if custom_prompt_file and custom_prompt_file.exists():
            self.logger.info(f"Loading custom prompt from {custom_prompt_file}")
            self.prompt_template = custom_prompt_file.read_text()
        
        # Initialize the client
        if not use_managed_identity:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
            )
        else:
            # In a future version, we might need to add DefaultAzureCredential from azure-identity
            raise NotImplementedError("Managed identity authentication is not yet implemented")
        
    async def generate_story_segments(self, extraction_result: ExtractTextResult) -> List[PodcastStorySegment]:
        """Generate podcast story segments from an extracted text result.
        
        Args:
            extraction_result: Extracted text result from a document
            
        Returns:
            List of podcast story segments
        """
        self.logger.info(f"Generating story segments for document {extraction_result.document_id}")
        
        # Determine number of segments based on podcast length
        # For 5 minutes, we'll generate 3 segments
        num_segments = max(3, self.target_podcast_length_minutes // 2)
        
        # Format the prompt
        prompt = self.prompt_template.format(
            document_content=extraction_result.extracted_text[:3000],  # Limiting to avoid token limits
            num_segments=num_segments
        )
        
        if self.show_prompts:
            self.logger.debug(f"Prompt: {prompt}")
        
        # Call Azure OpenAI
        response = await self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": "You are an expert podcast writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        # Extract content
        content = response.choices[0].message.content
        
        try:
            # Parse JSON response
            result = json.loads(content)
            
            # Create segments
            segments = []
            for segment_data in result["segments"]:
                segment = PodcastStorySegment(
                    title=segment_data["title"],
                    content=segment_data["content"],
                    source_document=extraction_result.document_id,
                    voice_name=None,
                    voice_style=None
                )
                segments.append(segment)
                
            return segments
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Error parsing OpenAI response: {str(e)}")
            self.logger.debug(f"Raw response: {content}")
            
            # Return a default segment if parsing fails
            return [
                PodcastStorySegment(
                    title="Error generating segments",
                    content="There was an error generating podcast segments. Please try again.",
                    source_document=extraction_result.document_id,
                    voice_name=None,
                    voice_style=None
                )
            ]
    
    async def generate_story_segments_batch(self, extraction_results: List[ExtractTextResult]) -> List[PodcastStorySegment]:
        """Generate podcast story segments from multiple extracted text results.
        
        Args:
            extraction_results: List of extracted text results from documents
            
        Returns:
            List of podcast story segments
        """
        all_segments = []
        for result in extraction_results:
            segments = await self.generate_story_segments(result)
            all_segments.extend(segments)
        return all_segments


class MCPOpenAIAgent:
    """MCP wrapper for the AzureOpenAIAgent."""
    
    def __init__(self, config: Settings, resource_id_manager: ResourceIDManager, document_processor):
        """Initialize the MCP OpenAI agent.
        
        Args:
            config: Application configuration
            resource_id_manager: Resource ID manager
            document_processor: Document processor service
        """
        self.openai_agent = AzureOpenAIAgent(
            endpoint=config.azure_openai_endpoint,
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version,
            deployment_name=config.azure_openai_deployment,
            use_managed_identity=config.use_managed_identity,
            target_podcast_length_minutes=config.default_podcast_length_minutes
        )
        
        self.storage_path = config.mcp_storage_path
        self.podcast_storage_path = self.storage_path / "podcasts"
        self.podcast_storage_path.mkdir(parents=True, exist_ok=True)
        
        self.resource_id_manager = resource_id_manager
        self.document_processor = document_processor
        self.logger = logging.getLogger("mcp-server-podcast.mcp-openai-agent")
    
    async def generate_podcast(self, 
                               document_ids: List[str], 
                               podcast_title: Optional[str] = None, 
                               length_minutes: Optional[int] = None, 
                               custom_prompt: Optional[str] = None,
                               ctx: Optional[Context] = None) -> Tuple[str, Dict[str, Any]]:
        """Generate a podcast from document IDs and return a podcast ID.
        
        Args:
            document_ids: List of document IDs to process
            podcast_title: Optional title for the podcast
            length_minutes: Optional target podcast length in minutes
            custom_prompt: Optional custom prompt for script generation
            ctx: MCP context for progress reporting
            
        Returns:
            Tuple of podcast ID and metadata
        """
        progress = ProgressReporter(ctx)
        await progress.report_progress(0, "Starting podcast generation...")
        
        # Set custom parameters
        if length_minutes is not None:
            self.openai_agent.target_podcast_length_minutes = length_minutes
        
        # Retrieve extraction results for document IDs
        extraction_results = await self._load_extraction_results(document_ids)
        if not extraction_results:
            raise ValueError(f"No valid documents found with IDs: {document_ids}")
        
        await progress.report_progress(20, "Loaded document content, generating story segments...")
        
        # Generate story segments
        story_segments = await self.openai_agent.generate_story_segments_batch(extraction_results)
        
        await progress.report_progress(60, "Generated story segments, storing results...")
        
        # Determine podcast title if not provided
        if not podcast_title and len(story_segments) > 0:
            podcast_title = f"Podcast from {len(document_ids)} documents"
        
        # Store the result for access via resources
        podcast_id = self.resource_id_manager.generate_id("podcast")
        podcast_metadata = {
            "podcast_id": podcast_id,
            "title": podcast_title,
            "document_ids": document_ids,
            "segment_count": len(story_segments),
            "status": "segments_generated"
        }
        
        await self._store_story_segments(podcast_id, story_segments, podcast_title)
        
        await progress.report_progress(100, "Podcast segments generation complete")
        
        return podcast_id, podcast_metadata
    
    async def _load_extraction_results(self, document_ids: List[str]) -> List[ExtractTextResult]:
        """Load extraction results from document IDs.
        
        Args:
            document_ids: List of document IDs
            
        Returns:
            List of extraction results
        """
        results = []
        
        for doc_id in document_ids:
            # Get document content
            content = await self.document_processor.get_document_content(doc_id)
            metadata = await self.document_processor.get_document_metadata(doc_id)
            
            if content and metadata:
                result = ExtractTextResult(
                    document_id=doc_id,
                    original_filename=metadata.get("original_filename", f"doc_{doc_id}"),
                    extracted_text=content,
                    page_count=metadata.get("page_count", 1),
                    success=True,
                    metadata=metadata
                )
                results.append(result)
            else:
                self.logger.warning(f"Document not found or no content for ID: {doc_id}")
                
        return results
    
    async def _store_story_segments(self, podcast_id: str, segments: List[PodcastStorySegment], title: str) -> None:
        """Store story segments for a podcast ID.
        
        Args:
            podcast_id: Podcast ID
            segments: List of podcast story segments
            title: Podcast title
        """
        # Create podcast directory
        podcast_dir = self.podcast_storage_path / podcast_id
        podcast_dir.mkdir(parents=True, exist_ok=True)
        
        # Store segments
        segments_path = podcast_dir / "segments.json"
        segments_data = {
            "podcast_id": podcast_id,
            "title": title,
            "segments": [
                {
                    "title": segment.title,
                    "content": segment.content,
                    "source_document": segment.source_document,
                    "segment_type": segment.segment_type
                }
                for segment in segments
            ]
        }
        
        with open(segments_path, "w") as f:
            json.dump(segments_data, indent=2, f)
            
        # Create metadata path
        metadata_path = podcast_dir / "metadata.json"
        metadata = {
            "podcast_id": podcast_id,
            "title": title,
            "segment_count": len(segments),
            "created_at": os.path.getmtime(segments_path),
            "status": "segments_generated"
        }
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, indent=2, f)
        
        # Register with resource manager
        self.resource_id_manager.add_mapping(
            resource_type="podcast",
            resource_id=podcast_id,
            file_path=segments_path,
            metadata={
                "title": title,
                "segment_count": len(segments),
                "metadata_path": str(metadata_path),
                "segments_path": str(segments_path),
                "status": "segments_generated"
            }
        )