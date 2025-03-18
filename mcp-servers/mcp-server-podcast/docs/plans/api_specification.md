# Podcast MCP Server API Specification

This document defines the API specification for the Podcast MCP Server, outlining the resources, tools, and prompts that will be implemented.

## Resources

### 1. Document Resources

#### `document://{document_id}`
- **Description**: Access a processed document by ID
- **Returns**: Extracted text content from the document
- **MIME Type**: `text/plain`

#### `document://{document_id}/metadata`
- **Description**: Access metadata about a processed document
- **Returns**: JSON metadata including file name, page count, and processing status
- **MIME Type**: `application/json`

### 2. Podcast Resources

#### `podcast://{podcast_id}/script`
- **Description**: Access the generated podcast script
- **Returns**: Full text of the podcast script
- **MIME Type**: `text/plain`

#### `podcast://{podcast_id}/segments`
- **Description**: Access individual podcast segments
- **Returns**: JSON array of podcast segments with type and content
- **MIME Type**: `application/json`

#### `podcast://{podcast_id}/metadata`
- **Description**: Access metadata about a generated podcast
- **Returns**: JSON metadata including title, generation date, and segment count
- **MIME Type**: `application/json`

### 3. Audio Resources

#### `audio://{audio_id}`
- **Description**: Access a generated audio file
- **Returns**: MP3 audio file of the generated podcast
- **MIME Type**: `audio/mpeg`

#### `audio://{audio_id}/segment/{segment_id}`
- **Description**: Access audio for a specific podcast segment
- **Returns**: MP3 audio file of the specific segment
- **MIME Type**: `audio/mpeg`

### 4. Voice Resources

#### `voices://list`
- **Description**: List all available voices
- **Returns**: JSON array of available voices with properties
- **MIME Type**: `application/json`

#### `voices://recommended`
- **Description**: List recommended voices for podcasts
- **Returns**: JSON array of recommended voices with descriptions
- **MIME Type**: `application/json`

## Tools

### 1. Document Processing Tools

#### `upload_document`
- **Description**: Upload a document for podcast generation
- **Parameters**:
  - `document_content` (string, required): Base64-encoded document content
  - `document_name` (string, required): Original filename
  - `document_type` (string, optional): MIME type of the document
- **Returns**: Document ID for the uploaded document

#### `extract_text`
- **Description**: Extract text from an uploaded document
- **Parameters**:
  - `document_id` (string, required): ID of the uploaded document
- **Returns**: Extraction result with document ID and status

### 2. Podcast Generation Tools

#### `generate_podcast`
- **Description**: Generate a podcast script from documents
- **Parameters**:
  - `document_ids` (array, required): List of document IDs to process
  - `title` (string, optional): Custom title for the podcast
  - `length` (integer, optional): Target podcast length in minutes (default: 5)
  - `custom_prompt` (string, optional): Custom prompt for script generation
- **Returns**: Podcast ID for the generated podcast

#### `customize_podcast`
- **Description**: Customize podcast generation settings
- **Parameters**:
  - `podcast_id` (string, required): ID of the podcast to customize
  - `show_transitions` (boolean, optional): Include transition segments (default: true)
  - `format` (string, optional): Podcast format (conversational, narrative, etc.)
- **Returns**: Updated podcast ID

### 3. Audio Generation Tools

#### `generate_audio`
- **Description**: Generate audio for a podcast script
- **Parameters**:
  - `podcast_id` (string, required): ID of the podcast
  - `voice_name` (string, optional): Voice name (e.g., "en-US-JennyNeural" or "female")
  - `voice_style` (string, optional): Voice style (e.g., "cheerful", "newscast")
- **Returns**: Audio ID for the generated audio

#### `test_audio`
- **Description**: Test audio generation with sample text
- **Parameters**:
  - `text` (string, required): Text to synthesize
  - `voice_name` (string, optional): Voice to use
  - `voice_style` (string, optional): Voice style to use
- **Returns**: Audio ID for the test audio

### 4. Voice Management Tools

#### `list_voices`
- **Description**: List available voices and their properties
- **Parameters**:
  - `gender` (string, optional): Filter by gender ("Male" or "Female")
  - `locale` (string, optional): Filter by language/locale (e.g., "en-US")
- **Returns**: List of matching voice details

#### `get_voice_details`
- **Description**: Get detailed information about a specific voice
- **Parameters**:
  - `voice_name` (string, required): Name of the voice to query
- **Returns**: Detailed voice information including supported styles

## Prompts

### 1. Guided Creation Prompts

#### `podcast_creation`
- **Description**: Guide through the podcast creation process
- **Arguments**:
  - `title` (string): Optional title for the podcast
  - `topic` (string): Optional topic area for the podcast

#### `voice_selection`
- **Description**: Help select the most appropriate voice
- **Arguments**:
  - `podcast_type` (string): Type of podcast (news, storytelling, etc.)
  - `gender_preference` (string): Optional gender preference

### 2. Customization Prompts

#### `podcast_customization`
- **Description**: Guide through podcast style customization
- **Arguments**:
  - `podcast_id` (string): ID of the podcast to customize
  - `style_preference` (string): Preferred style (formal, casual, etc.)

#### `script_editing`
- **Description**: Assist with editing a generated script
- **Arguments**:
  - `podcast_id` (string): ID of the podcast to edit
  - `edit_focus` (string): Focus of the edits (length, tone, etc.)

## Error Handling

The MCP server will provide detailed error messages in the following format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": {
      "additional": "error details"
    }
  }
}
```

Common error codes include:
- `document_not_found`: The requested document does not exist
- `podcast_not_found`: The requested podcast does not exist
- `audio_not_found`: The requested audio does not exist
- `invalid_document`: The uploaded document cannot be processed
- `generation_failed`: Podcast or audio generation failed
- `invalid_voice`: The specified voice is not available

## Response Format

### Resource Responses

Resources will be returned with appropriate MIME types and content.

### Tool Responses

Tool responses will generally follow this format:

```json
{
  "success": true,
  "result": {
    "id": "generated_id",
    "status": "status_message",
    "details": {
      "additional": "response details"
    }
  }
}
```

### Progress Reporting

For long-running operations, progress updates will be provided:

```json
{
  "progress": {
    "percentage": 45,
    "status": "Processing document",
    "eta_seconds": 120
  }
}
```

## Security Considerations

1. Document content will be stored securely and accessible only via the assigned document ID
2. Rate limiting will be implemented for resource-intensive operations
3. Input validation will be performed on all tool parameters
4. Azure service credentials will be secured appropriately
5. Resource URIs will be validated to prevent access to unauthorized resources