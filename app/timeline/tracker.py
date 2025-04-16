"""
Timeline Tracker Module

This module provides utilities for tracking events in a timeline.
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable

from app.timeline.models import Timeline, TimelineEvent, EventType
from app.timeline.storage import TimelineStorage


class TimelineTracker:
    """
    Class for tracking events in a timeline.
    
    This class provides utilities for creating and tracking events
    in a timeline, with support for nested events and duration tracking.
    """
    
    def __init__(
        self,
        storage: Optional[TimelineStorage] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        auto_save: bool = True
    ):
        """
        Initialize a timeline tracker.
        
        Args:
            storage: Storage for timelines
            conversation_id: ID of the conversation
            user_id: ID of the user
            auto_save: Whether to automatically save the timeline
        """
        self.storage = storage
        self.timeline = Timeline(conversation_id=conversation_id, user_id=user_id)
        self.auto_save = auto_save
        self._active_events: Dict[str, TimelineEvent] = {}
        self._lock = threading.Lock()
    
    def add_event(
        self,
        event_type: Union[EventType, str],
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> str:
        """
        Add an event to the timeline.
        
        Args:
            event_type: Type of the event
            title: Title of the event
            description: Description of the event
            metadata: Additional metadata for the event
            parent_id: ID of the parent event
            tags: Tags for the event
            status: Status of the event
            
        Returns:
            str: ID of the added event
        """
        with self._lock:
            # Create event
            event = TimelineEvent(
                event_type=event_type,
                title=title,
                description=description,
                metadata=metadata,
                parent_id=parent_id,
                conversation_id=self.timeline.conversation_id,
                user_id=self.timeline.user_id,
                tags=tags,
                status=status
            )
            
            # Add event to the timeline
            if parent_id and parent_id in self._active_events:
                # Add as child of parent
                parent = self._active_events[parent_id]
                parent.add_child(event)
            else:
                # Add as top-level event
                self.timeline.add_event(event)
            
            # Save timeline if auto_save is enabled
            if self.auto_save and self.storage:
                self.storage.save_timeline(self.timeline)
            
            return event.event_id
    
    def start_event(
        self,
        event_type: Union[EventType, str],
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Start a new event with duration tracking.
        
        Args:
            event_type: Type of the event
            title: Title of the event
            description: Description of the event
            metadata: Additional metadata for the event
            parent_id: ID of the parent event
            tags: Tags for the event
            
        Returns:
            str: ID of the started event
        """
        with self._lock:
            # Create event
            event = TimelineEvent(
                event_type=event_type,
                title=title,
                description=description,
                metadata=metadata or {},
                parent_id=parent_id,
                conversation_id=self.timeline.conversation_id,
                user_id=self.timeline.user_id,
                tags=tags,
                status="started"
            )
            
            # Add start time to metadata
            event.metadata["start_time"] = time.time()
            
            # Add event to the timeline
            if parent_id and parent_id in self._active_events:
                # Add as child of parent
                parent = self._active_events[parent_id]
                parent.add_child(event)
            else:
                # Add as top-level event
                self.timeline.add_event(event)
            
            # Add to active events
            self._active_events[event.event_id] = event
            
            # Save timeline if auto_save is enabled
            if self.auto_save and self.storage:
                self.storage.save_timeline(self.timeline)
            
            return event.event_id
    
    def end_event(
        self,
        event_id: str,
        status: str = "completed",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[float]:
        """
        End an event and calculate its duration.
        
        Args:
            event_id: ID of the event to end
            status: Final status of the event
            metadata: Additional metadata to add
            
        Returns:
            Optional[float]: Duration of the event in seconds, or None if the event was not found
        """
        with self._lock:
            # Get the event
            event = self.timeline.get_event(event_id)
            if not event:
                return None
            
            # Calculate duration
            start_time = event.metadata.get("start_time")
            if start_time:
                end_time = time.time()
                duration = end_time - start_time
                event.duration = duration
                event.metadata["end_time"] = end_time
            else:
                duration = None
            
            # Update status
            event.status = status
            
            # Add additional metadata
            if metadata:
                event.metadata.update(metadata)
            
            # Remove from active events
            if event_id in self._active_events:
                del self._active_events[event_id]
            
            # Save timeline if auto_save is enabled
            if self.auto_save and self.storage:
                self.storage.save_timeline(self.timeline)
            
            return duration
    
    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Update an existing event.
        
        Args:
            event_id: ID of the event to update
            title: New title
            description: New description
            metadata: Additional metadata
            status: New status
            tags: New tags
            
        Returns:
            bool: True if the event was updated, False otherwise
        """
        with self._lock:
            # Get the event
            event = self.timeline.get_event(event_id)
            if not event:
                return False
            
            # Update fields
            if title is not None:
                event.title = title
            
            if description is not None:
                event.description = description
            
            if metadata is not None:
                event.metadata.update(metadata)
            
            if status is not None:
                event.status = status
            
            if tags is not None:
                event.tags = tags
            
            # Save timeline if auto_save is enabled
            if self.auto_save and self.storage:
                self.storage.save_timeline(self.timeline)
            
            return True
    
    def get_timeline(self) -> Timeline:
        """
        Get the current timeline.
        
        Returns:
            Timeline: Current timeline
        """
        return self.timeline
    
    def save_timeline(self) -> bool:
        """
        Save the timeline to storage.
        
        Returns:
            bool: True if the timeline was saved, False otherwise
        """
        if not self.storage:
            return False
        
        return self.storage.save_timeline(self.timeline)
    
    def load_timeline(self, timeline_id: str) -> bool:
        """
        Load a timeline from storage.
        
        Args:
            timeline_id: ID of the timeline to load
            
        Returns:
            bool: True if the timeline was loaded, False otherwise
        """
        if not self.storage:
            return False
        
        timeline = self.storage.load_timeline(timeline_id)
        if not timeline:
            return False
        
        self.timeline = timeline
        return True
    
    def track_function(
        self,
        event_type: Union[EventType, str],
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Callable:
        """
        Create a decorator for tracking function execution.
        
        Args:
            event_type: Type of the event
            title: Title of the event
            description: Description of the event
            metadata: Additional metadata for the event
            parent_id: ID of the parent event
            tags: Tags for the event
            
        Returns:
            Callable: Decorator function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Start event
                event_id = self.start_event(
                    event_type=event_type,
                    title=title,
                    description=description,
                    metadata=metadata,
                    parent_id=parent_id,
                    tags=tags
                )
                
                try:
                    # Call the function
                    result = func(*args, **kwargs)
                    
                    # End event with success
                    self.end_event(
                        event_id=event_id,
                        status="completed",
                        metadata={"result": str(result)}
                    )
                    
                    return result
                except Exception as e:
                    # End event with error
                    self.end_event(
                        event_id=event_id,
                        status="failed",
                        metadata={"error": str(e)}
                    )
                    
                    # Re-raise the exception
                    raise
            
            return wrapper
        
        return decorator
    
    def track_context(
        self,
        event_type: Union[EventType, str],
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Create a context manager for tracking a block of code.
        
        Args:
            event_type: Type of the event
            title: Title of the event
            description: Description of the event
            metadata: Additional metadata for the event
            parent_id: ID of the parent event
            tags: Tags for the event
            
        Returns:
            ContextManager: Context manager for tracking
        """
        class TimelineContext:
            def __init__(self, tracker):
                self.tracker = tracker
                self.event_id = None
            
            def __enter__(self):
                # Start event
                self.event_id = self.tracker.start_event(
                    event_type=event_type,
                    title=title,
                    description=description,
                    metadata=metadata,
                    parent_id=parent_id,
                    tags=tags
                )
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                # End event
                if exc_type:
                    # Error occurred
                    self.tracker.end_event(
                        event_id=self.event_id,
                        status="failed",
                        metadata={"error": str(exc_val)}
                    )
                else:
                    # Success
                    self.tracker.end_event(
                        event_id=self.event_id,
                        status="completed"
                    )
                
                # Don't suppress exceptions
                return False
        
        return TimelineContext(self)
