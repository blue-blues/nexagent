"""
Versioned Memory Context Implementation

This module provides an in-memory implementation of the versioned context protocol.
It extends the memory context with versioning capabilities.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import os
import copy

from app.core.context.memory import MemoryContext
from app.core.context.protocol import ContextEntry, ContextVersion, VersionedContextProtocol


class VersionedMemoryContext(MemoryContext, VersionedContextProtocol):
    """
    In-memory implementation of the versioned context protocol.
    Extends the memory context with versioning capabilities.
    """
    
    def __init__(self, max_entries: int = 1000, max_versions: int = 50):
        """
        Initialize a versioned memory context.
        
        Args:
            max_entries: Maximum number of entries to store
            max_versions: Maximum number of versions to store
        """
        super().__init__(max_entries=max_entries)
        self.versions: Dict[str, ContextVersion] = {}
        self.max_versions = max_versions
    
    def create_version(self, description: Optional[str] = None) -> str:
        """
        Create a new version of the current context.
        
        Args:
            description: Optional description of this version
            
        Returns:
            The ID of the created version
        """
        # Create a deep copy of the current entries
        entries_copy = [copy.deepcopy(entry) for entry in self.entries.values()]
        
        # Create a new version
        version = ContextVersion(
            entries=entries_copy,
            description=description
        )
        
        # If we've reached the maximum number of versions, remove the oldest one
        if len(self.versions) >= self.max_versions:
            oldest_version_id = min(
                self.versions.keys(),
                key=lambda k: self.versions[k].timestamp
            )
            del self.versions[oldest_version_id]
        
        # Store the version
        self.versions[version.version_id] = version
        
        return version.version_id
    
    def get_version(self, version_id: str) -> Optional[ContextVersion]:
        """
        Retrieve a specific version by ID.
        
        Args:
            version_id: The ID of the version to retrieve
            
        Returns:
            The version if found, None otherwise
        """
        return self.versions.get(version_id)
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """
        List all available versions.
        
        Returns:
            A list of version metadata
        """
        return [
            {
                "version_id": version.version_id,
                "timestamp": version.timestamp.isoformat(),
                "description": version.description,
                "entry_count": len(version.entries)
            }
            for version in sorted(
                self.versions.values(),
                key=lambda v: v.timestamp,
                reverse=True
            )
        ]
    
    def rollback_to_version(self, version_id: str) -> bool:
        """
        Roll back the context to a specific version.
        
        Args:
            version_id: The ID of the version to roll back to
            
        Returns:
            True if the rollback was successful, False otherwise
        """
        version = self.get_version(version_id)
        if not version:
            return False
        
        # Create a version of the current state before rolling back
        self.create_version(description="Auto-saved before rollback")
        
        # Clear the current entries
        self.entries.clear()
        
        # Copy the entries from the version
        for entry in version.entries:
            entry_copy = copy.deepcopy(entry)
            self.entries[entry_copy.entry_id] = entry_copy
        
        return True
    
    def compare_versions(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        Compare two versions of the context.
        
        Args:
            version_id1: The ID of the first version
            version_id2: The ID of the second version
            
        Returns:
            A dictionary containing the differences between the versions
        """
        version1 = self.get_version(version_id1)
        version2 = self.get_version(version_id2)
        
        if not version1 or not version2:
            return {"error": "One or both versions not found"}
        
        # Get the entry IDs in each version
        entry_ids1 = {entry.entry_id for entry in version1.entries}
        entry_ids2 = {entry.entry_id for entry in version2.entries}
        
        # Find entries that are in version1 but not in version2
        entries_only_in_v1 = entry_ids1 - entry_ids2
        
        # Find entries that are in version2 but not in version1
        entries_only_in_v2 = entry_ids2 - entry_ids1
        
        # Find entries that are in both versions
        common_entry_ids = entry_ids1.intersection(entry_ids2)
        
        # Create a mapping of entry IDs to entries for each version
        entries_map1 = {entry.entry_id: entry for entry in version1.entries}
        entries_map2 = {entry.entry_id: entry for entry in version2.entries}
        
        # Find entries that have changed between versions
        changed_entries = []
        for entry_id in common_entry_ids:
            entry1 = entries_map1[entry_id]
            entry2 = entries_map2[entry_id]
            
            # Compare the entries
            if entry1.content != entry2.content or entry1.importance != entry2.importance:
                changed_entries.append({
                    "entry_id": entry_id,
                    "changes": {
                        "content_changed": entry1.content != entry2.content,
                        "importance_changed": entry1.importance != entry2.importance,
                        "metadata_changed": entry1.metadata != entry2.metadata
                    }
                })
        
        return {
            "version1": {
                "version_id": version1.version_id,
                "timestamp": version1.timestamp.isoformat(),
                "description": version1.description,
                "entry_count": len(version1.entries)
            },
            "version2": {
                "version_id": version2.version_id,
                "timestamp": version2.timestamp.isoformat(),
                "description": version2.description,
                "entry_count": len(version2.entries)
            },
            "entries_only_in_v1": list(entries_only_in_v1),
            "entries_only_in_v2": list(entries_only_in_v2),
            "changed_entries": changed_entries,
            "total_differences": len(entries_only_in_v1) + len(entries_only_in_v2) + len(changed_entries)
        }
    
    def save_context(self, path: str) -> bool:
        """
        Save the current context and all versions to a file.
        
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
                        "versions": {
                            version_id: version.to_dict()
                            for version_id, version in self.versions.items()
                        },
                        "max_entries": self.max_entries,
                        "max_versions": self.max_versions
                    },
                    f,
                    indent=2
                )
            return True
        except Exception as e:
            print(f"Error saving versioned context: {e}")
            return False
    
    def load_context(self, path: str) -> bool:
        """
        Load context and all versions from a file.
        
        Args:
            path: The file path to load from
            
        Returns:
            True if the context was loaded successfully, False otherwise
        """
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.max_entries = data.get("max_entries", self.max_entries)
            self.max_versions = data.get("max_versions", self.max_versions)
            
            self.entries = {
                entry_id: ContextEntry.from_dict(entry_data)
                for entry_id, entry_data in data.get("entries", {}).items()
            }
            
            self.versions = {
                version_id: ContextVersion.from_dict(version_data)
                for version_id, version_data in data.get("versions", {}).items()
            }
            
            return True
        except Exception as e:
            print(f"Error loading versioned context: {e}")
            return False
