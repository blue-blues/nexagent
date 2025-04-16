"""
Timeline Module

This module provides a timeline feature for tracking and visualizing events
in the agent's execution. It allows for detailed tracking of agent activities,
tool calls, and other events, with support for nested events and duration tracking.
"""

from app.timeline.models import Timeline, TimelineEvent, EventType
from app.timeline.tracker import TimelineTracker
from app.timeline.storage import TimelineStorage, FileTimelineStorage, SQLiteTimelineStorage
from app.timeline.api import TimelineAPI
from app.timeline.visualization import TimelineFormatter

__all__ = [
    'Timeline',
    'TimelineEvent',
    'EventType',
    'TimelineTracker',
    'TimelineStorage',
    'FileTimelineStorage',
    'SQLiteTimelineStorage',
    'TimelineAPI',
    'TimelineFormatter'
]