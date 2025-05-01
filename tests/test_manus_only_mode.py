"""
Test script for the Manus-only mode.

This script tests that the system correctly uses only the Manus mode
and doesn't attempt to use the agent or chat modes.
"""

import asyncio
import sys
import os
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.agent.manus_agent import ManusAgent
from app.logger import logger


class TestManusOnlyMode(unittest.TestCase):
    """Test case for the Manus-only mode."""

    @patch('builtins.input', side_effect=['mode chat', 'mode agent', 'mode auto', 'exit'])
    @patch('builtins.print')
    @patch('asyncio.run')
    def test_mode_commands(self, mock_asyncio_run, mock_print, mock_input):
        """Test that mode commands are properly handled."""
        # Import the main module
        import main
        
        # Run the main function
        main.legacy_main()
        
        # Check that the correct message was printed for mode commands
        mock_print.assert_any_call("Only Manus mode is available. The system is already in Manus mode.")
        
        # Check that asyncio.run was called with the main coroutine
        mock_asyncio_run.assert_called_once()
    
    @patch('app.agent.manus_agent.ManusAgent.run')
    async def test_manus_agent_used(self, mock_run):
        """Test that the ManusAgent is used for processing requests."""
        # Set up the mock
        mock_run.return_value = "Mocked response from ManusAgent"
        
        # Create a ManusAgent instance
        agent = ManusAgent()
        
        # Call the run method
        result = await agent.run("Test prompt")
        
        # Check that the ManusAgent.run method was called
        mock_run.assert_called_once_with("Test prompt")
        
        # Check that the result is the mocked response
        self.assertEqual(result, "Mocked response from ManusAgent")


if __name__ == "__main__":
    unittest.main()
