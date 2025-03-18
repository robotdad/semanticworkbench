# Main entry point for the MCP Server

import argparse
import logging
import sys
from pathlib import Path

from .server import create_mcp_server
from . import settings


def setup_logging() -> None:
    """Set up logging for the MCP server."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main() -> None:
    """Main entry point for the MCP server."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger("mcp-server-podcast")
    
    # Command-line arguments for transport and port
    parse_args = argparse.ArgumentParser(description="Start the MCP server.")
    parse_args.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse"],
        help="Transport protocol to use ('stdio' or 'sse'). Default is 'stdio'.",
    )
    parse_args.add_argument(
        "--port", type=int, default=6090, help="Port to use for SSE (default is 6090)."
    )
    parse_args.add_argument(
        "--storage-path", type=Path, help="Path to store MCP resources. Default is set in configuration."
    )
    args = parse_args.parse_args()

    # Override storage path if provided
    if args.storage_path:
        settings.mcp_storage_path = args.storage_path
        settings.mcp_storage_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting MCP server with storage path: {settings.mcp_storage_path}")
    
    # Create and run the MCP server
    mcp = create_mcp_server()
    if args.transport == "sse":
        mcp.settings.port = args.port
        logger.info(f"Using SSE transport on port {args.port}")
    else:
        logger.info("Using stdio transport")

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
