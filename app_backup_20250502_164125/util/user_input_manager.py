"""
User Input Manager

This module provides a class for managing user input requests and responses
during agent execution.
"""

import asyncio
from typing import Dict, Optional, Any
import uuid
from datetime import datetime

from app.logger import logger


class UserInputManager:
    """
    Manages user input requests and responses during agent execution.

    This class provides methods to register input requests, wait for responses,
    and retrieve responses once they are available.
    """

    def __init__(self):
        """Initialize the user input manager."""
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.responses: Dict[str, str] = {}
        self._events: Dict[str, asyncio.Event] = {}

    def register_request(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a new input request.

        Args:
            text: The question or request to present to the user
            metadata: Optional metadata to associate with the request

        Returns:
            str: A unique request ID
        """
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        self.pending_requests[request_id] = {
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "status": "pending"
        }
        self._events[request_id] = asyncio.Event()
        logger.info(f"Registered user input request: {request_id} - {text[:50]}...")

        # Display a notification in the terminal
        self._notify_new_request(request_id, text)

        return request_id

    def _notify_new_request(self, request_id: str, text: str):
        """
        Display a notification in the terminal for a new input request.

        Args:
            request_id: The ID of the request
            text: The text of the request
        """
        try:
            # Create a visually distinct notification
            notification = f"""
\033[1;31m
================================================================================
                        !!! USER INPUT REQUIRED !!!
================================================================================
\033[0m
\033[1mRequest ID: \033[1;33m{request_id}\033[0m
\033[1mQuestion:\033[0m
{text[:150]}{'...' if len(text) > 150 else ''}

\033[1;32mTo respond, simply run:\033[0m
  \033[1;36mrespond.bat\033[0m  or  \033[1;36mpython respond.py\033[0m

This will show you the full question and let you enter your response.
"""
            print(notification)
        except Exception as e:
            logger.error(f"Error displaying notification: {str(e)}")

    def submit_response(self, request_id: str, response: str) -> bool:
        """
        Submit a response to a pending request.

        Args:
            request_id: The ID of the request to respond to
            response: The user's response

        Returns:
            bool: True if the response was accepted, False otherwise
        """
        if request_id not in self.pending_requests:
            logger.warning(f"Attempted to submit response for unknown request: {request_id}")
            print(f"\033[1;31mError: No pending request found with ID {request_id}\033[0m")
            return False

        if self.pending_requests[request_id]["status"] != "pending":
            logger.warning(f"Attempted to submit response for non-pending request: {request_id}")
            print(f"\033[1;31mError: Request {request_id} is not pending (status: {self.pending_requests[request_id]['status']})\033[0m")
            return False

        self.responses[request_id] = response
        self.pending_requests[request_id]["status"] = "completed"

        # Set the event to signal that the response is available
        if request_id in self._events:
            self._events[request_id].set()

        logger.info(f"Received response for request {request_id}")

        # Display a confirmation message
        print(f"""
\033[1;32m
================================================================================
                        RESPONSE SUBMITTED SUCCESSFULLY
================================================================================
\033[0m
\033[1mRequest ID: \033[1;33m{request_id}\033[0m
\033[1mStatus: \033[1;32mCompleted\033[0m

The agent will now continue processing with your response.
""")

        return True

    async def wait_for_response(self, request_id: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        Wait for a response to a pending request.

        Args:
            request_id: The ID of the request to wait for
            timeout: Optional timeout in seconds

        Returns:
            Optional[str]: The response if available, None if timed out or request not found
        """
        if request_id not in self.pending_requests:
            logger.warning(f"Attempted to wait for unknown request: {request_id}")
            return None

        if request_id not in self._events:
            logger.warning(f"No event found for request: {request_id}")
            return None

        if self.pending_requests[request_id]["status"] == "completed":
            return self.responses.get(request_id)

        try:
            # Wait for the response
            await asyncio.wait_for(self._events[request_id].wait(), timeout=timeout)
            return self.responses.get(request_id)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response to request: {request_id}")
            return None

    def get_response(self, request_id: str) -> Optional[str]:
        """
        Get a response to a request if available.

        Args:
            request_id: The ID of the request

        Returns:
            Optional[str]: The response if available, None otherwise
        """
        return self.responses.get(request_id)

    def has_pending_requests(self) -> bool:
        """
        Check if there are any pending requests.

        Returns:
            bool: True if there are pending requests, False otherwise
        """
        return any(req["status"] == "pending" for req in self.pending_requests.values())

    def get_pending_requests(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pending requests.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary of pending requests
        """
        return {
            req_id: req_data
            for req_id, req_data in self.pending_requests.items()
            if req_data["status"] == "pending"
        }

    def clear_request(self, request_id: str) -> bool:
        """
        Clear a request from the manager.

        Args:
            request_id: The ID of the request to clear

        Returns:
            bool: True if the request was cleared, False otherwise
        """
        if request_id not in self.pending_requests:
            return False

        self.pending_requests.pop(request_id, None)
        self.responses.pop(request_id, None)
        self._events.pop(request_id, None)
        return True

    def clear_all(self) -> None:
        """Clear all requests and responses."""
        self.pending_requests.clear()
        self.responses.clear()
        self._events.clear()


# Create a singleton instance
input_manager = UserInputManager()
