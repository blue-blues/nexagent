"""
Tests for the Web Browsing History UI Component.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.ui.web_browsing_history_component import WebBrowsingHistoryComponent, WebPageBookmark


class TestWebBrowsingHistoryComponent(unittest.TestCase):
    """Tests for the Web Browsing History UI Component."""

    def setUp(self):
        """Set up test fixtures."""
        self.component = WebBrowsingHistoryComponent()
        
        # Mock timeline storage
        self.mock_storage = MagicMock()
        self.component.set_timeline_storage(self.mock_storage)
        
        # Mock timeline
        self.mock_timeline = MagicMock()
        self.mock_timeline.timeline_id = "test_timeline"
        self.mock_timeline.conversation_id = "test_conversation"
        self.mock_timeline.events = []
        
        # Mock event
        self.mock_event = MagicMock()
        self.mock_event.event_id = "test_event"
        self.mock_event.event_type = "web_browsing"
        self.mock_event.timestamp = datetime.now()
        self.mock_event.title = "Test Web Page"
        self.mock_event.description = "Visited test web page"
        self.mock_event.metadata = {
            "url": "https://example.com",
            "action": "visit"
        }
        
        # Add event to timeline
        self.mock_timeline.events.append(self.mock_event)
        
        # Configure mock storage to return mock timeline
        self.mock_storage.load_timeline.return_value = self.mock_timeline
        self.mock_storage.list_timelines.return_value = [{"timeline_id": "test_timeline"}]

    def test_set_timeline_storage(self):
        """Test setting timeline storage."""
        # Already set in setUp
        self.assertEqual(self.component.timeline_storage, self.mock_storage)

    def test_set_current_timeline(self):
        """Test setting current timeline."""
        result = self.component.set_current_timeline("test_timeline")
        self.assertTrue(result)
        self.assertEqual(self.component.current_timeline_id, "test_timeline")
        self.assertEqual(self.component.current_conversation_id, "test_conversation")
        
        # Test with invalid timeline ID
        self.mock_storage.load_timeline.return_value = None
        result = self.component.set_current_timeline("invalid_timeline")
        self.assertFalse(result)

    def test_set_current_conversation(self):
        """Test setting current conversation."""
        result = self.component.set_current_conversation("test_conversation")
        self.assertTrue(result)
        self.assertEqual(self.component.current_conversation_id, "test_conversation")
        self.assertEqual(self.component.current_timeline_id, "test_timeline")
        
        # Test with invalid conversation ID
        self.mock_storage.list_timelines.return_value = []
        result = self.component.set_current_conversation("invalid_conversation")
        self.assertFalse(result)

    def test_get_browsing_history(self):
        """Test getting browsing history."""
        # Set current timeline
        self.component.set_current_timeline("test_timeline")
        
        # Get browsing history
        history = self.component.get_browsing_history()
        
        # Check result
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["event_id"], "test_event")
        self.assertEqual(history[0]["url"], "https://example.com")
        self.assertEqual(history[0]["action"], "visit")
        
        # Test with filters
        history = self.component.get_browsing_history(filter_by_domain="example.com")
        self.assertEqual(len(history), 1)
        
        history = self.component.get_browsing_history(filter_by_domain="invalid.com")
        self.assertEqual(len(history), 0)
        
        history = self.component.get_browsing_history(filter_by_action="visit")
        self.assertEqual(len(history), 1)
        
        history = self.component.get_browsing_history(filter_by_action="click")
        self.assertEqual(len(history), 0)

    def test_search_history(self):
        """Test searching browsing history."""
        # Set current timeline
        self.component.set_current_timeline("test_timeline")
        
        # Search history
        results = self.component.search_history("example")
        
        # Check result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://example.com")
        
        # Test with no results
        results = self.component.search_history("invalid")
        self.assertEqual(len(results), 0)

    def test_bookmarks(self):
        """Test bookmark functionality."""
        # Add bookmark
        bookmark_id = self.component.add_bookmark(
            url="https://example.com",
            title="Example Website",
            description="An example website",
            tags=["example", "test"]
        )
        
        # Check bookmark was added
        self.assertIn(bookmark_id, self.component.bookmarks)
        
        # Get bookmarks
        bookmarks = self.component.get_bookmarks()
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0].url, "https://example.com")
        self.assertEqual(bookmarks[0].title, "Example Website")
        
        # Get bookmarks by tag
        bookmarks = self.component.get_bookmarks(tag="example")
        self.assertEqual(len(bookmarks), 1)
        
        bookmarks = self.component.get_bookmarks(tag="invalid")
        self.assertEqual(len(bookmarks), 0)
        
        # Remove bookmark
        result = self.component.remove_bookmark(bookmark_id)
        self.assertTrue(result)
        self.assertEqual(len(self.component.bookmarks), 0)
        
        # Try to remove non-existent bookmark
        result = self.component.remove_bookmark("invalid_id")
        self.assertFalse(result)

    def test_export_history(self):
        """Test exporting browsing history."""
        # Set current timeline
        self.component.set_current_timeline("test_timeline")
        
        # Export history in different formats
        json_export = self.component.export_history(format="json")
        self.assertIn("https://example.com", json_export)
        
        csv_export = self.component.export_history(format="csv")
        self.assertIn("https://example.com", csv_export)
        
        md_export = self.component.export_history(format="markdown")
        self.assertIn("https://example.com", md_export)
        
        # Test with invalid format
        invalid_export = self.component.export_history(format="invalid")
        self.assertIn("Unsupported export format", invalid_export)

    def test_render_timeline(self):
        """Test rendering timeline."""
        # Set current timeline
        self.component.set_current_timeline("test_timeline")
        
        # Render timeline
        timeline = self.component.render_timeline()
        
        # Check result
        self.assertIn("Web Browsing History", timeline)
        self.assertIn("https://example.com", timeline)
        
        # Test with filters
        self.component.filter_domain = "example.com"
        timeline = self.component.render_timeline()
        self.assertIn("Filters: Domain: example.com", timeline)
        
        # Clear filters
        self.component.filter_domain = None
        
        # Test with no history
        self.mock_timeline.events = []
        timeline = self.component.render_timeline()
        self.assertIn("No browsing history available", timeline)

    def test_render_page_preview(self):
        """Test rendering page preview."""
        # Set current timeline
        self.component.set_current_timeline("test_timeline")
        
        # Render page preview
        preview = self.component.render_page_preview("test_event")
        
        # Check result
        self.assertIn("Test Web Page", preview)
        self.assertIn("https://example.com", preview)
        self.assertIn("+ Add Bookmark", preview)
        
        # Add bookmark and check preview again
        self.component.add_bookmark(
            url="https://example.com",
            title="Example Website"
        )
        
        preview = self.component.render_page_preview("test_event")
        self.assertIn("✓ Bookmarked", preview)
        
        # Test with invalid event ID
        preview = self.component.render_page_preview("invalid_event")
        self.assertIn("Event not found", preview)


if __name__ == "__main__":
    unittest.main()
