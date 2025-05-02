"""
Task-based Nexagent implementation.

This module provides a TaskBasedNexagent class that executes tasks using the planner's to-do list
rather than using a fixed number of steps.
"""

from datetime import datetime
import re
from typing import Dict, List, Optional, Any, Tuple

from pydantic import Field

from app.agent.task_based_toolcall import TaskBasedToolCallAgent
from app.agent.task_based_agent import Task
from app.logger import logger
from app.schema import Message
from app.tools import ToolCollection
from app.tools.code import PythonExecute, CodeAnalyzer
from app.tools.browser import WebSearch, EnhancedBrowserTool
from app.tools.file_saver import FileSaver
from app.tools.terminal import Terminal, EnhancedTerminal
from app.tools.data_processor import DataProcessor
from app.tools.output_formatter import OutputFormatter
from app.tools.message_notification import MessageNotifyUser, MessageAskUser
from app.tools.task_analytics import TaskAnalytics
from app.tools.planning import Planning
from app.tools.long_running_command import LongRunningCommand
from app.tools.terminate import Terminate


# System prompt for the Nexagent
SYSTEM_PROMPT = """You are Nexagent, an advanced AI assistant designed to solve complex tasks efficiently.
You have a powerful set of tools at your disposal to handle a wide variety of requests.
Whether it's coding, data analysis, information retrieval, file operations, or web browsing,
you can tackle any challenge presented by the user.

Your approach is to:
1. Understand the task thoroughly
2. Break it down into manageable steps
3. Use the appropriate tools to complete each step
4. Provide clear explanations of your process and results

You are designed to be helpful, accurate, and efficient in completing tasks.
"""

# Task prompt for the Nexagent
TASK_PROMPT = """Complete this task using the available tools.
Think step by step about how to approach this task.
If you want to stop interaction, use `terminate` tool/function call.
"""


class TaskBasedNexagent(TaskBasedToolCallAgent):
    """
    A task-based Nexagent that executes tasks using the planner's to-do list.

    This agent automatically breaks down complex tasks into manageable steps
    and executes them using the appropriate tools.
    """

    name: str = "task_based_nexagent"
    description: str = "A task-based Nexagent that executes tasks efficiently"

    system_prompt: str = SYSTEM_PROMPT
    task_prompt: str = TASK_PROMPT

    # Add comprehensive tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            # Code tools
            PythonExecute(),
            CodeAnalyzer(),

            # Browser tools
            WebSearch(),
            EnhancedBrowserTool(),

            # File and data tools
            FileSaver(),
            DataProcessor(),
            OutputFormatter(),

            # Terminal tools
            Terminal(),
            EnhancedTerminal(),
            LongRunningCommand(),

            # User interaction tools
            MessageNotifyUser(),
            MessageAskUser(),

            # Planning and analytics tools
            Planning(),
            TaskAnalytics(),

            # System tools
            Terminate()
        )
    )

    # Task history tracking
    task_history: List[Dict] = Field(default_factory=list)

    # Thinking process tracking
    show_thinking: bool = Field(default=True, description="Whether to show thinking process")
    thought_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of thinking steps"
    )

    async def _create_initial_tasks(self, request: str) -> None:
        """Create initial tasks from the request by analyzing it and breaking it down."""
        # First, analyze the request to determine its complexity and type
        task_type, subtasks = await self._analyze_request(request)

        # Create the main task
        main_task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.add_task(
            task_id=main_task_id,
            description=f"Complete request: {request}"
        )

        # If we have subtasks, create them and make the main task depend on them
        if subtasks:
            prev_task_id = None
            for i, subtask in enumerate(subtasks):
                subtask_id = f"{main_task_id}_subtask_{i+1}"

                # Create dependencies for sequential execution
                dependencies = []
                if prev_task_id:
                    dependencies.append(prev_task_id)

                self.add_task(
                    task_id=subtask_id,
                    description=subtask,
                    dependencies=dependencies
                )

                prev_task_id = subtask_id

            # Update the main task to depend on all subtasks
            self.tasks[main_task_id].dependencies = [f"{main_task_id}_subtask_{i+1}" for i in range(len(subtasks))]

        # Record the task in history
        self.task_history.append({
            "request": request,
            "task_type": task_type,
            "main_task_id": main_task_id,
            "subtasks": subtasks,
            "start_time": datetime.now().isoformat(),
        })

    async def _analyze_request(self, request: str) -> Tuple[str, List[str]]:
        """
        Analyze the request to determine its complexity and type.

        Returns:
            A tuple of (task_type, subtasks)
        """
        # Create a message to analyze the request
        analysis_prompt = f"""
        Analyze the following request and break it down into subtasks:

        REQUEST: {request}

        1. What type of task is this? (coding, research, analysis, etc.)
        2. How complex is this task? (simple, moderate, complex)
        3. What are the logical subtasks needed to complete this request?

        Format your response as:
        TASK_TYPE: [type]
        COMPLEXITY: [complexity]
        SUBTASKS:
        - [subtask 1]
        - [subtask 2]
        - ...
        """

        # Get a response from the LLM
        messages = [Message.user_message(analysis_prompt)]
        response = await self.llm.ask(
            messages=messages,
            system_msgs=[Message.system_message("You are a task analysis assistant.")],
        )

        # Parse the response to extract task type and subtasks
        task_type = "general"
        subtasks = []

        # Extract task type
        task_type_match = re.search(r"TASK_TYPE:\s*(\w+)", response)
        if task_type_match:
            task_type = task_type_match.group(1).lower()

        # Extract subtasks
        subtasks_section = re.search(r"SUBTASKS:(.*?)($|NOTES:)", response, re.DOTALL)
        if subtasks_section:
            subtasks_text = subtasks_section.group(1)
            subtasks = [
                line.strip()[2:].strip()  # Remove the leading "- " and whitespace
                for line in subtasks_text.strip().split("\n")
                if line.strip().startswith("-")
            ]

        # If no subtasks were found, create a default one
        if not subtasks:
            subtasks = [f"Complete the {task_type} task: {request}"]

        return task_type, subtasks

    async def _execute_task_impl(self, task: Task) -> str:
        """Execute a task with thinking process tracking."""
        # Record the start of thinking
        if self.show_thinking:
            logger.info(f"✨ Nexagent's thoughts for task: {task.id}")

        # Execute the task using the parent implementation
        result = await super()._execute_task_impl(task)

        # Update task history
        for task_record in self.task_history:
            if task_record.get("main_task_id") == task.id:
                task_record["end_time"] = datetime.now().isoformat()
                task_record["result"] = result
                break

        return result

    async def think(self) -> bool:
        """Process current task and decide next actions using tools, with thought tracking."""
        # Call the parent think method
        should_act = await super().think()

        # Extract and store the thinking process from the last assistant message
        if self.messages and self.messages[-1].role == "assistant" and self.messages[-1].content:
            thought = {
                "task_id": self.current_task_id,
                "content": self.messages[-1].content,
                "timestamp": datetime.now().isoformat(),
            }
            self.thought_history.append(thought)

            # If thinking should be visible, log it
            if self.show_thinking:
                logger.info(f"✨ Nexagent's thoughts: {thought['content']}")

        return should_act

    def _calculate_task_complexity(self, request: str) -> int:
        """Calculate the complexity of a task based on its description."""
        # Simple heuristic based on length and complexity indicators
        complexity = 1

        # Length-based complexity
        if len(request) > 100:
            complexity += 1
        if len(request) > 300:
            complexity += 1

        # Keyword-based complexity
        complexity_keywords = [
            "complex", "difficult", "challenging", "analyze", "research",
            "implement", "create", "design", "optimize", "debug", "fix"
        ]

        for keyword in complexity_keywords:
            if keyword.lower() in request.lower():
                complexity += 1
                break

        return min(complexity, 5)  # Cap at 5
