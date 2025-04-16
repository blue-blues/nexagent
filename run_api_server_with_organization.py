#!/usr/bin/env python
"""
Nexagent API Server with Conversation Organization

This script starts the Nexagent API server with conversation organization features,
which provides a RESTful API for interacting with the Nexagent AI Assistant and
organizing conversations into folders with associated materials.
"""

import argparse
import asyncio
import uvicorn
from app.api.server_with_organization import server
from app.logger import logger

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Start the Nexagent API server with conversation organization")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    return parser.parse_args()

def main():
    """Main entry point for the API server with conversation organization"""
    args = parse_args()
    
    # Log startup information
    logger.info(f"Starting Nexagent API server with conversation organization at http://{args.host}:{args.port}")
    logger.info("Press Ctrl+C to stop the server")
    
    # Start the server
    server.start(host=args.host, port=args.port)
    
    try:
        # Keep the main thread alive
        while True:
            asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping Nexagent API server...")
        server.stop()
        logger.info("Nexagent API server stopped")

if __name__ == "__main__":
    main()
