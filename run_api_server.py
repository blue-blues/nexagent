#!/usr/bin/env python
"""
Nexagent API Server

This script starts the Nexagent API server, which provides a RESTful API
for interacting with the Nexagent AI Assistant.
"""

import argparse
import time
from app.api.server import nexagent_server
from app.logger import logger

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Start the Nexagent API server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    return parser.parse_args()

def main():
    """Main entry point for the API server"""
    args = parse_args()

    # Log startup information
    logger.info(f"Starting Nexagent API server at http://{args.host}:{args.port}")
    logger.info("Press Ctrl+C to stop the server")

    # Start the server
    nexagent_server.start(host=args.host, port=args.port)

    try:
        # Keep the main thread alive
        while True:
            # Use time.sleep instead of asyncio.sleep since we're in a synchronous context
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping Nexagent API server...")
        nexagent_server.stop()
        logger.info("Nexagent API server stopped")

if __name__ == "__main__":
    main()
