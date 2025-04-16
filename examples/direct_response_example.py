"""
Example script demonstrating the direct response system for simple prompts.

This script shows how the IntegratedFlow handles both simple prompts with direct
responses and complex prompts that are routed to the agent system.
"""

import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.flow.integrated_flow import IntegratedFlow
from app.logger import logger


async def main():
    """Run the direct response example."""
    # Create an IntegratedFlow instance
    flow = IntegratedFlow()
    
    # Examples of simple prompts that should get direct responses
    simple_prompts = [
        "hello",
        "hi there",
        "how are you",
        "what can you do",
        "who are you",
        "thanks",
        "goodbye"
    ]
    
    # Examples of complex prompts that should be routed to the agent system
    complex_prompts = [
        "write a python function to calculate fibonacci numbers",
        "explain how to use React hooks",
        "help me debug this error message",
        "what is the capital of France"
    ]
    
    print("\n=== Testing Simple Prompts (Direct Responses) ===\n")
    for prompt in simple_prompts:
        print(f"\nPrompt: '{prompt}'")
        result = await flow.execute(prompt)
        print(f"Response: '{result}'")
        print("-" * 50)
    
    print("\n=== Testing Complex Prompts (Agent System) ===\n")
    # Only test the first complex prompt to save time
    prompt = complex_prompts[0]
    print(f"\nPrompt: '{prompt}'")
    print("(This will be processed by the agent system and may take longer...)")
    result = await flow.execute(prompt)
    print(f"Response: '{result[:200]}...' (truncated)")


if __name__ == "__main__":
    # Configure logging
    logger.setLevel("INFO")
    
    # Run the example
    asyncio.run(main())
