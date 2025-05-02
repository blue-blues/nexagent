\"""Manus-like agent for Nexagent.

This module provides a versatile agent that can handle complex tasks with visible thinking
processes, supporting use cases like data analysis, travel planning, research, and more.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.manus import SYSTEM_PROMPT
from app.schema import AgentState, Message
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.python_execute import PythonExecute
from app.tool.web_search import WebSearch


class ManusAgent(ToolCallAgent):
    """A versatile agent that can handle complex tasks with visible thinking processes.
    
    This agent extends ToolCallAgent with enhanced capabilities for task interpretation,
    thought process visibility, and action execution across various domains including
    data analysis, travel planning, research, and more.
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
    - BrowserUseTool: For navigating websites and extracting information
    - FileSaver: For saving results and outputs
    
    Show your thinking process as you work through this task.
    """

    max_observe: int = 2000
    max_steps: int = 30
    
    # Track thought visibility preference
    show_thinking: bool = Field(default=True, description="Whether to show thinking process")
    
    # Store the current task
    current_task: str = Field(default="", description="The current task being processed")
    
    # Track thought history for analysis
    thought_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of thinking steps"
    )

    # Add comprehensive tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(), WebSearch(), BrowserUseTool(), FileSaver(), Terminate()
        )
    )

    async def set_task(self, task: str) -> None:
        """Set the current task and initialize the agent.
        
        Args:
            task: The task description to process
        """
        self.current_task = task
        self.thought_history = []
        self.state = AgentState.IDLE
        self.current_step = 0
        
        # Add the task to memory as a user message
        self.update_memory("user", task)
        
        # Format the next step prompt with the task
        self.next_step_prompt = self.next_step_prompt.format(task=task)

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
        # Call the parent think method
        should_act = await super().think()
        
        # Extract and store the thinking process from the last assistant message
        if self.messages and self.messages[-1].role == "assistant" and self.messages[-1].content:
            thought = {
                "step": self.current_step,
                "content": self.messages[-1].content,
                "timestamp": None,  # Could add timestamp if needed
            }
            self.thought_history.append(thought)
            
            # If thinking should be visible, log it
            if self.show_thinking:
                print(f"\n[Thinking Step {self.current_step}]\n{thought['content']}\n")
        
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

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop with enhanced reporting.
        
        Args:
            request: Optional initial user request to process
            
        Returns:
            str: A summary of the execution results with thinking process if enabled
        """
        # If a request is provided, set it as the current task
        if request and not self.current_task:
            await self.set_task(request)
        elif request:
            # Update the current task and memory
            self.current_task = request
            self.update_memory("user", request)
            
        # Run the standard execution loop
        result = await super().run()
        
        # Add thinking process summary if enabled
        if self.show_thinking and self.thought_history:
            thinking_summary = await self.get_thinking_summary()
            result = f"{result}\n\n{thinking_summary}"
            
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
            await self.available_tools.get_tool(BrowserUseTool().name).cleanup()
            await super()._handle_special_tool(name, result, **kwargs)