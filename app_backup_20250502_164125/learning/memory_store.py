"""
Interaction Memory Store for Nexagent.

This module provides functionality for storing and retrieving past interactions,
decisions, and outcomes for future reference and learning.
"""

import json
import os
import time
import sqlite3
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.logger import logger


class InteractionRecord(BaseModel):
    """
    Represents a single interaction record in the memory store.
    """
    
    id: str = Field(default_factory=lambda: f"int_{int(time.time())}_{id(object())}")
    timestamp: float = Field(default_factory=time.time)
    user_prompt: str
    bot_response: str
    task_type: Optional[str] = None
    tools_used: List[str] = Field(default_factory=list)
    success: bool = True
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryStore:
    """
    Stores and retrieves past interactions, decisions, and outcomes.
    
    This class provides functionality for:
    1. Storing interaction records in a SQLite database
    2. Retrieving records based on various criteria
    3. Analyzing patterns in past interactions
    4. Providing examples for few-shot learning
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the memory store.
        
        Args:
            db_path: Path to the SQLite database file. If None, a default path is used.
        """
        if db_path is None:
            # Create a default path in the user's home directory
            home_dir = os.path.expanduser("~")
            nexagent_dir = os.path.join(home_dir, ".nexagent")
            os.makedirs(nexagent_dir, exist_ok=True)
            db_path = os.path.join(nexagent_dir, "memory_store.db")
        
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the SQLite database with the required tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create the interactions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                user_prompt TEXT,
                bot_response TEXT,
                task_type TEXT,
                tools_used TEXT,
                success INTEGER,
                execution_time REAL,
                error_message TEXT,
                metadata TEXT
            )
            ''')
            
            # Create the embeddings table for semantic search
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                interaction_id TEXT PRIMARY KEY,
                embedding BLOB,
                FOREIGN KEY (interaction_id) REFERENCES interactions (id)
            )
            ''')
            
            # Create indices for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON interactions (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_type ON interactions (task_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_success ON interactions (success)')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Initialized memory store database at {self.db_path}")
        
        except Exception as e:
            logger.error(f"Error initializing memory store database: {str(e)}")
            raise
    
    def store_interaction(self, record: InteractionRecord) -> str:
        """
        Store an interaction record in the database.
        
        Args:
            record: The interaction record to store
            
        Returns:
            The ID of the stored record
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert tools_used list to JSON string
            tools_used_json = json.dumps(record.tools_used)
            
            # Convert metadata dict to JSON string
            metadata_json = json.dumps(record.metadata)
            
            # Insert the record
            cursor.execute('''
            INSERT INTO interactions (
                id, timestamp, user_prompt, bot_response, task_type,
                tools_used, success, execution_time, error_message, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.id, record.timestamp, record.user_prompt, record.bot_response,
                record.task_type, tools_used_json, int(record.success), record.execution_time,
                record.error_message, metadata_json
            ))
            
            conn.commit()
            conn.close()
            
            # Generate and store embedding asynchronously
            self._generate_and_store_embedding(record)
            
            logger.info(f"Stored interaction record with ID: {record.id}")
            return record.id
        
        except Exception as e:
            logger.error(f"Error storing interaction record: {str(e)}")
            raise
    
    def _generate_and_store_embedding(self, record: InteractionRecord):
        """
        Generate and store an embedding for the interaction record.
        
        This is a placeholder for now. In a real implementation, this would use
        a model to generate embeddings for semantic search.
        
        Args:
            record: The interaction record to generate an embedding for
        """
        # This is a placeholder. In a real implementation, this would use
        # a model to generate embeddings for semantic search.
        pass
    
    def get_interaction(self, interaction_id: str) -> Optional[InteractionRecord]:
        """
        Get an interaction record by ID.
        
        Args:
            interaction_id: The ID of the interaction record to get
            
        Returns:
            The interaction record, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, timestamp, user_prompt, bot_response, task_type,
                   tools_used, success, execution_time, error_message, metadata
            FROM interactions
            WHERE id = ?
            ''', (interaction_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None:
                return None
            
            # Convert JSON strings back to Python objects
            tools_used = json.loads(row[5])
            metadata = json.loads(row[9])
            
            return InteractionRecord(
                id=row[0],
                timestamp=row[1],
                user_prompt=row[2],
                bot_response=row[3],
                task_type=row[4],
                tools_used=tools_used,
                success=bool(row[6]),
                execution_time=row[7],
                error_message=row[8],
                metadata=metadata
            )
        
        except Exception as e:
            logger.error(f"Error getting interaction record: {str(e)}")
            return None
    
    def search_interactions(
        self,
        query: Optional[str] = None,
        task_type: Optional[str] = None,
        tool_used: Optional[str] = None,
        success: Optional[bool] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[InteractionRecord]:
        """
        Search for interaction records based on various criteria.
        
        Args:
            query: Optional text query to search in user_prompt and bot_response
            task_type: Optional task type to filter by
            tool_used: Optional tool name to filter by
            success: Optional success flag to filter by
            start_time: Optional start timestamp to filter by
            end_time: Optional end timestamp to filter by
            limit: Maximum number of records to return
            offset: Offset for pagination
            
        Returns:
            List of matching interaction records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build the query
            sql = '''
            SELECT id, timestamp, user_prompt, bot_response, task_type,
                   tools_used, success, execution_time, error_message, metadata
            FROM interactions
            WHERE 1=1
            '''
            
            params = []
            
            if query is not None:
                sql += " AND (user_prompt LIKE ? OR bot_response LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%"])
            
            if task_type is not None:
                sql += " AND task_type = ?"
                params.append(task_type)
            
            if tool_used is not None:
                sql += " AND tools_used LIKE ?"
                params.append(f"%{tool_used}%")
            
            if success is not None:
                sql += " AND success = ?"
                params.append(int(success))
            
            if start_time is not None:
                sql += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time is not None:
                sql += " AND timestamp <= ?"
                params.append(end_time)
            
            sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to InteractionRecord objects
            records = []
            for row in rows:
                tools_used = json.loads(row[5])
                metadata = json.loads(row[9])
                
                record = InteractionRecord(
                    id=row[0],
                    timestamp=row[1],
                    user_prompt=row[2],
                    bot_response=row[3],
                    task_type=row[4],
                    tools_used=tools_used,
                    success=bool(row[6]),
                    execution_time=row[7],
                    error_message=row[8],
                    metadata=metadata
                )
                
                records.append(record)
            
            return records
        
        except Exception as e:
            logger.error(f"Error searching interaction records: {str(e)}")
            return []
    
    def get_similar_interactions(
        self,
        prompt: str,
        limit: int = 5
    ) -> List[InteractionRecord]:
        """
        Get interactions similar to the given prompt.
        
        This is a placeholder for now. In a real implementation, this would use
        embeddings for semantic search.
        
        Args:
            prompt: The prompt to find similar interactions for
            limit: Maximum number of records to return
            
        Returns:
            List of similar interaction records
        """
        # This is a placeholder. In a real implementation, this would use
        # embeddings for semantic search.
        return self.search_interactions(query=prompt, limit=limit)
    
    def get_successful_examples(
        self,
        task_type: str,
        limit: int = 3
    ) -> List[InteractionRecord]:
        """
        Get successful examples for a specific task type.
        
        Args:
            task_type: The task type to get examples for
            limit: Maximum number of examples to return
            
        Returns:
            List of successful interaction records for the task type
        """
        return self.search_interactions(
            task_type=task_type,
            success=True,
            limit=limit
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the stored interactions.
        
        Returns:
            Dictionary with statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM interactions")
            total_count = cursor.fetchone()[0]
            
            # Get success rate
            cursor.execute("SELECT COUNT(*) FROM interactions WHERE success = 1")
            success_count = cursor.fetchone()[0]
            success_rate = success_count / total_count if total_count > 0 else 0
            
            # Get average execution time
            cursor.execute("SELECT AVG(execution_time) FROM interactions")
            avg_execution_time = cursor.fetchone()[0] or 0
            
            # Get task type distribution
            cursor.execute("""
            SELECT task_type, COUNT(*) as count
            FROM interactions
            WHERE task_type IS NOT NULL
            GROUP BY task_type
            ORDER BY count DESC
            """)
            task_type_distribution = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get tool usage
            cursor.execute("SELECT tools_used FROM interactions")
            tool_usage = {}
            for row in cursor.fetchall():
                tools = json.loads(row[0])
                for tool in tools:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            conn.close()
            
            return {
                "total_count": total_count,
                "success_count": success_count,
                "success_rate": success_rate,
                "avg_execution_time": avg_execution_time,
                "task_type_distribution": task_type_distribution,
                "tool_usage": tool_usage
            }
        
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {
                "error": str(e)
            }
    
    def clear_old_records(self, days: int = 30) -> int:
        """
        Clear records older than the specified number of days.
        
        Args:
            days: Number of days to keep records for
            
        Returns:
            Number of records deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate the cutoff timestamp
            cutoff_timestamp = time.time() - (days * 24 * 60 * 60)
            
            # Get the IDs of records to delete
            cursor.execute(
                "SELECT id FROM interactions WHERE timestamp < ?",
                (cutoff_timestamp,)
            )
            ids_to_delete = [row[0] for row in cursor.fetchall()]
            
            # Delete the embeddings first (due to foreign key constraint)
            cursor.execute(
                "DELETE FROM embeddings WHERE interaction_id IN ({})".format(
                    ",".join(["?"] * len(ids_to_delete))
                ),
                ids_to_delete
            )
            
            # Delete the interactions
            cursor.execute(
                "DELETE FROM interactions WHERE timestamp < ?",
                (cutoff_timestamp,)
            )
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleared {deleted_count} old records from memory store")
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error clearing old records: {str(e)}")
            return 0


# Create a default memory store instance
default_memory_store = MemoryStore()
