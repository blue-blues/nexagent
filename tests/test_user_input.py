"""
Test script for the user input functionality.

This script demonstrates how to use the MessageAskUser tool to request input from the user
and how to submit responses using the user_input_handler CLI.
"""

import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.message_notification import MessageAskUser
from app.ui.user_input_cli import user_input_cli
from app.util.user_input_manager import input_manager


async def test_user_input():
    """Test the user input functionality."""
    print("Starting user input test...")
    
    # Start the user input CLI
    user_input_cli.start()
    print("User input CLI started")
    
    try:
        # Create a MessageAskUser tool
        ask_tool = MessageAskUser()
        
        # Ask a simple question
        print("\nAsking a simple question...")
        result1 = await ask_tool.execute(
            text="What is your name?",
            timeout=60  # Wait up to 60 seconds for a response
        )
        print(f"Received response: {result1.output}")
        
        # Ask a more complex question
        print("\nAsking a more complex question...")
        result2 = await ask_tool.execute(
            text="What is your favorite programming language and why?",
            timeout=60
        )
        print(f"Received response: {result2.output}")
        
        # Ask a question with a takeover suggestion
        print("\nAsking a question with a takeover suggestion...")
        result3 = await ask_tool.execute(
            text="Would you like to take control of the browser to perform a sensitive operation?",
            suggest_user_takeover="browser",
            timeout=60
        )
        print(f"Received response: {result3.output}")
        
        print("\nAll tests completed successfully!")
    except Exception as e:
        print(f"Error during test: {str(e)}")
    finally:
        # Stop the user input CLI
        user_input_cli.stop()
        print("User input CLI stopped")


if __name__ == "__main__":
    asyncio.run(test_user_input())
