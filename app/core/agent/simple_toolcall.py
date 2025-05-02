"""
Simplified ToolCallAgent implementation to avoid import issues.
"""

from typing import Any, Dict

from pydantic import Field

from app.core.agent.simple_react import ReActAgent
from app.core.exceptions.simple_exceptions import TokenLimitExceeded
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.core.schema.simple_schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tools.simple_tool_collection import ToolCollection


class ToolCallAgent(ReActAgent):
    """
    Agent that uses tool calling to solve tasks.
    """

    name: str = "ToolCallAgent"
    description: str = "Agent that uses tool calling to solve tasks"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = Field(default_factory=ToolCollection)

    async def run(self, prompt: str) -> str:
        """Run the agent with the given prompt."""
        # Initialize the agent state
        self.state = AgentState(
            messages=[
                Message(role="system", content=self.system_prompt),
                Message(role="user", content=prompt),
            ],
            max_steps=self.max_steps,
        )

        # Run the agent loop
        return await self._run_agent_loop()

    async def _run_agent_loop(self) -> str:
        """Run the agent loop."""
        # Initialize the agent loop
        step = 0
        while step < self.max_steps:
            # Increment the step counter
            step += 1

            # Get the next action from the LLM
            try:
                response = await self._get_next_action()
            except TokenLimitExceeded as e:
                logger.warning(f"Token limit exceeded: {e}")
                return f"Error: Token limit exceeded. Please try a simpler prompt or increase the token limit."

            # Check if the agent is done
            if response.content and not response.tool_calls:
                return response.content

            # Execute the tool calls
            for tool_call in response.tool_calls:
                # Execute the tool
                result = await self._execute_tool(tool_call.name, **tool_call.parameters)

                # Add the tool call and result to the messages
                self.state.messages.append(
                    Message(
                        role="assistant",
                        content=None,
                        tool_calls=[tool_call],
                    )
                )
                self.state.messages.append(
                    Message(
                        role="tool",
                        content=str(result),
                        tool_call_id=tool_call.id,
                    )
                )

        # If we reach here, we've exceeded the maximum number of steps
        return "Error: Maximum number of steps exceeded. Please try a simpler prompt or increase the maximum number of steps."

    async def _get_next_action(self) -> Message:
        """Get the next action from the LLM."""
        # Get the tool choice
        tool_choice = ToolChoice(type=TOOL_CHOICE_TYPE.AUTO)

        # Get the available tools
        tools = self.available_tools.get_tools_schema()

        # Get the response from the LLM
        response = await self.llm.create_chat_completion(
            messages=self.state.messages,
            tools=tools,
            tool_choice=tool_choice,
        )

        return response

    async def _execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a tool."""
        # Get the tool
        tool = self.available_tools.get_tool(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        # Execute the tool
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return f"Error executing tool '{name}': {e}"
