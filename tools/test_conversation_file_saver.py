#!/usr/bin/env python
"""
Test script for the ConversationFileSaver.

This script tests the ConversationFileSaver to ensure it correctly redirects file paths
to the conversation-specific folder.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.conversation_file_saver import ConversationFileSaver
from app.logger import logger


async def test_conversation_file_saver():
    """Test the ConversationFileSaver."""
    # Create a ConversationFileSaver
    file_saver = ConversationFileSaver()
    
    # Set the active conversation ID
    conversation_id = "test_conversation"
    file_saver.set_active_conversation(conversation_id)
    
    # Test saving a file with a relative path
    content = "This is a test file."
    result = await file_saver.execute(
        content=content,
        file_path="test.txt"
    )
    
    print(f"Result of saving file with relative path: {result.output}")
    
    # Test saving a file with an absolute path
    temp_path = os.path.join(os.environ.get("TEMP", "/tmp"), "absolute_test.txt")
    result = await file_saver.execute(
        content=content,
        file_path=temp_path
    )
    
    print(f"Result of saving file with absolute path: {result.output}")
    
    # Test saving a file with a path that's already in a conversation folder
    base_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations"))
    conversation_path = base_folder / conversation_id / "outputs" / "already_in_conversation.txt"
    result = await file_saver.execute(
        content=content,
        file_path=str(conversation_path)
    )
    
    print(f"Result of saving file with path already in conversation folder: {result.output}")
    
    # Test saving a file with no active conversation ID
    file_saver.active_conversation_id = None
    result = await file_saver.execute(
        content=content,
        file_path="no_conversation.txt"
    )
    
    print(f"Result of saving file with no active conversation ID: {result.output}")


if __name__ == "__main__":
    asyncio.run(test_conversation_file_saver())
