"""
Timeline Visualization Module

This module provides utilities for visualizing timelines.
"""

import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

from app.timeline.models import Timeline, TimelineEvent, EventType


class TimelineFormatter:
    """
    Class for formatting timelines for visualization.
    
    This class provides utilities for converting timelines to formats
    suitable for visualization in different contexts.
    """
    
    @staticmethod
    def format_for_console(timeline: Timeline) -> str:
        """
        Format a timeline for console output.
        
        Args:
            timeline: Timeline to format
            
        Returns:
            str: Formatted timeline
        """
        output = []
        
        # Add header
        output.append(f"Timeline: {timeline.timeline_id}")
        output.append(f"Conversation: {timeline.conversation_id}")
        output.append(f"User: {timeline.user_id}")
        output.append(f"Created: {timeline.created_at.isoformat()}")
        output.append(f"Updated: {timeline.updated_at.isoformat()}")
        output.append(f"Events: {len(timeline.events)}")
        output.append("")
        
        # Add events
        def format_event(event: TimelineEvent, level: int = 0):
            indent = "  " * level
            duration_str = f" ({event.duration:.2f}s)" if event.duration else ""
            status_str = f" [{event.status}]" if event.status else ""
            
            output.append(f"{indent}{event.timestamp.isoformat()} - {event.event_type}: {event.title}{duration_str}{status_str}")
            output.append(f"{indent}  {event.description}")
            
            if event.tags:
                output.append(f"{indent}  Tags: {', '.join(event.tags)}")
            
            if event.metadata:
                output.append(f"{indent}  Metadata: {json.dumps(event.metadata, indent=2)}")
            
            if event.children:
                for child in event.children:
                    format_event(child, level + 1)
        
        for event in timeline.events:
            format_event(event)
        
        return "\n".join(output)
    
    @staticmethod
    def format_for_html(timeline: Timeline) -> str:
        """
        Format a timeline for HTML output.
        
        Args:
            timeline: Timeline to format
            
        Returns:
            str: HTML representation of the timeline
        """
        html = []
        
        # Add header
        html.append("<div class='timeline-container'>")
        html.append(f"<h2>Timeline: {timeline.timeline_id}</h2>")
        html.append("<div class='timeline-info'>")
        html.append(f"<p><strong>Conversation:</strong> {timeline.conversation_id}</p>")
        html.append(f"<p><strong>User:</strong> {timeline.user_id}</p>")
        html.append(f"<p><strong>Created:</strong> {timeline.created_at.isoformat()}</p>")
        html.append(f"<p><strong>Updated:</strong> {timeline.updated_at.isoformat()}</p>")
        html.append(f"<p><strong>Events:</strong> {len(timeline.events)}</p>")
        html.append("</div>")
        
        # Add events
        html.append("<div class='timeline-events'>")
        
        def format_event(event: TimelineEvent):
            event_class = f"timeline-event-{event.event_type}"
            status_class = f"timeline-status-{event.status}" if event.status else ""
            
            duration_str = f"<span class='timeline-duration'>{event.duration:.2f}s</span>" if event.duration else ""
            status_str = f"<span class='timeline-status'>{event.status}</span>" if event.status else ""
            
            html.append(f"<div class='timeline-event {event_class} {status_class}'>")
            html.append(f"<div class='timeline-event-header'>")
            html.append(f"<span class='timeline-timestamp'>{event.timestamp.isoformat()}</span>")
            html.append(f"<span class='timeline-event-type'>{event.event_type}</span>")
            html.append(f"<span class='timeline-title'>{event.title}</span>")
            html.append(f"{duration_str}")
            html.append(f"{status_str}")
            html.append("</div>")
            
            html.append(f"<div class='timeline-description'>{event.description}</div>")
            
            if event.tags:
                html.append("<div class='timeline-tags'>")
                for tag in event.tags:
                    html.append(f"<span class='timeline-tag'>{tag}</span>")
                html.append("</div>")
            
            if event.metadata:
                html.append("<div class='timeline-metadata'>")
                html.append("<pre>")
                html.append(json.dumps(event.metadata, indent=2))
                html.append("</pre>")
                html.append("</div>")
            
            if event.children:
                html.append("<div class='timeline-children'>")
                for child in event.children:
                    format_event(child)
                html.append("</div>")
            
            html.append("</div>")
        
        for event in timeline.events:
            format_event(event)
        
        html.append("</div>")
        html.append("</div>")
        
        return "\n".join(html)
    
    @staticmethod
    def format_for_json(timeline: Timeline) -> Dict[str, Any]:
        """
        Format a timeline for JSON output.
        
        Args:
            timeline: Timeline to format
            
        Returns:
            Dict[str, Any]: JSON-serializable representation of the timeline
        """
        return timeline.to_dict()
    
    @staticmethod
    def format_for_chart(timeline: Timeline) -> Dict[str, Any]:
        """
        Format a timeline for chart visualization.
        
        Args:
            timeline: Timeline to format
            
        Returns:
            Dict[str, Any]: Chart data for the timeline
        """
        # Collect all events with duration
        events_with_duration = []
        
        def collect_events(event_list: List[TimelineEvent]):
            for event in event_list:
                if event.duration is not None:
                    events_with_duration.append(event)
                
                if event.children:
                    collect_events(event.children)
        
        collect_events(timeline.events)
        
        # Sort events by start time
        events_with_duration.sort(key=lambda e: e.timestamp)
        
        # Create chart data
        chart_data = {
            "timeline_id": timeline.timeline_id,
            "labels": [],
            "datasets": [
                {
                    "label": "Event Duration",
                    "data": [],
                    "backgroundColor": []
                }
            ]
        }
        
        # Color map for event types
        color_map = {
            "agent_start": "rgba(75, 192, 192, 0.6)",
            "agent_stop": "rgba(255, 99, 132, 0.6)",
            "agent_error": "rgba(255, 99, 132, 0.6)",
            "agent_thinking": "rgba(54, 162, 235, 0.6)",
            "agent_response": "rgba(153, 102, 255, 0.6)",
            "user_message": "rgba(255, 159, 64, 0.6)",
            "tool_call": "rgba(255, 205, 86, 0.6)",
            "tool_result": "rgba(201, 203, 207, 0.6)",
            "plan_created": "rgba(75, 192, 192, 0.6)",
            "plan_updated": "rgba(54, 162, 235, 0.6)",
            "plan_executed": "rgba(153, 102, 255, 0.6)",
            "task_started": "rgba(255, 159, 64, 0.6)",
            "task_completed": "rgba(75, 192, 192, 0.6)",
            "task_failed": "rgba(255, 99, 132, 0.6)",
            "code_generated": "rgba(54, 162, 235, 0.6)",
            "code_executed": "rgba(153, 102, 255, 0.6)",
            "web_browsing": "rgba(255, 159, 64, 0.6)",
            "context_updated": "rgba(201, 203, 207, 0.6)",
            "custom": "rgba(201, 203, 207, 0.6)"
        }
        
        # Add events to chart data
        for event in events_with_duration:
            chart_data["labels"].append(event.title)
            chart_data["datasets"][0]["data"].append(event.duration)
            
            # Get color for event type
            color = color_map.get(event.event_type, "rgba(201, 203, 207, 0.6)")
            chart_data["datasets"][0]["backgroundColor"].append(color)
        
        return chart_data
    
    @staticmethod
    def format_for_gantt(timeline: Timeline) -> Dict[str, Any]:
        """
        Format a timeline for Gantt chart visualization.
        
        Args:
            timeline: Timeline to format
            
        Returns:
            Dict[str, Any]: Gantt chart data for the timeline
        """
        # Collect all events with duration
        events_with_duration = []
        
        def collect_events(event_list: List[TimelineEvent], parent_id: Optional[str] = None):
            for event in event_list:
                if event.duration is not None:
                    events_with_duration.append({
                        "id": event.event_id,
                        "title": event.title,
                        "start": event.timestamp,
                        "end": event.timestamp + timedelta(seconds=event.duration),
                        "parent_id": parent_id,
                        "event_type": event.event_type,
                        "status": event.status
                    })
                
                if event.children:
                    collect_events(event.children, event.event_id)
        
        collect_events(timeline.events)
        
        # Create gantt data
        gantt_data = {
            "timeline_id": timeline.timeline_id,
            "tasks": []
        }
        
        # Add events to gantt data
        for event in events_with_duration:
            gantt_data["tasks"].append({
                "id": event["id"],
                "title": event["title"],
                "start": event["start"].isoformat(),
                "end": event["end"].isoformat(),
                "parent_id": event["parent_id"],
                "event_type": event["event_type"],
                "status": event["status"]
            })
        
        return gantt_data
