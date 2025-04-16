"""
Timeline-Aware Agent Module

This module provides an agent implementation that integrates with the timeline feature.
It extends the base agent with timeline tracking capabilities.
"""

from typing import Dict, List, Any, Optional, Union
import json
from datetime import datetime

from app.timeline import (
    Timeline,
    TimelineEvent,
    EventType,
    TimelineTracker,
    TimelineStorage,
    FileTimelineStorage
)


class TimelineAwareAgent:
    """
    An agent that integrates with the timeline feature.
    This class can be used to extend any agent with timeline tracking capabilities.
    """
    
    def __init__(
        self,
        agent,
        storage: Optional[TimelineStorage] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        auto_save: bool = True
    ):
        """
        Initialize a timeline-aware agent.
        
        Args:
            agent: The agent to extend
            storage: Storage for timelines
            conversation_id: ID of the conversation
            user_id: ID of the user
            auto_save: Whether to automatically save the timeline
        """
        self.agent = agent
        
        # Create storage if not provided
        if storage is None:
            import os
            storage_dir = os.path.join("data", "timelines")
            os.makedirs(storage_dir, exist_ok=True)
            storage = FileTimelineStorage(storage_dir)
        
        # Create tracker
        self.tracker = TimelineTracker(
            storage=storage,
            conversation_id=conversation_id,
            user_id=user_id,
            auto_save=auto_save
        )
        
        # Add agent start event
        self.tracker.add_event(
            event_type=EventType.AGENT_START,
            title="Agent Started",
            description=f"Agent initialized with conversation ID: {conversation_id}",
            metadata={
                "agent_type": type(agent).__name__,
                "conversation_id": conversation_id,
                "user_id": user_id
            }
        )
    
    def process_message(self, message: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Process a message, tracking the interaction in the timeline.
        
        Args:
            message: The message to process
            **kwargs: Additional arguments to pass to the agent
            
        Returns:
            Dict[str, Any]: The agent's response
        """
        # Add user message event
        user_event_id = self.tracker.add_event(
            event_type=EventType.USER_MESSAGE,
            title="User Message",
            description=message.get("content", ""),
            metadata={
                "message": message
            }
        )
        
        # Start agent thinking event
        thinking_event_id = self.tracker.start_event(
            event_type=EventType.AGENT_THINKING,
            title="Agent Thinking",
            description="Agent is processing the message",
            parent_id=user_event_id
        )
        
        try:
            # Process the message with the agent
            response = self.agent.process_message(message, **kwargs)
            
            # End agent thinking event
            self.tracker.end_event(
                event_id=thinking_event_id,
                status="completed"
            )
            
            # Add agent response event
            self.tracker.add_event(
                event_type=EventType.AGENT_RESPONSE,
                title="Agent Response",
                description=response.get("content", ""),
                parent_id=user_event_id,
                metadata={
                    "response": response
                }
            )
            
            return response
        except Exception as e:
            # End agent thinking event with error
            self.tracker.end_event(
                event_id=thinking_event_id,
                status="failed",
                metadata={
                    "error": str(e)
                }
            )
            
            # Add agent error event
            self.tracker.add_event(
                event_type=EventType.AGENT_ERROR,
                title="Agent Error",
                description=f"Error processing message: {str(e)}",
                parent_id=user_event_id,
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            
            # Re-raise the exception
            raise
    
    def track_tool_call(
        self,
        tool_name: str,
        tool_input: Any,
        parent_id: Optional[str] = None
    ) -> str:
        """
        Track a tool call in the timeline.
        
        Args:
            tool_name: Name of the tool
            tool_input: Input to the tool
            parent_id: ID of the parent event
            
        Returns:
            str: ID of the tool call event
        """
        # Start tool call event
        return self.tracker.start_event(
            event_type=EventType.TOOL_CALL,
            title=f"Tool Call: {tool_name}",
            description=f"Calling tool: {tool_name}",
            parent_id=parent_id,
            metadata={
                "tool_name": tool_name,
                "tool_input": tool_input
            }
        )
    
    def track_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        success: bool = True
    ):
        """
        Track a tool result in the timeline.
        
        Args:
            tool_call_id: ID of the tool call event
            result: Result from the tool
            success: Whether the tool call was successful
        """
        # End tool call event
        self.tracker.end_event(
            event_id=tool_call_id,
            status="completed" if success else "failed",
            metadata={
                "result": result,
                "success": success
            }
        )
        
        # Add tool result event
        self.tracker.add_event(
            event_type=EventType.TOOL_RESULT,
            title="Tool Result",
            description=str(result)[:100] + ("..." if len(str(result)) > 100 else ""),
            parent_id=tool_call_id,
            metadata={
                "result": result,
                "success": success
            }
        )
    
    def track_plan_created(
        self,
        plan: Dict[str, Any],
        parent_id: Optional[str] = None
    ) -> str:
        """
        Track a plan creation in the timeline.
        
        Args:
            plan: The created plan
            parent_id: ID of the parent event
            
        Returns:
            str: ID of the plan created event
        """
        return self.tracker.add_event(
            event_type=EventType.PLAN_CREATED,
            title="Plan Created",
            description=plan.get("description", ""),
            parent_id=parent_id,
            metadata={
                "plan": plan
            }
        )
    
    def track_plan_updated(
        self,
        plan_id: str,
        plan: Dict[str, Any],
        parent_id: Optional[str] = None
    ) -> str:
        """
        Track a plan update in the timeline.
        
        Args:
            plan_id: ID of the plan
            plan: The updated plan
            parent_id: ID of the parent event
            
        Returns:
            str: ID of the plan updated event
        """
        return self.tracker.add_event(
            event_type=EventType.PLAN_UPDATED,
            title="Plan Updated",
            description=f"Plan {plan_id} updated",
            parent_id=parent_id,
            metadata={
                "plan_id": plan_id,
                "plan": plan
            }
        )
    
    def track_plan_executed(
        self,
        plan_id: str,
        parent_id: Optional[str] = None
    ) -> str:
        """
        Track a plan execution in the timeline.
        
        Args:
            plan_id: ID of the plan
            parent_id: ID of the parent event
            
        Returns:
            str: ID of the plan executed event
        """
        return self.tracker.start_event(
            event_type=EventType.PLAN_EXECUTED,
            title="Plan Executed",
            description=f"Executing plan {plan_id}",
            parent_id=parent_id,
            metadata={
                "plan_id": plan_id
            }
        )
    
    def track_task_started(
        self,
        task: Dict[str, Any],
        parent_id: Optional[str] = None
    ) -> str:
        """
        Track a task start in the timeline.
        
        Args:
            task: The task to start
            parent_id: ID of the parent event
            
        Returns:
            str: ID of the task started event
        """
        return self.tracker.start_event(
            event_type=EventType.TASK_STARTED,
            title=f"Task Started: {task.get('title', '')}",
            description=task.get("description", ""),
            parent_id=parent_id,
            metadata={
                "task": task
            }
        )
    
    def track_task_completed(
        self,
        task_id: str,
        result: Any
    ):
        """
        Track a task completion in the timeline.
        
        Args:
            task_id: ID of the task
            result: Result of the task
        """
        self.tracker.end_event(
            event_id=task_id,
            status="completed",
            metadata={
                "result": result
            }
        )
        
        self.tracker.add_event(
            event_type=EventType.TASK_COMPLETED,
            title="Task Completed",
            description=str(result)[:100] + ("..." if len(str(result)) > 100 else ""),
            parent_id=task_id,
            metadata={
                "result": result
            }
        )
    
    def track_task_failed(
        self,
        task_id: str,
        error: Any
    ):
        """
        Track a task failure in the timeline.
        
        Args:
            task_id: ID of the task
            error: Error that occurred
        """
        self.tracker.end_event(
            event_id=task_id,
            status="failed",
            metadata={
                "error": str(error)
            }
        )
        
        self.tracker.add_event(
            event_type=EventType.TASK_FAILED,
            title="Task Failed",
            description=str(error),
            parent_id=task_id,
            metadata={
                "error": str(error),
                "error_type": type(error).__name__
            }
        )
    
    def get_timeline(self) -> Timeline:
        """
        Get the current timeline.
        
        Returns:
            Timeline: Current timeline
        """
        return self.tracker.get_timeline()
    
    def save_timeline(self) -> bool:
        """
        Save the timeline to storage.
        
        Returns:
            bool: True if the timeline was saved, False otherwise
        """
        return self.tracker.save_timeline()
    
    def __del__(self):
        """Clean up when the agent is destroyed."""
        # Add agent stop event
        try:
            self.tracker.add_event(
                event_type=EventType.AGENT_STOP,
                title="Agent Stopped",
                description="Agent was destroyed",
                metadata={
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Save timeline
            self.tracker.save_timeline()
        except:
            # Ignore errors during cleanup
            pass
