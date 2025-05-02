"""
Web Browsing History UI Component for Nexagent.

This module provides a UI component for displaying and interacting with
web browsing history, including timeline view, page previews, search,
filtering, bookmarking, and export/import capabilities.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable

from pydantic import BaseModel, Field

from app.timeline.models import Timeline, TimelineEvent, EventType
from app.timeline.storage import TimelineStorage
from app.logger import logger


class WebPageBookmark(BaseModel):
    """Represents a bookmarked web page."""

    id: str = Field(default_factory=lambda: f"bookmark_{datetime.now().timestamp()}")
    url: str
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class WebBrowsingHistoryComponent(BaseModel):
    """
    Web Browsing History UI Component with advanced features.

    This component provides a rich interface for viewing and interacting with
    web browsing history, including timeline view, page previews, search,
    filtering, bookmarking, and export/import capabilities.
    """

    # Configuration
    model_config = {"arbitrary_types_allowed": True}

    # Storage
    timeline_storage: Optional[TimelineStorage] = None
    
    # State
    current_timeline_id: Optional[str] = None
    current_conversation_id: Optional[str] = None
    
    # Filtering
    filter_date_start: Optional[datetime] = None
    filter_date_end: Optional[datetime] = None
    filter_domain: Optional[str] = None
    filter_action: Optional[str] = None
    
    # Search
    search_query: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Bookmarks
    bookmarks: Dict[str, WebPageBookmark] = Field(default_factory=dict)

    def __init__(self, **data):
        """Initialize the component."""
        super().__init__(**data)
        logger.info("Web Browsing History Component initialized")

    def set_timeline_storage(self, storage: TimelineStorage) -> None:
        """
        Set the timeline storage to use.

        Args:
            storage: The timeline storage to use
        """
        self.timeline_storage = storage
        logger.info(f"Timeline storage set: {storage.__class__.__name__}")

    def set_current_timeline(self, timeline_id: str) -> bool:
        """
        Set the current timeline to display.

        Args:
            timeline_id: ID of the timeline to display

        Returns:
            bool: True if the timeline was set successfully, False otherwise
        """
        if not self.timeline_storage:
            logger.warning("Cannot set timeline: No storage configured")
            return False

        # Try to load the timeline
        timeline = self.timeline_storage.load_timeline(timeline_id)
        if not timeline:
            logger.warning(f"Timeline not found: {timeline_id}")
            return False

        self.current_timeline_id = timeline_id
        self.current_conversation_id = timeline.conversation_id
        logger.info(f"Current timeline set: {timeline_id}")
        return True

    def set_current_conversation(self, conversation_id: str) -> bool:
        """
        Set the current conversation to display timelines for.

        Args:
            conversation_id: ID of the conversation

        Returns:
            bool: True if the conversation was set successfully, False otherwise
        """
        if not self.timeline_storage:
            logger.warning("Cannot set conversation: No storage configured")
            return False

        # List timelines for this conversation
        timelines = self.timeline_storage.list_timelines(conversation_id=conversation_id)
        if not timelines:
            logger.warning(f"No timelines found for conversation: {conversation_id}")
            return False

        self.current_conversation_id = conversation_id
        
        # Set the most recent timeline as current
        if timelines:
            self.current_timeline_id = timelines[0].get("timeline_id")
            
        logger.info(f"Current conversation set: {conversation_id}")
        return True

    def get_browsing_history(self, 
                            max_entries: Optional[int] = None,
                            filter_by_domain: Optional[str] = None,
                            filter_by_action: Optional[str] = None,
                            filter_by_date_start: Optional[datetime] = None,
                            filter_by_date_end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get web browsing history from the current timeline.

        Args:
            max_entries: Maximum number of entries to return
            filter_by_domain: Filter by domain
            filter_by_action: Filter by action type
            filter_by_date_start: Filter by start date
            filter_by_date_end: Filter by end date

        Returns:
            List of web browsing history entries
        """
        if not self.timeline_storage or not self.current_timeline_id:
            logger.warning("Cannot get browsing history: No timeline set")
            return []

        # Load the timeline
        timeline = self.timeline_storage.load_timeline(self.current_timeline_id)
        if not timeline:
            logger.warning(f"Timeline not found: {self.current_timeline_id}")
            return []

        # Filter web browsing events
        browsing_events = []
        
        for event in timeline.events:
            # Check if this is a web browsing event
            if event.event_type == "web_browsing" or event.event_type == "WEB_BROWSE":
                # Apply filters
                if filter_by_domain and filter_by_domain not in event.metadata.get("url", ""):
                    continue
                    
                if filter_by_action and filter_by_action != event.metadata.get("action", ""):
                    continue
                    
                event_time = event.timestamp
                if filter_by_date_start and event_time < filter_by_date_start:
                    continue
                    
                if filter_by_date_end and event_time > filter_by_date_end:
                    continue
                
                # Add to results
                browsing_events.append({
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "title": event.title,
                    "description": event.description,
                    "url": event.metadata.get("url", ""),
                    "action": event.metadata.get("action", ""),
                    "metadata": event.metadata
                })

        # Sort by timestamp (newest first)
        browsing_events.sort(key=lambda e: e["timestamp"], reverse=True)
        
        # Limit number of entries if specified
        if max_entries is not None:
            browsing_events = browsing_events[:max_entries]
            
        return browsing_events

    def search_history(self, query: str) -> List[Dict[str, Any]]:
        """
        Search in browsing history.

        Args:
            query: The search query

        Returns:
            List of search results
        """
        self.search_query = query
        self.search_results = []

        if not query:
            return []

        # Get all browsing history
        all_history = self.get_browsing_history()
        
        # Search in history
        for entry in all_history:
            if (query.lower() in entry["url"].lower() or
                query.lower() in entry["title"].lower() or
                query.lower() in entry["description"].lower()):
                self.search_results.append(entry)
        
        return self.search_results

    def add_bookmark(self, url: str, title: str, description: Optional[str] = None, tags: Optional[List[str]] = None) -> str:
        """
        Add a bookmark.

        Args:
            url: URL of the page to bookmark
            title: Title of the page
            description: Optional description
            tags: Optional tags

        Returns:
            ID of the created bookmark
        """
        bookmark = WebPageBookmark(
            url=url,
            title=title,
            description=description,
            tags=tags or []
        )
        
        self.bookmarks[bookmark.id] = bookmark
        logger.info(f"Bookmark added: {title} ({url})")
        
        return bookmark.id

    def remove_bookmark(self, bookmark_id: str) -> bool:
        """
        Remove a bookmark.

        Args:
            bookmark_id: ID of the bookmark to remove

        Returns:
            True if the bookmark was removed, False otherwise
        """
        if bookmark_id not in self.bookmarks:
            return False
            
        bookmark = self.bookmarks.pop(bookmark_id)
        logger.info(f"Bookmark removed: {bookmark.title} ({bookmark.url})")
        
        return True

    def get_bookmarks(self, tag: Optional[str] = None) -> List[WebPageBookmark]:
        """
        Get all bookmarks, optionally filtered by tag.

        Args:
            tag: Optional tag to filter by

        Returns:
            List of bookmarks
        """
        if not tag:
            return list(self.bookmarks.values())
            
        return [b for b in self.bookmarks.values() if tag in b.tags]

    def export_history(self, format: str = "json") -> str:
        """
        Export browsing history.

        Args:
            format: Export format ("json", "csv", "markdown")

        Returns:
            Exported history as a string
        """
        history = self.get_browsing_history()
        
        if format == "json":
            return json.dumps(history, default=str, indent=2)
            
        elif format == "csv":
            # Create CSV
            csv_lines = ["timestamp,title,url,action"]
            for entry in history:
                csv_lines.append(f"{entry['timestamp']},{entry['title']},{entry['url']},{entry['action']}")
            return "\n".join(csv_lines)
            
        elif format == "markdown":
            # Create Markdown
            md_lines = ["# Web Browsing History", "", "| Time | Title | URL | Action |", "| ---- | ----- | --- | ------ |"]
            for entry in history:
                timestamp = entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry['timestamp'], datetime) else entry['timestamp']
                md_lines.append(f"| {timestamp} | {entry['title']} | {entry['url']} | {entry['action']} |")
            return "\n".join(md_lines)
            
        else:
            return f"Unsupported export format: {format}"

    def import_history(self, data: str, format: str = "json") -> bool:
        """
        Import browsing history.

        Args:
            data: The data to import
            format: Import format ("json", "csv")

        Returns:
            True if the import was successful, False otherwise
        """
        # This would require creating new timeline events from the imported data
        # For now, just log that this feature is not implemented
        logger.warning("History import not implemented yet")
        return False

    def render_timeline(self) -> str:
        """
        Render the browsing history timeline.

        Returns:
            Rendered timeline
        """
        history = self.get_browsing_history(
            filter_by_domain=self.filter_domain,
            filter_by_action=self.filter_action,
            filter_by_date_start=self.filter_date_start,
            filter_by_date_end=self.filter_date_end
        )
        
        if not history:
            return "No browsing history available."
            
        # Build the timeline
        output = []
        output.append("# Web Browsing History")
        output.append("")
        
        # Add filters if applied
        filters_applied = []
        if self.filter_domain:
            filters_applied.append(f"Domain: {self.filter_domain}")
        if self.filter_action:
            filters_applied.append(f"Action: {self.filter_action}")
        if self.filter_date_start:
            filters_applied.append(f"From: {self.filter_date_start.strftime('%Y-%m-%d')}")
        if self.filter_date_end:
            filters_applied.append(f"To: {self.filter_date_end.strftime('%Y-%m-%d')}")
            
        if filters_applied:
            output.append("Filters: " + ", ".join(filters_applied))
            output.append("")
        
        # Group by date
        history_by_date = {}
        for entry in history:
            timestamp = entry['timestamp']
            if isinstance(timestamp, datetime):
                date_str = timestamp.strftime("%Y-%m-%d")
            else:
                # Handle string timestamps
                try:
                    date_str = datetime.fromisoformat(str(timestamp).split('T')[0]).strftime("%Y-%m-%d")
                except:
                    date_str = "Unknown Date"
                    
            if date_str not in history_by_date:
                history_by_date[date_str] = []
                
            history_by_date[date_str].append(entry)
        
        # Sort dates (newest first)
        sorted_dates = sorted(history_by_date.keys(), reverse=True)
        
        # Add entries by date
        for date_str in sorted_dates:
            output.append(f"## {date_str}")
            output.append("")
            
            entries = history_by_date[date_str]
            for entry in entries:
                timestamp = entry['timestamp']
                if isinstance(timestamp, datetime):
                    time_str = timestamp.strftime("%H:%M:%S")
                else:
                    # Handle string timestamps
                    try:
                        time_str = str(timestamp).split('T')[1].split('.')[0]
                    except:
                        time_str = "Unknown Time"
                        
                output.append(f"### {time_str} - {entry['title']}")
                output.append(f"URL: {entry['url']}")
                output.append(f"Action: {entry['action']}")
                
                if entry.get('description'):
                    output.append(f"Description: {entry['description']}")
                    
                output.append("")
        
        return "\n".join(output)

    def render_page_preview(self, event_id: str) -> str:
        """
        Render a preview of a web page.

        Args:
            event_id: ID of the event to preview

        Returns:
            Rendered preview
        """
        if not self.timeline_storage or not self.current_timeline_id:
            return "Cannot render preview: No timeline set"

        # Load the timeline
        timeline = self.timeline_storage.load_timeline(self.current_timeline_id)
        if not timeline:
            return f"Timeline not found: {self.current_timeline_id}"

        # Find the event
        event = None
        for e in timeline.events:
            if e.event_id == event_id:
                event = e
                break
                
        if not event:
            return f"Event not found: {event_id}"
            
        # Build the preview
        output = []
        output.append(f"# {event.title}")
        output.append("")
        output.append(f"URL: {event.metadata.get('url', 'Unknown URL')}")
        output.append(f"Visited: {event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp}")
        output.append(f"Action: {event.metadata.get('action', 'Unknown Action')}")
        output.append("")
        
        if event.description:
            output.append("## Description")
            output.append(event.description)
            output.append("")
            
        # Add content preview if available
        if event.metadata.get('content_preview'):
            output.append("## Content Preview")
            output.append(event.metadata.get('content_preview'))
            output.append("")
            
        # Add screenshot if available
        if event.metadata.get('screenshot'):
            output.append("## Screenshot")
            output.append("[Screenshot available]")
            output.append("")
            
        # Add bookmark button
        is_bookmarked = any(b.url == event.metadata.get('url', '') for b in self.bookmarks.values())
        if is_bookmarked:
            output.append("✓ Bookmarked")
        else:
            output.append("+ Add Bookmark")
            
        return "\n".join(output)


# Create a singleton instance
web_browsing_history = WebBrowsingHistoryComponent()
