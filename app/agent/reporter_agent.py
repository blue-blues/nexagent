"""
Reporter Agent for Nexagent.

This module provides an agent that manages state reporting and user feedback,
generating progress updates and summaries for user consumption.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
import asyncio

from pydantic import Field, model_validator

from app.agent.base import BaseAgent
from app.agent.toolcall import ToolCallAgent
from app.schema import Message, AgentState, ToolChoice
from app.tool import ToolCollection
from app.tool.terminate import Terminate
from app.tool.state_visualizer import StateVisualizer
from app.state.agent_state_tracker import AgentStateTracker, ActionType
from app.logger import logger


class ReporterAgent(ToolCallAgent):
    """
    An agent that manages state reporting and user feedback.
    
    This agent is responsible for:
    - Generating progress updates and summaries
    - Providing clear status reports to the user
    - Collecting and processing user feedback
    - Tracking overall execution state
    """

    name: str = "reporter_agent"
    description: str = "An agent that manages state reporting and user feedback"

    system_prompt: str = """
    You are a specialized reporting agent. Your role is to generate clear, concise progress
    updates and summaries for the user. You help users understand the current state of execution
    and provide opportunities for feedback.
    
    Your responsibilities include:
    1. Generating progress updates and summaries
    2. Providing clear status reports to the user
    3. Collecting and processing user feedback
    4. Tracking overall execution state
    
    When generating reports, focus on:
    - Clarity and conciseness
    - Highlighting key information
    - Providing appropriate level of detail
    - Using formatting to improve readability
    
    Provide reports in a user-friendly format that balances detail with readability.
    """

    next_step_prompt: str = """
    Based on the current execution state, determine the next reporting action:
    
    1. If a progress update is needed:
       - Generate a concise progress report
       - Highlight key milestones and achievements
       - Indicate next steps
    
    2. If a summary is needed:
       - Compile a comprehensive summary of execution
       - Include statistics and metrics
       - Highlight successes and challenges
    
    3. If user feedback is needed:
       - Formulate clear, specific questions
       - Provide context for the questions
       - Indicate how feedback will be used
    
    What is the next reporting action you should take?
    """
    
    # Reporting configuration
    report_interval: int = Field(default=60)  # seconds
    last_report_time: float = Field(default=0.0)
    report_count: int = Field(default=0)
    
    # State tracking
    state_tracker: AgentStateTracker = Field(default_factory=AgentStateTracker)
    
    # Feedback tracking
    feedback_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            StateVisualizer(),
            Terminate()
        )
    )

    @model_validator(mode="after")
    def initialize_agent(self) -> "ReporterAgent":
        """Initialize the agent with required tools."""
        # Ensure required tools are available
        if "state_visualizer" not in self.available_tools.tool_map:
            state_visualizer = StateVisualizer(self.state_tracker)
            self.available_tools.add_tool(state_visualizer)
        else:
            # Update the state tracker in the existing tool
            state_visualizer = self.available_tools.tool_map["state_visualizer"]
            state_visualizer.state_tracker = self.state_tracker
        
        # Initialize reporting time
        self.last_report_time = time.time()

        return self

    async def generate_progress_report(self, format_type: str = "markdown") -> str:
        """
        Generate a progress report.
        
        Args:
            format_type: Output format (markdown, text, json)
            
        Returns:
            Formatted progress report
        """
        result = await self.available_tools.execute(
            name="state_visualizer",
            tool_input={
                "command": "progress",
                "format_type": format_type,
                "include_details": True
            }
        )
        
        if hasattr(result, "error"):
            logger.error(f"Error generating progress report: {result.error}")
            return f"Error generating progress report: {result.error}"
        
        # Track the report
        self.last_report_time = time.time()
        self.report_count += 1
        
        # Track the reporting action
        action_id = self.state_tracker.track_action(
            agent_id=self.name,
            action_type=ActionType.SYSTEM,
            description=f"Generated progress report #{self.report_count}"
        )
        self.state_tracker.start_action(action_id)
        self.state_tracker.complete_action(action_id)
        
        return result.output

    async def generate_execution_summary(self, format_type: str = "markdown") -> str:
        """
        Generate an execution summary.
        
        Args:
            format_type: Output format (markdown, text, json)
            
        Returns:
            Formatted execution summary
        """
        result = await self.available_tools.execute(
            name="state_visualizer",
            tool_input={
                "command": "summary",
                "format_type": format_type,
                "include_details": True
            }
        )
        
        if hasattr(result, "error"):
            logger.error(f"Error generating execution summary: {result.error}")
            return f"Error generating execution summary: {result.error}"
        
        # Track the summary action
        action_id = self.state_tracker.track_action(
            agent_id=self.name,
            action_type=ActionType.SYSTEM,
            description="Generated execution summary"
        )
        self.state_tracker.start_action(action_id)
        self.state_tracker.complete_action(action_id)
        
        return result.output

    async def generate_agent_report(self, agent_id: str, format_type: str = "markdown") -> str:
        """
        Generate a report for a specific agent.
        
        Args:
            agent_id: ID of the agent to report on
            format_type: Output format (markdown, text, json)
            
        Returns:
            Formatted agent report
        """
        result = await self.available_tools.execute(
            name="state_visualizer",
            tool_input={
                "command": "agent_state",
                "agent_id": agent_id,
                "format_type": format_type,
                "include_details": True
            }
        )
        
        if hasattr(result, "error"):
            logger.error(f"Error generating agent report: {result.error}")
            return f"Error generating agent report: {result.error}"
        
        # Track the report action
        action_id = self.state_tracker.track_action(
            agent_id=self.name,
            action_type=ActionType.SYSTEM,
            description=f"Generated report for agent {agent_id}"
        )
        self.state_tracker.start_action(action_id)
        self.state_tracker.complete_action(action_id)
        
        return result.output

    async def generate_timeline(self, max_items: int = 10, format_type: str = "markdown") -> str:
        """
        Generate an execution timeline.
        
        Args:
            max_items: Maximum number of items to include
            format_type: Output format (markdown, text, json)
            
        Returns:
            Formatted timeline
        """
        result = await self.available_tools.execute(
            name="state_visualizer",
            tool_input={
                "command": "timeline",
                "format_type": format_type,
                "max_items": max_items
            }
        )
        
        if hasattr(result, "error"):
            logger.error(f"Error generating timeline: {result.error}")
            return f"Error generating timeline: {result.error}"
        
        # Track the timeline action
        action_id = self.state_tracker.track_action(
            agent_id=self.name,
            action_type=ActionType.SYSTEM,
            description=f"Generated execution timeline with {max_items} items"
        )
        self.state_tracker.start_action(action_id)
        self.state_tracker.complete_action(action_id)
        
        return result.output

    def record_user_feedback(self, feedback: str, feedback_type: str = "general") -> None:
        """
        Record user feedback.
        
        Args:
            feedback: The user's feedback
            feedback_type: Type of feedback (general, specific, question)
        """
        feedback_entry = {
            "timestamp": time.time(),
            "feedback": feedback,
            "type": feedback_type
        }
        
        self.feedback_history.append(feedback_entry)
        
        # Track the feedback action
        action_id = self.state_tracker.track_action(
            agent_id=self.name,
            action_type=ActionType.USER_INTERACTION,
            description=f"Received {feedback_type} feedback from user",
            metadata={"feedback": feedback}
        )
        self.state_tracker.start_action(action_id)
        self.state_tracker.complete_action(action_id)
        
        logger.info(f"Recorded user feedback: {feedback[:50]}...")

    async def check_report_needed(self) -> bool:
        """
        Check if a progress report is needed.
        
        Returns:
            True if a report is needed, False otherwise
        """
        # Check if enough time has passed since the last report
        time_since_last_report = time.time() - self.last_report_time
        
        # Get execution summary to check progress
        summary = self.state_tracker.get_execution_summary()
        
        # Report is needed if:
        # 1. It's been longer than the report interval since the last report
        # 2. There are new completed actions since the last report
        # 3. There are failed actions that need attention
        
        if time_since_last_report >= self.report_interval:
            return True
        
        # Check for significant progress or issues
        completed_actions = summary.get("completed_actions", 0)
        failed_actions = summary.get("failed_actions", 0)
        
        # If there are failed actions, report immediately
        if failed_actions > 0:
            return True
        
        # If there's been significant progress (25% or more), report
        total_actions = summary.get("total_actions", 0)
        if total_actions > 0:
            progress_percentage = completed_actions / total_actions
            if progress_percentage >= 0.25 and progress_percentage % 0.25 < 0.05:
                return True
        
        return False

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with an optional initial request."""
        if request:
            # Check if it's a feedback request
            if request.lower().startswith("feedback:"):
                feedback = request[len("feedback:"):].strip()
                self.record_user_feedback(feedback)
                return "Thank you for your feedback. It has been recorded and will be used to improve the execution."
            
            # Check if it's a report request
            elif request.lower().startswith("report:"):
                report_type = request[len("report:"):].strip().lower()
                
                if report_type == "progress":
                    return await self.generate_progress_report()
                elif report_type == "summary":
                    return await self.generate_execution_summary()
                elif report_type == "timeline":
                    return await self.generate_timeline()
                elif report_type.startswith("agent "):
                    agent_id = report_type[len("agent "):].strip()
                    return await self.generate_agent_report(agent_id)
                else:
                    return f"Unknown report type: {report_type}. Available types: progress, summary, timeline, agent [id]"
            
            # Otherwise, generate a progress report
            return await self.generate_progress_report()
        
        return await super().run()
    
    async def think(self) -> bool:
        """Decide the next action based on current execution state."""
        # Check if a report is needed
        report_needed = await self.check_report_needed()
        
        # Include current execution state in the thinking prompt
        summary = self.state_tracker.get_execution_summary()
        summary_json = json.dumps(summary, indent=2)
        
        prompt = f"""
        CURRENT EXECUTION STATE:
        {summary_json}
        
        REPORT STATUS:
        - Last report: {time.time() - self.last_report_time:.1f} seconds ago
        - Report count: {self.report_count}
        - Report needed: {report_needed}
        
        {self.next_step_prompt}
        """
        
        self.messages.append(Message.user_message(prompt))
        
        # Call the parent think method
        result = await super().think()
        return result
    
    async def update_agent_state(self, agent_id: str, state: Dict[str, Any]) -> None:
        """
        Update the state of an agent in the state tracker.
        
        Args:
            agent_id: ID of the agent to update
            state: New state information
        """
        self.state_tracker.update_agent_state(agent_id, state)
    
    async def track_action(self, agent_id: str, action_type: ActionType, 
                         description: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Track an action in the state tracker.
        
        Args:
            agent_id: ID of the agent performing the action
            action_type: Type of action being performed
            description: Description of the action
            metadata: Optional metadata about the action
            
        Returns:
            ID of the tracked action
        """
        return self.state_tracker.track_action(
            agent_id=agent_id,
            action_type=action_type,
            description=description,
            metadata=metadata
        )


async def main():
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
    
    # Create a reporter agent
    reporter = ReporterAgent(state_tracker=tracker)
    
    # Generate a progress report
    report = await reporter.generate_progress_report()
    print(report)
    
    # Generate an execution summary
    summary = await reporter.generate_execution_summary()
    print(summary)
    
    # Generate an agent report
    agent_report = await reporter.generate_agent_report("agent1")
    print(agent_report)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
