"""
Memory Store for the Adaptive Learning System.

This module contains the MemoryStore class that provides storage and retrieval
capabilities for memories in the adaptive learning system.
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from app.adaptive_learning.core.config import AdaptiveLearningConfig
from app.adaptive_learning.core.exceptions import MemoryStorageError, MemoryRetrievalError
from app.adaptive_learning.memory.memory_schema import Memory, MemoryType

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Storage backend for memories in the adaptive learning system.
    
    This class provides methods for storing, retrieving, updating, and
    searching memories, with support for vector-based similarity search.
    
    Attributes:
        config (AdaptiveLearningConfig): Configuration for memory storage
        memories (Dict[str, Memory]): In-memory store for memories (would use a database in production)
    """
    
    def __init__(self, config: AdaptiveLearningConfig):
        """
        Initialize the MemoryStore.
        
        Args:
            config: Configuration for memory storage
        """
        self.config = config
        self.memories = {}  # In-memory store (would use a database in production)
        
        # In a real implementation, this would initialize vector storage
        # self.vector_store = VectorStore(config.memory.embedding_dimension)
        
        logger.info("MemoryStore initialized")
    
    async def store_memory(self, memory: Memory) -> str:
        """
        Store a memory.
        
        Args:
            memory: The memory to store
            
        Returns:
            The ID of the stored memory
            
        Raises:
            MemoryStorageError: If memory storage fails
        """
        try:
            # In a real implementation, this would compute embeddings
            # memory.embedding = await self._compute_embedding(memory.content)
            
            # Store the memory
            self.memories[memory.id] = memory
            
            # In a real implementation, this would also store in vector storage
            # await self.vector_store.add_vector(memory.id, memory.embedding)
            
            logger.debug(f"Stored memory {memory.id} of type {memory.type.value}")
            return memory.id
            
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")
            raise MemoryStorageError(f"Failed to store memory: {str(e)}")
    
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            The memory if found, None otherwise
            
        Raises:
            MemoryRetrievalError: If memory retrieval fails
        """
        try:
            return self.memories.get(memory_id)
        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {str(e)}")
            raise MemoryRetrievalError(f"Failed to retrieve memory {memory_id}: {str(e)}")
    
    async def update_memory(self, memory: Memory) -> str:
        """
        Update an existing memory.
        
        Args:
            memory: The memory to update
            
        Returns:
            The ID of the updated memory
            
        Raises:
            MemoryStorageError: If memory update fails
        """
        try:
            if memory.id not in self.memories:
                raise MemoryStorageError(f"Memory {memory.id} not found")
            
            # In a real implementation, this would update embeddings if content changed
            # if memory.content != self.memories[memory.id].content:
            #     memory.embedding = await self._compute_embedding(memory.content)
            
            # Update the memory
            self.memories[memory.id] = memory
            
            # In a real implementation, this would also update in vector storage
            # await self.vector_store.update_vector(memory.id, memory.embedding)
            
            logger.debug(f"Updated memory {memory.id}")
            return memory.id
            
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            raise MemoryStorageError(f"Failed to update memory: {str(e)}")
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            True if the memory was deleted, False otherwise
            
        Raises:
            MemoryStorageError: If memory deletion fails
        """
        try:
            if memory_id not in self.memories:
                return False
            
            # Delete the memory
            del self.memories[memory_id]
            
            # In a real implementation, this would also delete from vector storage
            # await self.vector_store.delete_vector(memory_id)
            
            logger.debug(f"Deleted memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {str(e)}")
            raise MemoryStorageError(f"Failed to delete memory {memory_id}: {str(e)}")
    
    async def get_all_memories(self) -> List[Memory]:
        """
        Retrieve all memories.
        
        Returns:
            List of all memories
            
        Raises:
            MemoryRetrievalError: If memory retrieval fails
        """
        try:
            return list(self.memories.values())
        except Exception as e:
            logger.error(f"Error retrieving all memories: {str(e)}")
            raise MemoryRetrievalError(f"Failed to retrieve all memories: {str(e)}")
    
    async def get_memories_by_type(self, memory_type: MemoryType) -> List[Memory]:
        """
        Retrieve memories of a specific type.
        
        Args:
            memory_type: Type of memories to retrieve
            
        Returns:
            List of memories of the specified type
            
        Raises:
            MemoryRetrievalError: If memory retrieval fails
        """
        try:
            return [m for m in self.memories.values() if m.type == memory_type]
        except Exception as e:
            logger.error(f"Error retrieving memories by type {memory_type}: {str(e)}")
            raise MemoryRetrievalError(f"Failed to retrieve memories by type {memory_type}: {str(e)}")
    
    async def get_memories_by_interaction(self, interaction_id: str) -> List[Memory]:
        """
        Retrieve memories related to a specific interaction.
        
        Args:
            interaction_id: ID of the interaction
            
        Returns:
            List of memories related to the interaction
            
        Raises:
            MemoryRetrievalError: If memory retrieval fails
        """
        try:
            return [
                m for m in self.memories.values()
                if m.source_id == interaction_id or
                   (m.metadata and m.metadata.get("interaction_id") == interaction_id)
            ]
        except Exception as e:
            logger.error(f"Error retrieving memories for interaction {interaction_id}: {str(e)}")
            raise MemoryRetrievalError(f"Failed to retrieve memories for interaction {interaction_id}: {str(e)}")
    
    async def search_memories(self, query: str, limit: int = 10) -> List[Memory]:
        """
        Search for memories similar to the query.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of memories similar to the query
            
        Raises:
            MemoryRetrievalError: If memory search fails
        """
        try:
            # In a real implementation, this would use vector similarity search
            # query_embedding = await self._compute_embedding(query)
            # similar_ids = await self.vector_store.search_similar(query_embedding, limit)
            # return [self.memories[memory_id] for memory_id in similar_ids if memory_id in self.memories]
            
            # Simple text-based search as a fallback
            query_lower = query.lower()
            results = []
            
            for memory in self.memories.values():
                if query_lower in memory.content.lower():
                    results.append(memory)
            
            # Sort by importance
            results.sort(key=lambda m: m.importance, reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            raise MemoryRetrievalError(f"Failed to search memories: {str(e)}")
    
    async def backup_memories(self, backup_path: Optional[str] = None) -> str:
        """
        Backup all memories to a file.
        
        Args:
            backup_path: Optional path for the backup file
            
        Returns:
            Path to the backup file
            
        Raises:
            MemoryStorageError: If backup fails
        """
        try:
            # Use default path if not specified
            if not backup_path:
                os.makedirs(self.config.storage_path, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                backup_path = os.path.join(self.config.storage_path, f"memory_backup_{timestamp}.json")
            
            # Convert memories to dictionaries
            memory_dicts = {memory_id: memory.to_dict() for memory_id, memory in self.memories.items()}
            
            # Write to file
            with open(backup_path, 'w') as f:
                json.dump(memory_dicts, f, indent=2)
            
            logger.info(f"Backed up {len(memory_dicts)} memories to {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error backing up memories: {str(e)}")
            raise MemoryStorageError(f"Failed to backup memories: {str(e)}")
    
    async def restore_memories(self, backup_path: str) -> int:
        """
        Restore memories from a backup file.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            Number of memories restored
            
        Raises:
            MemoryStorageError: If restore fails
        """
        try:
            # Read from file
            with open(backup_path, 'r') as f:
                memory_dicts = json.load(f)
            
            # Convert dictionaries to Memory objects
            for memory_id, memory_dict in memory_dicts.items():
                self.memories[memory_id] = Memory.from_dict(memory_dict)
            
            logger.info(f"Restored {len(memory_dicts)} memories from {backup_path}")
            return len(memory_dicts)
            
        except Exception as e:
            logger.error(f"Error restoring memories: {str(e)}")
            raise MemoryStorageError(f"Failed to restore memories: {str(e)}")
    
    # async def _compute_embedding(self, text: str) -> List[float]:
    #     """
    #     Compute embedding vector for text.
    #     
    #     Args:
    #         text: Text to embed
    #         
    #     Returns:
    #         Embedding vector
    #     """
    #     # In a real implementation, this would use an embedding model
    #     # For now, return a placeholder
    #     return [0.0] * self.config.memory.embedding_dimension
