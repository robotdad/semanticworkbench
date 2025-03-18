# Podcast MCP Server

The Podcast MCP Server is a Model Context Protocol (MCP) server that provides podcast generation capabilities. It allows users to upload documents and generate informational podcasts using Azure AI services.

## Overview

This project is an MCP adaptation of the original Podcastly CLI application. It exposes the core functionality of Podcastly through MCP resources, tools, and prompts, allowing for integration with MCP-capable clients like Claude Desktop.

## Key Features

- Upload documents for processing
- Generate podcast scripts from document content
- Create audio from podcast scripts using Azure Speech Services
- Customize voice selection and podcast styles
- Access generated resources through MCP URIs

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. Clone the repository
2. Install dependencies:

```bash
make install
```

Or manually:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Configuration

The server uses environment variables for configuration. Create a `.env` file with the following settings:

```bash
# Logging
LOG_LEVEL=INFO

# MCP Storage
MCP_STORAGE_PATH=/path/to/storage

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Azure Document Intelligence
DOCUMENT_INTELLIGENCE_ENDPOINT=
DOCUMENT_INTELLIGENCE_API_KEY=
DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-layout

# Azure Speech
SPEECH_RESOURCE_ID=
SPEECH_REGION=
SPEECH_KEY=
SPEECH_HOST_VOICE=en-US-JennyNeural
SPEECH_REPORTER_VOICES=en-US-GuyNeural,en-US-DavisNeural

# Authentication
USE_MANAGED_IDENTITY=False

# Podcast Generation
DEFAULT_PODCAST_LENGTH_MINUTES=5
SHOW_TRANSITIONS=True
```

## Usage

### Running the Server

#### Using stdio Transport (for Claude Desktop)

```bash
uv run mcp-server-podcast
```

#### Using SSE Transport (for Web Clients)

```bash
uv run mcp-server-podcast --transport sse --port 6090
```

### Installing in Claude Desktop

```bash
mcp install .
```

### Development Mode

```bash
mcp dev .
```

## MCP API Overview

### Resources

- `document://{document_id}` - Access processed document text
- `podcast://{podcast_id}/script` - Access generated podcast script
- `podcast://{podcast_id}/segments` - Access individual podcast segments
- `audio://{audio_id}` - Access generated podcast audio
- `voices://list` - List available voice options

### Tools

- `upload_document` - Upload a document for processing
- `generate_podcast` - Generate a podcast script from documents
- `generate_audio` - Generate audio from a podcast script
- `list_voices` - List available voices and styles

### Prompts

- `podcast_creation` - Guide through the podcast creation process
- `voice_selection` - Help select appropriate voices

## Development

### Common Commands

- Build/Install: `make install`
- Format: `make format`
- Lint: `make lint`
- Type-check: `make type-check`
- Test: `make test`

### Project Structure

```
mcp-server-podcast/
├── mcp_server_podcast/
│   ├── __init__.py
│   ├── config.py                 # Configuration management
│   ├── server.py                 # MCP server definition
│   ├── start.py                  # Entry point
│   ├── models/                   # Domain and resource models
│   ├── resources/                # Resource handlers
│   ├── tools/                    # Tool implementations
│   ├── services/                 # Service implementations
│   ├── prompts/                  # Prompt templates
│   └── utils/                    # Utility functions
├── tests/                        # Test suite
├── docs/                         # Documentation
│   ├── adrs/                     # Architecture Decision Records
│   ├── ai-context/               # AI assistant guides
│   └── plans/                    # Implementation plans
├── CLAUDE.md                     # Claude-specific guidelines
├── Makefile                      # Build commands
├── pyproject.toml                # Project configuration
└── README.md                     # Project overview
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Based on the Podcastly CLI application
- Uses MCP Python SDK for protocol implementation
- Powered by Azure AI services