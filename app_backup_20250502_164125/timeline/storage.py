"""
Timeline Storage Module

This module provides storage implementations for timelines.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod

from app.timeline.models import Timeline


class TimelineStorage(ABC):
    """
    Abstract base class for timeline storage.
    
    This class defines the interface that all timeline storage implementations must follow.
    """
    
    @abstractmethod
    def save_timeline(self, timeline: Timeline) -> bool:
        """
        Save a timeline to storage.
        
        Args:
            timeline: Timeline to save
            
        Returns:
            bool: True if the timeline was saved successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def load_timeline(self, timeline_id: str) -> Optional[Timeline]:
        """
        Load a timeline from storage.
        
        Args:
            timeline_id: ID of the timeline to load
            
        Returns:
            Optional[Timeline]: The loaded timeline, or None if not found
        """
        pass
    
    @abstractmethod
    def delete_timeline(self, timeline_id: str) -> bool:
        """
        Delete a timeline from storage.
        
        Args:
            timeline_id: ID of the timeline to delete
            
        Returns:
            bool: True if the timeline was deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def list_timelines(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List timelines in storage.
        
        Args:
            conversation_id: Filter by conversation ID
            user_id: Filter by user ID
            
        Returns:
            List[Dict[str, Any]]: List of timeline metadata
        """
        pass


class FileTimelineStorage(TimelineStorage):
    """
    File-based implementation of timeline storage.
    
    This class stores timelines as JSON files on disk.
    """
    
    def __init__(self, storage_dir: str):
        """
        Initialize file-based timeline storage.
        
        Args:
            storage_dir: Directory to store timeline files
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def _get_timeline_path(self, timeline_id: str) -> str:
        """
        Get the file path for a timeline.
        
        Args:
            timeline_id: ID of the timeline
            
        Returns:
            str: File path for the timeline
        """
        return os.path.join(self.storage_dir, f"{timeline_id}.json")
    
    def _get_index_path(self) -> str:
        """
        Get the file path for the timeline index.
        
        Returns:
            str: File path for the index
        """
        return os.path.join(self.storage_dir, "index.json")
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Load the timeline index.
        
        Returns:
            Dict[str, Dict[str, Any]]: Timeline index
        """
        index_path = self._get_index_path()
        
        if not os.path.exists(index_path):
            return {}
        
        try:
            with open(index_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    
    def _save_index(self, index: Dict[str, Dict[str, Any]]) -> bool:
        """
        Save the timeline index.
        
        Args:
            index: Timeline index to save
            
        Returns:
            bool: True if the index was saved successfully, False otherwise
        """
        index_path = self._get_index_path()
        
        try:
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            return True
        except Exception:
            return False
    
    def _update_index(self, timeline: Timeline) -> bool:
        """
        Update the timeline index.
        
        Args:
            timeline: Timeline to update in the index
            
        Returns:
            bool: True if the index was updated successfully, False otherwise
        """
        index = self._load_index()
        
        # Update index entry
        index[timeline.timeline_id] = {
            "timeline_id": timeline.timeline_id,
            "conversation_id": timeline.conversation_id,
            "user_id": timeline.user_id,
            "created_at": timeline.created_at.isoformat(),
            "updated_at": timeline.updated_at.isoformat(),
            "event_count": len(timeline.events)
        }
        
        return self._save_index(index)
    
    def _remove_from_index(self, timeline_id: str) -> bool:
        """
        Remove a timeline from the index.
        
        Args:
            timeline_id: ID of the timeline to remove
            
        Returns:
            bool: True if the timeline was removed from the index successfully, False otherwise
        """
        index = self._load_index()
        
        if timeline_id in index:
            del index[timeline_id]
            return self._save_index(index)
        
        return True
    
    def save_timeline(self, timeline: Timeline) -> bool:
        """
        Save a timeline to storage.
        
        Args:
            timeline: Timeline to save
            
        Returns:
            bool: True if the timeline was saved successfully, False otherwise
        """
        # Update timestamp
        timeline.updated_at = datetime.now()
        
        # Get file path
        file_path = self._get_timeline_path(timeline.timeline_id)
        
        try:
            # Save timeline to file
            with open(file_path, 'w') as f:
                f.write(timeline.to_json())
            
            # Update index
            self._update_index(timeline)
            
            return True
        except Exception:
            return False
    
    def load_timeline(self, timeline_id: str) -> Optional[Timeline]:
        """
        Load a timeline from storage.
        
        Args:
            timeline_id: ID of the timeline to load
            
        Returns:
            Optional[Timeline]: The loaded timeline, or None if not found
        """
        # Get file path
        file_path = self._get_timeline_path(timeline_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            # Load timeline from file
            with open(file_path, 'r') as f:
                return Timeline.from_json(f.read())
        except Exception:
            return None
    
    def delete_timeline(self, timeline_id: str) -> bool:
        """
        Delete a timeline from storage.
        
        Args:
            timeline_id: ID of the timeline to delete
            
        Returns:
            bool: True if the timeline was deleted successfully, False otherwise
        """
        # Get file path
        file_path = self._get_timeline_path(timeline_id)
        
        if not os.path.exists(file_path):
            return True
        
        try:
            # Delete timeline file
            os.remove(file_path)
            
            # Remove from index
            self._remove_from_index(timeline_id)
            
            return True
        except Exception:
            return False
    
    def list_timelines(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List timelines in storage.
        
        Args:
            conversation_id: Filter by conversation ID
            user_id: Filter by user ID
            
        Returns:
            List[Dict[str, Any]]: List of timeline metadata
        """
        index = self._load_index()
        
        # Filter timelines
        filtered_timelines = []
        
        for timeline_data in index.values():
            # Apply filters
            if conversation_id and timeline_data.get("conversation_id") != conversation_id:
                continue
            
            if user_id and timeline_data.get("user_id") != user_id:
                continue
            
            filtered_timelines.append(timeline_data)
        
        # Sort by updated_at (newest first)
        filtered_timelines.sort(
            key=lambda t: t.get("updated_at", ""),
            reverse=True
        )
        
        return filtered_timelines


class SQLiteTimelineStorage(TimelineStorage):
    """
    SQLite-based implementation of timeline storage.
    
    This class stores timelines in a SQLite database.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize SQLite-based timeline storage.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            sqlite3.Connection: Database connection
        """
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create timelines table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS timelines (
            timeline_id TEXT PRIMARY KEY,
            conversation_id TEXT,
            user_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            metadata TEXT,
            data TEXT
        )
        ''')
        
        # Create index on conversation_id
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timelines_conversation_id
        ON timelines (conversation_id)
        ''')
        
        # Create index on user_id
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timelines_user_id
        ON timelines (user_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_timeline(self, timeline: Timeline) -> bool:
        """
        Save a timeline to storage.
        
        Args:
            timeline: Timeline to save
            
        Returns:
            bool: True if the timeline was saved successfully, False otherwise
        """
        # Update timestamp
        timeline.updated_at = datetime.now()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert timeline to JSON
            timeline_data = timeline.to_json()
            metadata_json = json.dumps(timeline.metadata)
            
            # Insert or update timeline
            cursor.execute('''
            INSERT OR REPLACE INTO timelines
            (timeline_id, conversation_id, user_id, created_at, updated_at, metadata, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timeline.timeline_id,
                timeline.conversation_id,
                timeline.user_id,
                timeline.created_at.isoformat(),
                timeline.updated_at.isoformat(),
                metadata_json,
                timeline_data
            ))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception:
            return False
    
    def load_timeline(self, timeline_id: str) -> Optional[Timeline]:
        """
        Load a timeline from storage.
        
        Args:
            timeline_id: ID of the timeline to load
            
        Returns:
            Optional[Timeline]: The loaded timeline, or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Query timeline
            cursor.execute('''
            SELECT data FROM timelines
            WHERE timeline_id = ?
            ''', (timeline_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Parse timeline data
            timeline_data = row[0]
            return Timeline.from_json(timeline_data)
        except Exception:
            return None
    
    def delete_timeline(self, timeline_id: str) -> bool:
        """
        Delete a timeline from storage.
        
        Args:
            timeline_id: ID of the timeline to delete
            
        Returns:
            bool: True if the timeline was deleted successfully, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Delete timeline
            cursor.execute('''
            DELETE FROM timelines
            WHERE timeline_id = ?
            ''', (timeline_id,))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception:
            return False
    
    def list_timelines(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List timelines in storage.
        
        Args:
            conversation_id: Filter by conversation ID
            user_id: Filter by user ID
            
        Returns:
            List[Dict[str, Any]]: List of timeline metadata
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build query
            query = '''
            SELECT timeline_id, conversation_id, user_id, created_at, updated_at, metadata
            FROM timelines
            '''
            
            params = []
            where_clauses = []
            
            if conversation_id:
                where_clauses.append("conversation_id = ?")
                params.append(conversation_id)
            
            if user_id:
                where_clauses.append("user_id = ?")
                params.append(user_id)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY updated_at DESC"
            
            # Execute query
            cursor.execute(query, params)
            
            # Process results
            timelines = []
            for row in cursor.fetchall():
                timeline_id, conversation_id, user_id, created_at, updated_at, metadata_json = row
                
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {}
                
                timelines.append({
                    "timeline_id": timeline_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "metadata": metadata
                })
            
            conn.close()
            
            return timelines
        except Exception:
            return []
