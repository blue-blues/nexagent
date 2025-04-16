"""
Memory-based Context Implementation

This module provides an in-memory implementation of the context protocol.
It stores all context entries in memory, making it fast but non-persistent.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import os

from app.core.context.protocol import ContextEntry, ContextProtocol


class MemoryContext(ContextProtocol):
    """
    In-memory implementation of the context protocol.
    Stores all context entries in memory for fast access.
    """
    
    def __init__(self, max_entries: int = 1000):
        """
        Initialize a memory context.
        
        Args:
            max_entries: Maximum number of entries to store
        """
        self.entries: Dict[str, ContextEntry] = {}
        self.max_entries = max_entries
    
    def add_entry(self, entry: ContextEntry) -> str:
        """
        Add a new entry to the context.
        
        Args:
            entry: The context entry to add
            
        Returns:
            The ID of the added entry
        """
        # If we've reached the maximum number of entries, remove the oldest one
        if len(self.entries) >= self.max_entries:
            oldest_entry_id = min(
                self.entries.keys(),
                key=lambda k: self.entries[k].timestamp
            )
            del self.entries[oldest_entry_id]
        
        self.entries[entry.entry_id] = entry
        return entry.entry_id
    
    def get_entry(self, entry_id: str) -> Optional[ContextEntry]:
        """
        Retrieve a specific entry by ID.
        
        Args:
            entry_id: The ID of the entry to retrieve
            
        Returns:
            The entry if found, None otherwise
        """
        return self.entries.get(entry_id)
    
    def update_entry(self, entry_id: str, updated_entry: ContextEntry) -> bool:
        """
        Update an existing entry.
        
        Args:
            entry_id: The ID of the entry to update
            updated_entry: The new entry data
            
        Returns:
            True if the entry was updated, False otherwise
        """
        if entry_id not in self.entries:
            return False
        
        self.entries[entry_id] = updated_entry
        return True
    
    def remove_entry(self, entry_id: str) -> bool:
        """
        Remove an entry from the context.
        
        Args:
            entry_id: The ID of the entry to remove
            
        Returns:
            True if the entry was removed, False otherwise
        """
        if entry_id not in self.entries:
            return False
        
        del self.entries[entry_id]
        return True
    
    def get_entries_by_type(self, entry_type: str) -> List[ContextEntry]:
        """
        Get all entries of a specific type.
        
        Args:
            entry_type: The type of entries to retrieve
            
        Returns:
            A list of matching entries
        """
        return [
            entry for entry in self.entries.values()
            if entry.entry_type == entry_type
        ]
    
    def get_entries_by_source(self, source: str) -> List[ContextEntry]:
        """
        Get all entries from a specific source.
        
        Args:
            source: The source of entries to retrieve
            
        Returns:
            A list of matching entries
        """
        return [
            entry for entry in self.entries.values()
            if entry.source == source
        ]
    
    def get_recent_entries(self, count: int = 10) -> List[ContextEntry]:
        """
        Get the most recent entries.
        
        Args:
            count: The number of entries to retrieve
            
        Returns:
            A list of the most recent entries
        """
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda entry: entry.timestamp,
            reverse=True
        )
        return sorted_entries[:count]
    
    def get_important_entries(self, threshold: float = 1.5) -> List[ContextEntry]:
        """
        Get entries above an importance threshold.
        
        Args:
            threshold: The importance threshold
            
        Returns:
            A list of entries with importance >= threshold
        """
        return [
            entry for entry in self.entries.values()
            if entry.importance >= threshold
        ]
    
    def clear_context(self) -> None:
        """Clear all entries from the context."""
        self.entries.clear()
    
    def save_context(self, path: str) -> bool:
        """
        Save the current context to a file.
        
        Args:
            path: The file path to save to
            
        Returns:
            True if the context was saved successfully, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(
                    {
                        "entries": {
                            entry_id: entry.to_dict()
                            for entry_id, entry in self.entries.items()
                        },
                        "max_entries": self.max_entries
                    },
                    f,
                    indent=2
                )
            return True
        except Exception as e:
            print(f"Error saving context: {e}")
            return False
    
    def load_context(self, path: str) -> bool:
        """
        Load context from a file.
        
        Args:
            path: The file path to load from
            
        Returns:
            True if the context was loaded successfully, False otherwise
        """
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.max_entries = data.get("max_entries", self.max_entries)
            self.entries = {
                entry_id: ContextEntry.from_dict(entry_data)
                for entry_id, entry_data in data.get("entries", {}).items()
            }
            return True
        except Exception as e:
            print(f"Error loading context: {e}")
            return False
    
    def get_formatted_context(self, max_tokens: Optional[int] = None) -> str:
        """
        Get a formatted string representation of the context suitable for
        passing to a language model.
        
        Args:
            max_tokens: Optional maximum number of tokens to include
            
        Returns:
            A formatted string representation of the context
        """
        # Sort entries by timestamp
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda entry: entry.timestamp
        )
        
        # Format each entry
        formatted_entries = []
        for entry in sorted_entries:
            formatted_entry = f"[{entry.source}] ({entry.entry_type}): {entry.content}"
            formatted_entries.append(formatted_entry)
        
        # Join entries with newlines
        formatted_context = "\n\n".join(formatted_entries)
        
        # If max_tokens is specified, truncate the context
        if max_tokens is not None:
            # This is a very rough approximation
            # In a real implementation, you would use a tokenizer
            tokens = formatted_context.split()
            if len(tokens) > max_tokens:
                tokens = tokens[-max_tokens:]
                formatted_context = " ".join(tokens)
        
        return formatted_context
    
    def get_context_summary(self) -> str:
        """
        Get a summary of the current context.
        
        Returns:
            A summary of the context
        """
        entry_types = {}
        sources = {}
        
        for entry in self.entries.values():
            entry_types[entry.entry_type] = entry_types.get(entry.entry_type, 0) + 1
            sources[entry.source] = sources.get(entry.source, 0) + 1
        
        summary = [
            f"Context Summary:",
            f"Total Entries: {len(self.entries)}",
            f"Entry Types: {entry_types}",
            f"Sources: {sources}",
            f"Oldest Entry: {min(self.entries.values(), key=lambda e: e.timestamp).timestamp.isoformat() if self.entries else 'None'}",
            f"Newest Entry: {max(self.entries.values(), key=lambda e: e.timestamp).timestamp.isoformat() if self.entries else 'None'}"
        ]
        
        return "\n".join(summary)
