#!/usr/bin/env python
"""
Nexagent API Server

This script starts the Nexagent API server, which provides a RESTful API
for interacting with the Nexagent AI Assistant.
"""

import argparse
import time
import os

from app.api.server import nexagent_server
from app.logger import logger
from app.memory import MemoryReasoning
from app.tools.browser import WebSearch, EnhancedBrowserTool
from app.tools.search.brave_search import BraveSearchEngine
from app.tools.git_tool import GitTool

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Start the Nexagent API server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    return parser.parse_args()

def setup_browser_tools():
    """Set up browser tools for the Nexagent server"""
    # Initialize browser tools
    web_search = WebSearch()
    enhanced_browser = EnhancedBrowserTool()

    # Add Brave search engine if API key is available
    brave_api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if brave_api_key:
        logger.info("Brave Search API key found, adding Brave search engine")
        web_search._search_engine["brave"] = BraveSearchEngine()
    else:
        logger.warning("Brave Search API key not found, Brave search engine will not be available")

    # Register browser tools with the server
    nexagent_server.register_tool(web_search)
    nexagent_server.register_tool(enhanced_browser)

    logger.info("Browser tools initialized and registered")

def setup_memory_reasoning():
    """Set up memory reasoning for the Nexagent server"""
    # Initialize memory reasoning
    memory_reasoning = MemoryReasoning(max_memories=1000)

    # Register memory reasoning with the server
    nexagent_server.register_memory_reasoning(memory_reasoning)

    # Set up a handler to inject memory reasoning into flows
    def inject_memory_reasoning(flow):
        if hasattr(flow, '_memory_reasoning'):
            flow._memory_reasoning = memory_reasoning
            logger.info(f"Injected memory reasoning into flow: {flow.__class__.__name__}")

    # Register the handler with the server
    nexagent_server.register_flow_initializer(inject_memory_reasoning)

    logger.info("Memory reasoning initialized and registered")

def setup_git_tool():
    """Set up Git tool for the Nexagent server"""
    # Initialize Git tool
    git_tool = GitTool()

    # Register Git tool with the server
    nexagent_server.register_tool(git_tool)

    logger.info("Git tool initialized and registered")

def main():
    """Main entry point for the API server"""
    args = parse_args()

    # Log startup information
    logger.info(f"Starting Nexagent API server at http://{args.host}:{args.port}")
    logger.info("Press Ctrl+C to stop the server")

    # Set up browser tools
    setup_browser_tools()

    # Set up memory reasoning
    setup_memory_reasoning()

    # Set up Git tool
    setup_git_tool()

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
