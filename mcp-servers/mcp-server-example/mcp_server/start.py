# Main entry point for the MCP Server

import argparse
import logging

from . import settings
from .server import create_mcp_server, logger, query_parameters, http_headers


# Note: We replaced the FastMCP.run_sse_async method with our custom implementation
# This allows us to intercept and validate the SSE connection parameters
# by directly overriding the core method that handles SSE requests

def main() -> None:
    # Command-line arguments for transport and port
    parse_args = argparse.ArgumentParser(description="Start the MCP server.")
    parse_args.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse"],
        help="Transport protocol to use ('stdio' or 'sse'). Default is 'stdio'.",
    )
    parse_args.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to use for SSE (default is 8000)."
    )
    parse_args.add_argument(
        "--allowed-dirs",
        help="Comma-separated list of allowed directories (required for stdio, optional for SSE)"
    )
    # Add debug option
    parse_args.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with more verbose logging"
    )
    args = parse_args.parse_args()

    # Enable debug logging if requested
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Create the MCP server
    mcp = create_mcp_server()

    # Handle command-line allowed-dirs parameter
    if args.allowed_dirs:
        logger.info(f"Setting allowed_dirs from command line: {args.allowed_dirs}")
        settings.allowed_dirs = args.allowed_dirs

    if args.transport == "sse":
        # For SSE transport
        logger.info(f"Starting SSE server on port {args.port}")
        logger.info(f"Use http://127.0.0.1:{args.port}/sse?allowed_dirs=path1,path2 to connect")

        # Let user know about parameters
        if args.allowed_dirs:
            logger.info(f"Default allowed_dirs from command line: {args.allowed_dirs}")
            logger.info("Note: This can be overridden by the client connection parameter")
        else:
            logger.info("No default allowed_dirs provided - client must provide it in the connection URL")

        # Set the port in settings
        mcp.settings.port = args.port

        # Run with our custom SSE implementation
        logger.info("Starting SSE server with parameter extraction")
        mcp.run(transport="sse")
    else:
        # For stdio transport, make sure allowed_dirs is provided
        if not settings.allowed_dirs:
            logger.error("allowed_dirs parameter is required for stdio transport")
            parse_args.error("the --allowed-dirs parameter is required for stdio transport")
            return

        # Run with stdio transport using standard method
        logger.info("Starting with stdio transport")
        logger.info(f"Using allowed_dirs: {settings.allowed_dirs}")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
