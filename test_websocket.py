#!/usr/bin/env python
"""
Test script for WebSocket connections to the Nexagent API server.

This script tests the WebSocket connection for timeline updates.
"""

import asyncio
import websockets
import json
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket(host, port, conversation_id):
    """Test the WebSocket connection for timeline updates"""
    uri = f"ws://{host}:{port}/api/ws/timeline/{conversation_id}"
    
    logger.info(f"Connecting to WebSocket at {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("WebSocket connection established")
            
            # Send a ping message
            await websocket.send("ping")
            logger.info("Sent ping message")
            
            # Wait for a response
            response = await websocket.recv()
            logger.info(f"Received response: {response}")
            
            # Keep the connection open for a while to see if we receive any updates
            logger.info("Keeping connection open for 10 seconds...")
            for i in range(10):
                try:
                    # Set a timeout for receiving messages
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    logger.info(f"Received message: {response}")
                except asyncio.TimeoutError:
                    logger.info(f"No message received in the last second ({i+1}/10)")
            
            # Send another ping before closing
            await websocket.send("ping")
            logger.info("Sent final ping message")
            
            # Wait for a response
            response = await websocket.recv()
            logger.info(f"Received response: {response}")
            
            logger.info("WebSocket test completed successfully")
    except Exception as e:
        logger.error(f"WebSocket test failed: {str(e)}")
        return False
    
    return True

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test WebSocket connection to Nexagent API server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host of the API server")
    parser.add_argument("--port", type=int, default=8000, help="Port of the API server")
    parser.add_argument("--conversation-id", type=str, default="test-conversation", 
                        help="Conversation ID to use for the WebSocket connection")
    return parser.parse_args()

async def main():
    """Main entry point for the test script"""
    args = parse_args()
    
    logger.info(f"Testing WebSocket connection to {args.host}:{args.port}")
    
    # Test the WebSocket connection
    success = await test_websocket(args.host, args.port, args.conversation_id)
    
    if success:
        logger.info("WebSocket test completed successfully")
    else:
        logger.error("WebSocket test failed")

if __name__ == "__main__":
    asyncio.run(main())
