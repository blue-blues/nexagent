"""
Test script for the ManusAgent thinking summary fix.

This script tests the fix for the 'string indices must be integers, not 'str'' error
that occurs when the ManusAgent tries to generate a thinking summary with mixed thought types.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.agent.manus_agent import ManusAgent
from app.logger import logger


async def test_manus_agent_thinking_summary():
    """Test the ManusAgent thinking summary with mixed thought types."""
    logger.info("Starting ManusAgent thinking summary test")
    
    # Create the ManusAgent
    agent = ManusAgent()
    
    # Add a mix of dictionary and string thoughts to simulate the issue
    dict_thought = {
        "step": 1,
        "content": "I need to search for information about Python programming",
        "timestamp": "2023-05-02T12:00:00"
    }
    string_thought = "This is a string thought that would cause the error"
    
    # Add the mixed thoughts to the thought history
    agent.thought_history.append(dict_thought)
    agent.thought_history.append(string_thought)
    
    # Test the get_thinking_summary method with mixed thought types
    try:
        thinking_summary = await agent.get_thinking_summary()
        logger.info("Successfully generated thinking summary with mixed thought types")
        logger.info(f"Summary: {thinking_summary}")
        return "Test completed successfully"
    except Exception as e:
        logger.error(f"Error generating thinking summary: {e}")
        return f"Test failed: {e}"


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_manus_agent_thinking_summary())
    print("\nFinal result:", result)
