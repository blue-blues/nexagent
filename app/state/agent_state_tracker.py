"""
Agent State Tracker for Nexagent.

This module provides functionality for tracking and managing agent state,
including actions, decisions, and progress across multiple agents.
"""

import time
import json
from typing import Dict, List, Optional, Any, Set, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

from app.logger import logger


class ActionType(str, Enum):
    """Types of actions that can be tracked."""
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    USER_INTERACTION = "user_interaction"
    SYSTEM = "system"


class ActionStatus(str, Enum):
    """Status of tracked actions."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrackedAction(BaseModel):
    """
    Represents a single tracked action in the agent's execution.
    
    This model stores detailed information about actions performed by agents,
    including timestamps, status, and related metadata.
    """
    
    id: str
    agent_id: str
    action_type: ActionType
    description: str
    timestamp: float = Field(default_factory=time.time)
    status: ActionStatus = ActionStatus.PENDING
    duration: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    parent_action_id: Optional[str] = None
    
    def complete(self, result: Any = None) -> None:
        """Mark the action as completed with an optional result."""
        self.status = ActionStatus.COMPLETED
        self.duration = time.time() - self.timestamp
        if result is not None:
            self.result = result
    
    def fail(self, error: Any = None) -> None:
        """Mark the action as failed with an optional error."""
        self.status = ActionStatus.FAILED
        self.duration = time.time() - self.timestamp
        if error is not None:
            self.result = error
    
    def cancel(self) -> None:
        """Mark the action as cancelled."""
        self.status = ActionStatus.CANCELLED
        self.duration = time.time() - self.timestamp
    
    def start(self) -> None:
        """Mark the action as in progress."""
        self.status = ActionStatus.IN_PROGRESS
    
    def update_metadata(self, **kwargs) -> None:
        """Update the action's metadata."""
        self.metadata.update(kwargs)


class AgentStateTracker:
    """
    Tracks and manages the state of agents during execution.
    
    This class provides functionality for recording agent actions, decisions,
    and state changes, as well as generating reports and visualizations of
    agent execution.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize the agent state tracker.
        
        Args:
            session_id: Optional session ID for tracking
        """
        self.session_id = session_id or f"session_{int(time.time())}"
        self.start_time = time.time()
        self.actions: Dict[str, TrackedAction] = {}
        self.action_history: List[str] = []
        self.agent_states: Dict[str, Dict[str, Any]] = {}
        self.current_action_id: Optional[str] = None
    
    def track_action(self, agent_id: str, action_type: ActionType, description: str,
                    metadata: Optional[Dict[str, Any]] = None,
                    parent_action_id: Optional[str] = None) -> str:
        """
        Track a new action performed by an agent.
        
        Args:
            agent_id: ID of the agent performing the action
            action_type: Type of action being performed
            description: Description of the action
            metadata: Optional metadata about the action
            parent_action_id: Optional ID of the parent action
            
        Returns:
            ID of the tracked action
        """
        action_id = f"{agent_id}_{action_type}_{int(time.time())}_{len(self.actions)}"
        
        action = TrackedAction(
            id=action_id,
            agent_id=agent_id,
            action_type=action_type,
            description=description,
            metadata=metadata or {},
            parent_action_id=parent_action_id
        )
        
        self.actions[action_id] = action
        self.action_history.append(action_id)
        self.current_action_id = action_id
        
        logger.info(f"Tracked action: {agent_id} - {action_type} - {description[:50]}")
        
        return action_id
    
    def start_action(self, action_id: str) -> None:
        """
        Mark an action as in progress.
        
        Args:
            action_id: ID of the action to start
        """
        if action_id in self.actions:
            self.actions[action_id].start()
            logger.info(f"Started action: {action_id}")
        else:
            logger.error(f"Action not found: {action_id}")
    
    def complete_action(self, action_id: str, result: Any = None) -> None:
        """
        Mark an action as completed.
        
        Args:
            action_id: ID of the action to complete
            result: Optional result of the action
        """
        if action_id in self.actions:
            self.actions[action_id].complete(result)
            logger.info(f"Completed action: {action_id}")
        else:
            logger.error(f"Action not found: {action_id}")
    
    def fail_action(self, action_id: str, error: Any = None) -> None:
        """
        Mark an action as failed.
        
        Args:
            action_id: ID of the action to fail
            error: Optional error information
        """
        if action_id in self.actions:
            self.actions[action_id].fail(error)
            logger.error(f"Failed action: {action_id} - {error}")
        else:
            logger.error(f"Action not found: {action_id}")
    
    def cancel_action(self, action_id: str) -> None:
        """
        Mark an action as cancelled.
        
        Args:
            action_id: ID of the action to cancel
        """
        if action_id in self.actions:
            self.actions[action_id].cancel()
            logger.info(f"Cancelled action: {action_id}")
        else:
            logger.error(f"Action not found: {action_id}")
    
    def update_action_metadata(self, action_id: str, **kwargs) -> None:
        """
        Update an action's metadata.
        
        Args:
            action_id: ID of the action to update
            **kwargs: Metadata key-value pairs to update
        """
        if action_id in self.actions:
            self.actions[action_id].update_metadata(**kwargs)
        else:
            logger.error(f"Action not found: {action_id}")
    
    def update_agent_state(self, agent_id: str, state: Dict[str, Any]) -> None:
        """
        Update the state of an agent.
        
        Args:
            agent_id: ID of the agent to update
            state: New state information
        """
        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = {}
        
        self.agent_states[agent_id].update(state)
        self.agent_states[agent_id]["last_updated"] = time.time()
        
        logger.info(f"Updated state for agent: {agent_id}")
    
    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """
        Get the current state of an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Current state of the agent
        """
        return self.agent_states.get(agent_id, {})
    
    def get_action(self, action_id: str) -> Optional[TrackedAction]:
        """
        Get a tracked action by ID.
        
        Args:
            action_id: ID of the action
            
        Returns:
            The tracked action, or None if not found
        """
        return self.actions.get(action_id)
    
    def get_actions_by_agent(self, agent_id: str) -> List[TrackedAction]:
        """
        Get all actions performed by an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of actions performed by the agent
        """
        return [action for action in self.actions.values() if action.agent_id == agent_id]
    
    def get_actions_by_type(self, action_type: ActionType) -> List[TrackedAction]:
        """
        Get all actions of a specific type.
        
        Args:
            action_type: Type of actions to get
            
        Returns:
            List of actions of the specified type
        """
        return [action for action in self.actions.values() if action.action_type == action_type]
    
    def get_recent_actions(self, limit: int = 10) -> List[TrackedAction]:
        """
        Get the most recent actions.
        
        Args:
            limit: Maximum number of actions to return
            
        Returns:
            List of the most recent actions
        """
        recent_ids = self.action_history[-limit:] if self.action_history else []
        return [self.actions[action_id] for action_id in recent_ids if action_id in self.actions]
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the execution.
        
        Returns:
            Dictionary containing execution summary
        """
        total_actions = len(self.actions)
        completed_actions = sum(1 for action in self.actions.values() if action.status == ActionStatus.COMPLETED)
        failed_actions = sum(1 for action in self.actions.values() if action.status == ActionStatus.FAILED)
        in_progress_actions = sum(1 for action in self.actions.values() if action.status == ActionStatus.IN_PROGRESS)
        
        execution_time = time.time() - self.start_time
        
        # Calculate action type distribution
        action_types = {}
        for action in self.actions.values():
            if action.action_type not in action_types:
                action_types[action.action_type] = 0
            action_types[action.action_type] += 1
        
        # Calculate agent activity
        agent_activity = {}
        for action in self.actions.values():
            if action.agent_id not in agent_activity:
                agent_activity[action.agent_id] = 0
            agent_activity[action.agent_id] += 1
        
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "execution_time": execution_time,
            "total_actions": total_actions,
            "completed_actions": completed_actions,
            "failed_actions": failed_actions,
            "in_progress_actions": in_progress_actions,
            "action_types": action_types,
            "agent_activity": agent_activity,
            "active_agents": len(self.agent_states),
            "completion_rate": (completed_actions / total_actions) if total_actions > 0 else 0
        }
    
    def get_execution_timeline(self) -> List[Dict[str, Any]]:
        """
        Get a timeline of the execution.
        
        Returns:
            List of actions in chronological order with timing information
        """
        timeline = []
        
        for action_id in self.action_history:
            if action_id in self.actions:
                action = self.actions[action_id]
                
                timeline_entry = {
                    "id": action.id,
                    "agent_id": action.agent_id,
                    "action_type": action.action_type,
                    "description": action.description,
                    "timestamp": action.timestamp,
                    "status": action.status,
                    "duration": action.duration,
                    "parent_action_id": action.parent_action_id
                }
                
                timeline.append(timeline_entry)
        
        return timeline
    
    def export_to_json(self) -> str:
        """
        Export the tracker state to JSON.
        
        Returns:
            JSON string representation of the tracker state
        """
        export_data = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "current_time": time.time(),
            "actions": {action_id: action.dict() for action_id, action in self.actions.items()},
            "action_history": self.action_history,
            "agent_states": self.agent_states
        }
        
        return json.dumps(export_data, indent=2)
    
    @classmethod
    def import_from_json(cls, json_data: str) -> "AgentStateTracker":
        """
        Import tracker state from JSON.
        
        Args:
            json_data: JSON string representation of tracker state
            
        Returns:
            Initialized AgentStateTracker instance
        """
        data = json.loads(json_data)
        
        tracker = cls(session_id=data.get("session_id"))
        tracker.start_time = data.get("start_time", time.time())
        tracker.action_history = data.get("action_history", [])
        tracker.agent_states = data.get("agent_states", {})
        
        # Reconstruct actions
        for action_id, action_data in data.get("actions", {}).items():
            tracker.actions[action_id] = TrackedAction(**action_data)
        
        return tracker


# Example usage
if __name__ == "__main__":
    # Create a tracker
    tracker = AgentStateTracker()
    
    # Track some actions
    action1 = tracker.track_action(
        agent_id="agent1",
        action_type=ActionType.TOOL_CALL,
        description="Executing web search for 'Python REST API'"
    )
    
    # Start the action
    tracker.start_action(action1)
    
    # Complete the action
    tracker.complete_action(action1, result={"search_results": ["Result 1", "Result 2"]})
    
    # Track another action
    action2 = tracker.track_action(
        agent_id="agent1",
        action_type=ActionType.DECISION,
        description="Deciding on framework for REST API",
        parent_action_id=action1
    )
    
    # Start the action
    tracker.start_action(action2)
    
    # Update agent state
    tracker.update_agent_state("agent1", {
        "current_task": "Framework selection",
        "progress": 0.3,
        "decisions": ["Using Python", "Considering Flask or FastAPI"]
    })
    
    # Complete the action
    tracker.complete_action(action2, result="Selected FastAPI")
    
    # Get execution summary
    summary = tracker.get_execution_summary()
    print(json.dumps(summary, indent=2))
    
    # Export to JSON
    json_data = tracker.export_to_json()
    print(json_data)
