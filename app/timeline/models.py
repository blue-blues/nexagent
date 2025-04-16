"""
Timeline Models Module

This module defines the data models for the timeline feature.
"""

import uuid
import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union


class EventType(Enum):
    """Enum representing different types of timeline events."""
    AGENT_START = "agent_start"
    AGENT_STOP = "agent_stop"
    AGENT_ERROR = "agent_error"
    AGENT_THINKING = "agent_thinking"
    AGENT_RESPONSE = "agent_response"
    USER_MESSAGE = "user_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    PLAN_EXECUTED = "plan_executed"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    CODE_GENERATED = "code_generated"
    CODE_EXECUTED = "code_executed"
    WEB_BROWSING = "web_browsing"
    CONTEXT_UPDATED = "context_updated"
    CUSTOM = "custom"


class TimelineEvent:
    """Class representing a timeline event."""
    
    def __init__(
        self,
        event_type: Union[EventType, str],
        title: str,
        description: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        event_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        duration: Optional[float] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Initialize a timeline event.
        
        Args:
            event_type: Type of the event
            title: Title of the event
            description: Description of the event
            timestamp: When the event occurred
            metadata: Additional metadata for the event
            parent_id: ID of the parent event
            event_id: Unique identifier for the event
            conversation_id: ID of the conversation
            user_id: ID of the user
            duration: Duration of the event in seconds
            status: Status of the event
            tags: Tags for the event
        """
        self.event_type = event_type.value if isinstance(event_type, EventType) else event_type
        self.title = title
        self.description = description
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        self.parent_id = parent_id
        self.event_id = event_id or str(uuid.uuid4())
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.duration = duration
        self.status = status
        self.tags = tags or []
        self.children: List[TimelineEvent] = []
    
    def add_child(self, event: 'TimelineEvent'):
        """
        Add a child event.
        
        Args:
            event: Child event to add
        """
        event.parent_id = self.event_id
        self.children.append(event)
    
    def to_dict(self, include_children: bool = True) -> Dict[str, Any]:
        """
        Convert the event to a dictionary.
        
        Args:
            include_children: Whether to include children
            
        Returns:
            Dict[str, Any]: Dictionary representation of the event
        """
        result = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "duration": self.duration,
            "status": self.status,
            "tags": self.tags
        }
        
        if include_children:
            result["children"] = [child.to_dict(include_children=True) for child in self.children]
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimelineEvent':
        """
        Create an event from a dictionary.
        
        Args:
            data: Dictionary representation of the event
            
        Returns:
            TimelineEvent: Created event
        """
        # Convert timestamp string to datetime
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Create event
        event = cls(
            event_type=data.get("event_type"),
            title=data.get("title"),
            description=data.get("description"),
            timestamp=timestamp,
            metadata=data.get("metadata"),
            parent_id=data.get("parent_id"),
            event_id=data.get("event_id"),
            conversation_id=data.get("conversation_id"),
            user_id=data.get("user_id"),
            duration=data.get("duration"),
            status=data.get("status"),
            tags=data.get("tags")
        )
        
        # Add children
        children_data = data.get("children", [])
        for child_data in children_data:
            child = cls.from_dict(child_data)
            event.add_child(child)
        
        return event
    
    def __str__(self) -> str:
        """String representation of the event."""
        return f"{self.event_type}: {self.title} ({self.timestamp.isoformat()})"


class Timeline:
    """Class representing a timeline of events."""
    
    def __init__(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        events: Optional[List[TimelineEvent]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeline_id: Optional[str] = None
    ):
        """
        Initialize a timeline.
        
        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user
            events: Initial events
            metadata: Additional metadata
            timeline_id: Unique identifier for the timeline
        """
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.events = events or []
        self.metadata = metadata or {}
        self.timeline_id = timeline_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = self.created_at
    
    def add_event(self, event: TimelineEvent) -> str:
        """
        Add an event to the timeline.
        
        Args:
            event: Event to add
            
        Returns:
            str: ID of the added event
        """
        # Set conversation_id and user_id if not set
        if not event.conversation_id:
            event.conversation_id = self.conversation_id
        
        if not event.user_id:
            event.user_id = self.user_id
        
        # Add event to the timeline
        self.events.append(event)
        
        # Update timestamp
        self.updated_at = datetime.now()
        
        return event.event_id
    
    def get_event(self, event_id: str) -> Optional[TimelineEvent]:
        """
        Get an event by ID.
        
        Args:
            event_id: ID of the event to get
            
        Returns:
            Optional[TimelineEvent]: The event if found, None otherwise
        """
        # Check top-level events
        for event in self.events:
            if event.event_id == event_id:
                return event
        
        # Check child events (recursive)
        def search_children(events: List[TimelineEvent]) -> Optional[TimelineEvent]:
            for event in events:
                if event.event_id == event_id:
                    return event
                
                if event.children:
                    result = search_children(event.children)
                    if result:
                        return result
            
            return None
        
        return search_children(self.events)
    
    def get_events_by_type(self, event_type: Union[EventType, str]) -> List[TimelineEvent]:
        """
        Get events by type.
        
        Args:
            event_type: Type of events to get
            
        Returns:
            List[TimelineEvent]: List of matching events
        """
        event_type_str = event_type.value if isinstance(event_type, EventType) else event_type
        
        # Collect matching events (recursive)
        def collect_events(events: List[TimelineEvent]) -> List[TimelineEvent]:
            result = []
            
            for event in events:
                if event.event_type == event_type_str:
                    result.append(event)
                
                if event.children:
                    result.extend(collect_events(event.children))
            
            return result
        
        return collect_events(self.events)
    
    def get_events_by_tag(self, tag: str) -> List[TimelineEvent]:
        """
        Get events by tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List[TimelineEvent]: List of matching events
        """
        # Collect matching events (recursive)
        def collect_events(events: List[TimelineEvent]) -> List[TimelineEvent]:
            result = []
            
            for event in events:
                if tag in event.tags:
                    result.append(event)
                
                if event.children:
                    result.extend(collect_events(event.children))
            
            return result
        
        return collect_events(self.events)
    
    def get_events_in_time_range(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[TimelineEvent]:
        """
        Get events in a time range.
        
        Args:
            start_time: Start of the time range
            end_time: End of the time range
            
        Returns:
            List[TimelineEvent]: List of matching events
        """
        # Collect matching events (recursive)
        def collect_events(events: List[TimelineEvent]) -> List[TimelineEvent]:
            result = []
            
            for event in events:
                # Check if event is in the time range
                in_range = True
                
                if start_time and event.timestamp < start_time:
                    in_range = False
                
                if end_time and event.timestamp > end_time:
                    in_range = False
                
                if in_range:
                    result.append(event)
                
                if event.children:
                    result.extend(collect_events(event.children))
            
            return result
        
        return collect_events(self.events)
    
    def to_dict(self, include_events: bool = True) -> Dict[str, Any]:
        """
        Convert the timeline to a dictionary.
        
        Args:
            include_events: Whether to include events
            
        Returns:
            Dict[str, Any]: Dictionary representation of the timeline
        """
        result = {
            "timeline_id": self.timeline_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        
        if include_events:
            result["events"] = [event.to_dict() for event in self.events]
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Timeline':
        """
        Create a timeline from a dictionary.
        
        Args:
            data: Dictionary representation of the timeline
            
        Returns:
            Timeline: Created timeline
        """
        # Convert timestamp strings to datetime
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        # Create timeline
        timeline = cls(
            conversation_id=data.get("conversation_id"),
            user_id=data.get("user_id"),
            metadata=data.get("metadata"),
            timeline_id=data.get("timeline_id")
        )
        
        timeline.created_at = created_at or timeline.created_at
        timeline.updated_at = updated_at or timeline.updated_at
        
        # Add events
        events_data = data.get("events", [])
        for event_data in events_data:
            event = TimelineEvent.from_dict(event_data)
            timeline.events.append(event)
        
        return timeline
    
    def to_json(self, include_events: bool = True) -> str:
        """
        Convert the timeline to a JSON string.
        
        Args:
            include_events: Whether to include events
            
        Returns:
            str: JSON representation of the timeline
        """
        return json.dumps(self.to_dict(include_events=include_events), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Timeline':
        """
        Create a timeline from a JSON string.
        
        Args:
            json_str: JSON representation of the timeline
            
        Returns:
            Timeline: Created timeline
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation of the timeline."""
        return f"Timeline({self.timeline_id}, {len(self.events)} events)"
