#!/usr/bin/env python
"""
Test script for the Nexagent API server.

This script tests the basic functionality of the Nexagent API server
by making requests to the API endpoints.
"""

import argparse
import requests
import json
import sys
import time
import websocket
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test the Nexagent API server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host of the API server")
    parser.add_argument("--port", type=int, default=8000, help="Port of the API server")
    parser.add_argument("--organization", action="store_true", help="Test the server with organization features")
    return parser.parse_args()

def test_health_check(base_url):
    """Test the health check endpoint"""
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            logger.info("Health check: OK")
            return True
        else:
            logger.error(f"Health check failed with status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Health check failed with error: {str(e)}")
        return False

def test_process_message(base_url):
    """Test the process message endpoint"""
    try:
        data = {
            "content": "Hello, Nexagent!",
            "conversation_id": None
        }
        response = requests.post(f"{base_url}/api/message", json=data)
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Process message: OK (conversation_id: {result['conversation_id']})")
            return result['conversation_id']
        else:
            logger.error(f"Process message failed with status code {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Process message failed with error: {str(e)}")
        return None

def test_get_conversations(base_url):
    """Test the get conversations endpoint"""
    try:
        response = requests.get(f"{base_url}/api/conversations")
        if response.status_code == 200:
            conversations = response.json()
            logger.info(f"Get conversations: OK ({len(conversations)} conversations)")
            return True
        else:
            logger.error(f"Get conversations failed with status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Get conversations failed with error: {str(e)}")
        return False

def test_get_conversation(base_url, conversation_id):
    """Test the get conversation endpoint"""
    try:
        response = requests.get(f"{base_url}/api/conversations/{conversation_id}")
        if response.status_code == 200:
            conversation = response.json()
            logger.info(f"Get conversation: OK (title: {conversation['title']})")
            return True
        else:
            logger.error(f"Get conversation failed with status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Get conversation failed with error: {str(e)}")
        return False

def test_websocket(base_url, conversation_id):
    """Test the WebSocket connection"""
    ws_url = f"ws://{base_url.split('//')[1]}/api/ws/timeline/{conversation_id}"
    
    def on_message(ws, message):
        logger.info(f"WebSocket message received: {message[:100]}...")
    
    def on_error(ws, error):
        logger.error(f"WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
    
    def on_open(ws):
        logger.info("WebSocket connection established")
        # Send a ping message
        ws.send("ping")
    
    # Create WebSocket connection
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Start WebSocket connection in a separate thread
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Wait for a moment to see if the connection is established
    time.sleep(3)
    
    # Close the WebSocket connection
    ws.close()
    
    return True

def test_organization_features(base_url, conversation_id):
    """Test the organization features"""
    try:
        # Test save material
        material_data = {
            "conversation_id": conversation_id,
            "material_name": "test_material.txt",
            "material_content": "This is a test material."
        }
        response = requests.post(f"{base_url}/api/materials", json=material_data)
        if response.status_code == 200:
            logger.info("Save material: OK")
        else:
            logger.error(f"Save material failed with status code {response.status_code}")
            return False
        
        # Test generate output
        output_data = {
            "conversation_id": conversation_id,
            "output_format": "markdown"
        }
        response = requests.post(f"{base_url}/api/generate-output", json=output_data)
        if response.status_code == 200:
            logger.info("Generate output: OK")
            return True
        else:
            logger.error(f"Generate output failed with status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Organization features test failed with error: {str(e)}")
        return False

def main():
    """Main entry point for the test script"""
    args = parse_args()
    base_url = f"http://{args.host}:{args.port}"
    
    logger.info(f"Testing Nexagent API server at {base_url}")
    
    # Test health check
    if not test_health_check(base_url):
        logger.error("Health check failed. Make sure the server is running.")
        sys.exit(1)
    
    # Test process message
    conversation_id = test_process_message(base_url)
    if not conversation_id:
        logger.error("Process message test failed.")
        sys.exit(1)
    
    # Test get conversations
    if not test_get_conversations(base_url):
        logger.error("Get conversations test failed.")
        sys.exit(1)
    
    # Test get conversation
    if not test_get_conversation(base_url, conversation_id):
        logger.error("Get conversation test failed.")
        sys.exit(1)
    
    # Test WebSocket connection
    if not test_websocket(base_url, conversation_id):
        logger.error("WebSocket test failed.")
        sys.exit(1)
    
    # Test organization features if requested
    if args.organization:
        if not test_organization_features(base_url, conversation_id):
            logger.error("Organization features test failed.")
            sys.exit(1)
    
    logger.info("All tests passed successfully!")

if __name__ == "__main__":
    main()
