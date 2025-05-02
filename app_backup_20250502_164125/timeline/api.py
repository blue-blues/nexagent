"""
Timeline API Module

This module provides API endpoints for interacting with timelines.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from app.timeline.models import Timeline, TimelineEvent, EventType
from app.timeline.tracker import TimelineTracker
from app.timeline.storage import TimelineStorage


class TimelineAPI:
    """
    API for interacting with timelines.
    
    This class provides methods for creating, retrieving, and manipulating
    timelines and events through a simple API.
    """
    
    def __init__(self, storage: TimelineStorage):
        """
        Initialize the timeline API.
        
        Args:
            storage: Storage for timelines
        """
        self.storage = storage
        self.active_trackers: Dict[str, TimelineTracker] = {}
    
    def create_timeline(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new timeline.
        
        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: Created timeline metadata
        """
        # Create timeline
        timeline = Timeline(
            conversation_id=conversation_id,
            user_id=user_id,
            metadata=metadata
        )
        
        # Save timeline
        self.storage.save_timeline(timeline)
        
        # Create tracker
        tracker = TimelineTracker(
            storage=self.storage,
            conversation_id=conversation_id,
            user_id=user_id,
            auto_save=True
        )
        tracker.timeline = timeline
        
        # Add to active trackers
        self.active_trackers[timeline.timeline_id] = tracker
        
        return {
            "timeline_id": timeline.timeline_id,
            "conversation_id": timeline.conversation_id,
            "user_id": timeline.user_id,
            "created_at": timeline.created_at.isoformat(),
            "updated_at": timeline.updated_at.isoformat()
        }
    
    def get_timeline(self, timeline_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a timeline by ID.
        
        Args:
            timeline_id: ID of the timeline to get
            
        Returns:
            Optional[Dict[str, Any]]: Timeline data, or None if not found
        """
        # Check active trackers
        if timeline_id in self.active_trackers:
            timeline = self.active_trackers[timeline_id].timeline
        else:
            # Load from storage
            timeline = self.storage.load_timeline(timeline_id)
        
        if not timeline:
            return None
        
        return timeline.to_dict()
    
    def get_timeline_events(
        self,
        timeline_id: str,
        event_type: Optional[Union[EventType, str]] = None,
        tag: Optional[str] = None,
        start_time: Optional[Union[datetime, str]] = None,
        end_time: Optional[Union[datetime, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get events from a timeline.
        
        Args:
            timeline_id: ID of the timeline
            event_type: Filter by event type
            tag: Filter by tag
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            List[Dict[str, Any]]: List of events
        """
        # Check active trackers
        if timeline_id in self.active_trackers:
            timeline = self.active_trackers[timeline_id].timeline
        else:
            # Load from storage
            timeline = self.storage.load_timeline(timeline_id)
        
        if not timeline:
            return []
        
        # Convert string timestamps to datetime
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
        
        # Apply filters
        events = []
        
        if event_type:
            # Filter by event type
            event_type_str = event_type.value if isinstance(event_type, EventType) else event_type
            filtered_events = timeline.get_events_by_type(event_type_str)
            events.extend(filtered_events)
        elif tag:
            # Filter by tag
            filtered_events = timeline.get_events_by_tag(tag)
            events.extend(filtered_events)
        elif start_time or end_time:
            # Filter by time range
            filtered_events = timeline.get_events_in_time_range(start_time, end_time)
            events.extend(filtered_events)
        else:
            # No filters, get all events
            events = timeline.events
        
        # Convert to dictionaries
        return [event.to_dict(include_children=True) for event in events]
    
    def add_event(
        self,
        timeline_id: str,
        event_type: Union[EventType, str],
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> Optional[str]:
        """
        Add an event to a timeline.
        
        Args:
            timeline_id: ID of the timeline
            event_type: Type of the event
            title: Title of the event
            description: Description of the event
            metadata: Additional metadata
            parent_id: ID of the parent event
            tags: Tags for the event
            status: Status of the event
            
        Returns:
            Optional[str]: ID of the added event, or None if the timeline was not found
        """
        # Get or create tracker
        tracker = self._get_or_create_tracker(timeline_id)
        if not tracker:
            return None
        
        # Add event
        return tracker.add_event(
            event_type=event_type,
            title=title,
            description=description,
            metadata=metadata,
            parent_id=parent_id,
            tags=tags,
            status=status
        )
    
    def start_event(
        self,
        timeline_id: str,
        event_type: Union[EventType, str],
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Start an event in a timeline.
        
        Args:
            timeline_id: ID of the timeline
            event_type: Type of the event
            title: Title of the event
            description: Description of the event
            metadata: Additional metadata
            parent_id: ID of the parent event
            tags: Tags for the event
            
        Returns:
            Optional[str]: ID of the started event, or None if the timeline was not found
        """
        # Get or create tracker
        tracker = self._get_or_create_tracker(timeline_id)
        if not tracker:
            return None
        
        # Start event
        return tracker.start_event(
            event_type=event_type,
            title=title,
            description=description,
            metadata=metadata,
            parent_id=parent_id,
            tags=tags
        )
    
    def end_event(
        self,
        timeline_id: str,
        event_id: str,
        status: str = "completed",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[float]:
        """
        End an event in a timeline.
        
        Args:
            timeline_id: ID of the timeline
            event_id: ID of the event to end
            status: Final status of the event
            metadata: Additional metadata
            
        Returns:
            Optional[float]: Duration of the event in seconds, or None if the timeline or event was not found
        """
        # Get tracker
        if timeline_id not in self.active_trackers:
            return None
        
        tracker = self.active_trackers[timeline_id]
        
        # End event
        return tracker.end_event(
            event_id=event_id,
            status=status,
            metadata=metadata
        )
    
    def update_event(
        self,
        timeline_id: str,
        event_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Update an event in a timeline.
        
        Args:
            timeline_id: ID of the timeline
            event_id: ID of the event to update
            title: New title
            description: New description
            metadata: Additional metadata
            status: New status
            tags: New tags
            
        Returns:
            bool: True if the event was updated, False otherwise
        """
        # Get tracker
        if timeline_id not in self.active_trackers:
            # Load timeline
            timeline = self.storage.load_timeline(timeline_id)
            if not timeline:
                return False
            
            # Create tracker
            tracker = TimelineTracker(
                storage=self.storage,
                auto_save=True
            )
            tracker.timeline = timeline
            
            # Add to active trackers
            self.active_trackers[timeline_id] = tracker
        else:
            tracker = self.active_trackers[timeline_id]
        
        # Update event
        return tracker.update_event(
            event_id=event_id,
            title=title,
            description=description,
            metadata=metadata,
            status=status,
            tags=tags
        )
    
    def delete_timeline(self, timeline_id: str) -> bool:
        """
        Delete a timeline.
        
        Args:
            timeline_id: ID of the timeline to delete
            
        Returns:
            bool: True if the timeline was deleted, False otherwise
        """
        # Remove from active trackers
        if timeline_id in self.active_trackers:
            del self.active_trackers[timeline_id]
        
        # Delete from storage
        return self.storage.delete_timeline(timeline_id)
    
    def list_timelines(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List timelines.
        
        Args:
            conversation_id: Filter by conversation ID
            user_id: Filter by user ID
            
        Returns:
            List[Dict[str, Any]]: List of timeline metadata
        """
        return self.storage.list_timelines(
            conversation_id=conversation_id,
            user_id=user_id
        )
    
    def _get_or_create_tracker(self, timeline_id: str) -> Optional[TimelineTracker]:
        """
        Get or create a tracker for a timeline.
        
        Args:
            timeline_id: ID of the timeline
            
        Returns:
            Optional[TimelineTracker]: Tracker for the timeline, or None if the timeline was not found
        """
        # Check if tracker exists
        if timeline_id in self.active_trackers:
            return self.active_trackers[timeline_id]
        
        # Load timeline
        timeline = self.storage.load_timeline(timeline_id)
        if not timeline:
            return None
        
        # Create tracker
        tracker = TimelineTracker(
            storage=self.storage,
            conversation_id=timeline.conversation_id,
            user_id=timeline.user_id,
            auto_save=True
        )
        tracker.timeline = timeline
        
        # Add to active trackers
        self.active_trackers[timeline_id] = tracker
        
        return tracker
