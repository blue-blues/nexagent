"""
Timeline tracking system for agent actions and thinking process.

This module provides classes and functions for tracking and managing
timeline events during agent execution.
"""

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field


class TimelineEventType(str, Enum):
    """Types of events that can occur in the timeline."""
    
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    PLAN = "plan"
    WEB_BROWSE = "web_browse"
    CODE_EXECUTION = "code_execution"
    FILE_OPERATION = "file_operation"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    AGENT_RESPONSE = "agent_response"


class TimelineEvent(BaseModel):
    """
    Represents a single event in the agent timeline.
    
    This class tracks details about an event that occurred during
    agent execution, including its type, timestamp, and associated data.
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TimelineEventType
    timestamp: float = Field(default_factory=time.time)
    status: str = "pending"  # pending, success, error
    title: str
    description: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    duration: Optional[float] = None
    
    def mark_success(self, result: Optional[Any] = None) -> "TimelineEvent":
        """Mark the event as successful and record the duration."""
        self.status = "success"
        self.duration = time.time() - self.timestamp
        if result is not None:
            self.data["result"] = result
        return self
    
    def mark_error(self, error: Union[str, Exception]) -> "TimelineEvent":
        """Mark the event as failed and record the error."""
        self.status = "error"
        self.duration = time.time() - self.timestamp
        if isinstance(error, Exception):
            self.data["error"] = str(error)
            self.data["error_type"] = type(error).__name__
        else:
            self.data["error"] = error
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "status": self.status,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "duration": self.duration
        }


class Timeline(BaseModel):
    """
    Tracks a sequence of events during agent execution.
    
    This class manages a timeline of events that occur during agent execution,
    providing methods for adding events and retrieving timeline data.
    """
    
    events: List[TimelineEvent] = Field(default_factory=list)
    
    def add_event(self, 
                 event_type: TimelineEventType, 
                 title: str, 
                 description: Optional[str] = None, 
                 data: Optional[Dict[str, Any]] = None) -> TimelineEvent:
        """
        Add a new event to the timeline.
        
        Args:
            event_type: The type of event
            title: A short title for the event
            description: An optional detailed description
            data: Optional additional data associated with the event
            
        Returns:
            The newly created event
        """
        event = TimelineEvent(
            type=event_type,
            title=title,
            description=description,
            data=data or {}
        )
        self.events.append(event)
        return event
    
    def get_events(self, 
                  event_type: Optional[TimelineEventType] = None, 
                  status: Optional[str] = None) -> List[TimelineEvent]:
        """
        Get events filtered by type and/or status.
        
        Args:
            event_type: Optional event type to filter by
            status: Optional status to filter by
            
        Returns:
            A list of matching events
        """
        filtered_events = self.events
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.type == event_type]
        
        if status:
            filtered_events = [e for e in filtered_events if e.status == status]
        
        return filtered_events
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the timeline to a dictionary for serialization."""
        return {
            "events": [event.to_dict() for event in self.events],
            "event_count": len(self.events),
            "start_time": self.events[0].timestamp if self.events else None,
            "end_time": self.events[-1].timestamp if self.events else None,
        }
    
    def clear(self) -> None:
        """Clear all events from the timeline."""
        self.events = []
