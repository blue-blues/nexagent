"""
Task-based tool call agent implementation.

This module provides a TaskBasedToolCallAgent class that executes tasks using tool calls
rather than using a fixed number of steps.
"""

import json
from typing import Any, List, Optional, Union

from pydantic import Field

from app.agent.task_based_agent import Task, TaskBasedAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tools import ToolCollection
# CreateChatCompletion is not available yet, so we'll use Terminate only
from app.tools.terminate import Terminate


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class TaskBasedToolCallAgent(TaskBasedAgent):
    """Task-based agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "task_based_toolcall"
    description: str = "a task-based agent that can execute tool calls."

    system_prompt: str = "You are an agent that can execute tool calls to complete tasks"
    task_prompt: str = "Complete this task using the available tools. If you want to stop interaction, use `terminate` tool/function call."

    available_tools: ToolCollection = ToolCollection(
        Terminate()
    )

    # Tool call settings
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO
    tool_calls: List[ToolCall] = Field(default_factory=list)
    max_observe: Optional[int] = 2000  # Limit observation length

    async def _execute_task_impl(self, task: Task) -> str:
        """Execute a task using tool calls."""
        # Reset tool calls for this task
        self.tool_calls = []

        # Execute think-act loop until task is completed or terminated
        while True:
            # Think about the task
            should_act = await self.think()
            if not should_act:
                return "Task completed without further action"

            # Act on the thought
            action_result = await self.act()

            # Check if the task is completed or terminated
            if self.state == AgentState.FINISHED:
                return f"Task completed: {action_result}"

            # Check if we've reached a conclusion
            if self._is_task_complete(action_result):
                return action_result

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
        """Handle special tools like terminate."""
        if name == "terminate":
            logger.info("🛑 Agent received terminate command")
            self.state = AgentState.FINISHED

    def _is_task_complete(self, result: str) -> bool:
        """Check if the task is complete based on the result."""
        # This is a simple implementation that can be overridden by subclasses
        # For now, we'll consider the task complete if the agent has been terminated
        return self.state == AgentState.FINISHED
