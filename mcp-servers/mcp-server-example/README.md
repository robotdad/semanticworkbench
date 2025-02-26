# Example MCP Server

This is an example MCP server demonstrating how to implement query parameter handling in an SSE-based MCP server. The server requires a "query_param" parameter to be passed either via command line or in the URL.

This is a [Model Context Protocol](https://github.com/modelcontextprotocol) (MCP) server project.

## Setup and Installation

Simply run:

```bash
make
```

To create the virtual environment and install dependencies.

### Running the Server

Use the VSCode launch configuration, or run manually:

Defaults to stdio transport (query_param parameter is required):

```bash
uv run -m mcp_server.start --query-param "example_value"
```

For SSE transport:

```bash
uv run -m mcp_server.start --transport sse --port 6066
```

When connecting to the SSE endpoint, the client's URL must include the required `query_param` parameter:

```
http://127.0.0.1:6066/sse?query_param=example_value
```

If the `query_param` parameter is not provided in the client's URL, the server will return a 400 error, but the server itself can be started without this parameter.

## Client Configuration

To use this MCP server in your setup, consider the following configuration:

### Stdio

```json
{
  "mcpServers": {
    "mcp-server-example": {
      "command": "uv",
      "args": ["run", "-m", "mcp_server.start", "--query-param", "example_value"]
    }
  }
}
```

### SSE

```json
{
  "mcpServers": {
    "mcp-server-example": {
      "command": "http://127.0.0.1:6066/sse?query_param=example_value",
      "args": []
    }
  }
}
```

### Parameter Passing with the Assistant Client

In configurations with an AI assistant client connecting via SSE transport, you can specify parameters in two ways:

1. Directly in the URL:
```json
{
  "mcpServers": {
    "mcp-server-example": {
      "command": "http://127.0.0.1:6066/sse?query_param=example_value",
      "args": []
    }
  }
}
```

2. Using the args array (processed by the client):
```json
{
  "mcpServers": {
    "mcp-server-example": {
      "command": "http://127.0.0.1:6066/sse",
      "args": ["query_param", "example_value"]
    }
  }
}
```

## Implementation Details

This section explains the key implementation details for handling query parameters in SSE transports with MCP.

### Server-Side Parameter Handling

The server implements query parameter handling by overriding the standard FastMCP SSE transport functionality. The key parts are:

1. **Creating a custom SSE implementation**: We override the `run_sse_async` method of FastMCP.

2. **Request handling**: Using Starlette, we intercept SSE connection requests and extract parameters.

3. **Parameter validation**: We check that required parameters are present and return a 400 error if they're missing.

Here's the core implementation from server.py:

```python
# Store the original method for reference
original_run_sse_async = mcp.run_sse_async

# Create a custom implementation
async def custom_run_sse_async():
    sse = SseServerTransport("/messages/")
    
    async def handle_sse(request: Request):
        # Extract and validate query parameters
        query_params = dict(request.query_params)
        
        # Check for required parameters
        if "query_param" in query_params:
            param_value = query_params["query_param"]
            settings.query_param = param_value
        elif not settings.query_param:
            # Return error if required parameter is missing
            return PlainTextResponse(
                "Error: query_param parameter is required",
                status_code=400
            )
            
        # Continue with normal SSE connection
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options(),
            )
    
    # Create Starlette app with routes
    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )
    
    # Run with uvicorn
    import uvicorn
    config = uvicorn.Config(
        starlette_app,
        host=mcp.settings.host,
        port=mcp.settings.port,
    )
    server = uvicorn.Server(config)
    await server.serve()

# Replace the original method
mcp.run_sse_async = custom_run_sse_async
```

### Client-Side Parameter Handling

On the client side, there are two main approaches for handling parameters:

1. **Direct URL Parameters**: Include parameters directly in the URL:
   ```
   http://127.0.0.1:6066/sse?query_param=example_value
   ```

2. **Arguments Array Processing**: For clients that support it, the first argument in the `args` array is the parameter name, and subsequent arguments are joined with commas as the value:
   ```python
   # Convert this config:
   # {
   #   "command": "http://example.com/sse",
   #   "args": ["query_param", "value1", "value2"]
   # }
   
   # Into this URL:
   # http://example.com/sse?query_param=value1,value2
   
   if server_config.args and len(server_config.args) >= 1:
       param_name = server_config.args[0]
       param_values = []
       
       # Get values from remaining args
       if len(server_config.args) > 1:
           param_values = server_config.args[1:]
       
       # Join values with commas
       param_value = ",".join(param_values)
       
       # Add to URL using URL parameter handling function
       if param_name:
           url_params = {param_name: param_value}
           url = add_params_to_url(url, url_params)
   ```

This allows for flexible parameter passing while maintaining compatibility with different client implementations.
