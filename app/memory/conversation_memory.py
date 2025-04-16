"""
Conversation Memory Module

This module provides functionality for storing and retrieving conversation history
across multiple sessions, enabling short-term memory between conversations.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from app.logger import logger
from app.schema import Message


class ConversationEntry(BaseModel):
    """Represents a single conversation entry in the memory store."""
    
    id: str = Field(..., description="Unique identifier for the entry")
    timestamp: float = Field(default_factory=time.time, description="When the entry was created")
    user_prompt: str = Field(..., description="The user's input prompt")
    bot_response: str = Field(..., description="The bot's response")
    conversation_id: str = Field(..., description="ID of the conversation this entry belongs to")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationSummary(BaseModel):
    """Represents a summary of a conversation."""
    
    conversation_id: str = Field(..., description="ID of the conversation")
    last_updated: float = Field(default_factory=time.time, description="When the conversation was last updated")
    topic: Optional[str] = Field(None, description="The main topic of the conversation")
    summary: Optional[str] = Field(None, description="A summary of the conversation")
    entry_count: int = Field(default=0, description="Number of entries in the conversation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationMemory(BaseModel):
    """
    Manages conversation memory across multiple sessions.
    
    This class provides functionality for storing and retrieving conversation history,
    enabling short-term memory between conversations.
    """
    
    entries: Dict[str, ConversationEntry] = Field(default_factory=dict, description="Conversation entries by ID")
    summaries: Dict[str, ConversationSummary] = Field(default_factory=dict, description="Conversation summaries by conversation ID")
    max_entries_per_conversation: int = Field(default=20, description="Maximum number of entries to store per conversation")
    max_conversations: int = Field(default=10, description="Maximum number of conversations to store")
    storage_path: Optional[str] = Field(None, description="Path to store conversation memory")
    
    def __init__(self, **data):
        """Initialize the conversation memory."""
        super().__init__(**data)
        
        # Set default storage path if not provided
        if not self.storage_path:
            self.storage_path = os.path.join(os.path.expanduser("~"), ".nexagent", "conversation_memory")
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load existing memory if available
        self._load_memory()
    
    def _load_memory(self) -> None:
        """Load memory from disk."""
        try:
            # Load summaries
            summaries_path = os.path.join(self.storage_path, "summaries.json")
            if os.path.exists(summaries_path):
                with open(summaries_path, "r") as f:
                    summaries_data = json.load(f)
                    for summary_data in summaries_data:
                        summary = ConversationSummary(**summary_data)
                        self.summaries[summary.conversation_id] = summary
            
            # Load entries for each conversation
            for conversation_id in self.summaries:
                entries_path = os.path.join(self.storage_path, f"{conversation_id}_entries.json")
                if os.path.exists(entries_path):
                    with open(entries_path, "r") as f:
                        entries_data = json.load(f)
                        for entry_data in entries_data:
                            entry = ConversationEntry(**entry_data)
                            self.entries[entry.id] = entry
            
            logger.info(f"Loaded {len(self.summaries)} conversations with {len(self.entries)} entries from memory")
        except Exception as e:
            logger.error(f"Error loading conversation memory: {str(e)}")
    
    def _save_memory(self) -> None:
        """Save memory to disk."""
        try:
            # Save summaries
            summaries_path = os.path.join(self.storage_path, "summaries.json")
            with open(summaries_path, "w") as f:
                summaries_data = [summary.model_dump() for summary in self.summaries.values()]
                json.dump(summaries_data, f, indent=2)
            
            # Save entries for each conversation
            for conversation_id in self.summaries:
                # Get entries for this conversation
                conversation_entries = [
                    entry for entry in self.entries.values()
                    if entry.conversation_id == conversation_id
                ]
                
                # Save entries
                entries_path = os.path.join(self.storage_path, f"{conversation_id}_entries.json")
                with open(entries_path, "w") as f:
                    entries_data = [entry.model_dump() for entry in conversation_entries]
                    json.dump(entries_data, f, indent=2)
            
            logger.info(f"Saved {len(self.summaries)} conversations with {len(self.entries)} entries to memory")
        except Exception as e:
            logger.error(f"Error saving conversation memory: {str(e)}")
    
    def add_entry(self, user_prompt: str, bot_response: str, conversation_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a new entry to the conversation memory.
        
        Args:
            user_prompt: The user's input prompt
            bot_response: The bot's response
            conversation_id: ID of the conversation this entry belongs to
            metadata: Additional metadata
            
        Returns:
            The ID of the added entry
        """
        # Generate entry ID
        entry_id = f"entry_{int(time.time())}_{len(self.entries)}"
        
        # Create entry
        entry = ConversationEntry(
            id=entry_id,
            timestamp=time.time(),
            user_prompt=user_prompt,
            bot_response=bot_response,
            conversation_id=conversation_id,
            metadata=metadata or {}
        )
        
        # Add entry to memory
        self.entries[entry_id] = entry
        
        # Update or create conversation summary
        if conversation_id in self.summaries:
            summary = self.summaries[conversation_id]
            summary.last_updated = time.time()
            summary.entry_count += 1
        else:
            # Create new summary
            summary = ConversationSummary(
                conversation_id=conversation_id,
                last_updated=time.time(),
                entry_count=1
            )
            self.summaries[conversation_id] = summary
        
        # Prune old entries for this conversation if needed
        self._prune_conversation_entries(conversation_id)
        
        # Prune old conversations if needed
        self._prune_conversations()
        
        # Save memory to disk
        self._save_memory()
        
        return entry_id
    
    def get_conversation_history(self, conversation_id: str, max_entries: Optional[int] = None) -> List[ConversationEntry]:
        """
        Get the history of a conversation.
        
        Args:
            conversation_id: ID of the conversation
            max_entries: Maximum number of entries to return
            
        Returns:
            A list of conversation entries
        """
        # Get entries for this conversation
        conversation_entries = [
            entry for entry in self.entries.values()
            if entry.conversation_id == conversation_id
        ]
        
        # Sort by timestamp
        conversation_entries.sort(key=lambda entry: entry.timestamp)
        
        # Limit number of entries if specified
        if max_entries is not None:
            conversation_entries = conversation_entries[-max_entries:]
        
        return conversation_entries
    
    def get_recent_conversations(self, max_conversations: Optional[int] = None) -> List[ConversationSummary]:
        """
        Get the most recent conversations.
        
        Args:
            max_conversations: Maximum number of conversations to return
            
        Returns:
            A list of conversation summaries
        """
        # Sort summaries by last_updated
        sorted_summaries = sorted(
            self.summaries.values(),
            key=lambda summary: summary.last_updated,
            reverse=True
        )
        
        # Limit number of conversations if specified
        if max_conversations is not None:
            sorted_summaries = sorted_summaries[:max_conversations]
        
        return sorted_summaries
    
    def get_all_entries(self) -> List[ConversationEntry]:
        """
        Get all conversation entries.
        
        Returns:
            A list of all conversation entries
        """
        return list(self.entries.values())
    
    def get_conversation_summary(self, conversation_id: str) -> Optional[ConversationSummary]:
        """
        Get the summary of a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            The conversation summary if found, None otherwise
        """
        return self.summaries.get(conversation_id)
    
    def update_conversation_summary(self, conversation_id: str, topic: Optional[str] = None, summary: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the summary of a conversation.
        
        Args:
            conversation_id: ID of the conversation
            topic: The main topic of the conversation
            summary: A summary of the conversation
            metadata: Additional metadata
        """
        if conversation_id not in self.summaries:
            logger.warning(f"Conversation {conversation_id} not found in memory")
            return
        
        # Update summary
        if topic is not None:
            self.summaries[conversation_id].topic = topic
        
        if summary is not None:
            self.summaries[conversation_id].summary = summary
        
        if metadata is not None:
            self.summaries[conversation_id].metadata.update(metadata)
        
        # Update last_updated
        self.summaries[conversation_id].last_updated = time.time()
        
        # Save memory to disk
        self._save_memory()
    
    def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear all entries for a conversation.
        
        Args:
            conversation_id: ID of the conversation
        """
        # Remove entries for this conversation
        self.entries = {
            entry_id: entry for entry_id, entry in self.entries.items()
            if entry.conversation_id != conversation_id
        }
        
        # Remove summary
        if conversation_id in self.summaries:
            del self.summaries[conversation_id]
        
        # Save memory to disk
        self._save_memory()
    
    def clear_all(self) -> None:
        """Clear all conversation memory."""
        self.entries.clear()
        self.summaries.clear()
        
        # Save memory to disk
        self._save_memory()
    
    def _prune_conversation_entries(self, conversation_id: str) -> None:
        """
        Prune old entries for a conversation if needed.
        
        Args:
            conversation_id: ID of the conversation
        """
        # Get entries for this conversation
        conversation_entries = [
            entry for entry in self.entries.values()
            if entry.conversation_id == conversation_id
        ]
        
        # If we have too many entries, remove the oldest ones
        if len(conversation_entries) > self.max_entries_per_conversation:
            # Sort by timestamp
            conversation_entries.sort(key=lambda entry: entry.timestamp)
            
            # Remove oldest entries
            entries_to_remove = conversation_entries[:-self.max_entries_per_conversation]
            for entry in entries_to_remove:
                if entry.id in self.entries:
                    del self.entries[entry.id]
    
    def _prune_conversations(self) -> None:
        """Prune old conversations if needed."""
        # If we have too many conversations, remove the oldest ones
        if len(self.summaries) > self.max_conversations:
            # Sort summaries by last_updated
            sorted_summaries = sorted(
                self.summaries.values(),
                key=lambda summary: summary.last_updated
            )
            
            # Remove oldest conversations
            conversations_to_remove = sorted_summaries[:-self.max_conversations]
            for summary in conversations_to_remove:
                # Remove entries for this conversation
                self.entries = {
                    entry_id: entry for entry_id, entry in self.entries.items()
                    if entry.conversation_id != summary.conversation_id
                }
                
                # Remove summary
                if summary.conversation_id in self.summaries:
                    del self.summaries[summary.conversation_id]
    
    def format_recent_history(self, conversation_id: str, max_entries: int = 5) -> str:
        """
        Format recent conversation history for inclusion in prompts.
        
        Args:
            conversation_id: ID of the conversation
            max_entries: Maximum number of entries to include
            
        Returns:
            Formatted conversation history
        """
        # Get recent entries
        entries = self.get_conversation_history(conversation_id, max_entries)
        
        if not entries:
            return "No previous conversation history."
        
        # Format entries
        formatted_entries = []
        for entry in entries:
            formatted_entries.append(f"User: {entry.user_prompt}")
            formatted_entries.append(f"Assistant: {entry.bot_response}")
        
        return "\n\n".join(formatted_entries)
    
    def get_messages_for_llm(self, conversation_id: str, max_entries: int = 5) -> List[Message]:
        """
        Get conversation history as a list of messages for the LLM.
        
        Args:
            conversation_id: ID of the conversation
            max_entries: Maximum number of entries to include
            
        Returns:
            List of messages
        """
        # Get recent entries
        entries = self.get_conversation_history(conversation_id, max_entries)
        
        if not entries:
            return []
        
        # Convert entries to messages
        messages = []
        for entry in entries:
            messages.append(Message.user_message(entry.user_prompt))
            messages.append(Message.assistant_message(entry.bot_response))
        
        return messages


# Global conversation memory instance
conversation_memory = ConversationMemory()
