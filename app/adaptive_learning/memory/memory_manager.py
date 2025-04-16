"""
Memory Manager for the Adaptive Learning System.

This module contains the MemoryManager class that coordinates the storage,
retrieval, and management of memories for the adaptive learning system.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from app.adaptive_learning.core.config import AdaptiveLearningConfig
from app.adaptive_learning.core.exceptions import MemoryStorageError, MemoryRetrievalError
from app.adaptive_learning.memory.memory_store import MemoryStore
from app.adaptive_learning.memory.memory_schema import Memory, MemoryType

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages the storage and retrieval of memories for adaptive learning.
    
    This class coordinates all aspects of memory management, including storage,
    retrieval, importance assessment, and memory consolidation.
    
    Attributes:
        config (AdaptiveLearningConfig): Configuration for memory management
        memory_store (MemoryStore): Storage backend for memories
    """
    
    def __init__(self, config: AdaptiveLearningConfig):
        """
        Initialize the MemoryManager.
        
        Args:
            config: Configuration for memory management
        """
        self.config = config
        self.memory_store = MemoryStore(config)
        logger.info("MemoryManager initialized")
    
    async def store_interaction_memory(
        self, interaction_id: str, interaction_data: Dict[str, Any], performance_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store memories from an interaction.
        
        Args:
            interaction_id: Unique identifier for the interaction
            interaction_data: Data from the interaction
            performance_metrics: Performance metrics for the interaction
            
        Returns:
            Dict containing memory storage results
            
        Raises:
            MemoryStorageError: If memory storage fails
        """
        try:
            logger.debug(f"Storing memories for interaction {interaction_id}")
            
            # Extract memories from interaction data
            memories = self._extract_memories_from_interaction(
                interaction_id, interaction_data, performance_metrics
            )
            
            # Store each memory
            stored_memories = []
            for memory in memories:
                memory_id = await self.memory_store.store_memory(memory)
                stored_memories.append({
                    "memory_id": memory_id,
                    "type": memory.type.value,
                    "importance": memory.importance,
                })
            
            # Consolidate memories if needed
            if len(await self.memory_store.get_all_memories()) > self.config.memory.max_memories:
                await self._consolidate_memories()
            
            result = {
                "interaction_id": interaction_id,
                "memories_stored": len(stored_memories),
                "stored_memory_ids": [m["memory_id"] for m in stored_memories],
                "memory_types": {m_type: sum(1 for m in stored_memories if m["type"] == m_type)
                               for m_type in set(m["type"] for m in stored_memories)},
            }
            
            logger.info(f"Stored {len(stored_memories)} memories for interaction {interaction_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error storing memories: {str(e)}")
            raise MemoryStorageError(f"Failed to store memories: {str(e)}")
    
    async def update_from_feedback(self, feedback_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update memories based on feedback.
        
        Args:
            feedback_result: Processed feedback data
            
        Returns:
            Dict containing memory update results
            
        Raises:
            MemoryStorageError: If memory update fails
        """
        try:
            interaction_id = feedback_result.get("interaction_id")
            logger.debug(f"Updating memories from feedback for interaction {interaction_id}")
            
            # Get existing memories for the interaction
            existing_memories = await self.memory_store.get_memories_by_interaction(interaction_id)
            
            # Extract new memories from feedback
            feedback_memories = self._extract_memories_from_feedback(feedback_result)
            
            # Update existing memories with feedback insights
            updated_memories = []
            for memory in existing_memories:
                # Update importance based on feedback
                if "impact_assessment" in feedback_result:
                    impact = feedback_result["impact_assessment"]
                    if "impact_score" in impact:
                        # Increase importance for memories related to high-impact feedback
                        memory.importance = min(1.0, memory.importance + impact["impact_score"] * 0.2)
                
                # Update memory with feedback insights
                if "actionable_insights" in feedback_result:
                    insights = feedback_result["actionable_insights"]
                    if insights and not memory.metadata.get("feedback_insights"):
                        memory.metadata["feedback_insights"] = insights
                
                # Save the updated memory
                memory_id = await self.memory_store.update_memory(memory)
                updated_memories.append(memory_id)
            
            # Store new memories from feedback
            stored_feedback_memories = []
            for memory in feedback_memories:
                memory_id = await self.memory_store.store_memory(memory)
                stored_feedback_memories.append(memory_id)
            
            result = {
                "interaction_id": interaction_id,
                "updated_memories": len(updated_memories),
                "new_memories": len(stored_feedback_memories),
                "updated_memory_ids": updated_memories,
                "new_memory_ids": stored_feedback_memories,
            }
            
            logger.info(f"Updated {len(updated_memories)} memories and added {len(stored_feedback_memories)} new memories from feedback")
            return result
            
        except Exception as e:
            logger.error(f"Error updating memories from feedback: {str(e)}")
            raise MemoryStorageError(f"Failed to update memories from feedback: {str(e)}")
    
    async def retrieve_memory(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve memories based on query parameters.
        
        Args:
            query_params: Parameters to filter and customize memory retrieval
            
        Returns:
            Dict containing retrieved memories and metadata
            
        Raises:
            MemoryRetrievalError: If memory retrieval fails
        """
        try:
            logger.debug(f"Retrieving memories with params: {query_params}")
            
            # Extract query parameters
            memory_type = query_params.get("type")
            content_query = query_params.get("content")
            interaction_id = query_params.get("interaction_id")
            min_importance = query_params.get("min_importance", 0.0)
            limit = query_params.get("limit", 10)
            
            # Retrieve memories based on parameters
            if interaction_id:
                memories = await self.memory_store.get_memories_by_interaction(interaction_id)
            elif content_query:
                memories = await self.memory_store.search_memories(content_query)
            else:
                memories = await self.memory_store.get_all_memories()
            
            # Filter by type if specified
            if memory_type:
                try:
                    memory_type_enum = MemoryType(memory_type)
                    memories = [m for m in memories if m.type == memory_type_enum]
                except ValueError:
                    logger.warning(f"Invalid memory type: {memory_type}")
            
            # Filter by importance
            memories = [m for m in memories if m.importance >= min_importance]
            
            # Sort by importance (descending)
            memories.sort(key=lambda m: m.importance, reverse=True)
            
            # Apply limit
            memories = memories[:limit]
            
            # Prepare result
            result = {
                "query": query_params,
                "count": len(memories),
                "memories": [m.to_dict() for m in memories],
            }
            
            logger.info(f"Retrieved {len(memories)} memories")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            raise MemoryRetrievalError(f"Failed to retrieve memories: {str(e)}")
    
    async def generate_report(self, time_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a report on memory management.
        
        Args:
            time_period: Optional time period to cover in the report
            
        Returns:
            Dict containing the memory report data
        """
        # Implementation would generate statistics and insights from memory data
        memories = await self.memory_store.get_all_memories()
        
        # Count memories by type
        type_counts = {}
        for memory in memories:
            type_name = memory.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # Calculate average importance
        avg_importance = sum(m.importance for m in memories) / len(memories) if memories else 0
        
        # Calculate memory growth over time
        # In a real implementation, this would analyze creation timestamps
        growth_metrics = {
            "total_memories": len(memories),
            "high_importance_memories": sum(1 for m in memories if m.importance > 0.7),
            "medium_importance_memories": sum(1 for m in memories if 0.3 <= m.importance <= 0.7),
            "low_importance_memories": sum(1 for m in memories if m.importance < 0.3),
        }
        
        # Analyze memory evolution
        # In a real implementation, this would track changes over time
        evolution = {
            "new_concepts_learned": 15,  # Example value
            "reinforced_concepts": 28,   # Example value
            "forgotten_concepts": 3,     # Example value
        }
        
        return {
            "memory_count": len(memories),
            "type_distribution": type_counts,
            "average_importance": avg_importance,
            "growth_metrics": growth_metrics,
            "evolution": evolution,
            "top_memories": [m.to_dict() for m in sorted(memories, key=lambda m: m.importance, reverse=True)[:5]],
        }
    
    def _extract_memories_from_interaction(
        self, interaction_id: str, interaction_data: Dict[str, Any], performance_metrics: Dict[str, Any]
    ) -> List[Memory]:
        """
        Extract memories from interaction data.
        
        Args:
            interaction_id: Unique identifier for the interaction
            interaction_data: Data from the interaction
            performance_metrics: Performance metrics for the interaction
            
        Returns:
            List of extracted memories
        """
        memories = []
        
        # Extract interaction context
        if "context" in interaction_data:
            context = interaction_data["context"]
            memory = Memory(
                id=str(uuid.uuid4()),
                type=MemoryType.CONTEXT,
                content=str(context),
                source_id=interaction_id,
                importance=0.5,  # Default importance
                created_at=datetime.now().isoformat(),
                metadata={
                    "interaction_id": interaction_id,
                    "context_type": "interaction_context",
                }
            )
            memories.append(memory)
        
        # Extract user input
        if "user_input" in interaction_data:
            user_input = interaction_data["user_input"]
            memory = Memory(
                id=str(uuid.uuid4()),
                type=MemoryType.USER_INPUT,
                content=user_input,
                source_id=interaction_id,
                importance=0.6,  # User input is important
                created_at=datetime.now().isoformat(),
                metadata={
                    "interaction_id": interaction_id,
                }
            )
            memories.append(memory)
        
        # Extract agent response
        if "agent_response" in interaction_data:
            agent_response = interaction_data["agent_response"]
            memory = Memory(
                id=str(uuid.uuid4()),
                type=MemoryType.AGENT_RESPONSE,
                content=agent_response,
                source_id=interaction_id,
                importance=0.5,  # Default importance
                created_at=datetime.now().isoformat(),
                metadata={
                    "interaction_id": interaction_id,
                }
            )
            memories.append(memory)
        
        # Extract tool usage
        if "tools_used" in interaction_data:
            tools_used = interaction_data["tools_used"]
            for tool in tools_used:
                memory = Memory(
                    id=str(uuid.uuid4()),
                    type=MemoryType.TOOL_USAGE,
                    content=str(tool),
                    source_id=interaction_id,
                    importance=0.4,  # Tool usage is moderately important
                    created_at=datetime.now().isoformat(),
                    metadata={
                        "interaction_id": interaction_id,
                        "tool_name": tool.get("name") if isinstance(tool, dict) else str(tool),
                    }
                )
                memories.append(memory)
        
        # Extract performance insights
        if performance_metrics:
            # Overall performance memory
            memory = Memory(
                id=str(uuid.uuid4()),
                type=MemoryType.PERFORMANCE,
                content=str(performance_metrics),
                source_id=interaction_id,
                importance=0.7,  # Performance metrics are important
                created_at=datetime.now().isoformat(),
                metadata={
                    "interaction_id": interaction_id,
                    "metrics": performance_metrics,
                }
            )
            memories.append(memory)
            
            # Extract specific insights
            if "insights" in performance_metrics:
                for insight in performance_metrics["insights"]:
                    memory = Memory(
                        id=str(uuid.uuid4()),
                        type=MemoryType.INSIGHT,
                        content=str(insight),
                        source_id=interaction_id,
                        importance=0.8,  # Insights are highly important
                        created_at=datetime.now().isoformat(),
                        metadata={
                            "interaction_id": interaction_id,
                            "insight_type": insight.get("type") if isinstance(insight, dict) else "general",
                        }
                    )
                    memories.append(memory)
        
        return memories
    
    def _extract_memories_from_feedback(self, feedback_result: Dict[str, Any]) -> List[Memory]:
        """
        Extract memories from feedback data.
        
        Args:
            feedback_result: Processed feedback data
            
        Returns:
            List of extracted memories
        """
        memories = []
        
        interaction_id = feedback_result.get("interaction_id")
        feedback_id = feedback_result.get("feedback_id")
        
        # Extract feedback content
        if "impact_assessment" in feedback_result:
            impact = feedback_result["impact_assessment"]
            
            # Create a memory for the feedback
            memory = Memory(
                id=str(uuid.uuid4()),
                type=MemoryType.FEEDBACK,
                content=str(feedback_result),
                source_id=feedback_id,
                importance=impact.get("impact_score", 0.5),  # Use impact score as importance
                created_at=datetime.now().isoformat(),
                metadata={
                    "interaction_id": interaction_id,
                    "feedback_id": feedback_id,
                    "impact_level": impact.get("impact_level", "medium"),
                }
            )
            memories.append(memory)
        
        # Extract actionable insights
        if "actionable_insights" in feedback_result:
            insights = feedback_result["actionable_insights"]
            for insight in insights:
                memory = Memory(
                    id=str(uuid.uuid4()),
                    type=MemoryType.INSIGHT,
                    content=str(insight),
                    source_id=feedback_id,
                    importance=0.8 if insight.get("priority") == "high" else 
                               0.6 if insight.get("priority") == "medium" else 0.4,
                    created_at=datetime.now().isoformat(),
                    metadata={
                        "interaction_id": interaction_id,
                        "feedback_id": feedback_id,
                        "insight_type": "feedback_insight",
                        "priority": insight.get("priority", "medium"),
                    }
                )
                memories.append(memory)
        
        return memories
    
    async def _consolidate_memories(self) -> None:
        """
        Consolidate memories to stay within storage limits.
        
        This method removes or merges less important memories to maintain
        the memory store within configured limits.
        """
        logger.debug("Consolidating memories")
        
        # Get all memories
        memories = await self.memory_store.get_all_memories()
        
        # If we're under the limit, no need to consolidate
        if len(memories) <= self.config.memory.max_memories:
            return
        
        # Sort by importance (ascending, so least important are first)
        memories.sort(key=lambda m: m.importance)
        
        # Calculate how many memories to remove
        to_remove = len(memories) - self.config.memory.max_memories
        
        # Remove least important memories
        for memory in memories[:to_remove]:
            await self.memory_store.delete_memory(memory.id)
        
        logger.info(f"Consolidated memories, removed {to_remove} least important memories")
