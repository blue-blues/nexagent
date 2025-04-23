"""
Tests for the Terminal UI Component.
"""

import os
import unittest
from datetime import datetime

from app.ui.terminal_ui_component import TerminalUIComponent


class TestTerminalUIComponent(unittest.TestCase):
    """Test cases for the Terminal UI Component."""
    
    def setUp(self):
        """Set up test environment."""
        self.terminal = TerminalUIComponent()
    
    def test_create_tab(self):
        """Test creating a new tab."""
        tab_id = self.terminal.create_tab("Test Tab")
        self.assertIn(tab_id, self.terminal.tabs)
        self.assertEqual(self.terminal.tabs[tab_id].name, "Test Tab")
    
    def test_close_tab(self):
        """Test closing a tab."""
        tab_id = self.terminal.create_tab("Test Tab")
        self.assertTrue(self.terminal.close_tab(tab_id))
        self.assertNotIn(tab_id, self.terminal.tabs)
    
    def test_switch_tab(self):
        """Test switching between tabs."""
        tab1_id = self.terminal.create_tab("Tab 1")
        tab2_id = self.terminal.create_tab("Tab 2")
        
        self.terminal.switch_tab(tab1_id)
        self.assertEqual(self.terminal.active_tab_id, tab1_id)
        
        self.terminal.switch_tab(tab2_id)
        self.assertEqual(self.terminal.active_tab_id, tab2_id)
    
    def test_next_prev_tab(self):
        """Test navigating between tabs."""
        tab1_id = self.terminal.create_tab("Tab 1")
        tab2_id = self.terminal.create_tab("Tab 2")
        tab3_id = self.terminal.create_tab("Tab 3")
        
        self.terminal.switch_tab(tab1_id)
        
        # Test next_tab
        self.assertEqual(self.terminal.next_tab(), tab2_id)
        self.assertEqual(self.terminal.next_tab(), tab3_id)
        self.assertEqual(self.terminal.next_tab(), tab1_id)  # Wraps around
        
        # Test prev_tab
        self.assertEqual(self.terminal.prev_tab(), tab3_id)
        self.assertEqual(self.terminal.prev_tab(), tab2_id)
        self.assertEqual(self.terminal.prev_tab(), tab1_id)  # Wraps around
    
    def test_command_history(self):
        """Test command history functionality."""
        tab_id = self.terminal.create_tab("Test Tab")
        self.terminal.switch_tab(tab_id)
        
        # Add commands to history
        self.terminal.add_command_to_history("ls -la")
        self.terminal.add_command_to_history("cd /tmp")
        self.terminal.add_command_to_history("echo 'hello'")
        
        # Check history
        history = self.terminal.get_command_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0], "ls -la")
        self.assertEqual(history[1], "cd /tmp")
        self.assertEqual(history[2], "echo 'hello'")
        
        # Check limited history
        limited_history = self.terminal.get_command_history(2)
        self.assertEqual(len(limited_history), 2)
        self.assertEqual(limited_history[0], "cd /tmp")
        self.assertEqual(limited_history[1], "echo 'hello'")
    
    def test_output_history(self):
        """Test output history functionality."""
        tab_id = self.terminal.create_tab("Test Tab")
        self.terminal.switch_tab(tab_id)
        
        # Add output to history
        self.terminal.add_output_to_history("ls -la", "file1.txt\nfile2.txt")
        self.terminal.add_output_to_history("cd /tmp", "", "Directory not found", False)
        
        # Check history
        history = self.terminal.get_output_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["command"], "ls -la")
        self.assertEqual(history[0]["output"], "file1.txt\nfile2.txt")
        self.assertEqual(history[0]["error"], "")
        self.assertTrue(history[0]["success"])
        
        self.assertEqual(history[1]["command"], "cd /tmp")
        self.assertEqual(history[1]["output"], "")
        self.assertEqual(history[1]["error"], "Directory not found")
        self.assertFalse(history[1]["success"])
    
    def test_highlight_code(self):
        """Test code highlighting."""
        python_code = "def hello():\n    print('Hello, world!')"
        highlighted = self.terminal.highlight_code(python_code, "python")
        
        # We can't easily test the exact output since it contains ANSI color codes,
        # but we can check that it's different from the input
        self.assertNotEqual(highlighted, python_code)
    
    def test_search(self):
        """Test search functionality."""
        tab_id = self.terminal.create_tab("Test Tab")
        self.terminal.switch_tab(tab_id)
        
        # Add commands and output to history
        self.terminal.add_command_to_history("ls -la")
        self.terminal.add_output_to_history("ls -la", "file1.txt\nfile2.txt")
        self.terminal.add_command_to_history("grep 'hello' file.txt")
        self.terminal.add_output_to_history("grep 'hello' file.txt", "hello world")
        
        # Search for 'file'
        results = self.terminal.search("file")
        self.assertEqual(len(results), 3)  # Should find in both command and output
        
        # Search for 'hello'
        results = self.terminal.search("hello")
        self.assertEqual(len(results), 2)  # Should find in command and output
    
    def test_folding(self):
        """Test code folding functionality."""
        tab_id = self.terminal.create_tab("Test Tab")
        
        # Fold a region
        self.terminal.fold_region(10, 20, tab_id)
        
        # Check folded regions
        regions = self.terminal.get_folded_regions(tab_id)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["start"], 10)
        self.assertEqual(regions[0]["end"], 20)
        self.assertTrue(regions[0]["folded"])
        
        # Unfold the region
        self.terminal.unfold_region(10, 20, tab_id)
        
        # Check that it's gone
        regions = self.terminal.get_folded_regions(tab_id)
        self.assertEqual(len(regions), 0)
    
    def test_render(self):
        """Test rendering the terminal UI."""
        tab_id = self.terminal.create_tab("Test Tab")
        self.terminal.switch_tab(tab_id)
        
        # Add some content
        self.terminal.add_command_to_history("ls -la")
        self.terminal.add_output_to_history("ls -la", "file1.txt\nfile2.txt")
        
        # Render the UI
        rendered = self.terminal.render()
        
        # Check that it contains expected elements
        self.assertIn("Test Tab", rendered)
        self.assertIn("Working directory:", rendered)
        self.assertIn("$ ls -la", rendered)
        self.assertIn("file1.txt", rendered)
        self.assertIn("file2.txt", rendered)


if __name__ == "__main__":
    unittest.main()
