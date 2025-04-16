"""
Context Utilities Module

This module provides utility functions for working with context.
"""

from typing import Any, Dict, List, Optional, Union
import json
import os
from datetime import datetime

from app.core.context.protocol import ContextEntry, ContextProtocol, VersionedContextProtocol


def extract_context_for_llm(
    context: ContextProtocol,
    max_tokens: Optional[int] = None,
    include_types: Optional[List[str]] = None,
    exclude_types: Optional[List[str]] = None,
    include_sources: Optional[List[str]] = None,
    exclude_sources: Optional[List[str]] = None,
    min_importance: float = 0.0,
    format_template: Optional[str] = None
) -> str:
    """
    Extract and format context for use with a language model.
    
    Args:
        context: The context to extract from
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
    # Get all entries
    entries = list(context.entries.values())
    
    # Filter by type
    if include_types:
        entries = [entry for entry in entries if entry.entry_type in include_types]
    if exclude_types:
        entries = [entry for entry in entries if entry.entry_type not in exclude_types]
    
    # Filter by source
    if include_sources:
        entries = [entry for entry in entries if entry.source in include_sources]
    if exclude_sources:
        entries = [entry for entry in entries if entry.source not in exclude_sources]
    
    # Filter by importance
    entries = [entry for entry in entries if entry.importance >= min_importance]
    
    # Sort by timestamp
    entries = sorted(entries, key=lambda entry: entry.timestamp)
    
    # Format entries
    if format_template:
        formatted_entries = [
            format_template.format(
                content=entry.content,
                source=entry.source,
                entry_type=entry.entry_type,
                timestamp=entry.timestamp.isoformat(),
                importance=entry.importance,
                **entry.metadata
            )
            for entry in entries
        ]
    else:
        formatted_entries = [
            f"[{entry.source}] ({entry.entry_type}): {entry.content}"
            for entry in entries
        ]
    
    # Join entries
    formatted_context = "\n\n".join(formatted_entries)
    
    # Truncate if necessary
    if max_tokens is not None:
        # This is a very rough approximation
        # In a real implementation, you would use a tokenizer
        tokens = formatted_context.split()
        if len(tokens) > max_tokens:
            tokens = tokens[-max_tokens:]
            formatted_context = " ".join(tokens)
    
    return formatted_context


def merge_contexts(
    contexts: List[ContextProtocol],
    output_context: ContextProtocol,
    conflict_resolution: str = "latest"
) -> ContextProtocol:
    """
    Merge multiple contexts into a single context.
    
    Args:
        contexts: List of contexts to merge
        output_context: Context to merge into
        conflict_resolution: How to resolve conflicts ('latest', 'oldest', 'important')
        
    Returns:
        Merged context
    """
    # Collect all entries
    all_entries: Dict[str, List[ContextEntry]] = {}
    
    for context in contexts:
        for entry_id, entry in context.entries.items():
            if entry_id not in all_entries:
                all_entries[entry_id] = []
            all_entries[entry_id].append(entry)
    
    # Resolve conflicts
    for entry_id, entries in all_entries.items():
        if len(entries) == 1:
            # No conflict
            output_context.add_entry(entries[0])
        else:
            # Conflict
            if conflict_resolution == "latest":
                selected_entry = max(entries, key=lambda e: e.timestamp)
            elif conflict_resolution == "oldest":
                selected_entry = min(entries, key=lambda e: e.timestamp)
            elif conflict_resolution == "important":
                selected_entry = max(entries, key=lambda e: e.importance)
            else:
                # Default to latest
                selected_entry = max(entries, key=lambda e: e.timestamp)
            
            output_context.add_entry(selected_entry)
    
    return output_context


def create_context_snapshot(
    context: ContextProtocol,
    path: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Create a snapshot of the current context.
    
    Args:
        context: The context to snapshot
        path: Path to save the snapshot to
        metadata: Additional metadata to include
        
    Returns:
        True if the snapshot was created successfully, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Create snapshot data
        snapshot_data = {
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "context": {
                "entries": {
                    entry_id: entry.to_dict()
                    for entry_id, entry in context.entries.items()
                }
            }
        }
        
        # Add version information if available
        if isinstance(context, VersionedContextProtocol):
            snapshot_data["context"]["versions"] = {
                version_id: version.to_dict()
                for version_id, version in context.versions.items()
            }
        
        # Save snapshot
        with open(path, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error creating context snapshot: {e}")
        return False


def filter_context_by_date(
    context: ContextProtocol,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[ContextEntry]:
    """
    Filter context entries by date range.
    
    Args:
        context: The context to filter
        start_date: Only include entries after this date
        end_date: Only include entries before this date
        
    Returns:
        Filtered list of entries
    """
    entries = list(context.entries.values())
    
    if start_date:
        entries = [entry for entry in entries if entry.timestamp >= start_date]
    
    if end_date:
        entries = [entry for entry in entries if entry.timestamp <= end_date]
    
    return entries


def create_entry_from_message(
    message: Dict[str, Any],
    source: str = "user",
    importance: float = 1.0
) -> ContextEntry:
    """
    Create a context entry from a message.
    
    Args:
        message: The message to create an entry from
        source: The source of the message
        importance: The importance of the message
        
    Returns:
        A new context entry
    """
    content = message.get("content", "")
    entry_type = message.get("type", "message")
    timestamp = message.get("timestamp", datetime.now())
    
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)
    
    metadata = {
        "message_id": message.get("id", ""),
        "role": message.get("role", ""),
    }
    
    return ContextEntry(
        content=content,
        source=source,
        entry_type=entry_type,
        timestamp=timestamp,
        importance=importance,
        metadata=metadata
    )
