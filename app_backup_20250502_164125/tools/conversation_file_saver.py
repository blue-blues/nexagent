"""
Conversation-aware file saver tool.

This module provides a ConversationFileSaver tool that extends the FileSaver tool
to save files in the conversation-specific folder.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, ConfigDict

from app.logger import logger
from app.tools.base import ToolResult
from app.tools.file_saver import FileSaver


class ConversationFileSaver(FileSaver):
    """
    A file saver tool that saves files in the conversation-specific folder.

    This tool extends the FileSaver tool to ensure that files are saved in the
    conversation-specific folder rather than in temporary directories or other
    locations.
    """

    name: str = "file_saver"
    description: str = """Save content to a file in the conversation folder.
    Use this tool when you need to save text, code, or generated content to a file.
    Files will be saved in the conversation-specific folder to ensure they are properly organized.
    Supports automatic formatting for data structures in various formats (JSON, YAML, CSV, table).
    Also supports binary content for image and other binary files.
    """

    # Fields for conversation-aware file saving
    active_conversation_id: Optional[str] = Field(default=None, description="The ID of the active conversation")
    base_folder: Optional[Path] = Field(default=None, description="The base folder for conversations")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self):
        """Initialize the ConversationFileSaver tool."""
        super().__init__()
        # Initialize the base folder
        self.base_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations"))
        self.base_folder.mkdir(parents=True, exist_ok=True)

    def set_active_conversation(self, conversation_id: str) -> None:
        """Set the active conversation ID."""
        self.active_conversation_id = conversation_id
        logger.info(f"ConversationFileSaver: Active conversation set to {conversation_id}")

    def _get_conversation_folder(self, conversation_id: str) -> Path:
        """Get the folder path for a conversation."""
        return self.base_folder / conversation_id

    def _get_outputs_folder(self, conversation_id: str) -> Path:
        """Get the outputs folder path for a conversation."""
        folder = self._get_conversation_folder(conversation_id)
        outputs_folder = folder / "outputs"
        outputs_folder.mkdir(parents=True, exist_ok=True)
        return outputs_folder

    def _ensure_conversation_exists(self, conversation_id: str) -> bool:
        """Ensure that a conversation folder exists."""
        folder = self._get_conversation_folder(conversation_id)
        if not folder.exists():
            # Create the folder if it doesn't exist
            folder.mkdir(parents=True, exist_ok=True)

            # Create outputs subfolder
            outputs_folder = folder / "outputs"
            outputs_folder.mkdir(exist_ok=True)

            return True
        return False

    def _redirect_to_conversation_folder(self, file_path: str) -> str:
        """
        Redirect a file path to the conversation folder.

        Args:
            file_path: The original file path

        Returns:
            The redirected file path in the conversation folder
        """
        if not self.active_conversation_id:
            logger.warning("No active conversation ID set, cannot redirect file path")
            return file_path

        # Check if the path is already in a conversation folder
        if str(self.base_folder) in file_path:
            return file_path

        # Check if this is an absolute path
        if os.path.isabs(file_path):
            # Extract just the filename
            filename = os.path.basename(file_path)
        else:
            # Use the relative path as is
            filename = file_path

        try:
            # Get the outputs folder for the active conversation
            outputs_folder = self._get_outputs_folder(self.active_conversation_id)

            # Create the new path
            new_path = str(outputs_folder / filename)

            logger.info(f"Redirecting file path from {file_path} to {new_path}")

            return new_path
        except Exception as e:
            logger.error(f"Error redirecting file path: {str(e)}")
            return file_path

    async def execute(
        self,
        content: Union[str, Dict[str, Any], List, bytes],
        file_path: str,
        format: str = "auto",
        mode: str = "w",
        indent: int = 2,
        pretty: bool = True
    ) -> ToolResult:
        """
        Save content to a file in the conversation folder.

        Args:
            content: The content to save (string, data structure, or binary data)
            file_path: The path where the file should be saved
            format: Format to use for data structures (json, yaml, csv, table, text, auto, binary)
            mode: The file opening mode ('w' for write, 'a' for append, 'wb' for binary write)
            indent: Number of spaces for indentation in JSON format
            pretty: Whether to format the output for improved readability

        Returns:
            ToolResult with a message indicating the result of the operation
        """
        try:
            # Ensure the conversation folder exists
            if self.active_conversation_id:
                self._ensure_conversation_exists(self.active_conversation_id)

                # Redirect the file path to the conversation folder
                redirected_file_path = self._redirect_to_conversation_folder(file_path)
            else:
                # If no active conversation ID is set, use the original file path
                logger.warning("No active conversation ID set, using original file path")
                redirected_file_path = file_path
        except Exception as e:
            logger.error(f"Error preparing file path: {str(e)}")
            redirected_file_path = file_path

        # Call the parent execute method with the redirected file path
        return await super().execute(
            content=content,
            file_path=redirected_file_path,
            format=format,
            mode=mode,
            indent=indent,
            pretty=pretty
        )
