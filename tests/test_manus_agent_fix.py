"""
Test script for the ManusAgent thought handling fix.

This script tests the fix for the 'dict' object has no attribute 'lower' error
that occurs when the ManusAgent tries to use the _calculate_similarity method.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.agent.manus_agent import ManusAgent
from app.logger import logger


async def test_manus_agent_thought_handling():
    """Test the ManusAgent thought handling with the fix."""
    logger.info("Starting ManusAgent thought handling test")
    
    # Create the ManusAgent
    agent = ManusAgent()
    
    # Manually add some dictionary thoughts to simulate the ManusAgent behavior
    dict_thought1 = {
        "step": 1,
        "content": "I need to search for information about Python programming",
        "timestamp": "2023-05-02T12:00:00"
    }
    dict_thought2 = {
        "step": 2,
        "content": "I need to search for information about Python programming",
        "timestamp": "2023-05-02T12:01:00"
    }
    
    # Add the dictionary thoughts to the thought history
    agent.thought_history.append(dict_thought1)
    agent.thought_history.append(dict_thought2)
    
    # Test the _calculate_similarity method with dictionary inputs
    similarity = agent._calculate_similarity(dict_thought1, dict_thought2)
    logger.info(f"Similarity between dictionary thoughts: {similarity}")
    
    # Test the _is_in_thought_loop method with dictionary thoughts
    agent.thought_history.append(dict_thought2)  # Add a third similar thought
    is_in_loop = agent._is_in_thought_loop()
    logger.info(f"Is in thought loop: {is_in_loop}")
    
    return "Test completed successfully"


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_manus_agent_thought_handling())
    print("\nFinal result:", result)
