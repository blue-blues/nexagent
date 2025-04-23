"""
File attachment processor tool.

This module provides a tool for processing file attachments in conversations.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles
from pydantic import BaseModel, Field

from app.config import config
from app.logger import logger
from app.tools.base import BaseTool, ToolResult
from app.util.file_path_helper import get_conversation_folder


class FileAttachmentProcessor(BaseTool):
    """
    A tool for processing file attachments in conversations.

    This tool handles file uploads, validates them, and processes their content
    for use in conversations.
    """

    name: str = "file_attachment_processor"
    description: str = """Process file attachments in conversations.
    Use this tool to validate, save, and process file attachments uploaded by users.
    Files will be saved in the conversation-specific folder and their content can be
    processed for use in the conversation.
    """

    parameters: dict = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the uploaded file",
            },
            "conversation_id": {
                "type": "string",
                "description": "ID of the conversation",
            },
            "process_content": {
                "type": "boolean",
                "description": "Whether to process the content of the file",
                "default": True,
            },
        },
        "required": ["file_path", "conversation_id"],
    }

    async def execute(
        self,
        file_path: str,
        conversation_id: str,
        process_content: bool = True,
    ) -> ToolResult:
        """
        Process a file attachment.

        Args:
            file_path: Path to the uploaded file
            conversation_id: ID of the conversation
            process_content: Whether to process the content of the file

        Returns:
            ToolResult with information about the processed file
        """
        try:
            # Validate the file
            validation_result = self._validate_file(file_path)
            if not validation_result["valid"]:
                return ToolResult(
                    output=f"File validation failed: {validation_result['reason']}",
                    error=True,
                )

            # Save the file to the conversation folder
            saved_file_path = await self._save_file_to_conversation(file_path, conversation_id)

            # Process the file content if requested
            content = None
            if process_content:
                content = await self._process_file_content(saved_file_path)

            return ToolResult(
                output={
                    "message": f"File processed successfully: {os.path.basename(saved_file_path)}",
                    "file_path": saved_file_path,
                    "content": content,
                }
            )
        except Exception as e:
            logger.error(f"Error processing file attachment: {str(e)}")
            return ToolResult(
                output=f"Error processing file attachment: {str(e)}",
                error=True,
            )

    def _validate_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate a file attachment.

        Args:
            file_path: Path to the file

        Returns:
            Dict with validation result
        """
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                return {"valid": False, "reason": "File does not exist"}

            # Get file attachment settings
            settings = config.file_attachment_config
            if not settings:
                # Use default settings if not configured
                from app.config import FileAttachmentSettings
                settings = FileAttachmentSettings()

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > settings.max_file_size:
                return {
                    "valid": False,
                    "reason": f"File size ({file_size} bytes) exceeds maximum allowed size ({settings.max_file_size} bytes)",
                }

            # Check file extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in settings.allowed_extensions:
                return {
                    "valid": False,
                    "reason": f"File extension '{ext}' is not allowed. Allowed extensions: {', '.join(settings.allowed_extensions)}",
                }

            # Scan for malware if enabled
            if settings.scan_for_malware:
                # Implement malware scanning here
                # For now, we'll just log a message
                logger.info(f"Malware scanning is enabled but not implemented for file: {file_path}")

            return {"valid": True}
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return {"valid": False, "reason": f"Validation error: {str(e)}"}

    async def _save_file_to_conversation(self, file_path: str, conversation_id: str) -> str:
        """
        Save a file to the conversation folder.

        Args:
            file_path: Path to the file
            conversation_id: ID of the conversation

        Returns:
            Path to the saved file
        """
        try:
            # Get the conversation folder
            conversation_folder = get_conversation_folder(conversation_id)
            attachments_folder = conversation_folder / "attachments"
            attachments_folder.mkdir(parents=True, exist_ok=True)

            # Generate a unique filename to avoid collisions
            original_filename = os.path.basename(file_path)
            filename, ext = os.path.splitext(original_filename)
            unique_filename = f"{filename}_{str(uuid.uuid4())[:8]}{ext}"
            destination_path = attachments_folder / unique_filename

            # Copy the file
            shutil.copy2(file_path, destination_path)
            logger.info(f"File saved to conversation folder: {destination_path}")

            return str(destination_path)
        except Exception as e:
            logger.error(f"Error saving file to conversation folder: {str(e)}")
            raise

    async def _process_file_content(self, file_path: str) -> Optional[str]:
        """
        Process the content of a file.

        Args:
            file_path: Path to the file

        Returns:
            Processed content of the file, or None if processing is not possible
        """
        try:
            # Get file extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()

            # Process text-based files
            if ext in [".txt", ".md", ".py", ".js", ".ts", ".html", ".xml", ".json", ".csv"]:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    return content

            # For other file types, return None
            # In a real implementation, you might want to use specialized libraries
            # to extract text from PDFs, DOCXs, etc.
            return None
        except Exception as e:
            logger.error(f"Error processing file content: {str(e)}")
            return None
