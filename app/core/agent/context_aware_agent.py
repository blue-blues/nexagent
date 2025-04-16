"""
Context-Aware Agent Module

This module provides an agent implementation that is aware of context.
It extends the base agent with context management capabilities.
"""

from typing import Any, Dict, List, Optional, Union
import json
from datetime import datetime

from app.core.context import (
    ContextEntry,
    ContextProtocol,
    VersionedContextProtocol,
    ContextManager,
    extract_context_for_llm,
    create_entry_from_message
)


class ContextAwareAgent:
    """
    An agent that is aware of context.
    This class can be used to extend any agent with context management capabilities.
    """
    
    def __init__(
        self,
        agent,
        context_type: str = "memory",
        context_path: Optional[str] = None,
        versioned: bool = True,
        max_context_entries: int = 1000,
        max_context_versions: int = 50,
        auto_save: bool = True
    ):
        """
        Initialize a context-aware agent.
        
        Args:
            agent: The agent to extend
            context_type: Type of context to use ('memory' or 'file')
            context_path: Path to store context (for file context)
            versioned: Whether to use versioned context
            max_context_entries: Maximum number of context entries
            max_context_versions: Maximum number of context versions
            auto_save: Whether to automatically save context
        """
        self.agent = agent
        self.versioned = versioned
        
        # Create context
        if versioned:
            if context_type == "file" and context_path:
                self.context = ContextManager.create_versioned_context(
                    context_type,
                    file_path=context_path,
                    max_entries=max_context_entries,
                    max_versions=max_context_versions,
                    auto_save=auto_save
                )
            else:
                self.context = ContextManager.create_versioned_context(
                    "memory",
                    max_entries=max_context_entries,
                    max_versions=max_context_versions
                )
        else:
            if context_type == "file" and context_path:
                self.context = ContextManager.create_context(
                    context_type,
                    file_path=context_path,
                    max_entries=max_context_entries,
                    auto_save=auto_save
                )
            else:
                self.context = ContextManager.create_context(
                    "memory",
                    max_entries=max_context_entries
                )
    
    def add_to_context(
        self,
        content: str,
        source: str,
        entry_type: str,
        importance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add an entry to the context.
        
        Args:
            content: The content of the entry
            source: The source of the entry
            entry_type: The type of entry
            importance: The importance of the entry
            metadata: Additional metadata
            
        Returns:
            The ID of the added entry
        """
        entry = ContextEntry(
            content=content,
            source=source,
            entry_type=entry_type,
            importance=importance,
            metadata=metadata
        )
        
        return self.context.add_entry(entry)
    
    def add_message_to_context(
        self,
        message: Dict[str, Any],
        source: str = "user",
        importance: float = 1.0
    ) -> str:
        """
        Add a message to the context.
        
        Args:
            message: The message to add
            source: The source of the message
            importance: The importance of the message
            
        Returns:
            The ID of the added entry
        """
        entry = create_entry_from_message(
            message=message,
            source=source,
            importance=importance
        )
        
        return self.context.add_entry(entry)
    
    def create_context_version(self, description: Optional[str] = None) -> Optional[str]:
        """
        Create a version of the current context.
        
        Args:
            description: Description of the version
            
        Returns:
            The ID of the created version, or None if versioning is not enabled
        """
        if not self.versioned:
            return None
        
        return self.context.create_version(description)
    
    def rollback_context(self, version_id: str) -> bool:
        """
        Roll back the context to a specific version.
        
        Args:
            version_id: The ID of the version to roll back to
            
        Returns:
            True if the rollback was successful, False otherwise
        """
        if not self.versioned:
            return False
        
        return self.context.rollback_to_version(version_id)
    
    def get_context_for_llm(
        self,
        max_tokens: Optional[int] = None,
        include_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
        include_sources: Optional[List[str]] = None,
        exclude_sources: Optional[List[str]] = None,
        min_importance: float = 0.0,
        format_template: Optional[str] = None
    ) -> str:
        """
        Get formatted context for use with a language model.
        
        Args:
            max_tokens: Maximum number of tokens to include
            include_types: Only include entries of these types
            exclude_types: Exclude entries of these types
            include_sources: Only include entries from these sources
            exclude_sources: Exclude entries from these sources
            min_importance: Only include entries with importance >= this value
            format_template: Template for formatting entries
            
        Returns:
            Formatted context string
        """
        return extract_context_for_llm(
            context=self.context,
            max_tokens=max_tokens,
            include_types=include_types,
            exclude_types=exclude_types,
            include_sources=include_sources,
            exclude_sources=exclude_sources,
            min_importance=min_importance,
            format_template=format_template
        )
    
    def clear_context(self) -> None:
        """Clear all entries from the context."""
        self.context.clear_context()
    
    def save_context(self, path: Optional[str] = None) -> bool:
        """
        Save the current context to a file.
        
        Args:
            path: The file path to save to (defaults to the context's path)
            
        Returns:
            True if the context was saved successfully, False otherwise
        """
        if hasattr(self.context, 'file_path') and not path:
            path = self.context.file_path
        
        if not path:
            return False
        
        return self.context.save_context(path)
    
    def process_message(self, message: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Process a message, adding it to context and passing it to the agent.
        
        Args:
            message: The message to process
            **kwargs: Additional arguments to pass to the agent
            
        Returns:
            The agent's response
        """
        # Add the message to context
        self.add_message_to_context(message)
        
        # Create a context version before processing
        if self.versioned:
            self.create_context_version(f"Before processing message: {message.get('content', '')[:50]}...")
        
        # Get context for the agent
        context_str = self.get_context_for_llm(
            max_tokens=2000,  # Adjust as needed
            exclude_types=["system"]  # Exclude system messages
        )
        
        # Add context to the agent's kwargs
        kwargs['context'] = context_str
        
        # Process the message with the agent
        response = self.agent.process_message(message, **kwargs)
        
        # Add the response to context
        response_message = {
            "content": response.get("content", ""),
            "role": "assistant",
            "type": "message",
            "timestamp": datetime.now().isoformat()
        }
        self.add_message_to_context(response_message, source="agent")
        
        # Create a context version after processing
        if self.versioned:
            self.create_context_version(f"After processing message: {message.get('content', '')[:50]}...")
        
        return response
