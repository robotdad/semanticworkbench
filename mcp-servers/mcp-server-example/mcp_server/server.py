import logging
import sys
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from . import settings
from .config import logger

# Set the name of the MCP server
server_name = "Example MCP Server"

# Configure logging to stderr so it doesn't interfere with stdio transport
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

# Store query parameters globally for access across the server
query_parameters = {}
http_headers = {}

def create_mcp_server() -> FastMCP:
    logger.info(f"Creating MCP server: {server_name}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Initial query_param: {settings.query_param}")

    # Initialize FastMCP with debug logging
    mcp = FastMCP(name=server_name, log_level=settings.log_level)

    # Create a custom run_sse_async method to replace the standard one
    # This will allow us to intercept and log connection parameters
    original_run_sse_async = mcp.run_sse_async

    async def custom_run_sse_async():


        sse = SseServerTransport("/messages/")

        async def handle_sse(request: Request):
            # Log the connection details
            logger.info("===================== SSE CONNECTION DETAILS =====================")
            logger.info(f"Path: {request.url.path}")
            logger.info(f"Query string: {request.url.query}")

            # Parse and process query parameters
            query_params = dict(request.query_params)
            logger.info(f"Parsed query parameters: {query_params}")

            # Save parameters globally for diagnostics
            query_parameters.update(query_params)

            # Check for query_param parameter
            if "query_param" in query_params:
                param_value = query_params["query_param"]
                logger.info(f"Setting query_param from URL: {param_value}")
                settings.query_param = param_value
            elif not settings.query_param:
                logger.error("query_param parameter required but not provided")
                return PlainTextResponse(
                    "Error: query_param parameter is required",
                    status_code=400
                )

            # Log headers
            headers = dict(request.headers)
            logger.info(f"Headers: {headers}")
            http_headers.update(headers)
            logger.info("================================================================")

            # Continue with normal SSE connection
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await mcp._mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp._mcp_server.create_initialization_options(),
                )

        starlette_app = Starlette(
            debug=mcp.settings.debug,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        import uvicorn
        config = uvicorn.Config(
            starlette_app,
            host=mcp.settings.host,
            port=mcp.settings.port,
            log_level=mcp.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()

    # Replace the run_sse_async method
    mcp.run_sse_async = custom_run_sse_async

    # Diagnostic tool to check configuration
    @mcp.tool()
    async def get_config() -> str:
        """
        Returns the current server configuration.
        """
        logger.info("get_config tool called")

        config_info = {
            "server_name": server_name,
            "log_level": settings.log_level,
            "query_param": settings.query_param,
            "query_parameters": query_parameters,
            "http_headers": http_headers
        }

        # Format the config info as a string
        config_str = "\n".join([f"{k}: {v}" for k, v in config_info.items()])

        return config_str

    logger.info("MCP server created successfully")
    return mcp
