# Example MCP Server

Example MCP server

This is a [Model Context Protocol](https://github.com/modelcontextprotocol) (MCP) server project.

## Setup and Installation

Simply run:

```bash
make
```

To create the virtual environment and install dependencies.

### Running the Server

Use the VSCode launch configuration, or run manually:

Defaults to stdio transport (allowed_dirs parameter is required):

```bash
uv run -m mcp_server.start --allowed-dirs "/path1,/path2"
```

For SSE transport:

```bash
uv run -m mcp_server.start --transport sse --port 6066
```

When connecting to the SSE endpoint, the client's URL must include the required `allowed_dirs` parameter:

```
http://127.0.0.1:6066/sse?allowed_dirs=/path1,/path2
```

If the `allowed_dirs` parameter is not provided in the client's URL, the server will return a 400 error, but the server itself can be started without this parameter.

## Client Configuration

To use this MCP server in your setup, consider the following configuration:

### Stdio

```json
{
  "mcpServers": {
    "mcp-server-example": {
      "command": "uv",
      "args": ["run", "-m", "mcp_server.start", "--allowed-dirs", "/path1,/path2"]
    }
  }
}
```

### SSE

```json
{
  "mcpServers": {
    "mcp-server-example": {
      "command": "http://127.0.0.1:6066/sse?allowed_dirs=/path1,/path2",
      "args": []
    }
  }
}
```

Note: When using paths with backslashes (Windows), use URL encoding or forward slashes:

```json
{
  "mcpServers": {
    "mcp-server-example": {
      "command": "http://127.0.0.1:6066/sse?allowed_dirs=C:/Users/username/Desktop,D:/Projects",
      "args": []
    }
  }
}
```
