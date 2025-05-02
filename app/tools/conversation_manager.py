import os
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import aiofiles
import markdown
import pdfkit

from app.tools.base import BaseTool
from app.logger import logger


class ConversationManager(BaseTool):
    name: str = "conversation_manager"
    description: str = """
    Manage conversations by creating dedicated folders for each conversation or prompt.
    This tool helps organize conversations, save related materials, and generate final output documents.
    Use this tool to create new conversation folders, save materials to conversation folders,
    and generate final output documents (PDF or DOCX) from conversations.
    """
    base_folder: Optional[Path] = None
    conversations: Dict[str, Any] = {}
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "(required) The action to perform: 'create_folder', 'save_material', or 'generate_output'.",
                "enum": ["create_folder", "save_material", "generate_output"],
            },
            "conversation_id": {
                "type": "string",
                "description": "(required) The ID of the conversation to manage.",
            },
            "conversation_title": {
                "type": "string",
                "description": "(optional) The title of the conversation. Required for 'create_folder' action.",
            },
            "material_content": {
                "type": "string",
                "description": "(optional) The content of the material to save. Required for 'save_material' action.",
            },
            "material_name": {
                "type": "string",
                "description": "(optional) The name of the material file. Required for 'save_material' action.",
            },
            "output_format": {
                "type": "string",
                "description": "(optional) The format of the output document: 'pdf' or 'markdown'. Default is 'pdf'.",
                "enum": ["pdf", "markdown"],
                "default": "pdf",
            },
            "include_materials": {
                "type": "boolean",
                "description": "(optional) Whether to include materials in the output document. Default is true.",
                "default": True,
            },
        },
        "required": ["action", "conversation_id"],
    }

    def __init__(self):
        super().__init__()
        self.base_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations"))
        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.conversations = {}
        self._load_conversations()

    def _load_conversations(self):
        """Load existing conversations from the conversations directory"""
        try:
            for folder in self.base_folder.iterdir():
                if folder.is_dir():
                    conversation_id = folder.name
                    metadata_file = folder / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            self.conversations[conversation_id] = json.load(f)
        except Exception as e:
            logger.error(f"Error loading conversations: {str(e)}")

    def _get_conversation_folder(self, conversation_id: str) -> Path:
        """Get the folder path for a conversation"""
        return self.base_folder / conversation_id

    def _save_conversation_metadata(self, conversation_id: str, metadata: Dict[str, Any]):
        """Save conversation metadata to the conversation folder"""
        folder = self._get_conversation_folder(conversation_id)
        folder.mkdir(parents=True, exist_ok=True)
        metadata_file = folder / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    async def _create_folder(self, conversation_id: str, conversation_title: str) -> Dict[str, Any]:
        """Create a new folder for a conversation"""
        try:
            folder = self._get_conversation_folder(conversation_id)
            folder.mkdir(parents=True, exist_ok=True)
            
            # Create materials subfolder
            materials_folder = folder / "materials"
            materials_folder.mkdir(exist_ok=True)
            
            # Create metadata file
            metadata = {
                "id": conversation_id,
                "title": conversation_title,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "materials": []
            }
            
            self._save_conversation_metadata(conversation_id, metadata)
            self.conversations[conversation_id] = metadata
            
            return {
                "success": True,
                "message": f"Created folder for conversation: {conversation_title}",
                "folder_path": str(folder)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create conversation folder: {str(e)}"
            }

    async def _save_material(self, conversation_id: str, material_name: str, material_content: str) -> Dict[str, Any]:
        """Save material to a conversation folder"""
        try:
            if conversation_id not in self.conversations:
                return {
                    "success": False,
                    "error": f"Conversation {conversation_id} not found"
                }
            
            folder = self._get_conversation_folder(conversation_id)
            materials_folder = folder / "materials"
            materials_folder.mkdir(exist_ok=True)
            
            # Ensure the material has a proper extension
            if not any(material_name.endswith(ext) for ext in [".txt", ".md", ".py", ".html", ".json", ".csv"]):
                material_name = f"{material_name}.txt"
            
            material_path = materials_folder / material_name
            
            # Write the material to file
            async with aiofiles.open(material_path, "w", encoding="utf-8") as f:
                await f.write(material_content)
            
            # Update metadata
            metadata = self.conversations[conversation_id]
            material_info = {
                "name": material_name,
                "path": str(material_path),
                "added_at": datetime.now().isoformat()
            }
            
            if "materials" not in metadata:
                metadata["materials"] = []
                
            metadata["materials"].append(material_info)
            metadata["updated_at"] = datetime.now().isoformat()
            
            self._save_conversation_metadata(conversation_id, metadata)
            
            return {
                "success": True,
                "message": f"Saved material '{material_name}' to conversation folder",
                "material_path": str(material_path)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to save material: {str(e)}"
            }

    async def _generate_output(self, conversation_id: str, output_format: str = "pdf", include_materials: bool = True) -> Dict[str, Any]:
        """Generate a final output document for a conversation"""
        try:
            if conversation_id not in self.conversations:
                return {
                    "success": False,
                    "error": f"Conversation {conversation_id} not found"
                }
            
            metadata = self.conversations[conversation_id]
            folder = self._get_conversation_folder(conversation_id)
            
            # Get conversation messages
            messages_file = folder / "messages.json"
            messages = []
            if messages_file.exists():
                with open(messages_file, "r", encoding="utf-8") as f:
                    messages = json.load(f)
            
            # Generate markdown content
            md_content = f"# {metadata['title']}\n\n"
            md_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Add conversation messages
            md_content += "## Conversation\n\n"
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                
                if isinstance(timestamp, int):
                    timestamp = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                
                md_content += f"### {role.capitalize()} ({timestamp})\n\n{content}\n\n"
            
            # Add materials if requested
            if include_materials and "materials" in metadata and metadata["materials"]:
                md_content += "## Materials\n\n"
                
                for material in metadata["materials"]:
                    material_name = material.get("name", "")
                    material_path = material.get("path", "")
                    
                    if material_path and os.path.exists(material_path):
                        with open(material_path, "r", encoding="utf-8") as f:
                            material_content = f.read()
                        
                        md_content += f"### {material_name}\n\n"
                        md_content += f"```\n{material_content}\n```\n\n"
            
            # Save markdown file
            output_md_path = folder / f"{metadata['title']}_summary.md"
            async with aiofiles.open(output_md_path, "w", encoding="utf-8") as f:
                await f.write(md_content)
            
            # Convert to PDF if requested
            if output_format == "pdf":
                try:
                    output_pdf_path = folder / f"{metadata['title']}_summary.pdf"
                    html_content = markdown.markdown(md_content)
                    pdfkit.from_string(html_content, str(output_pdf_path))
                    
                    return {
                        "success": True,
                        "message": f"Generated PDF output for conversation: {metadata['title']}",
                        "output_path": str(output_pdf_path)
                    }
                except Exception as pdf_error:
                    logger.error(f"Error generating PDF: {str(pdf_error)}. Falling back to markdown.")
                    return {
                        "success": True,
                        "message": f"Generated Markdown output for conversation (PDF conversion failed): {metadata['title']}",
                        "output_path": str(output_md_path),
                        "warning": f"PDF conversion failed: {str(pdf_error)}"
                    }
            else:
                return {
                    "success": True,
                    "message": f"Generated Markdown output for conversation: {metadata['title']}",
                    "output_path": str(output_md_path)
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate output: {str(e)}"
            }

    async def execute(
        self,
        action: str,
        conversation_id: str,
        conversation_title: Optional[str] = None,
        material_content: Optional[str] = None,
        material_name: Optional[str] = None,
        output_format: str = "pdf",
        include_materials: bool = True,
    ) -> Dict[str, Any]:
        """Execute the conversation manager tool"""
        if action == "create_folder":
            if not conversation_title:
                return {"error": "conversation_title is required for create_folder action"}
            return await self._create_folder(conversation_id, conversation_title)
        
        elif action == "save_material":
            if not material_content or not material_name:
                return {"error": "material_content and material_name are required for save_material action"}
            return await self._save_material(conversation_id, material_name, material_content)
        
        elif action == "generate_output":
            return await self._generate_output(conversation_id, output_format, include_materials)
        
        else:
            return {"error": f"Unknown action: {action}"}