import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import aiofiles

from app.tool.base import BaseTool, ToolResult
from app.logger import logger


class OutputOrganizer(BaseTool):
    """
    Tool for organizing outputs generated during conversations.

    This tool ensures that for every conversation with Nexagent, a new folder is created
    to store related documents and generated outputs. It works in conjunction with the
    ConversationManager to maintain a consistent folder structure.
    """

    name: str = "output_organizer"
    description: str = """
    Organize outputs generated during conversations.
    This tool ensures that for every conversation, a new folder is created to store
    related documents and generated outputs.
    """

    base_folder: Optional[Path] = None
    active_conversation_id: Optional[str] = None
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "(required) The action to perform: 'set_active_conversation', 'save_output', 'list_outputs'.",
                "enum": ["set_active_conversation", "save_output", "list_outputs"],
            },
            "conversation_id": {
                "type": "string",
                "description": "(optional) The ID of the conversation. Required for 'set_active_conversation'.",
            },
            "output_content": {
                "type": "string",
                "description": "(optional) The content to save. Required for 'save_output'.",
            },
            "output_name": {
                "type": "string",
                "description": "(optional) The name of the output file. Required for 'save_output'.",
            },
            "output_type": {
                "type": "string",
                "description": "(optional) The type of output (e.g., 'code', 'document', 'image'). Default is 'document'.",
                "default": "document",
            },
        },
        "required": ["action"],
    }

    def __init__(self):
        super().__init__()
        self.base_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations"))
        self.base_folder.mkdir(parents=True, exist_ok=True)

    def _get_conversation_folder(self, conversation_id: str) -> Path:
        """Get the folder path for a conversation"""
        return self.base_folder / conversation_id

    def _get_outputs_folder(self, conversation_id: str) -> Path:
        """Get the outputs folder path for a conversation"""
        folder = self._get_conversation_folder(conversation_id)
        outputs_folder = folder / "outputs"
        outputs_folder.mkdir(parents=True, exist_ok=True)
        return outputs_folder

    def _ensure_conversation_exists(self, conversation_id: str) -> bool:
        """Ensure that a conversation folder exists"""
        folder = self._get_conversation_folder(conversation_id)
        if not folder.exists():
            # Create the folder if it doesn't exist
            folder.mkdir(parents=True, exist_ok=True)

            # Create outputs subfolder
            outputs_folder = folder / "outputs"
            outputs_folder.mkdir(exist_ok=True)

            # Create metadata file if it doesn't exist
            metadata_file = folder / "metadata.json"
            if not metadata_file.exists():
                metadata = {
                    "id": conversation_id,
                    "title": f"Conversation {conversation_id}",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "outputs": []
                }
                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)

            return True
        return True

    async def _set_active_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Set the active conversation for organizing outputs"""
        try:
            # Ensure the conversation folder exists
            if not self._ensure_conversation_exists(conversation_id):
                return {
                    "success": False,
                    "error": f"Failed to create or access conversation folder for {conversation_id}"
                }

            self.active_conversation_id = conversation_id

            return {
                "success": True,
                "message": f"Set active conversation to {conversation_id}",
                "folder_path": str(self._get_conversation_folder(conversation_id))
            }
        except Exception as e:
            logger.error(f"Error setting active conversation: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to set active conversation: {str(e)}"
            }

    async def _save_output(self, output_name: str, output_content: str, output_type: str = "document") -> Dict[str, Any]:
        """Save an output to the active conversation folder"""
        try:
            if not self.active_conversation_id:
                return {
                    "success": False,
                    "error": "No active conversation set. Use 'set_active_conversation' first."
                }

            # Get the outputs folder
            outputs_folder = self._get_outputs_folder(self.active_conversation_id)

            # Ensure the output has a proper extension
            if not any(output_name.endswith(ext) for ext in [".txt", ".md", ".py", ".html", ".json", ".csv", ".pdf"]):
                if output_type == "code":
                    output_name = f"{output_name}.py"
                else:
                    output_name = f"{output_name}.txt"

            # Create a unique filename to avoid overwriting
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            base_name, ext = os.path.splitext(output_name)
            unique_name = f"{base_name}_{timestamp}{ext}"

            output_path = outputs_folder / unique_name

            # Write the output to file
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(output_content)

            # Update metadata
            metadata_file = self._get_conversation_folder(self.active_conversation_id) / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                output_info = {
                    "name": unique_name,
                    "original_name": output_name,
                    "type": output_type,
                    "path": str(output_path),
                    "added_at": datetime.now().isoformat()
                }

                if "outputs" not in metadata:
                    metadata["outputs"] = []

                metadata["outputs"].append(output_info)
                metadata["updated_at"] = datetime.now().isoformat()

                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)

            return {
                "success": True,
                "message": f"Saved output '{unique_name}' to conversation folder",
                "output_path": str(output_path)
            }
        except Exception as e:
            logger.error(f"Error saving output: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save output: {str(e)}"
            }

    async def _list_outputs(self) -> Dict[str, Any]:
        """List all outputs in the active conversation folder"""
        try:
            if not self.active_conversation_id:
                return {
                    "success": False,
                    "error": "No active conversation set. Use 'set_active_conversation' first."
                }

            # Get the metadata file
            metadata_file = self._get_conversation_folder(self.active_conversation_id) / "metadata.json"
            if not metadata_file.exists():
                return {
                    "success": True,
                    "message": f"No outputs found for conversation {self.active_conversation_id}",
                    "outputs": []
                }

            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            outputs = metadata.get("outputs", [])

            return {
                "success": True,
                "message": f"Found {len(outputs)} outputs for conversation {self.active_conversation_id}",
                "outputs": outputs
            }
        except Exception as e:
            logger.error(f"Error listing outputs: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to list outputs: {str(e)}"
            }

    async def execute(
        self,
        action: str,
        conversation_id: Optional[str] = None,
        output_content: Optional[str] = None,
        output_name: Optional[str] = None,
        output_type: str = "document",
    ) -> ToolResult:
        """Execute the output organizer tool"""
        try:
            if action == "set_active_conversation":
                if not conversation_id:
                    return ToolResult(
                        output="Error: conversation_id is required for set_active_conversation action",
                        error="Missing required parameter: conversation_id"
                    )
                result = await self._set_active_conversation(conversation_id)
                return ToolResult(output=json.dumps(result, indent=2))

            elif action == "save_output":
                if not output_content or not output_name:
                    return ToolResult(
                        output="Error: output_content and output_name are required for save_output action",
                        error="Missing required parameters: output_name and/or output_content"
                    )
                result = await self._save_output(output_name, output_content, output_type)
                return ToolResult(output=json.dumps(result, indent=2))

            elif action == "list_outputs":
                result = await self._list_outputs()
                return ToolResult(output=json.dumps(result, indent=2))

            else:
                return ToolResult(
                    output=f"Error: Unrecognized action: {action}. Allowed actions are: set_active_conversation, save_output, list_outputs",
                    error=f"Unrecognized action: {action}"
                )
        except Exception as e:
            logger.error(f"Error executing output organizer: {str(e)}")
            return ToolResult(
                output=f"Error executing output organizer: {str(e)}",
                error=str(e)
            )
