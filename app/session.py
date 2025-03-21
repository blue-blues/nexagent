"""Session management module for NexAgent.

This module provides functionality for managing persistent sessions,
allowing the agent to remain active after completing a task and
prompt the user for additional input.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.logger import logger


class SessionState(str):
    """Enumeration of possible session states."""
    ACTIVE = "active"  # Session is active and processing requests
    WAITING = "waiting"  # Session has completed a task and is waiting for user input
    TERMINATED = "terminated"  # Session has been explicitly terminated by the user


class Session(BaseModel):
    """Represents a user session with the agent.
    
    This class tracks session state, history, and provides methods for
    managing the session lifecycle.
    """
    
    model_config = {"arbitrary_types_allowed": True}
    
    session_id: str = Field(..., description="Unique identifier for the session")
    state: SessionState = Field(default=SessionState.ACTIVE, description="Current state of the session")
    created_at: datetime = Field(default_factory=datetime.now, description="When the session was created")
    last_active: datetime = Field(default_factory=datetime.now, description="When the session was last active")
    task_history: List[Dict] = Field(default_factory=list, description="History of tasks processed in this session")
    
    def mark_waiting(self) -> None:
        """Mark the session as waiting for user input after completing a task."""
        self.state = SessionState.WAITING
        self.last_active = datetime.now()
        logger.info(f"Session {self.session_id} marked as waiting for user input")
    
    def mark_active(self) -> None:
        """Mark the session as active when processing a new request."""
        self.state = SessionState.ACTIVE
        self.last_active = datetime.now()
        logger.info(f"Session {self.session_id} marked as active")
    
    def mark_terminated(self) -> None:
        """Mark the session as explicitly terminated by the user."""
        self.state = SessionState.TERMINATED
        self.last_active = datetime.now()
        logger.info(f"Session {self.session_id} marked as terminated")
    
    def add_task(self, prompt: str, result: str, success: bool) -> None:
        """Add a completed task to the session history.
        
        Args:
            prompt: The user's input prompt
            result: The result of processing the prompt
            success: Whether the task was successful
        """
        self.task_history.append({
            "prompt": prompt,
            "result": result,
            "success": success,
            "timestamp": datetime.now()
        })
        logger.info(f"Added task to session {self.session_id} history")
    
    def get_last_task(self) -> Optional[Dict]:
        """Get the most recent task from the session history.
        
        Returns:
            The most recent task or None if no tasks exist
        """
        if self.task_history:
            return self.task_history[-1]
        return None
    
    def is_active(self) -> bool:
        """Check if the session is currently active.
        
        Returns:
            True if the session is active, False otherwise
        """
        return self.state == SessionState.ACTIVE
    
    def is_waiting(self) -> bool:
        """Check if the session is waiting for user input.
        
        Returns:
            True if the session is waiting, False otherwise
        """
        return self.state == SessionState.WAITING
    
    def is_terminated(self) -> bool:
        """Check if the session has been explicitly terminated.
        
        Returns:
            True if the session is terminated, False otherwise
        """
        return self.state == SessionState.TERMINATED


class SessionManager:
    """Manages multiple user sessions.
    
    This class provides functionality for creating, retrieving, and
    managing user sessions.
    """
    
    def __init__(self):
        """Initialize the session manager."""
        self.sessions: Dict[str, Session] = {}
    
    def create_session(self, session_id: Optional[str] = None) -> Session:
        """Create a new session.
        
        Args:
            session_id: Optional custom session ID. If not provided, a timestamp-based ID will be used.
            
        Returns:
            The newly created session
        """
        if session_id is None:
            session_id = f"session_{int(datetime.now().timestamp())}"
        
        session = Session(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"Created new session with ID {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by its ID.
        
        Args:
            session_id: The ID of the session to retrieve
            
        Returns:
            The session if found, None otherwise
        """
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        """Get an existing session or create a new one if it doesn't exist.
        
        Args:
            session_id: The ID of the session to retrieve or create
            
        Returns:
            The retrieved or newly created session
        """
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self.create_session(session_id)
    
    def terminate_session(self, session_id: str) -> bool:
        """Explicitly terminate a session.
        
        Args:
            session_id: The ID of the session to terminate
            
        Returns:
            True if the session was terminated, False if it wasn't found
        """
        session = self.get_session(session_id)
        if session:
            session.mark_terminated()
            return True
        return False
    
    def get_active_sessions(self) -> List[Session]:
        """Get all active sessions.
        
        Returns:
            List of active sessions
        """
        return [s for s in self.sessions.values() if not s.is_terminated()]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up sessions that have been inactive for a specified period.
        
        Args:
            max_age_hours: Maximum age of inactive sessions in hours
            
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            age = (now - session.last_active).total_seconds() / 3600  # Convert to hours
            if age > max_age_hours:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive sessions")
        
        return len(to_remove)


# Global session manager instance
session_manager = SessionManager()