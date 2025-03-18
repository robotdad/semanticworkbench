# AI Assistant Guide for Podcast MCP Server

This document provides essential information for AI assistants helping with this codebase. It contains development guidelines, architecture information, and best practices to follow when assisting with the Podcast MCP Server project.

> **CRITICAL: PRE-PRODUCTION STATUS**
> 
> This codebase is currently in **pre-production development**. Therefore:
> 
> - **NO BACKWARD COMPATIBILITY REQUIRED**: When refactoring or redesigning, do not maintain backward compatibility
> - **NO MIGRATION PATHS NEEDED**: Since the codebase is not in production use, do not implement migration paths
> - **PRIORITIZE CLEAN DESIGN**: Focus on creating clean, well-designed components without preserving old patterns
> - **REMOVE LEGACY CODE**: If you find code that seems focused on backward compatibility or migrations, suggest removing it
> - **ALWAYS CONFIRM**: If ever in doubt about backward compatibility needs, explicitly confirm with the human user
> 
> The goal is a clean, well-architected codebase without technical debt from compatibility concerns.

## Conversation Workflow

Every time you (the AI assistant) begin a new conversation with a user about this codebase:

1. **Initial Message**:
   - Acknowledge that you've read and will follow this guide
   - Briefly mention that you understand the pre-production nature of the codebase
   - Ask the user what they want to work on today

2. **Read Documentation First**:
   - Review docs/plans/ for implementation plans and API specifications
   - Review the CLAUDE.md file for project-specific guidelines
   - Review the pyproject.toml for development tools and dependencies
   - For MCP reference materials, check the content in ../../ai-assist-content/
     - mcp-python-sdk-README.md - Documentation for the Python SDK
     - mcp-llms-full.txt - Comprehensive MCP documentation
     - mcp-metadata-tips.md - Best practices for metadata
   - For deeper context, examine the original Podcastly code in ~/podcast

3. **Understand the Current Context**:
   - Check git status to understand what files are being modified
   - Look for a pre-existing work context or current task focus
   - When specific files are mentioned, examine their imports and dependencies

## Common Commands

### Development
- Build/Install: `make install` (installs dependencies)
- Format: `make format` (runs ruff formatter)
- Lint: `make lint` (runs ruff linter)
- Type-check: `make type-check` (runs pyright)
- Test: `make test` (runs pytest)
- Single test: `uv run pytest tests/test_file.py::test_function -v`
- Run MCP server: `uv run mcp-server-podcast` (stdio transport)
- Run with SSE: `uv run mcp-server-podcast --transport sse --port 6090`
- Install in Claude Desktop: `mcp install .`
- Development mode: `mcp dev .`

### Dependency Management
- Initialize project: `uv init` then `uv venv` then `source .venv/bin/activate`
- Install dependencies: `uv sync` or `uv pip install -e .`
- Add a dependency: `uv add <package>` 
- Add a dev dependency: `uv add --dev <package>`
- Lock dependencies: `uv lock`
- Install type stubs: `uv add --dev types-<package>`
- Show dependency tree: `uv tree`

### MCP Development
- Server structure: Use FastMCP for declarative API definition
- Resources: Define with `@mcp.resource()` decorator for data exposure (application-controlled)
- Tools: Implement with `@mcp.tool()` decorator for LLM-executable actions (model-controlled)
- Prompts: Create with `@mcp.prompt()` decorator for reusable templates (user-controlled)

## Codebase Philosophy and Goals

### MCP Server for Podcast Generation

This codebase is designed to provide podcast generation capabilities through the Model Context Protocol (MCP). The goal is to create a server that:

- Exposes podcast generation functionality as MCP resources, tools, and prompts
- Adapts the existing Podcastly capabilities for use in an MCP context WITHOUT changing functionality
- Provides a clean, well-documented API for LLM-powered clients
- Maintains separation of concerns and clean architecture

> **IMPORTANT: STRICT ADAPTATION APPROACH**
> 
> This project is a STRICT ADAPTATION of the existing Podcastly application:
> 
> - We are ONLY creating an MCP wrapper, not redesigning the application
> - Original functionality, algorithms, and prompt templates MUST be preserved exactly
> - Do not attempt to "improve" the existing implementation
> - Only make changes necessary to fit within the MCP protocol framework
> - Create direct 1:1 mappings between CLI commands and MCP capabilities
> 
> Any suggestions that would change the core functionality or approach should be avoided.

### Fast-Moving Innovation Environment

This codebase is designed for a **fast-moving team that needs to explore new ideas quickly**. Therefore:

- **Simplicity is paramount**: Code should be easy to understand and navigate
- **Modularity over monoliths**: Components should be well-isolated with clean interfaces
- **Reduced complexity**: Prefer straightforward implementations over clever or complex ones
- **Direct over indirect**: Favor direct communication paths over complex event chains
- **Lower cognitive load**: New team members should be able to contribute quickly
- **Safe experimentation**: Changes in one area should have minimal risk to others

The overall modular design of the application supports these goals by allowing:
- Independent development of different components
- Parallel exploration of multiple approaches
- Easier reasoning about the system's behavior
- Faster iteration cycles
- Better team collaboration

## Core Development Principles

### Architecture
- Follow MCP server architecture with FastMCP
- Maintain clear separation between resources, tools, and prompts
- Use Protocol classes for interfaces
- Implement service classes that fulfill these protocols
- Keep domain models separate and well-defined

### Code Style
* Indentation: 4 spaces
* Line length: 120 characters
* Imports: stdlib → third-party → local, alphabetized within groups
* Naming: `snake_case` for functions/variables, `CamelCase` for classes, `UPPER_SNAKE_CASE` for constants
* Types: Use type annotations consistently; prefer Union syntax (`str | None`) for Python 3.10+
* Documentation: Triple-quote docstrings with param/return descriptions
* Tool parameters: Use JSON Schema to define input validation
* Lifespan: Implement async context managers for server lifecycle management

### Testing
- Write tests for all new functionality
- Use pytest fixtures to mock dependencies
- Test each component separately
- Use pytest-asyncio for testing async code

## File Organization

```
mcp-server-podcast/
├── mcp_server_podcast/
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   ├── server.py                     # MCP server definition
│   ├── start.py                      # Entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── domain.py                 # Domain models with dataclasses
│   │   └── resource.py               # Resource models (if needed)
│   ├── resources/
│   │   ├── __init__.py  
│   │   ├── document_resources.py
│   │   ├── podcast_resources.py
│   │   ├── audio_resources.py
│   │   └── voice_resources.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── document_tools.py
│   │   ├── podcast_tools.py
│   │   ├── audio_tools.py
│   │   └── voice_tools.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── guided_creation.py
│   │   └── voice_selection.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_processor.py
│   │   ├── openai_agent.py
│   │   ├── podcast_composer.py
│   │   └── audio_generator.py
│   ├── storage/                      # Directory for resource storage
│   │   └── .gitkeep                  # Ensure directory is created in git
│   └── utils/
│       ├── __init__.py
│       ├── filename_generator.py     # Generate unique output filenames
│       └── progress_reporter.py      # Report progress to MCP clients
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Test fixtures
│   ├── test_resources/
│   │   ├── __init__.py
│   │   └── test_document_resources.py
│   ├── test_tools/
│   │   ├── __init__.py
│   │   └── test_document_tools.py
│   ├── test_services/
│   │   ├── __init__.py
│   │   └── test_document_processor.py
│   └── test_utils/
│       ├── __init__.py
│       └── test_filename_generator.py
├── docs/
│   ├── adrs/                         # Architecture Decision Records
│   │   ├── 0000-adr-template.md      # Template for new ADRs
│   │   └── README.md                 # Index of ADRs
│   ├── ai-context/
│   │   └── AI_ASSISTANT_GUIDE.md     # Guide for AI assistants
│   └── plans/                        # Implementation plans
│       ├── implementation_plan.md    # Overall implementation plan
│       ├── api_specification.md      # API specification
│       └── service_adaptation.md     # Service adaptation plan
├── CLAUDE.md                         # Claude-specific guidelines
├── Makefile                          # Build commands
├── pyproject.toml                    # Project configuration and dependencies
└── README.md                         # Project overview and user guide
```

## Engineering Excellence Guidelines

### Core Engineering Mindset

The most successful contributions to this codebase share these engineering attributes:

1. **First Principles Thinking**: Start with the core purpose of the component rather than incrementally modifying existing patterns. Ask "what is this actually trying to achieve?" before diving into implementation.

2. **Simplicity Over Flexibility**: Choose simpler designs over more flexible ones unless the flexibility is immediately needed. Complexity should be justified by current, not hypothetical, requirements.

3. **Follow Direct Paths**: Prefer direct communication between components over complex event chains or multiple layers of indirection. Each additional hop is a potential failure point.

4. **Visualize End-to-End Flow**: Think in terms of complete paths from input to output. Diagram these flows to identify unnecessary complexity or potential failure points.

5. **Resource Lifecycle Awareness**: Consider the full lifecycle of components including cleanup and shutdown. Any component that manages background tasks or resources must implement proper cleanup methods.

6. **Type Safety as Default**: Use proper type annotations throughout the codebase. Utilize Python's static typing capabilities to catch errors at development time.

7. **Code as Communication**: Write code primarily for human understanding, not just machine execution. Choose clarity over cleverness, even if it means a few more lines of code.

8. **Iterative Simplification**: After implementing a solution, look for further opportunities to simplify. Ask "can I remove this layer?" or "is this abstraction necessary?"

### Best Practices for Assisting with This Project

1. **Start with Current Status**: Always check git status to understand the current state of the project
2. **Understand Architecture First**: Review architecture documentation before making changes
3. **Test Rigorously**: Write and run comprehensive tests for all changes
4. **Maintain Type Safety**: Ensure all code has proper type annotations
5. **Document Changes**: Update or create documentation for any significant changes
6. **Propose Improvements**: Suggest better approaches when you see opportunities for improvement
7. **Provide Context**: Explain why certain approaches are recommended or required
8. **Fix Forward**: When encountering issues, address root causes rather than symptoms
9. **Prioritize Clean Design**: As this is pre-production code, prioritize clean architecture over backward compatibility
10. **Follow MCP Patterns**: Use MCP-specific patterns and practices for resources, tools, and prompts

Remember that this project prioritizes maintainability, type safety, and clarity over complex optimizations. Always aim to leave the codebase better than you found it.

## Project-Specific Information

### Podcast MCP Server Overview

Podcast MCP Server is an MCP server that generates informational podcasts from text documents, using Azure AI services. The workflow is:

1. Takes uploaded documents as input
2. Extracts text using Azure Document Intelligence
3. Generates podcast story segments from extracted text using Azure OpenAI
4. Composes a complete podcast script with intro, transitions, and outro
5. Optionally generates audio using Azure Speech Services
6. Exposes results as MCP resources for client access

### Key Components

1. **DocumentProcessor**: Extracts text from various file formats (PDF, DOCX, TXT)
2. **OpenAIAgent**: Handles communication with Azure OpenAI API
3. **PodcastComposer**: Creates podcast segments and full scripts
4. **AudioGenerator**: Generates spoken audio from scripts
5. **Resources**: Expose generated content (scripts, audio) to clients
6. **Tools**: Allow clients to upload documents and generate podcasts
7. **Prompts**: Guide users through podcast creation workflows

### Configuration

The application uses environment variables for configuration:
- AZURE_OPENAI_ENDPOINT
- DOCUMENT_INTELLIGENCE_ENDPOINT 
- SPEECH_RESOURCE_ID
- SPEECH_REGION

### Reference Materials

Important reference materials are available in the `../../ai-assist-content/` directory:

1. **MCP Python SDK Documentation**:
   - `mcp-python-sdk-README.md` - Complete documentation for the Python SDK
   - Contains examples of defining resources, tools, and prompts
   - Shows how to set up FastMCP server implementation

2. **MCP Comprehensive Documentation**:
   - `mcp-llms-full.txt` - Comprehensive guide to MCP concepts and implementation
   - Covers architecture, resources, tools, prompts, and sampling
   - Includes best practices and security considerations

3. **MCP TypeScript SDK Documentation**:
   - `mcp-typescript-sdk-README.md` - Documentation for the TypeScript SDK
   - Useful for understanding client perspectives and protocol details

4. **Other Helpful Resources**:
   - `mcp-metadata-tips.md` - Best practices for metadata handling
   - `mcp-example-brave-search.md` - Example implementation of an MCP server

Always refer to these materials when implementing MCP-specific features or when unsure about best practices.

### MCP Integration

The server integrates with the Model Context Protocol (MCP) to:
1. Expose resources like podcast scripts and audio files
2. Provide tools for document upload and podcast generation
3. Offer prompts for guided podcast creation
4. Report progress for long-running operations
5. Support both stdio and SSE transports

## Documentation Maintenance

### API Specification

The project maintains an API specification that documents:

1. **Resources**: URI patterns, parameters, and return values
2. **Tools**: Tool names, parameters, and return values
3. **Prompts**: Prompt names, arguments, and usage

When helping with this codebase:

1. **Check Spec**: Review the API specification to understand current design
2. **Update Spec**: After making API changes, suggest updating the specification
3. **Follow Patterns**: Ensure new resources, tools, and prompts follow established patterns

### Architecture Decision Records (ADRs)

The project uses Architecture Decision Records (ADRs) to document significant architectural decisions. These ADRs capture important learnings from the previous Podcastly project that should be carried forward:

1. **Clean Architecture with Protocols** (from [0001-clean-architecture-with-protocols.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0001-clean-architecture-with-protocols.md))
   - Use Python Protocols to define interfaces
   - Maintain clear separation between domain models, interfaces, and implementations
   - Enable testability through dependency injection

2. **Asyncio-First Approach** (from [0002-asyncio-first-approach.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0002-asyncio-first-approach.md))
   - Use async/await patterns throughout the codebase
   - Avoid mixing threading and asyncio
   - Leverage async capabilities for efficient I/O operations

3. **Dependency Injection Pattern** (from [0003-dependency-injection-pattern.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0003-dependency-injection-pattern.md))
   - Pass dependencies explicitly through constructors
   - Avoid global state and singletons
   - Facilitate easier testing and component replacement

4. **Domain Models with Dataclasses** (from [0004-domain-models-with-dataclasses.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0004-domain-models-with-dataclasses.md))
   - Use dataclasses for domain models
   - Ensure proper type annotations
   - Keep domain models separate from service implementations

When helping with this codebase:

1. **Review Existing ADRs**: Look at both the original Podcastly ADRs and any new ones in `/docs/adrs/` to understand architectural decisions
2. **Suggest New ADRs**: When making or discussing significant architecture decisions, suggest creating a new ADR
3. **ADR Format**: Follow the template in `/docs/adrs/0000-adr-template.md`
4. **Update ADR Index**: When creating a new ADR, update the index in `/docs/adrs/README.md`

### Implementation Plans

The project includes implementation plans for:

1. **Overall Strategy**: High-level approach and phases
2. **API Specification**: Detailed resource, tool, and prompt definitions
3. **Service Adaptation**: How to adapt Podcastly services for MCP

When helping with this codebase:

1. **Review Plans**: Understand the planned implementation approach
2. **Track Progress**: Keep track of what has been implemented vs. what remains
3. **Suggest Updates**: If implementation details change, suggest updating the plans

## Self-Improvement and Maintenance

As an AI assistant, you should:

1. **Update This Guide**: When you learn new information about the codebase or discover better ways to assist:
   - Suggest additions or improvements to this guide
   - Be specific about what could be added and why it would be helpful

2. **Identify Recurring Issues**: When you notice patterns of issues or questions:
   - Propose automated solutions 
   - Suggest documentation or guide updates to prevent future problems

3. **Record Common Commands**: When you or the user find useful commands:
   - Suggest adding them to this guide for future reference
   - Include context about when and how to use them

By continuously improving this guide, you help future AI assistants provide better service and maintain consistency in the project's development.