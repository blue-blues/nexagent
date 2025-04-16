#!/usr/bin/env python
"""
Command-line tool to classify messages using the MessageClassifier.

This script provides a simple command-line interface to classify messages
as either chat messages or messages requiring agent processing.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Dict, Any

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.message_classifier import MessageClassifier


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


async def classify_message(message: str, chat_threshold: float = None, agent_threshold: float = None) -> None:
    """Classify a message using the MessageClassifier."""
    # Create a MessageClassifier
    classifier = MessageClassifier()
    
    # Prepare threshold override if provided
    threshold_override = None
    if chat_threshold is not None or agent_threshold is not None:
        threshold_override = {}
        if chat_threshold is not None:
            threshold_override["chat_threshold"] = chat_threshold
        if agent_threshold is not None:
            threshold_override["agent_threshold"] = agent_threshold
    
    # Classify the message
    result = await classifier.execute(
        message=message,
        threshold_override=threshold_override
    )
    
    # Print the result
    print(f"\nMessage: {message}")
    print(format_result(result.output))
    
    # Print detailed analysis if requested
    if "--verbose" in sys.argv:
        print("\nDetailed Analysis:")
        print(json.dumps(result.output["analysis"], indent=2))


async def interactive_mode() -> None:
    """Run the classifier in interactive mode."""
    print("Message Classifier Interactive Mode")
    print("Enter messages to classify, or 'exit' to quit.")
    print("You can also use the following commands:")
    print("  !thresholds <chat> <agent>  - Set classification thresholds")
    print("  !verbose                   - Toggle verbose mode")
    print("  !help                      - Show this help message")
    print("  !exit                      - Exit interactive mode")
    
    # Create a MessageClassifier
    classifier = MessageClassifier()
    
    # Default thresholds
    chat_threshold = classifier.chat_threshold
    agent_threshold = classifier.agent_threshold
    
    # Verbose mode flag
    verbose = False
    
    while True:
        # Get user input
        try:
            message = input("\n> ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
        
        # Check for commands
        if message.lower() in ["exit", "quit", "!exit", "!quit"]:
            print("Exiting...")
            break
        elif message.lower() in ["!help", "help"]:
            print("Commands:")
            print("  !thresholds <chat> <agent>  - Set classification thresholds")
            print("  !verbose                   - Toggle verbose mode")
            print("  !help                      - Show this help message")
            print("  !exit                      - Exit interactive mode")
            continue
        elif message.lower() == "!verbose":
            verbose = not verbose
            print(f"Verbose mode {'enabled' if verbose else 'disabled'}")
            continue
        elif message.lower().startswith("!thresholds"):
            try:
                parts = message.split()
                if len(parts) >= 3:
                    chat_threshold = float(parts[1])
                    agent_threshold = float(parts[2])
                    print(f"Thresholds set: chat={chat_threshold}, agent={agent_threshold}")
                else:
                    print(f"Current thresholds: chat={chat_threshold}, agent={agent_threshold}")
            except ValueError:
                print("Invalid threshold values. Use format: !thresholds <chat> <agent>")
            continue
        
        # Prepare threshold override
        threshold_override = {
            "chat_threshold": chat_threshold,
            "agent_threshold": agent_threshold
        }
        
        # Classify the message
        result = await classifier.execute(
            message=message,
            threshold_override=threshold_override
        )
        
        # Print the result
        classification = result.output["classification"]
        analysis = result.output["analysis"]
        
        print(f"Classification: {classification.upper()}")
        print(f"Chat Score: {analysis['chat_score']:.2f}, Agent Score: {analysis['agent_score']:.2f}")
        
        # Print detailed analysis if verbose mode is enabled
        if verbose:
            print("\nDetailed Analysis:")
            print(json.dumps(analysis, indent=2))


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Classify messages using the MessageClassifier")
    parser.add_argument("message", nargs="?", help="The message to classify")
    parser.add_argument("--chat-threshold", type=float, help="Threshold for classifying as chat")
    parser.add_argument("--agent-threshold", type=float, help="Threshold for classifying as agent-requiring")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed analysis")
    
    args = parser.parse_args()
    
    if args.interactive:
        await interactive_mode()
    elif args.message:
        await classify_message(args.message, args.chat_threshold, args.agent_threshold)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
