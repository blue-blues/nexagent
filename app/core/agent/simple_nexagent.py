"""
Simplified Nexagent implementation to avoid import issues.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import Field

from app.core.agent.simple_toolcall import ToolCallAgent
from app.prompt.nexagent import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tools.simple_tool_collection import ToolCollection


class Nexagent(ToolCallAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends ToolCallAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "Nexagent"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 3000  # Increased from 2000 to allow for more comprehensive observations

    # Task history tracking
    task_history: List[Dict] = Field(default_factory=list)

    # Add websocket attribute with default None to prevent attribute errors
    websocket: Optional[Any] = None

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection()
    )

    async def run(self, prompt: str) -> str:
        """Run the agent with the given prompt and track task history."""
        start_time = datetime.now()

        # Dynamically set max_steps based on task complexity
        self.max_steps = self._calculate_max_steps(prompt)

        # Print for debugging
        print(f"Task complexity assessment - Dynamic max_steps set to: {self.max_steps}")

        result = await super().run(prompt)
        end_time = datetime.now()

        # Record task in history
        self.task_history.append({
            "prompt": prompt,
            "start_time": start_time,
            "end_time": end_time,
            "duration": (end_time - start_time).total_seconds(),
            "steps_taken": len(self.history) if hasattr(self, "history") else 0,
            "max_steps_allowed": self.max_steps,
        })

        return result

    def _calculate_max_steps(self, prompt: str) -> int:
        """
        Dynamically calculate maximum steps based on task complexity.

        This analyzes the input prompt to determine how complex the task is
        and sets an appropriate step limit.
        """
        # Base step count
        base_steps = 20

        # Count complexity factors in the prompt
        complexity_score = 0

        # Check for indicators of complexity
        web_scraping_indicators = [
            "scrape", "extract", "browse", "website", "web page", "data from",
            "get information", "navigate", "crawl", "fetch data"
        ]

        multi_step_indicators = [
            "then", "after that", "next", "subsequently", "finally", "lastly",
            "first", "second", "third", "step", "steps", "stages", "phases"
        ]

        data_processing_indicators = [
            "analyze", "process", "calculate", "compute", "transform",
            "convert", "clean", "filter", "sort", "compare"
        ]

        # Count matches for each indicator type
        web_complexity = sum(1 for indicator in web_scraping_indicators if indicator.lower() in prompt.lower())
        step_complexity = sum(1 for indicator in multi_step_indicators if indicator.lower() in prompt.lower())
        data_complexity = sum(1 for indicator in data_processing_indicators if indicator.lower() in prompt.lower())

        # Adjust score based on indicator counts
        if web_complexity > 0:
            complexity_score += min(web_complexity * 5, 25)  # Cap at 25

        if step_complexity > 0:
            complexity_score += min(step_complexity * 3, 30)  # Cap at 30

        if data_complexity > 0:
            complexity_score += min(data_complexity * 4, 20)  # Cap at 20

        # Calculate final step count
        final_steps = base_steps + complexity_score

        # Cap at a reasonable maximum to prevent excessive steps
        return min(final_steps, 100)  # Maximum of 100 steps for any task

    def get_task_history(self) -> List[Dict]:
        """Return the complete task history."""
        return self.task_history

    def get_last_task(self) -> Dict:
        """Return the most recent task if available."""
        if self.task_history:
            return self.task_history[-1]
        return {}
