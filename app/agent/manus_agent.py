"""Manus-like agent for Nexagent.

This module provides a versatile agent that can handle complex tasks with visible thinking
processes, supporting use cases like data analysis, travel planning, research, and more.

Enhanced with timeline tracking, memory reasoning, and advanced planning capabilities.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.manus import SYSTEM_PROMPT
from app.schema import AgentState
from app.tools import ToolCollection
from app.tools.browser import WebSearch, EnhancedBrowserTool, BrowserUseTool
from app.tools.code import PythonExecute
from app.tools.file_saver import FileSaver
from app.tools.planning import PlanningTool
from app.tools.terminate import Terminate
from app.timeline.models import Timeline, EventType
from app.timeline.tracker import TimelineTracker
from app.memory.memory_reasoning import MemoryReasoning
from app.logger import logger


class ManusAgent(ToolCallAgent):
    """A versatile agent that can handle complex tasks with visible thinking processes.

    This agent extends ToolCallAgent with enhanced capabilities for task interpretation,
    thought process visibility, and action execution across various domains including
    data analysis, travel planning, research, and more.

    Enhanced with timeline tracking, memory reasoning, and advanced planning capabilities.
    """

    name: str = "ManusAgent"
    description: str = (
        "A versatile agent that can solve complex tasks with visible thinking processes"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = """
    You are now working on the following task: {task}

    Think step by step about how to approach this task. Break it down into smaller steps if needed.
    Consider what information you need to gather and what actions you need to take.

    You have access to the following tools:
    - PythonExecute: For data analysis, calculations, and processing
    - WebSearch: For retrieving information from the web
    - EnhancedBrowserTool: For navigating websites and extracting information
    - BrowserUseTool: For more advanced browser interactions
    - FileSaver: For saving results and outputs
    - PlanningTool: For creating and managing plans
    - Terminate: For ending the task when complete

    Show your thinking process as you work through this task.
    """

    max_observe: int = 3000  # Increased from 2000 to allow for more comprehensive observations
    max_steps: int = 50  # Increased from 30 to allow for more complex tasks

    # Track thought visibility preference
    show_thinking: bool = Field(default=True, description="Whether to show thinking process")

    # Store the current task
    current_task: str = Field(default="", description="The current task being processed")

    # Track thought history for analysis
    thought_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of thinking steps"
    )

    # Timeline tracking
    timeline: Optional[Timeline] = Field(default=None, description="Timeline for tracking events")
    timeline_tracker: Optional[TimelineTracker] = Field(default=None, description="Timeline tracker")

    # Memory reasoning
    memory_reasoning: Optional[MemoryReasoning] = Field(default=None, description="Memory reasoning system")

    # Conversation tracking
    conversation_id: Optional[str] = Field(default=None, description="ID of the current conversation")
    user_id: Optional[str] = Field(default=None, description="ID of the current user")

    # Websocket for broadcasting updates
    websocket: Any = Field(default=None, description="Websocket for broadcasting updates")

    # Add comprehensive tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            WebSearch(),
            EnhancedBrowserTool(),
            BrowserUseTool(),
            FileSaver(),
            PlanningTool(),
            Terminate()
        )
    )

    def __init__(self, **data):
        """Initialize the ManusAgent."""
        super().__init__(**data)

        # Initialize conversation ID if not provided
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())

        # Initialize timeline
        self.timeline = Timeline(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            metadata={"agent_type": "manus_agent"}
        )

        # Initialize timeline tracker
        self.timeline_tracker = TimelineTracker(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            auto_save=True
        )

        # Initialize memory reasoning
        self.memory_reasoning = MemoryReasoning(max_memories=1000)

        logger.info("ManusAgent initialized with timeline and memory capabilities")

    async def set_task(self, task: str) -> None:
        """Set the current task and initialize the agent.

        Args:
            task: The task description to process
        """
        self.current_task = task
        self.thought_history = []
        self.state = AgentState.IDLE
        self.current_step = 0

        # Add the task to memory
        if self.memory_reasoning:
            self.memory_reasoning.add_memory(
                content=task,
                source="user",
                importance=0.8,
                metadata={"type": "task", "timestamp": datetime.now().isoformat()}
            )
        else:
            # Fallback to standard memory update
            self.update_memory("user", task)

        # Add task to timeline
        if self.timeline_tracker:
            self.timeline_tracker.add_event(
                event_type=EventType.USER_MESSAGE,
                title="User Task",
                description=task,
                metadata={"type": "task"}
            )

        # Format the next step prompt with the task
        self.next_step_prompt = self.next_step_prompt.format(task=task)

        logger.info(f"Task set: {task[:50]}...")

    async def toggle_thinking_visibility(self, show: bool) -> None:
        """Toggle the visibility of the thinking process.

        Args:
            show: Whether to show the thinking process
        """
        self.show_thinking = show

    async def think(self) -> bool:
        """Process current state and decide next actions using tools.

        This overrides the parent method to add thought tracking functionality.

        Returns:
            bool: Whether the agent should proceed to act
        """
        # Start a thinking event in the timeline
        thinking_event_id = None
        if self.timeline_tracker:
            thinking_event_id = self.timeline_tracker.start_event(
                event_type=EventType.AGENT_THINKING,
                title=f"Thinking Step {self.current_step}",
                description="Agent is analyzing the current state and deciding next actions",
                metadata={"step": self.current_step}
            )

        # Call the parent think method
        should_act = await super().think()

        # Extract and store the thinking process from the last assistant message
        if self.messages and self.messages[-1].role == "assistant" and self.messages[-1].content:
            thought = {
                "step": self.current_step,
                "content": self.messages[-1].content,
                "timestamp": datetime.now().isoformat(),
            }
            self.thought_history.append(thought)

            # Add to memory
            if self.memory_reasoning:
                self.memory_reasoning.add_memory(
                    content=self.messages[-1].content,
                    source="agent",
                    importance=0.6,
                    metadata={"type": "thinking", "step": self.current_step}
                )

            # If thinking should be visible, log it
            if self.show_thinking:
                print(f"\n[Thinking Step {self.current_step}]\n{thought['content']}\n")

        # End the thinking event in the timeline
        if self.timeline_tracker and thinking_event_id:
            self.timeline_tracker.end_event(
                event_id=thinking_event_id,
                status="completed",
                metadata={"result": "Thinking completed"}
            )

        return should_act

    async def get_thinking_summary(self) -> str:
        """Generate a summary of the thinking process.

        Returns:
            str: A summary of the key thinking steps
        """
        if not self.thought_history:
            return "No thinking steps recorded yet."

        # Create a summary of the thinking process
        summary = "Thinking Process Summary:\n\n"
        for i, thought in enumerate(self.thought_history):
            summary += f"Step {i+1}: {thought['content'][:100]}...\n"

        return summary

    async def act(self) -> bool:
        """Execute the selected action using tools.

        This overrides the parent method to add action tracking functionality.

        Returns:
            bool: Whether the agent should proceed to observe
        """
        # Start an action event in the timeline
        action_event_id = None
        if self.timeline_tracker:
            action_event_id = self.timeline_tracker.start_event(
                event_type=EventType.TOOL_CALL,
                title=f"Action Step {self.current_step}",
                description="Agent is executing an action using tools",
                metadata={"step": self.current_step}
            )

        # Call the parent act method
        should_observe = await super().act()

        # End the action event in the timeline
        if self.timeline_tracker and action_event_id:
            self.timeline_tracker.end_event(
                event_id=action_event_id,
                status="completed",
                metadata={"result": "Action completed"}
            )

        return should_observe

    async def observe(self) -> bool:
        """Observe the results of the action.

        This overrides the parent method to add observation tracking functionality.

        Returns:
            bool: Whether the agent should proceed to the next step
        """
        # Start an observation event in the timeline
        observation_event_id = None
        if self.timeline_tracker:
            observation_event_id = self.timeline_tracker.start_event(
                event_type=EventType.TOOL_RESULT,
                title=f"Observation Step {self.current_step}",
                description="Agent is observing the results of the action",
                metadata={"step": self.current_step}
            )

        # Call the parent observe method
        should_continue = await super().observe()

        # End the observation event in the timeline
        if self.timeline_tracker and observation_event_id:
            self.timeline_tracker.end_event(
                event_id=observation_event_id,
                status="completed",
                metadata={"result": "Observation completed"}
            )

        return should_continue

    async def get_relevant_memories(self, context: str, limit: int = 5) -> str:
        """Get memories relevant to the given context.

        Args:
            context: The context to find relevant memories for
            limit: Maximum number of memories to return

        Returns:
            str: A formatted string of relevant memories
        """
        if not self.memory_reasoning:
            return "Memory reasoning system not initialized."

        memories = self.memory_reasoning.get_relevant_memories(context, limit)

        if not memories:
            return "No relevant memories found."

        # Format the memories
        result = "Relevant Memories:\n\n"
        for i, memory in enumerate(memories):
            result += f"{i+1}. [{memory.source}] {memory.content[:100]}...\n"

        return result

    async def get_timeline_summary(self) -> str:
        """Generate a summary of the timeline.

        Returns:
            str: A summary of the timeline events
        """
        if not self.timeline_tracker:
            return "Timeline tracker not initialized."

        # Get all events
        events = self.timeline_tracker.timeline.events

        if not events:
            return "No timeline events recorded yet."

        # Format the timeline summary
        summary = "Timeline Summary:\n\n"
        for i, event in enumerate(events):
            event_type = event.event_type
            title = event.title
            status = event.status or "unknown"
            duration = f"{event.duration:.2f}s" if event.duration else "N/A"

            summary += f"{i+1}. [{event_type}] {title} - Status: {status}, Duration: {duration}\n"

        return summary

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop with enhanced reporting.

        Args:
            request: Optional initial user request to process

        Returns:
            str: A summary of the execution results with thinking process if enabled
        """
        # Start a task event in the timeline
        task_event_id = None
        if self.timeline_tracker:
            task_event_id = self.timeline_tracker.start_event(
                event_type=EventType.TASK_STARTED,
                title="Task Execution",
                description=request or self.current_task,
                metadata={"type": "task_execution"}
            )

        # If a request is provided, set it as the current task
        if request and not self.current_task:
            await self.set_task(request)
        elif request:
            # Update the current task and memory
            self.current_task = request

            # Add to memory
            if self.memory_reasoning:
                self.memory_reasoning.add_memory(
                    content=request,
                    source="user",
                    importance=0.8,
                    metadata={"type": "request"}
                )
            else:
                self.update_memory("user", request)

        # Run the standard execution loop
        result = await super().run()

        # Add thinking process summary if enabled
        if self.show_thinking and self.thought_history:
            thinking_summary = await self.get_thinking_summary()
            result = f"{result}\n\n{thinking_summary}"

        # End the task event in the timeline
        if self.timeline_tracker and task_event_id:
            self.timeline_tracker.end_event(
                event_id=task_event_id,
                status="completed",
                metadata={"result": result[:500] + "..." if len(result) > 500 else result}
            )

        return result

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and cleanup.

        Args:
            name: The name of the tool
            result: The result of the tool execution
            **kwargs: Additional arguments
        """
        if not self._is_special_tool(name):
            return
        else:
            # Clean up browser if it was used
            browser_tools = [
                tool for tool in self.available_tools.tools
                if hasattr(tool, "name") and "browser" in tool.name.lower()
            ]

            for tool in browser_tools:
                if hasattr(tool, "cleanup"):
                    await tool.cleanup()

            await super()._handle_special_tool(name, result, **kwargs)