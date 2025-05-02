"""
User Input CLI

This module provides a command-line interface for handling user input requests
during agent execution.
"""

import asyncio
import threading
from typing import Dict, Optional, Any, List
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory

from app.logger import logger
from app.util.user_input_manager import input_manager


class UserInputCLI:
    """CLI interface for handling user input requests."""

    def __init__(self):
        """Initialize the CLI interface."""
        self.session = PromptSession(
            history=InMemoryHistory(),
            style=Style.from_dict({
                'prompt': 'ansired bold',
                'input': 'ansiwhite',
            })
        )
        self.running = False
        self.thread = None
        self.check_interval = 0.5  # seconds

    def start(self):
        """Start the CLI interface in a separate thread."""
        if self.running:
            logger.warning("User input CLI is already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("User input CLI started")

    def stop(self):
        """Stop the CLI interface."""
        if not self.running:
            logger.warning("User input CLI is not running")
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        logger.info("User input CLI stopped")

    def _run_loop(self):
        """Run the main loop checking for pending input requests."""
        while self.running:
            try:
                # Check for pending requests
                pending_requests = input_manager.get_pending_requests()
                if pending_requests:
                    # Process the first pending request
                    request_id, request_data = next(iter(pending_requests.items()))
                    self._process_request(request_id, request_data)

                # Sleep for a short time before checking again
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in user input CLI loop: {str(e)}")
                time.sleep(1.0)  # Sleep a bit longer on error

    def _process_request(self, request_id: str, request_data: Dict[str, Any]):
        """Process a single input request."""
        try:
            # Extract request information
            text = request_data.get("text", "")
            attachments = request_data.get("metadata", {}).get("attachments", [])
            suggest_takeover = request_data.get("metadata", {}).get("suggest_user_takeover", "none")

            # Create a visually distinct prompt with clear separation
            print("\n" + "="*80)
            print("\033[1;31m>>> USER INPUT REQUIRED <<<\033[0m")
            print("="*80)
            print(f"\033[1m🤖 Agent is requesting input:\033[0m\n")
            print(f"{text}\n")

            # Add attachment information if present
            if attachments:
                if isinstance(attachments, str):
                    attachments = [attachments]
                print(f"\033[1mAttachments:\033[0m {', '.join(attachments)}")

            # Add takeover suggestion if present
            if suggest_takeover and suggest_takeover != "none":
                print(f"\n\033[1;33m(Suggestion: Consider taking control of {suggest_takeover})\033[0m")

            print("\n" + "-"*80)

            # Get user input with a clear prompt
            response = input("\033[1;32mYour response:\033[0m ")
            print("-"*80)

            # Submit the response
            input_manager.submit_response(request_id, response)
            print(f"\033[1;34mResponse submitted successfully for request {request_id}\033[0m\n")
            logger.info(f"Submitted user response for request {request_id}")
        except Exception as e:
            logger.error(f"Error processing input request {request_id}: {str(e)}")
            print(f"\n\033[1;31mError processing input request: {str(e)}\033[0m\n")
            # Try to submit an error response
            try:
                input_manager.submit_response(
                    request_id,
                    f"Error processing input request: {str(e)}"
                )
            except:
                pass


# Create a singleton instance
user_input_cli = UserInputCLI()
