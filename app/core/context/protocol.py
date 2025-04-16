"""
Context Protocol Module

This module defines the protocol interfaces for managing model context in Nexagent.
It provides a standardized way to store, retrieve, and manipulate context information
that is passed to language models during interactions.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json
import uuid


class ContextEntry:
    """
    Represents a single entry in the context, with metadata about when it was added
    and its importance/relevance.
    """
    
    def __init__(
        self,
        content: str,
        source: str,
        entry_type: str,
        timestamp: Optional[datetime] = None,
        importance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        entry_id: Optional[str] = None
    ):
        """
        Initialize a context entry.
        
        Args:
            content: The actual content of the entry
            source: Where this entry came from (user, agent, tool, etc.)
            entry_type: Type of entry (message, code, plan, etc.)
            timestamp: When this entry was created
            importance: How important this entry is (1.0 is normal, higher is more important)
            metadata: Additional information about this entry
            entry_id: Unique identifier for this entry
        """
        self.content = content
        self.source = source
        self.entry_type = entry_type
        self.timestamp = timestamp or datetime.now()
        self.importance = importance
        self.metadata = metadata or {}
        self.entry_id = entry_id or str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the entry to a dictionary for serialization."""
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "source": self.source,
            "entry_type": self.entry_type,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextEntry':
        """Create an entry from a dictionary."""
        timestamp = datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"]
        return cls(
            content=data["content"],
            source=data["source"],
            entry_type=data["entry_type"],
            timestamp=timestamp,
            importance=data["importance"],
            metadata=data["metadata"],
            entry_id=data["entry_id"]
        )
    
    def __str__(self) -> str:
        """String representation of the entry."""
        return f"{self.source} ({self.entry_type}): {self.content[:50]}..."


class ContextProtocol(ABC):
    """
    Abstract base class defining the protocol for context management.
    Implementations of this protocol handle how context is stored, retrieved,
    and manipulated during agent interactions.
    """
    
    @abstractmethod
    def add_entry(self, entry: ContextEntry) -> str:
        """
        Add a new entry to the context.
        
        Args:
            entry: The context entry to add
            
        Returns:
            The ID of the added entry
        """
        pass
    
    @abstractmethod
    def get_entry(self, entry_id: str) -> Optional[ContextEntry]:
        """
        Retrieve a specific entry by ID.
        
        Args:
            entry_id: The ID of the entry to retrieve
            
        Returns:
            The entry if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_entry(self, entry_id: str, updated_entry: ContextEntry) -> bool:
        """
        Update an existing entry.
        
        Args:
            entry_id: The ID of the entry to update
            updated_entry: The new entry data
            
        Returns:
            True if the entry was updated, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_entry(self, entry_id: str) -> bool:
        """
        Remove an entry from the context.
        
        Args:
            entry_id: The ID of the entry to remove
            
        Returns:
            True if the entry was removed, False otherwise
        """
        pass
    
    @abstractmethod
    def get_entries_by_type(self, entry_type: str) -> List[ContextEntry]:
        """
        Get all entries of a specific type.
        
        Args:
            entry_type: The type of entries to retrieve
            
        Returns:
            A list of matching entries
        """
        pass
    
    @abstractmethod
    def get_entries_by_source(self, source: str) -> List[ContextEntry]:
        """
        Get all entries from a specific source.
        
        Args:
            source: The source of entries to retrieve
            
        Returns:
            A list of matching entries
        """
        pass
    
    @abstractmethod
    def get_recent_entries(self, count: int = 10) -> List[ContextEntry]:
        """
        Get the most recent entries.
        
        Args:
            count: The number of entries to retrieve
            
        Returns:
            A list of the most recent entries
        """
        pass
    
    @abstractmethod
    def get_important_entries(self, threshold: float = 1.5) -> List[ContextEntry]:
        """
        Get entries above an importance threshold.
        
        Args:
            threshold: The importance threshold
            
        Returns:
            A list of entries with importance >= threshold
        """
        pass
    
    @abstractmethod
    def clear_context(self) -> None:
        """Clear all entries from the context."""
        pass
    
    @abstractmethod
    def save_context(self, path: str) -> bool:
        """
        Save the current context to a file.
        
        Args:
            path: The file path to save to
            
        Returns:
            True if the context was saved successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def load_context(self, path: str) -> bool:
        """
        Load context from a file.
        
        Args:
            path: The file path to load from
            
        Returns:
            True if the context was loaded successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_formatted_context(self, max_tokens: Optional[int] = None) -> str:
        """
        Get a formatted string representation of the context suitable for
        passing to a language model.
        
        Args:
            max_tokens: Optional maximum number of tokens to include
            
        Returns:
            A formatted string representation of the context
        """
        pass
    
    @abstractmethod
    def get_context_summary(self) -> str:
        """
        Get a summary of the current context.
        
        Returns:
            A summary of the context
        """
        pass


class ContextVersion:
    """
    Represents a version of the context at a specific point in time.
    Enables rollback and comparison of context states.
    """
    
    def __init__(
        self,
        entries: List[ContextEntry],
        version_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        description: Optional[str] = None
    ):
        """
        Initialize a context version.
        
        Args:
            entries: The context entries in this version
            version_id: Unique identifier for this version
            timestamp: When this version was created
            description: Description of this version
        """
        self.entries = entries
        self.version_id = version_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now()
        self.description = description or f"Version created at {self.timestamp.isoformat()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the version to a dictionary for serialization."""
        return {
            "version_id": self.version_id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "entries": [entry.to_dict() for entry in self.entries]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextVersion':
        """Create a version from a dictionary."""
        timestamp = datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"]
        entries = [ContextEntry.from_dict(entry_data) for entry_data in data["entries"]]
        return cls(
            entries=entries,
            version_id=data["version_id"],
            timestamp=timestamp,
            description=data["description"]
        )


class VersionedContextProtocol(ContextProtocol):
    """
    Extended context protocol that supports versioning.
    Allows for creating snapshots of context state and rolling back to previous versions.
    """
    
    @abstractmethod
    def create_version(self, description: Optional[str] = None) -> str:
        """
        Create a new version of the current context.
        
        Args:
            description: Optional description of this version
            
        Returns:
            The ID of the created version
        """
        pass
    
    @abstractmethod
    def get_version(self, version_id: str) -> Optional[ContextVersion]:
        """
        Retrieve a specific version by ID.
        
        Args:
            version_id: The ID of the version to retrieve
            
        Returns:
            The version if found, None otherwise
        """
        pass
    
    @abstractmethod
    def list_versions(self) -> List[Dict[str, Any]]:
        """
        List all available versions.
        
        Returns:
            A list of version metadata
        """
        pass
    
    @abstractmethod
    def rollback_to_version(self, version_id: str) -> bool:
        """
        Roll back the context to a specific version.
        
        Args:
            version_id: The ID of the version to roll back to
            
        Returns:
            True if the rollback was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def compare_versions(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        Compare two versions of the context.
        
        Args:
            version_id1: The ID of the first version
            version_id2: The ID of the second version
            
        Returns:
            A dictionary containing the differences between the versions
        """
        pass


class ContextManager:
    """
    Factory class for creating and managing context implementations.
    Provides utility methods for working with context.
    """
    
    @staticmethod
    def create_context(context_type: str, **kwargs) -> ContextProtocol:
        """
        Create a new context instance of the specified type.
        
        Args:
            context_type: The type of context to create
            **kwargs: Additional arguments to pass to the context constructor
            
        Returns:
            A new context instance
        """
        from app.core.context.memory import MemoryContext
        from app.core.context.file import FileContext
        
        if context_type == "memory":
            return MemoryContext(**kwargs)
        elif context_type == "file":
            return FileContext(**kwargs)
        else:
            raise ValueError(f"Unknown context type: {context_type}")
    
    @staticmethod
    def create_versioned_context(context_type: str, **kwargs) -> VersionedContextProtocol:
        """
        Create a new versioned context instance of the specified type.
        
        Args:
            context_type: The type of context to create
            **kwargs: Additional arguments to pass to the context constructor
            
        Returns:
            A new versioned context instance
        """
        from app.core.context.versioned_memory import VersionedMemoryContext
        from app.core.context.versioned_file import VersionedFileContext
        
        if context_type == "memory":
            return VersionedMemoryContext(**kwargs)
        elif context_type == "file":
            return VersionedFileContext(**kwargs)
        else:
            raise ValueError(f"Unknown context type: {context_type}")
