"""
Terminal UI Component for Nexagent.

This module provides a terminal UI component with features like syntax highlighting,
command history, autocomplete, code folding, and search/replace functionality.
"""

import os
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime

from pydantic import BaseModel, Field
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import TerminalFormatter
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from app.logger import logger


class TerminalTab(BaseModel):
    """Represents a single terminal tab."""

    id: str = Field(default_factory=lambda: f"tab_{datetime.now().timestamp()}")
    name: str
    working_directory: str = Field(default_factory=os.getcwd)
    command_history: List[str] = Field(default_factory=list)
    output_history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)


class TerminalUIComponent(BaseModel):
    """
    Terminal UI Component with advanced features.

    This component provides a rich terminal interface with syntax highlighting,
    command history, autocomplete, code folding, and search/replace functionality.
    """

    # Configuration
    model_config = {"arbitrary_types_allowed": True}

    # Terminal state
    tabs: Dict[str, TerminalTab] = Field(default_factory=dict)
    active_tab_id: Optional[str] = None

    # UI components
    history: Any = Field(default_factory=InMemoryHistory)
    session: Any = Field(default_factory=PromptSession)

    # Command suggestions
    command_completer: Any = Field(default=None)

    # Styling
    style: Any = Field(default=None)

    # Key bindings
    key_bindings: Any = Field(default=None)

    # Search state
    search_query: str = ""
    search_results: List[Dict[str, Any]] = Field(default_factory=list)

    # Code folding state
    folded_regions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_components()

    def _initialize_components(self):
        """Initialize UI components."""
        # Create default tab if none exists
        if not self.tabs:
            self.create_tab("Default")

        # Set active tab if not set
        if not self.active_tab_id and self.tabs:
            self.active_tab_id = next(iter(self.tabs.keys()))

        # Initialize command completer
        self.command_completer = WordCompleter([
            'cd', 'dir', 'ls', 'copy', 'move', 'del', 'mkdir', 'rmdir',
            'echo', 'type', 'more', 'find', 'where', 'help', 'python',
            'git', 'npm', 'pip', 'grep', 'cat', 'touch', 'code'
        ])

        # Initialize styling
        self.style = Style.from_dict({
            'prompt': 'ansigreen bold',
            'command': 'ansiwhite',
            'output': 'ansiwhite',
            'error': 'ansired',
            'info': 'ansiblue',
            'warning': 'ansiyellow',
            'path': 'ansiblue bold',
        })

        # Initialize key bindings
        self.key_bindings = KeyBindings()
        self._setup_key_bindings()

    def _setup_key_bindings(self):
        """Set up key bindings for the terminal."""
        kb = self.key_bindings

        @kb.add('c-f')
        def _(event):
            """Start search."""
            self.start_search(event)

        @kb.add('c-z')
        def _(event):
            """Fold/unfold code region."""
            self.toggle_fold(event)

        @kb.add('c-n')
        def _(event):
            """Switch to next tab."""
            self.next_tab()

        @kb.add('c-p')
        def _(event):
            """Switch to previous tab."""
            self.prev_tab()

    def create_tab(self, name: str) -> str:
        """
        Create a new terminal tab.

        Args:
            name: Name of the tab

        Returns:
            ID of the created tab
        """
        tab = TerminalTab(name=name)
        self.tabs[tab.id] = tab
        return tab.id

    def close_tab(self, tab_id: str) -> bool:
        """
        Close a terminal tab.

        Args:
            tab_id: ID of the tab to close

        Returns:
            True if tab was closed, False otherwise
        """
        if tab_id not in self.tabs:
            return False

        # Remove tab
        del self.tabs[tab_id]

        # Update active tab if needed
        if self.active_tab_id == tab_id:
            if self.tabs:
                self.active_tab_id = next(iter(self.tabs.keys()))
            else:
                self.active_tab_id = None

        return True

    def switch_tab(self, tab_id: str) -> bool:
        """
        Switch to a different tab.

        Args:
            tab_id: ID of the tab to switch to

        Returns:
            True if switch was successful, False otherwise
        """
        if tab_id not in self.tabs:
            return False

        self.active_tab_id = tab_id
        self.tabs[tab_id].last_active = datetime.now()
        return True

    def next_tab(self) -> str:
        """
        Switch to the next tab.

        Returns:
            ID of the new active tab
        """
        if not self.tabs:
            return None

        tab_ids = list(self.tabs.keys())
        if not self.active_tab_id or self.active_tab_id not in tab_ids:
            self.active_tab_id = tab_ids[0]
            return self.active_tab_id

        current_index = tab_ids.index(self.active_tab_id)
        next_index = (current_index + 1) % len(tab_ids)
        self.active_tab_id = tab_ids[next_index]
        self.tabs[self.active_tab_id].last_active = datetime.now()
        return self.active_tab_id

    def prev_tab(self) -> str:
        """
        Switch to the previous tab.

        Returns:
            ID of the new active tab
        """
        if not self.tabs:
            return None

        tab_ids = list(self.tabs.keys())
        if not self.active_tab_id or self.active_tab_id not in tab_ids:
            self.active_tab_id = tab_ids[-1]
            return self.active_tab_id

        current_index = tab_ids.index(self.active_tab_id)
        prev_index = (current_index - 1) % len(tab_ids)
        self.active_tab_id = tab_ids[prev_index]
        self.tabs[self.active_tab_id].last_active = datetime.now()
        return self.active_tab_id

    def get_active_tab(self) -> Optional[TerminalTab]:
        """
        Get the currently active tab.

        Returns:
            The active terminal tab, or None if no tab is active
        """
        if not self.active_tab_id or self.active_tab_id not in self.tabs:
            return None
        return self.tabs[self.active_tab_id]

    def add_command_to_history(self, command: str) -> None:
        """
        Add a command to the history of the active tab.

        Args:
            command: The command to add
        """
        tab = self.get_active_tab()
        if not tab:
            return

        tab.command_history.append(command)
        tab.last_active = datetime.now()

    def add_output_to_history(self, command: str, output: str, error: str = "", success: bool = True) -> None:
        """
        Add command output to the history of the active tab.

        Args:
            command: The command that was executed
            output: The command output
            error: Any error output
            success: Whether the command was successful
        """
        tab = self.get_active_tab()
        if not tab:
            return

        tab.output_history.append({
            "command": command,
            "output": output,
            "error": error,
            "success": success,
            "timestamp": datetime.now()
        })
        tab.last_active = datetime.now()

    def get_command_history(self, max_entries: Optional[int] = None) -> List[str]:
        """
        Get command history from the active tab.

        Args:
            max_entries: Maximum number of entries to return

        Returns:
            List of command history entries
        """
        tab = self.get_active_tab()
        if not tab:
            return []

        history = tab.command_history
        if max_entries is not None:
            history = history[-max_entries:]

        return history

    def get_output_history(self, max_entries: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get output history from the active tab.

        Args:
            max_entries: Maximum number of entries to return

        Returns:
            List of output history entries
        """
        tab = self.get_active_tab()
        if not tab:
            return []

        history = tab.output_history
        if max_entries is not None:
            history = history[-max_entries:]

        return history

    def highlight_code(self, code: str, language: Optional[str] = None) -> str:
        """
        Apply syntax highlighting to code.

        Args:
            code: The code to highlight
            language: The programming language (if known)

        Returns:
            Highlighted code
        """
        try:
            if language:
                lexer = get_lexer_by_name(language)
            else:
                lexer = guess_lexer(code)

            return highlight(code, lexer, TerminalFormatter())
        except Exception as e:
            logger.error(f"Error highlighting code: {str(e)}")
            return code

    def start_search(self, event: Any) -> None:
        """
        Start search in the terminal.

        Args:
            event: The key event that triggered the search
        """
        # Implementation will depend on the UI framework
        pass

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search in command and output history.

        Args:
            query: The search query

        Returns:
            List of search results
        """
        self.search_query = query
        self.search_results = []

        tab = self.get_active_tab()
        if not tab:
            return []

        # Search in command history
        for i, cmd in enumerate(tab.command_history):
            if query.lower() in cmd.lower():
                self.search_results.append({
                    "type": "command",
                    "index": i,
                    "content": cmd
                })

        # Search in output history
        for i, entry in enumerate(tab.output_history):
            if (query.lower() in entry["command"].lower() or
                query.lower() in entry["output"].lower() or
                query.lower() in entry["error"].lower()):
                self.search_results.append({
                    "type": "output",
                    "index": i,
                    "content": entry
                })

        return self.search_results

    def toggle_fold(self, event: Any) -> None:
        """
        Toggle code folding at the current position.

        Args:
            event: The key event that triggered the fold
        """
        # Implementation will depend on the UI framework
        pass

    def fold_region(self, start_line: int, end_line: int, tab_id: Optional[str] = None) -> None:
        """
        Fold a region of code.

        Args:
            start_line: Start line of the region
            end_line: End line of the region
            tab_id: ID of the tab (uses active tab if None)
        """
        tab_id = tab_id or self.active_tab_id
        if not tab_id or tab_id not in self.tabs:
            return

        if tab_id not in self.folded_regions:
            self.folded_regions[tab_id] = []

        self.folded_regions[tab_id].append({
            "start": start_line,
            "end": end_line,
            "folded": True
        })

    def unfold_region(self, start_line: int, end_line: int, tab_id: Optional[str] = None) -> None:
        """
        Unfold a region of code.

        Args:
            start_line: Start line of the region
            end_line: End line of the region
            tab_id: ID of the tab (uses active tab if None)
        """
        tab_id = tab_id or self.active_tab_id
        if not tab_id or tab_id not in self.tabs:
            return

        if tab_id not in self.folded_regions:
            return

        # Find and remove the folded region
        for i, region in enumerate(self.folded_regions[tab_id]):
            if region["start"] == start_line and region["end"] == end_line:
                self.folded_regions[tab_id].pop(i)
                break

    def get_folded_regions(self, tab_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all folded regions for a tab.

        Args:
            tab_id: ID of the tab (uses active tab if None)

        Returns:
            List of folded regions
        """
        tab_id = tab_id or self.active_tab_id
        if not tab_id or tab_id not in self.tabs:
            return []

        return self.folded_regions.get(tab_id, [])

    def render(self) -> str:
        """
        Render the terminal UI component.

        Returns:
            Rendered terminal UI
        """
        tab = self.get_active_tab()
        if not tab:
            return "No active terminal tab."

        # Build the terminal UI
        output = []

        # Add tab bar
        tab_bar = []
        for tab_id, tab_info in self.tabs.items():
            if tab_id == self.active_tab_id:
                tab_bar.append(f"[{tab_info.name}]")
            else:
                tab_bar.append(f" {tab_info.name} ")

        output.append(" ".join(tab_bar))
        output.append("-" * 80)

        # Add working directory
        output.append(f"Working directory: {tab.working_directory}")
        output.append("")

        # Add output history (last 10 entries)
        history = self.get_output_history(10)
        for entry in history:
            output.append(f"$ {entry['command']}")
            if entry['output']:
                output.append(entry['output'])
            if entry['error']:
                output.append(f"Error: {entry['error']}")
            output.append("")

        # Add command prompt
        output.append("$ ")

        return "\n".join(output)


# Create a singleton instance
terminal_ui = TerminalUIComponent()
