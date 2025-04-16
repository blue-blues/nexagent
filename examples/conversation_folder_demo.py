#!/usr/bin/env python
"""
Demo script for the conversation folder organization feature.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.flow.integrated_flow import IntegratedFlow
from app.tool.output_organizer import OutputOrganizer


async def main():
    """Run the demo."""
    print("=== Conversation Folder Organization Demo ===\n")

    # Generate a unique conversation ID
    conversation_id = f"demo_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    print(f"Generated conversation ID: {conversation_id}\n")

    # Initialize the flow with the conversation ID
    flow = IntegratedFlow(conversation_id=conversation_id)

    # Process a request
    print("Processing request: 'Tell me about Python programming language'")
    try:
        result = await flow.execute("Tell me about Python programming language")
        print(f"\nResult: {result[:100]}...\n")
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        result = "Error processing request"

    # Process another request in the same conversation
    print("Processing another request: 'What are the key features of Python?'")
    try:
        result = await flow.execute("What are the key features of Python?")
        print(f"\nResult: {result[:100]}...\n")
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        result = "Error processing request"

    # Create a new output organizer to list the outputs
    output_organizer = OutputOrganizer()

    # Set the active conversation
    await output_organizer.execute(
        action="set_active_conversation",
        conversation_id=conversation_id
    )

    # List the outputs
    outputs_result = await output_organizer.execute(
        action="list_outputs"
    )

    print(f"Outputs: {outputs_result.output}\n")

    # Show the folder structure
    folder_path = os.path.join(os.getcwd(), "data_store", "conversations", conversation_id)
    print(f"Conversation folder: {folder_path}")

    if os.path.exists(folder_path):
        print("\nFolder structure:")
        for root, _, files in os.walk(folder_path):
            level = root.replace(folder_path, '').count(os.sep)
            indent = ' ' * 4 * level
            print(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 4 * (level + 1)
            for file in files:
                print(f"{sub_indent}{file}")

    print("\nDemo completed!")


if __name__ == "__main__":
    asyncio.run(main())
