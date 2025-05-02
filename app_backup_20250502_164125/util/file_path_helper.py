"""
File path helper utilities.

This module provides utility functions for working with file paths,
particularly for redirecting file paths to conversation-specific folders.
"""

import os
from pathlib import Path
from typing import Optional

from app.logger import logger


def get_conversation_folder(conversation_id: str) -> Path:
    """
    Get the folder path for a conversation.
    
    Args:
        conversation_id: The ID of the conversation
        
    Returns:
        The path to the conversation folder
    """
    base_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations"))
    return base_folder / conversation_id


def get_outputs_folder(conversation_id: str) -> Path:
    """
    Get the outputs folder path for a conversation.
    
    Args:
        conversation_id: The ID of the conversation
        
    Returns:
        The path to the outputs folder for the conversation
    """
    folder = get_conversation_folder(conversation_id)
    outputs_folder = folder / "outputs"
    outputs_folder.mkdir(parents=True, exist_ok=True)
    return outputs_folder


def redirect_to_conversation_folder(file_path: str, conversation_id: Optional[str] = None) -> str:
    """
    Redirect a file path to the conversation folder.
    
    Args:
        file_path: The original file path
        conversation_id: The ID of the conversation
        
    Returns:
        The redirected file path in the conversation folder
    """
    if not conversation_id:
        logger.warning("No conversation ID provided, cannot redirect file path")
        return file_path
    
    # Get the base folder for conversations
    base_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations"))
    
    # Check if the path is already in a conversation folder
    if str(base_folder) in file_path:
        return file_path
    
    # Check if this is an absolute path
    if os.path.isabs(file_path):
        # Extract just the filename
        filename = os.path.basename(file_path)
    else:
        # Use the relative path as is
        filename = file_path
    
    # Get the outputs folder for the conversation
    outputs_folder = get_outputs_folder(conversation_id)
    
    # Create the new path
    new_path = str(outputs_folder / filename)
    
    logger.info(f"Redirecting file path from {file_path} to {new_path}")
    
    return new_path


def is_temp_path(file_path: str) -> bool:
    """
    Check if a file path is in a temporary directory.
    
    Args:
        file_path: The file path to check
        
    Returns:
        True if the path is in a temporary directory, False otherwise
    """
    temp_patterns = [
        "/tmp/",
        "\\tmp\\",
        "/temp/",
        "\\temp\\",
        os.path.join(os.environ.get("TEMP", ""), ""),
        os.path.join(os.environ.get("TMP", ""), "")
    ]
    
    return any(pattern in file_path for pattern in temp_patterns)
