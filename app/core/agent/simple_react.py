"""
Simplified ReActAgent implementation to avoid import issues.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from pydantic import Field

from app.core.agent.simple_base import BaseAgent
from app.core.agent.simple_web_output import WebOutputFormatter


class ReActAgent(BaseAgent, ABC):
    """
    Agent that uses the ReAct (Reasoning and Acting) paradigm.
    """
    
    name: str
    description: Optional[str] = None
    
    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None
    
    max_steps: int = 10
    current_step: int = 0
    
    # Web output formatting options
    web_output_enabled: bool = True
    web_output_formatter: WebOutputFormatter = Field(default_factory=WebOutputFormatter)
    web_output_options: Dict[str, Any] = Field(default_factory=dict)
    
    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""
        pass
    
    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""
        pass
    
    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            result = "Thinking complete - no action needed"
            return self.format_output(result) if self.web_output_enabled else result
        
        result = await self.act()
        return self.format_output(result) if self.web_output_enabled else result
    
    def format_output(self, output: str) -> str:
        """Format agent output for web display."""
        if not self.web_output_enabled or not output:
            return output
        
        return self.web_output_formatter.format_output(output)
    
    def format_tool_result(self, result: str) -> str:
        """Format tool execution result for web display."""
        if not self.web_output_enabled or not result:
            return result
        
        return self.web_output_formatter.structure_tool_result(result)
    
    def create_output_summary(self, output: str, max_length: int = 150) -> str:
        """Create a concise summary of the output for web display."""
        if not self.web_output_enabled or not output:
            return ""
        
        return self.web_output_formatter.create_summary(output, max_length)
