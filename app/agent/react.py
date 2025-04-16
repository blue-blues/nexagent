from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.agent.web_output import WebOutputFormatter
from app.llm import LLM
from app.schema import AgentState, Memory


class ReActAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    # Web output formatting options
    web_output_enabled: bool = True
    web_output_formatter: WebOutputFormatter = Field(default_factory=WebOutputFormatter)
    web_output_options: Dict[str, Any] = Field(default_factory=dict)

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            result = "Thinking complete - no action needed"
            return self.format_output(result) if self.web_output_enabled else result

        result = await self.act()
        return self.format_output(result) if self.web_output_enabled else result

    def format_output(self, output: str, is_final_output: bool = False) -> str:
        """Format agent output for web display.

        Args:
            output: Raw output string from agent actions
            is_final_output: Whether this is the final output (not an intermediate step)

        Returns:
            Formatted output string optimized for web display
        """
        if not self.web_output_enabled or not output:
            return output

        return self.web_output_formatter.format_output(output, is_final_output=is_final_output)

    def format_tool_result(self, result: str) -> str:
        """Format tool execution result for web display.

        Args:
            result: Raw tool execution result

        Returns:
            Formatted tool result optimized for web display
        """
        if not self.web_output_enabled or not result:
            return result

        return self.web_output_formatter.structure_tool_result(result)

    def create_output_summary(self, output: str, max_length: int = 150) -> str:
        """Create a concise summary of the output for web display.

        Args:
            output: Full output string
            max_length: Maximum length of summary

        Returns:
            Concise summary of the output
        """
        if not self.web_output_enabled or not output:
            return ""

        return self.web_output_formatter.create_summary(output, max_length)
