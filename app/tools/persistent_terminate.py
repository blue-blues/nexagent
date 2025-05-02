"""Persistent Terminate tool for NexAgent.

This module provides a modified version of the Terminate tool that
allows the agent to remain active after completing a task and
prompt the user for additional input.
"""

from typing import Optional

from app.logger import logger
from app.session import session_manager
# Try to import BaseTool from different locations
try:
    from app.tools.base import BaseTool
except ImportError:
    try:
        from app.core.tool.base import BaseTool
    except ImportError:
        # Define a minimal BaseTool class if both imports fail
        class BaseTool:
            """Fallback BaseTool implementation."""
            name = "base_tool"
            description = "Base tool class"
            parameters = {}
from app.util.response_formatter import format_response


_PERSISTENT_TERMINATE_DESCRIPTION = """Mark the current task as complete but keep the session active for further interaction.
When you have finished the current task, call this tool to indicate completion while remaining available for follow-up questions."""


class PersistentTerminate(BaseTool):
    """A tool that marks a task as complete but keeps the session active.

    Unlike the standard Terminate tool, this tool does not end the agent session
    but instead marks it as waiting for additional user input.
    """

    name: str = "terminate"
    description: str = _PERSISTENT_TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "The finish status of the current task.",
                "enum": ["success", "failure"],
            },
            "message": {
                "type": "string",
                "description": "Optional message to display to the user after task completion.",
            },
            "session_id": {
                "type": "string",
                "description": "Optional session ID. If not provided, the current session will be used.",
            },
            "summary": {
                "type": "string",
                "description": "Optional summary of the task results to display to the user.",
            },
            "detailed_response": {
                "type": "string",
                "description": "Optional detailed response to show to the user, overriding other messages.",
            }
        },
        "required": ["status"],
    }

    async def execute(
        self,
        status: str,
        message: Optional[str] = None,
        session_id: Optional[str] = None,
        summary: Optional[str] = None,
        detailed_response: Optional[str] = None
    ) -> str:
        """Mark the current task as complete but keep the session active.

        Args:
            status: The completion status of the task ("success" or "failure")
            message: Optional message to display to the user
            session_id: Optional session ID to use
            summary: Optional summary of the task results
            detailed_response: Optional detailed response to show to the user

        Returns:
            A string indicating the task has been completed and prompting for further input
        """
        # Get or create a session
        session = session_manager.get_or_create_session(session_id)

        # Mark the session as waiting for user input
        session.mark_waiting()

        # Log the task completion
        logger.info(f"Task completed with status: {status}. Session {session.session_id} is now waiting for user input.")

        # Generate appropriate follow-up message based on task status
        if not message:
            if status == "success":
                message = "The task was completed successfully."
            else:
                message = "The task encountered issues. Would you like to try a different approach or ask for help troubleshooting the errors?"

        # If we have a detailed response, format it properly
        if detailed_response:
            # Use the response formatter to ensure it's well-structured
            formatted_response = format_response(detailed_response)
            return formatted_response

        # If we have a summary, include it in the response
        if summary:
            # Format the summary to ensure it's well-structured
            formatted_summary = format_response(summary)
            return formatted_summary

        # Default response if no detailed content is provided
        return format_response(message)