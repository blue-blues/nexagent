"""Persistent Terminate tool for NexAgent.

This module provides a modified version of the Terminate tool that
allows the agent to remain active after completing a task and
prompt the user for additional input.
"""

from typing import Any, Optional

from app.logger import logger
from app.session import session_manager
from app.tool.base import BaseTool


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
            }
        },
        "required": ["status"],
    }

    async def execute(
        self, 
        status: str, 
        message: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Mark the current task as complete but keep the session active.
        
        Args:
            status: The completion status of the task ("success" or "failure")
            message: Optional message to display to the user
            session_id: Optional session ID to use
            
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
                message = "The task was completed successfully. Do you have any further questions or additional tasks?"
            else:
                message = "The task encountered issues. Would you like to try a different approach or ask for help troubleshooting the errors?"
        
        return f"The interaction has been completed with status: {status}\n\n{message}"