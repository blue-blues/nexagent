#!/usr/bin/env python
"""
Test script for the OutputOrganizer.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tool.output_organizer import OutputOrganizer


async def main():
    """Run the test."""
    print("=== OutputOrganizer Test ===\n")
    
    # Generate a unique conversation ID
    conversation_id = f"test_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    print(f"Generated conversation ID: {conversation_id}\n")
    
    # Initialize the output organizer
    output_organizer = OutputOrganizer()
    
    # Set the active conversation
    print("Setting active conversation...")
    result = await output_organizer.execute(
        action="set_active_conversation",
        conversation_id=conversation_id
    )
    print(f"Result: {result.output}\n")
    
    # Save an output
    print("Saving output 'test_document.txt'...")
    result = await output_organizer.execute(
        action="save_output",
        output_name="test_document",
        output_content="This is a test document.",
        output_type="document"
    )
    print(f"Result: {result.output}\n")
    
    # Save another output
    print("Saving output 'test_code.py'...")
    result = await output_organizer.execute(
        action="save_output",
        output_name="test_code",
        output_content="print('Hello, world!')",
        output_type="code"
    )
    print(f"Result: {result.output}\n")
    
    # List the outputs
    print("Listing outputs...")
    result = await output_organizer.execute(
        action="list_outputs"
    )
    print(f"Result: {result.output}\n")
    
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
    
    print("\nTest completed!")


if __name__ == "__main__":
    asyncio.run(main())
