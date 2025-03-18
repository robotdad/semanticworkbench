#!/usr/bin/env python
"""
Simple script to run the MCP server locally for testing.
"""

import argparse
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add current directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Import the server
from mcp_server_podcast.server import create_mcp_server
from mcp_server_podcast.start import run_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Podcast MCP Server")
    parser.add_argument("--transport", type=str, default="stdio", help="Transport type (stdio or sse)")
    parser.add_argument("--port", type=int, default=6090, help="Port for SSE transport")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for SSE transport")
    args = parser.parse_args()
    
    # Create the server
    mcp = create_mcp_server()
    
    # Run the server
    if args.transport == "stdio":
        print(f"Starting server with stdio transport")
        asyncio.run(run_server(mcp, "stdio"))
    elif args.transport == "sse":
        print(f"Starting server with SSE transport on {args.host}:{args.port}")
        asyncio.run(run_server(mcp, "sse", host=args.host, port=args.port))
    else:
        print(f"Unknown transport: {args.transport}")
        sys.exit(1)