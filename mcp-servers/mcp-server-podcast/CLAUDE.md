# Podcast MCP Server Developer Guidelines

## Common Commands
* Build/Install: `make install` (installs dependencies)
* Format: `make format` (runs ruff formatter)
* Lint: `make lint` (runs ruff linter)
* Type-check: `make type-check` (runs pyright)
* Test: `make test` (runs pytest)
* Single test: `uv run pytest tests/test_file.py::test_function -v`
* Run MCP server: `uv run mcp-server-podcast` (stdio transport)
* Run with SSE: `uv run mcp-server-podcast --transport sse --port 6090`
* Install in Claude Desktop: `mcp install .`
* Development mode: `mcp dev .`

## MCP Development
* Server structure: Use FastMCP for declarative API definition
* Resources: Define with `@mcp.resource()` decorator for data exposure (application-controlled)
* Tools: Implement with `@mcp.tool()` decorator for LLM-executable actions (model-controlled)
* Prompts: Create with `@mcp.prompt()` decorator for reusable templates (user-controlled)
* Resource URIs: Follow `scheme://path` pattern with parameters in curly braces
* Context: Use the Context parameter for access to MCP capabilities (progress tracking, logging)
* Authentication: Consider adding for remote MCP connections
* Error handling: Handle exceptions gracefully with clear error messages

## Code Style
### Python
* Indentation: 4 spaces
* Line length: 120 characters
* Imports: stdlib → third-party → local, alphabetized within groups
* Naming: `snake_case` for functions/variables, `CamelCase` for classes, `UPPER_SNAKE_CASE` for constants
* Types: Use type annotations consistently; prefer Union syntax (`str | None`) for Python 3.10+
* Documentation: Triple-quote docstrings with param/return descriptions
* Tool parameters: Use JSON Schema to define input validation
* Lifespan: Implement async context managers for server lifecycle management

## Tools
* Python: Uses uv for environment/dependency management (Python 3.11+)
* MCP SDK: Uses FastMCP for high-level API definition (version 1.2.1+)
* Transports: Supports stdio and SSE for client-server communication
* Linting/Formatting: Ruff
* Type checking: Pyright
* Testing: pytest