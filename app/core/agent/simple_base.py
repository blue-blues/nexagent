"""
Simplified BaseAgent implementation to avoid import issues.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Message model for agent communication."""
    
    role: str
    content: Optional[str] = None
    
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


class AgentState:
    """Agent state enum."""
    
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution."""
    
    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")
    
    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )
    
    # Dependencies
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: str = Field(
        default=AgentState.IDLE, description="Current agent state"
    )
    
    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")
    
    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses
    
    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow."""
        pass
    
    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages
    
    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
