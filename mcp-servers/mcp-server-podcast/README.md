# Podcast MCP Server

Provides a generated podcast from uploaded materials

This is a [Model Context Protocol](https://github.com/modelcontextprotocol) (MCP) server project.

## Setup and Installation

Simply run:

```bash
make
```

To create the virtual environment and install dependencies.

### Running the Server

Use the VSCode launch configuration, or run manually:

Defaults to stdio transport:

```bash
uv run mcp-server-podcast
```

For SSE transport:

```bash
uv run mcp-server-podcast --transport sse --port 6090
```

The SSE URL is:

```bash
http://127.0.0.1:6090/sse
```

## Client Configuration

To use this MCP server in your setup, consider the following configuration:

### Stdio

```json
{
  "mcpServers": {
    "mcp-server-podcast": {
      "command": "uv",
      "args": ["run", "-m", "mcp_server_podcast.start"]
    }
  }
}
```

### SSE

```json
{
  "mcpServers": {
    "mcp-server-podcast": {
      "command": "http://127.0.0.1:6090/sse",
      "args": []
    }
  }
}
```
