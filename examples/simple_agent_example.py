#!/usr/bin/env python3
"""
Simple Agent Example

This script demonstrates how to use the new architecture to create and run a simple agent.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent.factory import AgentFactory
from app.core.schema.schema import LLMSettings
from app.core.llm.llm import LLM
from app.utils.logging.logger import logger, configure_logger


async def main():
    """
    Main entry point for the example.
    """
    # Configure logging
    configure_logger(log_level="INFO")

    # Create LLM settings
    llm_settings = LLMSettings(
        model="gpt-3.5-turbo",
        api_type="openai",
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url="https://api.openai.com/v1",
        max_tokens=1024,
        temperature=0.7,
        allowed_domains=None,
        allowed_content_types=None
    )

    # Create an LLM instance
    try:
        llm = LLM(llm_config=llm_settings)
    except Exception as e:
        logger.error(f"Error creating LLM: {str(e)}")
        print(f"Error creating LLM: {str(e)}")
        print("Make sure you have set up your API keys correctly.")
        return 1

    # Create a simple agent
    try:
        agent = AgentFactory.create_agent(
            agent_type="simple",
            name="SimpleExample",
            llm=llm,
            max_steps=1,  # Only one step per interaction
        )
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        print(f"Error creating agent: {str(e)}")
        return 1

    print("\n=== Simple Agent Example ===\n")

    # Add a message to the agent
    agent.add_message("Hello, who are you?")

    # Run the agent
    try:
        print("Running agent...")
        print("Note: This example requires a valid OpenAI API key set in the OPENAI_API_KEY environment variable.")
        print("If you don't have a valid API key, you'll see connection errors.")
        print("This is expected behavior when testing without a valid API key.")
        print("\nExecuting agent...")
        result = await agent.run()
        print(f"\nResult: {result}")
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
