"""
Schema definitions for memory data in the Adaptive Learning System.

This module defines the structure and types for memory data used throughout
the Adaptive Learning System.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field


class MemoryType(Enum):
    """Types of memories that can be stored in the system."""
    
    CONTEXT = "context"
    USER_INPUT = "user_input"
    AGENT_RESPONSE = "agent_response"
    TOOL_USAGE = "tool_usage"
    PERFORMANCE = "performance"
    FEEDBACK = "feedback"
    INSIGHT = "insight"
    STRATEGY = "strategy"
    CONCEPT = "concept"
    ERROR = "error"


@dataclass
class Memory:
    """
    Schema for a memory in the adaptive learning system.
    
    Attributes:
        id: Unique identifier for the memory
        type: Type of memory
        content: Content of the memory
        source_id: ID of the source (e.g., interaction ID, feedback ID)
        importance: Importance score (0-1)
        created_at: Timestamp when the memory was created
        metadata: Additional metadata for the memory
        embedding: Optional vector embedding for similarity search
    """
    
    id: str
    type: MemoryType
    content: str
    source_id: str
    importance: float
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the memory to a dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "source_id": self.source_id,
            "importance": self.importance,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "embedding": self.embedding,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """Create a Memory instance from a dictionary."""
        return cls(
            id=data["id"],
            type=MemoryType(data["type"]),
            content=data["content"],
            source_id=data["source_id"],
            importance=data["importance"],
            created_at=data["created_at"],
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )
