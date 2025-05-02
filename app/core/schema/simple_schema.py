"""
Simplified schema implementation to avoid import issues.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class TOOL_CHOICE_TYPE:
    """Tool choice type enum."""
    
    AUTO = "auto"
    REQUIRED = "required"
    NONE = "none"


class AgentState:
    """Agent state enum."""
    
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class Message(BaseModel):
    """Message model for agent communication."""
    
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Any]] = None
    tool_call_id: Optional[str] = None
    
    @classmethod
    def user_message(cls, content: str) -> "Message":
        """Create a user message."""
        return cls(role="user", content=content)
    
    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message."""
        return cls(role="system", content=content)
    
    @classmethod
    def assistant_message(cls, content: str) -> "Message":
        """Create an assistant message."""
        return cls(role="assistant", content=content)
    
    @classmethod
    def tool_message(cls, content: str, **kwargs) -> "Message":
        """Create a tool message."""
        return cls(role="tool", content=content, **kwargs)


class Memory(BaseModel):
    """Memory model for storing agent messages."""
    
    messages: List[Message] = Field(default_factory=list)
    
    def add_message(self, message: Message) -> None:
        """Add a message to memory."""
        self.messages.append(message)


class ToolCall(BaseModel):
    """Tool call model."""
    
    id: str
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolChoice(BaseModel):
    """Tool choice model."""
    
    type: str = TOOL_CHOICE_TYPE.AUTO
    tool: Optional[Dict[str, Any]] = None
