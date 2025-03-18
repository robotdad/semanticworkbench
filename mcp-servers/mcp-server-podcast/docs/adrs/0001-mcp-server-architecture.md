# ADR 0001: MCP Server Architecture

## Context

We need to design the architecture for the Podcast MCP Server that adapts the existing Podcastly CLI application to the Model Context Protocol (MCP). The design should preserve the functionality of the original application while making it available through MCP resources, tools, and prompts.

## Decision

We will implement the MCP server using the FastMCP framework from the MCP Python SDK with the following architecture:

1. **Clean Separation of Components**:
   - Server configuration and startup in dedicated files
   - Domain models separate from resource models
   - Utilities in dedicated modules
   - Clear separation between resources, tools, and services

2. **Resource Management Approach**:
   - File-based storage for resources
   - Unique ID generation and mapping between IDs and files
   - Centralized resource ID management
   - Consistent URI schemes for resources

3. **Progress Reporting**:
   - Dedicated progress reporter for long-running operations
   - Rate-limited progress updates
   - Consistent progress format

4. **Adaptation Pattern for Services**:
   - Thin wrappers around original Podcastly services
   - Maintain core business logic from original services
   - Add MCP-specific concerns (resource management, progress reporting)

## Rationale

- **FastMCP Framework**: Provides a declarative approach to defining MCP resources and tools with minimal boilerplate.
- **File-based Storage**: Simplifies implementation and matches the approach used in the original Podcastly CLI.
- **Unique IDs**: Allows resources to be referenced without exposing implementation details or filesystem paths.
- **Resource ID Manager**: Centralizes resource tracking and mapping, simplifying resource lifecycle management.
- **Progress Reporting**: Provides feedback for long-running operations, essential for a good user experience in MCP clients.
- **Thin Service Wrappers**: Ensures core business logic is preserved while adapting to the MCP protocol requirements.

## Consequences

### Positive

- Clear separation of concerns makes the codebase easier to understand and maintain
- Centralized resource management simplifies resource access and lifecycle
- Progress reporting improves user experience
- Original business logic is preserved, minimizing the risk of functional changes

### Negative

- Additional complexity compared to direct CLI implementation
- Need to maintain mappings between resource IDs and files
- Potential for duplication in adapter layers

### Neutral

- Resources are stored as files, which may have scaling limitations but is adequate for the expected usage patterns
- Asynchronous implementation throughout requires careful error handling

## Implementation Notes

- Use Python's native `asyncio` for asynchronous operations
- Leverage FastMCP's resource and tool decorators for declarative API definition
- Use dataclasses for domain and resource models
- Ensure proper error handling and status reporting in all operations