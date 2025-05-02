"""
Task-based tool call agent implementation.

This module provides a TaskBasedToolCallAgent class that executes tasks using tool calls
rather than using a fixed number of steps. The agent implements a thinking-acting loop
pattern where it first thinks about what tools to use, then executes those tools.

The agent supports different tool choice modes:
- AUTO: The agent can choose whether to use tools or not
- REQUIRED: The agent must use tools
- NONE: The agent cannot use tools

Copyright (c) 2023-2024 Nexagent
"""

import json
from typing import Any, List

from pydantic import Field

from app.agent.task_based_agent import Task, TaskBasedAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.schema import AgentState, Message, ToolCall, ToolChoice
from app.tools import ToolCollection
from app.tools.terminate import Terminate


# Constants
TOOL_CALL_REQUIRED = "Tool calls required but none provided"
MAX_CONSECUTIVE_ERRORS = 3
DEFAULT_MAX_ITERATIONS = 10
DEFAULT_MAX_OBSERVE_LENGTH = 2000


class TaskBasedToolCallAgent(TaskBasedAgent):
    """
    Task-based agent class for handling tool/function calls with enhanced abstraction.

    This agent implements a thinking-acting loop pattern where it first thinks about
    what tools to use, then executes those tools. It supports different tool choice
    modes and provides robust error handling for tool execution.

    Attributes:
        name: Unique name of the agent
        description: Description of the agent
        system_prompt: System-level instruction prompt
        task_prompt: Prompt for executing a task
        available_tools: Collection of tools available to the agent
        tool_choices: Tool choice mode (AUTO, REQUIRED, NONE)
        tool_calls: List of tool calls to execute
        max_observe: Maximum length of tool observation to include in memory
        max_iterations: Maximum number of think-act iterations per task
        max_consecutive_errors: Maximum number of consecutive errors before failing
    """

    name: str = "task_based_toolcall"
    description: str = "A task-based agent that can execute tool calls to complete tasks"
    version: str = "1.0.0"

    system_prompt: str = """You are an agent that can execute tool calls to complete tasks.
You have access to a variety of tools that can help you accomplish your tasks.
Think carefully about which tools to use and how to use them effectively.
Always provide clear reasoning for your actions."""

    task_prompt: str = """Complete this task using the available tools.
Think step by step about how to approach this task.
If you want to stop interaction, use the `terminate` tool/function call."""

    # Tool configuration
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(Terminate()),
        description="Collection of tools available to the agent"
    )

    # Tool call settings
    tool_choices: ToolChoice = Field(
        default=ToolChoice.AUTO,
        description="Tool choice mode (AUTO, REQUIRED, NONE)"
    )
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="List of tool calls to execute"
    )
    max_observe: int = Field(
        default=DEFAULT_MAX_OBSERVE_LENGTH,
        description="Maximum length of tool observation to include in memory"
    )

    # Execution control
    max_iterations: int = Field(
        default=DEFAULT_MAX_ITERATIONS,
        description="Maximum number of think-act iterations per task"
    )
    max_consecutive_errors: int = Field(
        default=MAX_CONSECUTIVE_ERRORS,
        description="Maximum number of consecutive errors before failing"
    )

    # Execution statistics
    iteration_count: int = Field(
        default=0,
        description="Number of think-act iterations for the current task"
    )
    consecutive_errors: int = Field(
        default=0,
        description="Number of consecutive errors encountered"
    )

    async def _execute_task_impl(self, task: Task) -> str:
        """
        Execute a task using tool calls.

        This method implements the core thinking-acting loop for task execution.
        It repeatedly calls the think and act methods until the task is completed,
        the agent is terminated, or the maximum number of iterations is reached.

        Args:
            task: The task to execute

        Returns:
            The result of the task execution

        Raises:
            RuntimeError: If too many consecutive errors occur
        """
        # Reset execution state for this task
        self.tool_calls = []
        self.iteration_count = 0
        self.consecutive_errors = 0

        logger.info(f"Starting execution of task: {task.id} - {task.description}")

        # Execute think-act loop until task is completed or terminated
        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            logger.debug(f"Starting iteration {self.iteration_count}/{self.max_iterations}")

            try:
                # Think about the task
                should_act = await self.think()
                if not should_act:
                    logger.info("Agent decided no further action is needed")
                    return "Task completed without further action"

                # Reset consecutive errors counter on successful thinking
                self.consecutive_errors = 0

                # Act on the thought
                action_result = await self.act()

                # Check if the task is completed or terminated
                if self.state == AgentState.FINISHED:
                    logger.info(f"Task completed via termination: {action_result}")
                    return f"Task completed: {action_result}"

                # Check if we've reached a conclusion
                if self._is_task_complete(action_result):
                    logger.info(f"Task completed with result: {action_result}")
                    return action_result

            except Exception as e:
                self.consecutive_errors += 1
                error_msg = f"Error in iteration {self.iteration_count}: {str(e)}"
                logger.error(error_msg)

                # If too many consecutive errors, fail the task
                if self.consecutive_errors >= self.max_consecutive_errors:
                    raise RuntimeError(
                        f"Task failed after {self.consecutive_errors} consecutive errors: {str(e)}"
                    )

        # If we reach here, we've hit the maximum number of iterations
        logger.warning(f"Task reached maximum iterations ({self.max_iterations}) without completion")
        return f"Task incomplete after {self.max_iterations} iterations. Last result: {action_result if 'action_result' in locals() else 'No result'}"

    async def think(self) -> bool:
        """Process current task and decide next actions using tools."""
        self.tool_calls = []  # Reset tool calls

        try:
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=[Message.system_message(self.system_prompt)]
                if self.system_prompt
                else None,
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        # Store tool calls for later execution
        self.tool_calls = response.tool_calls or []

        # Log the thinking process
        if response.content:
            logger.info(f"✨ {self.name}'s thoughts: {response.content}")
        logger.info(f"🛠️ {self.name} selected {len(self.tool_calls)} tools to use")

        try:
            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if response.tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if response.content:
                    self.memory.add_message(Message.assistant_message(response.content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(
                    content=response.content, tool_calls=self.tool_calls
                )
                if self.tool_calls
                else Message.assistant_message(response.content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(response.content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            result = await self.execute_tool(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result, tool_call_id=command.id, name=command.function.name
            )
            self.memory.add_message(tool_msg)
            results.append(result)

        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Execute the tool
            logger.info(f"🔧 Activating tool: '{name}'...")
            result = await self.available_tools.execute(name=name, tool_input=args)

            # Format result for display
            raw_observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            # Apply web formatting if enabled
            observation = self.format_tool_result(raw_observation) if hasattr(self, 'format_tool_result') else raw_observation

            # Handle special tools like `finish`
            await self._handle_special_tool(name=name, result=result)

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any) -> None:
        """
        Handle special tools like terminate.

        Args:
            name: The name of the tool
            result: The result of the tool execution
        """
        if name == "terminate":
            logger.info("🛑 Agent received terminate command")
            self.state = AgentState.FINISHED

        # Add handling for other special tools here as needed

    def _is_task_complete(self, action_result: str) -> bool:
        """
        Check if the task is complete based on the action result.

        This is a simple implementation that can be overridden by subclasses
        to implement more sophisticated completion detection.

        Args:
            action_result: The result of the most recent action

        Returns:
            True if the task is complete, False otherwise
        """
        # For now, we'll consider the task complete if the agent has been terminated
        # or if the action result contains a specific completion marker
        if self.state == AgentState.FINISHED:
            return True

        # Check for completion markers in the action result
        completion_markers = [
            "Task completed successfully",
            "All requirements have been met",
            "Final result:",
            "Completed all requested actions"
        ]

        return any(marker in action_result for marker in completion_markers)
