import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.logger import logger
from app.tool.conversation_manager import ConversationManager


class ConversationHandler:
    """Handler for managing conversations with automatic folder organization.
    
    This class integrates with the API server to automatically organize conversations
    into dedicated folders, save materials, and generate final output documents.
    """
    
    def __init__(self):
        self.conversation_manager = ConversationManager()
        self.base_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations"))
        self.base_folder.mkdir(parents=True, exist_ok=True)
    
    async def handle_new_conversation(self, conversation_id: str, title: str) -> Dict[str, Any]:
        """Handle a new conversation by creating a dedicated folder.
        
        Args:
            conversation_id: The ID of the conversation
            title: The title of the conversation
            
        Returns:
            Dict containing the result of the operation
        """
        return await self.conversation_manager.execute(
            action="create_folder",
            conversation_id=conversation_id,
            conversation_title=title
        )
    
    async def save_conversation_messages(self, conversation_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Save conversation messages to the conversation folder.
        
        Args:
            conversation_id: The ID of the conversation
            messages: List of conversation messages
            
        Returns:
            Dict containing the result of the operation
        """
        try:
            folder = self.conversation_manager._get_conversation_folder(conversation_id)
            messages_file = folder / "messages.json"
            
            # Save messages to file
            with open(messages_file, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=2)
            
            # Update metadata
            if conversation_id in self.conversation_manager.conversations:
                metadata = self.conversation_manager.conversations[conversation_id]
                metadata["updated_at"] = datetime.now().isoformat()
                metadata["message_count"] = len(messages)
                self.conversation_manager._save_conversation_metadata(conversation_id, metadata)
            
            return {
                "success": True,
                "message": f"Saved {len(messages)} messages to conversation folder"
            }
        except Exception as e:
            logger.error(f"Error saving conversation messages: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save conversation messages: {str(e)}"
            }
    
    async def save_material(self, conversation_id: str, material_name: str, material_content: str) -> Dict[str, Any]:
        """Save material to the conversation folder.
        
        Args:
            conversation_id: The ID of the conversation
            material_name: The name of the material file
            material_content: The content of the material
            
        Returns:
            Dict containing the result of the operation
        """
        return await self.conversation_manager.execute(
            action="save_material",
            conversation_id=conversation_id,
            material_name=material_name,
            material_content=material_content
        )
    
    async def generate_output(self, conversation_id: str, output_format: str = "pdf") -> Dict[str, Any]:
        """Generate a final output document for the conversation.
        
        Args:
            conversation_id: The ID of the conversation
            output_format: The format of the output document ('pdf' or 'markdown')
            
        Returns:
            Dict containing the result of the operation
        """
        return await self.conversation_manager.execute(
            action="generate_output",
            conversation_id=conversation_id,
            output_format=output_format,
            include_materials=True
        )
    
    async def handle_url_content(self, conversation_id: str, url: str, content: str) -> Dict[str, Any]:
        """Save content from a URL as a material in the conversation folder.
        
        Args:
            conversation_id: The ID of the conversation
            url: The URL where the content was retrieved from
            content: The content retrieved from the URL
            
        Returns:
            Dict containing the result of the operation
        """
        # Extract filename from URL
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        path = parsed_url.path
        filename = os.path.basename(path) if path else "webpage"
        
        # Add domain to filename for clarity
        domain = parsed_url.netloc
        if domain and not filename.startswith(domain):
            filename = f"{domain}_{filename}"
        
        # Add extension if needed
        if not any(filename.endswith(ext) for ext in [".html", ".txt", ".json", ".md"]):
            filename = f"{filename}.html"
        
        return await self.save_material(conversation_id, filename, content)
    
    async def handle_file_download(self, conversation_id: str, url: str, file_path: str) -> Dict[str, Any]:
        """Handle a file download by copying it to the conversation folder.
        
        Args:
            conversation_id: The ID of the conversation
            url: The URL where the file was downloaded from
            file_path: The path to the downloaded file
            
        Returns:
            Dict containing the result of the operation
        """
        try:
            # Get the conversation folder
            folder = self.conversation_manager._get_conversation_folder(conversation_id)
            materials_folder = folder / "materials"
            materials_folder.mkdir(exist_ok=True)
            
            # Extract filename from file_path
            filename = os.path.basename(file_path)
            
            # Copy the file to the materials folder
            import shutil
            destination = materials_folder / filename
            shutil.copy2(file_path, destination)
            
            # Update metadata
            if conversation_id in self.conversation_manager.conversations:
                metadata = self.conversation_manager.conversations[conversation_id]
                
                if "materials" not in metadata:
                    metadata["materials"] = []
                
                material_info = {
                    "name": filename,
                    "path": str(destination),
                    "source_url": url,
                    "added_at": datetime.now().isoformat()
                }
                
                metadata["materials"].append(material_info)
                metadata["updated_at"] = datetime.now().isoformat()
                
                self.conversation_manager._save_conversation_metadata(conversation_id, metadata)
            
            return {
                "success": True,
                "message": f"Copied file '{filename}' to conversation materials folder",
                "material_path": str(destination)
            }
        except Exception as e:
            logger.error(f"Error handling file download: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to handle file download: {str(e)}"
            }