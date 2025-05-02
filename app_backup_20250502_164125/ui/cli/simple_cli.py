#!/usr/bin/env python3
"""
Simple CLI for testing the new architecture.

This script provides a simple command-line interface for interacting with
the new architecture.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.agent.factory import AgentFactory
from app.core.llm.llm import LLM
from app.utils.logging.logger import logger, configure_logger


async def main():
    """
    Main entry point for the simple CLI.
    """
    # Configure logging
    configure_logger(log_level="INFO")
    
    # Create an LLM instance
    try:
        llm = LLM()
    except Exception as e:
        logger.error(f"Error creating LLM: {str(e)}")
        print(f"Error creating LLM: {str(e)}")
        print("Make sure you have set up your API keys correctly.")
        return 1
    
    # Create a simple agent
    try:
        agent = AgentFactory.create_agent(
            agent_type="simple",
            name="SimpleCLI",
            llm=llm,
            max_steps=1,  # Only one step per interaction
        )
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        print(f"Error creating agent: {str(e)}")
        return 1
    
    print("\n=== Nexagent Simple CLI ===\n")
    print("This is a simple CLI for testing the new architecture.")
    print("Type 'exit' to quit.\n")
    
    try:
        while True:
            # Get user input
            user_input = input("You: ")
            
            if user_input.lower() == 'exit':
                print("Exiting...")
                break
            
            if not user_input.strip():
                print("Please enter a message.")
                continue
            
            # Process the user input
            try:
                print("Agent: ", end="", flush=True)
                response = await agent.chat(user_input)
                print(response)
            except Exception as e:
                logger.error(f"Error processing input: {str(e)}")
                print(f"Error: {str(e)}")
    
    except KeyboardInterrupt:
        print("\nExiting...")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
