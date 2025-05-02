"""
CLI interface for the Web Browsing History UI Component.

This module provides a command-line interface for interacting with
the Web Browsing History UI Component.
"""

import argparse
import sys
from datetime import datetime
from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

from app.ui.web_browsing_history_component import web_browsing_history
from app.timeline.storage import FileTimelineStorage, SQLiteTimelineStorage
from app.logger import logger


class WebBrowsingHistoryCLI:
    """CLI interface for the Web Browsing History UI Component."""
    
    def __init__(self, storage_dir: Optional[str] = None, db_path: Optional[str] = None):
        """
        Initialize the CLI interface.
        
        Args:
            storage_dir: Directory for file-based timeline storage
            db_path: Path to SQLite database for timeline storage
        """
        self.session = PromptSession(
            history=InMemoryHistory(),
            style=Style.from_dict({
                'prompt': 'ansiblue bold',
                'command': 'ansiwhite',
            }),
            completer=WordCompleter([
                'help', 'list', 'view', 'search', 'filter', 'clear-filter',
                'bookmark', 'bookmarks', 'remove-bookmark', 'export', 'import',
                'set-timeline', 'set-conversation', 'preview', 'exit', 'quit'
            ])
        )
        self.running = False
        
        # Initialize storage
        if db_path:
            storage = SQLiteTimelineStorage(db_path)
            web_browsing_history.set_timeline_storage(storage)
            logger.info(f"Using SQLite timeline storage: {db_path}")
        elif storage_dir:
            storage = FileTimelineStorage(storage_dir)
            web_browsing_history.set_timeline_storage(storage)
            logger.info(f"Using file-based timeline storage: {storage_dir}")
        else:
            logger.warning("No storage configured for Web Browsing History CLI")
    
    def start(self):
        """Start the CLI interface."""
        self.running = True
        print("Web Browsing History CLI")
        print("Type 'help' for a list of commands")
        
        while self.running:
            try:
                command = self.session.prompt("web-history> ")
                if command.strip():
                    result = self.process_command(command)
                    if result:
                        print(result)
            except KeyboardInterrupt:
                print("Use 'exit' or 'quit' to exit")
            except EOFError:
                self.running = False
                print("Exiting...")
    
    def process_command(self, command: str) -> str:
        """
        Process a command.
        
        Args:
            command: The command to process
            
        Returns:
            The result of the command
        """
        if command in ["exit", "quit"]:
            self.running = False
            return "Exiting..."
        
        elif command == "help":
            return self._get_help_text()
        
        elif command == "list":
            # List browsing history
            history = web_browsing_history.get_browsing_history(max_entries=10)
            if not history:
                return "No browsing history available."
            
            result = ["Recent browsing history:"]
            for entry in history:
                timestamp = entry['timestamp']
                if isinstance(timestamp, datetime):
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    time_str = str(timestamp)
                result.append(f"{time_str} - {entry['title']} ({entry['url']})")
            
            return "\n".join(result)
        
        elif command.startswith("view"):
            # Render timeline
            return web_browsing_history.render_timeline()
        
        elif command.startswith("search "):
            # Search history
            query = command[7:].strip()
            if not query:
                return "Please provide a search query"
            
            results = web_browsing_history.search_history(query)
            if not results:
                return f"No results found for '{query}'"
            
            result_lines = [f"Search results for '{query}':"]
            for entry in results:
                timestamp = entry['timestamp']
                if isinstance(timestamp, datetime):
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    time_str = str(timestamp)
                result_lines.append(f"{time_str} - {entry['title']} ({entry['url']})")
            
            return "\n".join(result_lines)
        
        elif command.startswith("filter"):
            # Apply filters
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return "Please specify filter criteria (domain, action, date-start, date-end)"
            
            filter_args = parts[1].strip()
            filter_parts = filter_args.split(" ")
            
            for part in filter_parts:
                if "=" not in part:
                    continue
                
                key, value = part.split("=", 1)
                
                if key == "domain":
                    web_browsing_history.filter_domain = value
                elif key == "action":
                    web_browsing_history.filter_action = value
                elif key == "date-start":
                    try:
                        web_browsing_history.filter_date_start = datetime.fromisoformat(value)
                    except ValueError:
                        return f"Invalid date format for date-start: {value}. Use YYYY-MM-DD."
                elif key == "date-end":
                    try:
                        web_browsing_history.filter_date_end = datetime.fromisoformat(value)
                    except ValueError:
                        return f"Invalid date format for date-end: {value}. Use YYYY-MM-DD."
            
            # List active filters
            filters = []
            if web_browsing_history.filter_domain:
                filters.append(f"domain={web_browsing_history.filter_domain}")
            if web_browsing_history.filter_action:
                filters.append(f"action={web_browsing_history.filter_action}")
            if web_browsing_history.filter_date_start:
                filters.append(f"date-start={web_browsing_history.filter_date_start.strftime('%Y-%m-%d')}")
            if web_browsing_history.filter_date_end:
                filters.append(f"date-end={web_browsing_history.filter_date_end.strftime('%Y-%m-%d')}")
            
            return "Filters applied: " + ", ".join(filters)
        
        elif command == "clear-filter":
            # Clear all filters
            web_browsing_history.filter_domain = None
            web_browsing_history.filter_action = None
            web_browsing_history.filter_date_start = None
            web_browsing_history.filter_date_end = None
            
            return "All filters cleared"
        
        elif command.startswith("bookmark "):
            # Add bookmark
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return "Please provide URL and title for bookmark"
            
            bookmark_args = parts[1].strip()
            
            # Parse URL and title
            if " " not in bookmark_args:
                return "Please provide both URL and title for bookmark"
            
            url, title = bookmark_args.split(" ", 1)
            
            # Add bookmark
            bookmark_id = web_browsing_history.add_bookmark(url=url, title=title)
            
            return f"Bookmark added: {title} ({url})"
        
        elif command == "bookmarks":
            # List bookmarks
            bookmarks = web_browsing_history.get_bookmarks()
            if not bookmarks:
                return "No bookmarks available."
            
            result = ["Bookmarks:"]
            for bookmark in bookmarks:
                result.append(f"{bookmark.title} ({bookmark.url})")
                if bookmark.tags:
                    result.append(f"  Tags: {', '.join(bookmark.tags)}")
            
            return "\n".join(result)
        
        elif command.startswith("remove-bookmark "):
            # Remove bookmark
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return "Please provide bookmark ID or URL to remove"
            
            bookmark_id_or_url = parts[1].strip()
            
            # Find bookmark by ID or URL
            bookmarks = web_browsing_history.get_bookmarks()
            bookmark_to_remove = None
            
            for bookmark in bookmarks:
                if bookmark.id == bookmark_id_or_url or bookmark.url == bookmark_id_or_url:
                    bookmark_to_remove = bookmark
                    break
            
            if not bookmark_to_remove:
                return f"Bookmark not found: {bookmark_id_or_url}"
            
            # Remove bookmark
            success = web_browsing_history.remove_bookmark(bookmark_to_remove.id)
            
            if success:
                return f"Bookmark removed: {bookmark_to_remove.title} ({bookmark_to_remove.url})"
            else:
                return f"Failed to remove bookmark: {bookmark_id_or_url}"
        
        elif command.startswith("export "):
            # Export history
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return "Please specify export format (json, csv, markdown)"
            
            export_format = parts[1].strip().lower()
            if export_format not in ["json", "csv", "markdown"]:
                return f"Unsupported export format: {export_format}. Use json, csv, or markdown."
            
            # Export history
            exported_data = web_browsing_history.export_history(format=export_format)
            
            # In a real CLI, we would save this to a file
            # For now, just return the first few lines
            lines = exported_data.split("\n")
            preview = "\n".join(lines[:10])
            if len(lines) > 10:
                preview += "\n... (output truncated)"
            
            return f"Exported history in {export_format} format:\n\n{preview}"
        
        elif command.startswith("set-timeline "):
            # Set current timeline
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return "Please provide timeline ID"
            
            timeline_id = parts[1].strip()
            
            # Set timeline
            success = web_browsing_history.set_current_timeline(timeline_id)
            
            if success:
                return f"Current timeline set: {timeline_id}"
            else:
                return f"Failed to set timeline: {timeline_id}"
        
        elif command.startswith("set-conversation "):
            # Set current conversation
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return "Please provide conversation ID"
            
            conversation_id = parts[1].strip()
            
            # Set conversation
            success = web_browsing_history.set_current_conversation(conversation_id)
            
            if success:
                return f"Current conversation set: {conversation_id}"
            else:
                return f"Failed to set conversation: {conversation_id}"
        
        elif command.startswith("preview "):
            # Preview web page
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return "Please provide event ID to preview"
            
            event_id = parts[1].strip()
            
            # Render preview
            return web_browsing_history.render_page_preview(event_id)
        
        else:
            return f"Unknown command: {command}\nType 'help' for a list of commands"
    
    def _get_help_text(self) -> str:
        """
        Get help text for the CLI.
        
        Returns:
            Help text
        """
        return """
Web Browsing History CLI Commands:

General:
  help                      Show this help text
  exit, quit                Exit the CLI

Browsing History:
  list                      List recent browsing history
  view                      View browsing history timeline
  search <query>            Search browsing history
  filter <criteria>         Apply filters to browsing history
                            Criteria: domain=<domain> action=<action> date-start=<YYYY-MM-DD> date-end=<YYYY-MM-DD>
  clear-filter              Clear all filters
  preview <event_id>        Preview a web page

Bookmarks:
  bookmark <url> <title>    Add a bookmark
  bookmarks                 List all bookmarks
  remove-bookmark <id|url>  Remove a bookmark

Import/Export:
  export <format>           Export browsing history (json, csv, markdown)
  import <format> <file>    Import browsing history (not implemented)

Timeline Management:
  set-timeline <id>         Set the current timeline
  set-conversation <id>     Set the current conversation
"""


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Web Browsing History CLI")
    parser.add_argument("--storage-dir", help="Directory for file-based timeline storage")
    parser.add_argument("--db-path", help="Path to SQLite database for timeline storage")
    
    args = parser.parse_args()
    
    cli = WebBrowsingHistoryCLI(
        storage_dir=args.storage_dir,
        db_path=args.db_path
    )
    
    cli.start()


if __name__ == "__main__":
    main()
