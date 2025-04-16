"""
Memory reasoning module for Nexagent.

This module provides functionality for reasoning with memory in the Nexagent system.
It enables the agent to use past conversations and experiences to inform current decisions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from pydantic import BaseModel, Field

from app.schema import Message
from app.logger import logger


class MemoryEntry(BaseModel):
    """A single memory entry in the memory store."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    importance: float = 0.5  # 0.0 to 1.0, with 1.0 being most important
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryReasoning:
    """
    Memory reasoning system for Nexagent.
    
    This class provides methods for storing, retrieving, and reasoning with memories
    to enhance the agent's decision-making capabilities.
    """
    
    def __init__(self, max_memories: int = 1000):
        """
        Initialize the memory reasoning system.
        
        Args:
            max_memories: Maximum number of memories to store
        """
        self.memories: List[MemoryEntry] = []
        self.max_memories = max_memories
        logger.info(f"Initialized memory reasoning system with max_memories={max_memories}")
    
    def add_memory(self, content: str, source: str, importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a new memory to the store.
        
        Args:
            content: The content of the memory
            source: The source of the memory (e.g., 'user', 'agent', 'tool')
            importance: The importance of the memory (0.0 to 1.0)
            metadata: Additional metadata for the memory
            
        Returns:
            The ID of the added memory
        """
        memory = MemoryEntry(
            content=content,
            source=source,
            importance=importance,
            metadata=metadata or {}
        )
        
        self.memories.append(memory)
        
        # If we've exceeded the maximum number of memories, remove the least important ones
        if len(self.memories) > self.max_memories:
            self._consolidate_memories()
            
        logger.debug(f"Added memory: {memory.id} (importance: {importance})")
        return memory.id
    
    def _consolidate_memories(self):
        """
        Consolidate memories to stay within the maximum limit.
        
        This method removes the least important memories to keep the total count
        under the maximum limit.
        """
        # Sort memories by importance (ascending)
        self.memories.sort(key=lambda m: m.importance)
        
        # Remove the least important memories
        excess = len(self.memories) - self.max_memories
        removed = self.memories[:excess]
        self.memories = self.memories[excess:]
        
        logger.info(f"Consolidated memories, removed {len(removed)} least important memories")
    
    def search_memories(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """
        Search for memories matching the query.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching memories
        """
        # Simple text-based search
        query_lower = query.lower()
        results = []
        
        for memory in self.memories:
            if query_lower in memory.content.lower():
                results.append(memory)
        
        # Sort by importance (descending)
        results.sort(key=lambda m: m.importance, reverse=True)
        
        return results[:limit]
    
    def get_recent_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """
        Get the most recent memories.
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            List of recent memories
        """
        # Sort by timestamp (descending)
        sorted_memories = sorted(
            self.memories,
            key=lambda m: m.timestamp,
            reverse=True
        )
        
        return sorted_memories[:limit]
    
    def get_important_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """
        Get the most important memories.
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            List of important memories
        """
        # Sort by importance (descending)
        sorted_memories = sorted(
            self.memories,
            key=lambda m: m.importance,
            reverse=True
        )
        
        return sorted_memories[:limit]
    
    def get_relevant_memories(self, context: str, limit: int = 10) -> List[MemoryEntry]:
        """
        Get memories relevant to the given context.
        
        Args:
            context: The context to find relevant memories for
            limit: Maximum number of memories to return
            
        Returns:
            List of relevant memories
        """
        # This is a simple implementation that uses text matching
        # In a production system, this would use embeddings and semantic search
        return self.search_memories(context, limit)
    
    def add_conversation_to_memory(self, messages: List[Message], conversation_id: str):
        """
        Add a conversation to memory.
        
        Args:
            messages: List of messages in the conversation
            conversation_id: ID of the conversation
        """
        for message in messages:
            importance = 0.5  # Default importance
            
            # Adjust importance based on role
            if message.role == "user":
                importance = 0.7  # User messages are more important
            elif message.role == "system":
                importance = 0.3  # System messages are less important
            
            self.add_memory(
                content=message.content,
                source=message.role,
                importance=importance,
                metadata={
                    "conversation_id": conversation_id,
                    "timestamp": message.timestamp,
                    "message_id": message.id
                }
            )
        
        logger.info(f"Added {len(messages)} messages from conversation {conversation_id} to memory")
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current memory state.
        
        Returns:
            Dictionary with memory statistics
        """
        sources = {}
        total_importance = 0.0
        
        for memory in self.memories:
            source = memory.source
            if source not in sources:
                sources[source] = 0
            sources[source] += 1
            total_importance += memory.importance
        
        avg_importance = total_importance / len(self.memories) if self.memories else 0.0
        
        return {
            "total_memories": len(self.memories),
            "sources": sources,
            "average_importance": avg_importance,
            "oldest_memory": min(self.memories, key=lambda m: m.timestamp).timestamp if self.memories else None,
            "newest_memory": max(self.memories, key=lambda m: m.timestamp).timestamp if self.memories else None,
        }
