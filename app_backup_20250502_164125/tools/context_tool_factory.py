"""
Context Tool Factory Module

This module provides a factory for creating context-aware tools.
It allows for easy creation of tools that can read from and write to context.
"""

from typing import Any, Dict, List, Optional, Union, Type
import json
from datetime import datetime

from app.core.context import (
    ContextEntry,
    ContextProtocol,
    VersionedContextProtocol,
    ContextManager
)
from app.tools.context_aware_tool import ContextAwareTool


class ContextToolFactory:
    """
    A factory for creating context-aware tools.
    """
    
    @staticmethod
    def create_context_tool(
        tool,
        context: Optional[ContextProtocol] = None,
        auto_add_results: bool = True,
        result_importance: float = 1.0
    ) -> ContextAwareTool:
        """
        Create a context-aware tool.
        
        Args:
            tool: The tool to extend
            context: The context to use
            auto_add_results: Whether to automatically add results to context
            result_importance: The importance to assign to results
            
        Returns:
            A context-aware tool
        """
        return ContextAwareTool(
            tool=tool,
            context=context,
            auto_add_results=auto_add_results,
            result_importance=result_importance
        )
    
    @staticmethod
    def create_context_tools(
        tools: List[Any],
        context: Optional[ContextProtocol] = None,
        auto_add_results: bool = True,
        result_importance: float = 1.0
    ) -> List[ContextAwareTool]:
        """
        Create multiple context-aware tools.
        
        Args:
            tools: The tools to extend
            context: The context to use
            auto_add_results: Whether to automatically add results to context
            result_importance: The importance to assign to results
            
        Returns:
            A list of context-aware tools
        """
        return [
            ContextToolFactory.create_context_tool(
                tool=tool,
                context=context,
                auto_add_results=auto_add_results,
                result_importance=result_importance
            )
            for tool in tools
        ]
    
    @staticmethod
    def create_context_query_tool(context: ContextProtocol) -> 'ContextQueryTool':
        """
        Create a tool for querying context.
        
        Args:
            context: The context to query
            
        Returns:
            A context query tool
        """
        return ContextQueryTool(context=context)
    
    @staticmethod
    def create_context_management_tool(context: ContextProtocol) -> 'ContextManagementTool':
        """
        Create a tool for managing context.
        
        Args:
            context: The context to manage
            
        Returns:
            A context management tool
        """
        return ContextManagementTool(context=context)


class ContextQueryTool:
    """
    A tool for querying context.
    """
    
    def __init__(self, context: ContextProtocol):
        """
        Initialize a context query tool.
        
        Args:
            context: The context to query
        """
        self.context = context
        self.name = "context_query"
    
    def get_recent_entries(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent entries.
        
        Args:
            count: The number of entries to retrieve
            
        Returns:
            A list of the most recent entries
        """
        entries = self.context.get_recent_entries(count=count)
        
        return [
            {
                "entry_id": entry.entry_id,
                "content": entry.content,
                "source": entry.source,
                "entry_type": entry.entry_type,
                "timestamp": entry.timestamp.isoformat(),
                "importance": entry.importance,
                "metadata": entry.metadata
            }
            for entry in entries
        ]
    
    def get_entries_by_type(self, entry_type: str) -> List[Dict[str, Any]]:
        """
        Get all entries of a specific type.
        
        Args:
            entry_type: The type of entries to retrieve
            
        Returns:
            A list of matching entries
        """
        entries = self.context.get_entries_by_type(entry_type=entry_type)
        
        return [
            {
                "entry_id": entry.entry_id,
                "content": entry.content,
                "source": entry.source,
                "entry_type": entry.entry_type,
                "timestamp": entry.timestamp.isoformat(),
                "importance": entry.importance,
                "metadata": entry.metadata
            }
            for entry in entries
        ]
    
    def get_entries_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Get all entries from a specific source.
        
        Args:
            source: The source of entries to retrieve
            
        Returns:
            A list of matching entries
        """
        entries = self.context.get_entries_by_source(source=source)
        
        return [
            {
                "entry_id": entry.entry_id,
                "content": entry.content,
                "source": entry.source,
                "entry_type": entry.entry_type,
                "timestamp": entry.timestamp.isoformat(),
                "importance": entry.importance,
                "metadata": entry.metadata
            }
            for entry in entries
        ]
    
    def get_important_entries(self, threshold: float = 1.5) -> List[Dict[str, Any]]:
        """
        Get entries above an importance threshold.
        
        Args:
            threshold: The importance threshold
            
        Returns:
            A list of entries with importance >= threshold
        """
        entries = self.context.get_important_entries(threshold=threshold)
        
        return [
            {
                "entry_id": entry.entry_id,
                "content": entry.content,
                "source": entry.source,
                "entry_type": entry.entry_type,
                "timestamp": entry.timestamp.isoformat(),
                "importance": entry.importance,
                "metadata": entry.metadata
            }
            for entry in entries
        ]
    
    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific entry by ID.
        
        Args:
            entry_id: The ID of the entry to retrieve
            
        Returns:
            The entry if found, None otherwise
        """
        entry = self.context.get_entry(entry_id=entry_id)
        
        if not entry:
            return None
        
        return {
            "entry_id": entry.entry_id,
            "content": entry.content,
            "source": entry.source,
            "entry_type": entry.entry_type,
            "timestamp": entry.timestamp.isoformat(),
            "importance": entry.importance,
            "metadata": entry.metadata
        }
    
    def get_context_summary(self) -> str:
        """
        Get a summary of the current context.
        
        Returns:
            A summary of the context
        """
        return self.context.get_context_summary()


class ContextManagementTool:
    """
    A tool for managing context.
    """
    
    def __init__(self, context: ContextProtocol):
        """
        Initialize a context management tool.
        
        Args:
            context: The context to manage
        """
        self.context = context
        self.name = "context_management"
    
    def add_entry(
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
            metadata=metadata or {}
        )
        
        return self.context.add_entry(entry)
    
    def update_entry(
        self,
        entry_id: str,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing entry.
        
        Args:
            entry_id: The ID of the entry to update
            content: The new content
            importance: The new importance
            metadata: The new metadata
            
        Returns:
            True if the entry was updated, False otherwise
        """
        entry = self.context.get_entry(entry_id=entry_id)
        
        if not entry:
            return False
        
        if content is not None:
            entry.content = content
        
        if importance is not None:
            entry.importance = importance
        
        if metadata is not None:
            entry.metadata = metadata
        
        return self.context.update_entry(entry_id=entry_id, updated_entry=entry)
    
    def remove_entry(self, entry_id: str) -> bool:
        """
        Remove an entry from the context.
        
        Args:
            entry_id: The ID of the entry to remove
            
        Returns:
            True if the entry was removed, False otherwise
        """
        return self.context.remove_entry(entry_id=entry_id)
    
    def clear_context(self) -> None:
        """Clear all entries from the context."""
        self.context.clear_context()
    
    def create_version(self, description: Optional[str] = None) -> Optional[str]:
        """
        Create a version of the current context.
        
        Args:
            description: Description of the version
            
        Returns:
            The ID of the created version, or None if versioning is not enabled
        """
        if not isinstance(self.context, VersionedContextProtocol):
            return None
        
        return self.context.create_version(description=description)
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """
        List all available versions.
        
        Returns:
            A list of version metadata
        """
        if not isinstance(self.context, VersionedContextProtocol):
            return []
        
        return self.context.list_versions()
    
    def rollback_to_version(self, version_id: str) -> bool:
        """
        Roll back the context to a specific version.
        
        Args:
            version_id: The ID of the version to roll back to
            
        Returns:
            True if the rollback was successful, False otherwise
        """
        if not isinstance(self.context, VersionedContextProtocol):
            return False
        
        return self.context.rollback_to_version(version_id=version_id)
    
    def save_context(self, path: str) -> bool:
        """
        Save the current context to a file.
        
        Args:
            path: The file path to save to
            
        Returns:
            True if the context was saved successfully, False otherwise
        """
        return self.context.save_context(path=path)
    
    def load_context(self, path: str) -> bool:
        """
        Load context from a file.
        
        Args:
            path: The file path to load from
            
        Returns:
            True if the context was loaded successfully, False otherwise
        """
        return self.context.load_context(path=path)
