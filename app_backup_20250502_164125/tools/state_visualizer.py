"""
State Visualizer Tool for Nexagent.

This tool provides functionality for visualizing agent state and execution progress,
generating formatted reports and summaries for user consumption.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
from pydantic import Field

from app.tool.base import BaseTool, ToolResult
from app.state.agent_state_tracker import AgentStateTracker, ActionType, ActionStatus
from app.logger import logger


class StateVisualizer(BaseTool):
    """
    Tool for visualizing agent state and execution progress.
    
    This tool generates formatted reports, summaries, and visualizations
    of agent state and execution progress for user consumption.
    """
    
    name: str = "state_visualizer"
    description: str = """
    Visualize agent state and execution progress.
    This tool generates formatted reports, summaries, and visualizations
    of agent state and execution progress for user consumption.
    """
    
    def __init__(self, state_tracker: Optional[AgentStateTracker] = None):
        """
        Initialize the state visualizer tool.
        
        Args:
            state_tracker: Optional state tracker instance to use
        """
        super().__init__()
        self.state_tracker = state_tracker or AgentStateTracker()
    
    async def execute(self, command: str, format_type: str = "text",
                     agent_id: Optional[str] = None,
                     include_details: bool = False,
                     max_items: int = 10) -> ToolResult:
        """
        Execute the state visualizer tool.
        
        Args:
            command: The command to execute (summary, timeline, agent_state, progress)
            format_type: Output format (text, json, markdown)
            agent_id: Optional agent ID to filter by
            include_details: Whether to include detailed information
            max_items: Maximum number of items to include
            
        Returns:
            ToolResult containing the visualization
        """
        try:
            if command == "summary":
                result = self._generate_summary(format_type, include_details)
                return ToolResult(output=result)
                
            elif command == "timeline":
                result = self._generate_timeline(format_type, agent_id, max_items)
                return ToolResult(output=result)
                
            elif command == "agent_state":
                if not agent_id:
                    return ToolResult(error="agent_id is required for agent_state command")
                
                result = self._generate_agent_state(agent_id, format_type, include_details)
                return ToolResult(output=result)
                
            elif command == "progress":
                result = self._generate_progress_report(format_type, include_details)
                return ToolResult(output=result)
                
            else:
                return ToolResult(error=f"Unknown command: {command}")
                
        except Exception as e:
            logger.error(f"Error in StateVisualizer: {str(e)}")
            return ToolResult(error=f"Failed to visualize state: {str(e)}")
    
    def _generate_summary(self, format_type: str, include_details: bool) -> str:
        """
        Generate a summary of the execution.
        
        Args:
            format_type: Output format
            include_details: Whether to include detailed information
            
        Returns:
            Formatted summary
        """
        summary = self.state_tracker.get_execution_summary()
        
        if format_type == "json":
            return json.dumps(summary, indent=2)
        
        elif format_type == "markdown":
            md = "# Execution Summary\n\n"
            md += f"**Session ID:** {summary['session_id']}\n"
            md += f"**Execution Time:** {summary['execution_time']:.2f} seconds\n\n"
            
            md += "## Progress\n"
            md += f"- Total Actions: {summary['total_actions']}\n"
            md += f"- Completed: {summary['completed_actions']} ({summary['completion_rate']*100:.1f}%)\n"
            md += f"- Failed: {summary['failed_actions']}\n"
            md += f"- In Progress: {summary['in_progress_actions']}\n\n"
            
            if include_details:
                md += "## Action Types\n"
                for action_type, count in summary['action_types'].items():
                    md += f"- {action_type}: {count}\n"
                
                md += "\n## Agent Activity\n"
                for agent_id, count in summary['agent_activity'].items():
                    md += f"- {agent_id}: {count} actions\n"
            
            return md
        
        else:  # text
            text = "=== Execution Summary ===\n\n"
            text += f"Session ID: {summary['session_id']}\n"
            text += f"Execution Time: {summary['execution_time']:.2f} seconds\n\n"
            
            text += "Progress:\n"
            text += f"- Total Actions: {summary['total_actions']}\n"
            text += f"- Completed: {summary['completed_actions']} ({summary['completion_rate']*100:.1f}%)\n"
            text += f"- Failed: {summary['failed_actions']}\n"
            text += f"- In Progress: {summary['in_progress_actions']}\n\n"
            
            if include_details:
                text += "Action Types:\n"
                for action_type, count in summary['action_types'].items():
                    text += f"- {action_type}: {count}\n"
                
                text += "\nAgent Activity:\n"
                for agent_id, count in summary['agent_activity'].items():
                    text += f"- {agent_id}: {count} actions\n"
            
            return text
    
    def _generate_timeline(self, format_type: str, agent_id: Optional[str], max_items: int) -> str:
        """
        Generate a timeline of the execution.
        
        Args:
            format_type: Output format
            agent_id: Optional agent ID to filter by
            max_items: Maximum number of items to include
            
        Returns:
            Formatted timeline
        """
        timeline = self.state_tracker.get_execution_timeline()
        
        # Filter by agent_id if provided
        if agent_id:
            timeline = [entry for entry in timeline if entry["agent_id"] == agent_id]
        
        # Limit to max_items
        timeline = timeline[-max_items:] if len(timeline) > max_items else timeline
        
        if format_type == "json":
            return json.dumps(timeline, indent=2)
        
        elif format_type == "markdown":
            md = "# Execution Timeline\n\n"
            
            if agent_id:
                md += f"*Filtered by agent: {agent_id}*\n\n"
            
            md += "| Time | Agent | Action | Status | Duration |\n"
            md += "|------|-------|--------|--------|----------|\n"
            
            for entry in timeline:
                timestamp = time.strftime("%H:%M:%S", time.localtime(entry["timestamp"]))
                duration = f"{entry['duration']:.2f}s" if entry["duration"] else "N/A"
                
                md += f"| {timestamp} | {entry['agent_id']} | {entry['description'][:30]}... | {entry['status']} | {duration} |\n"
            
            return md
        
        else:  # text
            text = "=== Execution Timeline ===\n\n"
            
            if agent_id:
                text += f"Filtered by agent: {agent_id}\n\n"
            
            for entry in timeline:
                timestamp = time.strftime("%H:%M:%S", time.localtime(entry["timestamp"]))
                duration = f"{entry['duration']:.2f}s" if entry["duration"] else "N/A"
                
                text += f"[{timestamp}] {entry['agent_id']} - {entry['description'][:50]}\n"
                text += f"  Status: {entry['status']}, Duration: {duration}\n\n"
            
            return text
    
    def _generate_agent_state(self, agent_id: str, format_type: str, include_details: bool) -> str:
        """
        Generate a report of an agent's state.
        
        Args:
            agent_id: ID of the agent
            format_type: Output format
            include_details: Whether to include detailed information
            
        Returns:
            Formatted agent state report
        """
        agent_state = self.state_tracker.get_agent_state(agent_id)
        agent_actions = self.state_tracker.get_actions_by_agent(agent_id)
        
        # Sort actions by timestamp
        agent_actions = sorted(agent_actions, key=lambda a: a.timestamp)
        
        # Get recent actions
        recent_actions = agent_actions[-5:] if len(agent_actions) > 5 else agent_actions
        
        if format_type == "json":
            result = {
                "agent_id": agent_id,
                "state": agent_state,
                "action_count": len(agent_actions),
                "recent_actions": [action.dict() for action in recent_actions] if include_details else None
            }
            return json.dumps(result, indent=2)
        
        elif format_type == "markdown":
            md = f"# Agent State: {agent_id}\n\n"
            
            if agent_state:
                md += "## Current State\n"
                for key, value in agent_state.items():
                    if key != "last_updated":
                        md += f"**{key}:** {value}\n"
                
                if "last_updated" in agent_state:
                    last_updated = time.strftime("%H:%M:%S", time.localtime(agent_state["last_updated"]))
                    md += f"\n*Last updated: {last_updated}*\n"
            else:
                md += "*No state information available*\n"
            
            md += f"\n## Actions ({len(agent_actions)} total)\n"
            
            if include_details and recent_actions:
                md += "\n### Recent Actions\n"
                for action in recent_actions:
                    timestamp = time.strftime("%H:%M:%S", time.localtime(action.timestamp))
                    duration = f"{action.duration:.2f}s" if action.duration else "N/A"
                    
                    md += f"- **{timestamp}:** {action.description}\n"
                    md += f"  - Status: {action.status}, Duration: {duration}\n"
            
            return md
        
        else:  # text
            text = f"=== Agent State: {agent_id} ===\n\n"
            
            if agent_state:
                text += "Current State:\n"
                for key, value in agent_state.items():
                    if key != "last_updated":
                        text += f"{key}: {value}\n"
                
                if "last_updated" in agent_state:
                    last_updated = time.strftime("%H:%M:%S", time.localtime(agent_state["last_updated"]))
                    text += f"\nLast updated: {last_updated}\n"
            else:
                text += "No state information available\n"
            
            text += f"\nActions: {len(agent_actions)} total\n"
            
            if include_details and recent_actions:
                text += "\nRecent Actions:\n"
                for action in recent_actions:
                    timestamp = time.strftime("%H:%M:%S", time.localtime(action.timestamp))
                    duration = f"{action.duration:.2f}s" if action.duration else "N/A"
                    
                    text += f"[{timestamp}] {action.description}\n"
                    text += f"  Status: {action.status}, Duration: {duration}\n\n"
            
            return text
    
    def _generate_progress_report(self, format_type: str, include_details: bool) -> str:
        """
        Generate a progress report of the execution.
        
        Args:
            format_type: Output format
            include_details: Whether to include detailed information
            
        Returns:
            Formatted progress report
        """
        summary = self.state_tracker.get_execution_summary()
        
        # Calculate progress percentage
        total_actions = summary["total_actions"]
        completed_actions = summary["completed_actions"]
        progress_percentage = (completed_actions / total_actions * 100) if total_actions > 0 else 0
        
        # Get active agents
        active_agents = []
        for agent_id, state in self.state_tracker.agent_states.items():
            if "current_task" in state:
                active_agents.append({
                    "agent_id": agent_id,
                    "current_task": state["current_task"],
                    "progress": state.get("progress", 0)
                })
        
        if format_type == "json":
            result = {
                "progress_percentage": progress_percentage,
                "completed_actions": completed_actions,
                "total_actions": total_actions,
                "execution_time": summary["execution_time"],
                "active_agents": active_agents
            }
            return json.dumps(result, indent=2)
        
        elif format_type == "markdown":
            md = "# Execution Progress\n\n"
            
            md += f"**Overall Progress:** {progress_percentage:.1f}% ({completed_actions}/{total_actions} actions)\n"
            md += f"**Execution Time:** {summary['execution_time']:.2f} seconds\n\n"
            
            # Create a progress bar
            progress_bar_length = 20
            filled_length = int(progress_bar_length * progress_percentage / 100)
            bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
            md += f"Progress: |{bar}| {progress_percentage:.1f}%\n\n"
            
            if active_agents:
                md += "## Active Agents\n\n"
                for agent in active_agents:
                    md += f"**{agent['agent_id']}:** {agent['current_task']}\n"
                    
                    if "progress" in agent:
                        agent_progress = agent["progress"] * 100
                        agent_bar_length = int(progress_bar_length * agent_progress / 100)
                        agent_bar = "█" * agent_bar_length + "░" * (progress_bar_length - agent_bar_length)
                        md += f"Progress: |{agent_bar}| {agent_progress:.1f}%\n\n"
            
            return md
        
        else:  # text
            text = "=== Execution Progress ===\n\n"
            
            text += f"Overall Progress: {progress_percentage:.1f}% ({completed_actions}/{total_actions} actions)\n"
            text += f"Execution Time: {summary['execution_time']:.2f} seconds\n\n"
            
            # Create a progress bar
            progress_bar_length = 20
            filled_length = int(progress_bar_length * progress_percentage / 100)
            bar = "#" * filled_length + "-" * (progress_bar_length - filled_length)
            text += f"Progress: [{bar}] {progress_percentage:.1f}%\n\n"
            
            if active_agents:
                text += "Active Agents:\n\n"
                for agent in active_agents:
                    text += f"{agent['agent_id']}: {agent['current_task']}\n"
                    
                    if "progress" in agent:
                        agent_progress = agent["progress"] * 100
                        agent_bar_length = int(progress_bar_length * agent_progress / 100)
                        agent_bar = "#" * agent_bar_length + "-" * (progress_bar_length - agent_bar_length)
                        text += f"Progress: [{agent_bar}] {agent_progress:.1f}%\n\n"
            
            return text


# Example usage
if __name__ == "__main__":
    # Create a state tracker
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
    
    # Create a state visualizer
    visualizer = StateVisualizer(tracker)
    
    # Generate a summary
    summary = visualizer._generate_summary(format_type="markdown", include_details=True)
    print(summary)
    
    # Generate a timeline
    timeline = visualizer._generate_timeline(format_type="markdown", agent_id=None, max_items=10)
    print(timeline)
    
    # Generate an agent state report
    agent_state = visualizer._generate_agent_state(agent_id="agent1", format_type="markdown", include_details=True)
    print(agent_state)
    
    # Generate a progress report
    progress = visualizer._generate_progress_report(format_type="markdown", include_details=True)
    print(progress)
