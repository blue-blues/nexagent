#!/usr/bin/env python
"""
Simple test script for the MessageClassifier.

This script tests the MessageClassifier with a few simple messages
to verify that it works correctly after the fixes.
"""

import asyncio
import os
import sys

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.message_classifier import MessageClassifier


async def test_message_classifier():
    """Test the MessageClassifier with a few simple messages."""
    # Create a MessageClassifier
    classifier = MessageClassifier()
    
    # Test messages
    test_messages = [
        "hi",
        "hello",
        "Write a Python function to calculate the Fibonacci sequence",
        "Can you help me debug this code?",
    ]
    
    # Test each message
    for message in test_messages:
        # Classify the message
        result = await classifier.execute(message=message)
        
        # Print the result
        classification = result.output["classification"]
        analysis = result.output["analysis"]
        
        print(f"\nMessage: {message}")
        print(f"Classification: {classification.upper()}")
        print(f"Chat Score: {analysis['chat_score']:.2f}, Agent Score: {analysis['agent_score']:.2f}")


if __name__ == "__main__":
    asyncio.run(test_message_classifier())
