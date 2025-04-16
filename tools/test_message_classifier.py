#!/usr/bin/env python
"""
Test script for the MessageClassifier.

This script tests the MessageClassifier with various types of messages
to evaluate its effectiveness in distinguishing between chat messages
and messages requiring agent processing.
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Any

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.message_classifier import MessageClassifier


# Test messages
TEST_MESSAGES = [
    # Simple chat messages
    {"message": "hi", "expected": "chat"},
    {"message": "hello", "expected": "chat"},
    {"message": "hey there", "expected": "chat"},
    {"message": "thanks", "expected": "chat"},
    {"message": "thank you", "expected": "chat"},
    {"message": "ok", "expected": "chat"},
    {"message": "yes", "expected": "chat"},
    {"message": "no", "expected": "chat"},
    {"message": "goodbye", "expected": "chat"},
    {"message": "how are you", "expected": "chat"},
    {"message": "good morning", "expected": "chat"},
    
    # Simple questions (borderline)
    {"message": "what's your name?", "expected": "agent"},
    {"message": "how does this work?", "expected": "agent"},
    {"message": "can you help me?", "expected": "agent"},
    
    # Agent-requiring messages
    {"message": "Write a Python function to calculate the Fibonacci sequence", "expected": "agent"},
    {"message": "Explain the difference between REST and GraphQL", "expected": "agent"},
    {"message": "Create a detailed marketing plan for a new product launch", "expected": "agent"},
    {"message": "Analyze the pros and cons of using microservices architecture", "expected": "agent"},
    {"message": "Help me debug this code: ```def factorial(n): return n * factorial(n-1)```", "expected": "agent"},
    {"message": "Can you provide a step-by-step guide to setting up a Docker container?", "expected": "agent"},
    {"message": "I need help understanding how blockchain technology works", "expected": "agent"},
    {"message": "Compare and contrast different machine learning algorithms for classification", "expected": "agent"},
    {"message": "Write a regex pattern to validate email addresses", "expected": "agent"},
    {"message": "Summarize the key points from the latest research on quantum computing", "expected": "agent"},
    
    # Complex messages
    {"message": "I'm working on a project that requires me to process large amounts of data efficiently. Can you recommend some techniques or libraries that would be helpful for this task?", "expected": "agent"},
    {"message": "I've been trying to implement a neural network for image classification but I'm getting poor accuracy. Here's my code: ```import tensorflow as tf...``` Can you help me improve it?", "expected": "agent"},
    {"message": "Write a comprehensive business plan for a SaaS startup that focuses on providing AI-powered analytics for e-commerce businesses. Include market analysis, financial projections, and marketing strategy.", "expected": "agent"},
    
    # Ambiguous messages
    {"message": "What do you think?", "expected": "chat"},
    {"message": "Can you do that?", "expected": "chat"},
    {"message": "Is that possible?", "expected": "chat"},
    {"message": "Tell me more", "expected": "chat"},
]


def format_result(result: Dict[str, Any]) -> str:
    """Format the classification result for display."""
    classification = result["classification"]
    analysis = result["analysis"]
    
    return (
        f"Classification: {classification.upper()}\n"
        f"Chat Score: {analysis['chat_score']:.2f}, Agent Score: {analysis['agent_score']:.2f}\n"
        f"Word Count: {analysis['word_count']}, Keywords: {analysis['agent_keyword_count']}, Complexity: {analysis['complexity_indicator_count']}\n"
        f"Length Score: {analysis['length_score']:.2f}, Question Score: {analysis['question_score']:.2f}, Code Score: {analysis['code_score']:.2f}"
    )


async def test_message_classifier():
    """Test the MessageClassifier with various messages."""
    # Create a MessageClassifier
    classifier = MessageClassifier()
    
    # Track results
    correct = 0
    total = len(TEST_MESSAGES)
    results = []
    
    # Test each message
    for i, test_case in enumerate(TEST_MESSAGES):
        message = test_case["message"]
        expected = test_case["expected"]
        
        # Classify the message
        result = await classifier.execute(message=message)
        classification = result.output["classification"]
        
        # Check if the classification matches the expected result
        is_correct = classification == expected
        if is_correct:
            correct += 1
        
        # Store the result
        results.append({
            "message": message,
            "expected": expected,
            "classification": classification,
            "is_correct": is_correct,
            "analysis": result.output["analysis"]
        })
        
        # Print the result
        print(f"\nTest {i+1}/{total}: {'✓' if is_correct else '✗'}")
        print(f"Message: {message}")
        print(f"Expected: {expected.upper()}")
        print(format_result(result.output))
    
    # Print summary
    accuracy = correct / total * 100
    print(f"\nAccuracy: {accuracy:.1f}% ({correct}/{total} correct)")
    
    # Analyze errors
    errors = [r for r in results if not r["is_correct"]]
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"\nMessage: {error['message']}")
            print(f"Expected: {error['expected'].upper()}, Got: {error['classification'].upper()}")
            analysis = error["analysis"]
            print(f"Chat Score: {analysis['chat_score']:.2f}, Agent Score: {analysis['agent_score']:.2f}")
    
    # Save results to file
    with open("message_classifier_results.json", "w") as f:
        json.dump({
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to message_classifier_results.json")


if __name__ == "__main__":
    asyncio.run(test_message_classifier())
