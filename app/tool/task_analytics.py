import json
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.tool.base import BaseTool


class TaskAnalytics(BaseTool):
    """Tool for analyzing task execution history and providing insights."""

    name: str = "TaskAnalytics"
    description: str = "Analyze task history and generate insights"

    def __init__(self):
        super().__init__()

    async def execute(self, **kwargs) -> Any:
        """Execute the task analytics tool. This implements the abstract method from BaseTool."""
        return await self._run(**kwargs)

    async def _run(
        self,
        command: str = "",
        agent_history: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Any:
        """
        Run analytics on the task history data.

        Args:
            command: The specific analytics command to run, e.g., "summary", "performance", etc.
            agent_history: The task history to analyze (optional)

        Returns:
            A JSON string with analytics results
        """
        if not agent_history:
            return json.dumps({"error": "No task history provided for analysis"})

        if command == "summary":
            return self._generate_summary(agent_history)
        elif command == "performance":
            return self._generate_performance_metrics(agent_history)
        elif command == "common_tools":
            return self._analyze_tool_usage(agent_history)
        else:
            return json.dumps({"error": f"Unknown analytics command: {command}"})

    def _generate_summary(self, history: List[Dict]) -> str:
        """Generate a summary of tasks completed."""
        total_tasks = len(history)
        total_duration = sum(task.get("duration", 0) for task in history)
        avg_duration = total_duration / total_tasks if total_tasks > 0 else 0

        return json.dumps({
            "total_tasks": total_tasks,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
            "tasks": [
                {
                    "prompt": task.get("prompt", ""),
                    "duration": task.get("duration", 0),
                    "steps": task.get("steps_taken", 0),
                }
                for task in history
            ]
        })

    def _generate_performance_metrics(self, history: List[Dict]) -> str:
        """Generate performance metrics for task execution."""
        if not history:
            return json.dumps({"error": "No history data available"})

        # Calculate average steps per task
        avg_steps = sum(task.get("steps_taken", 0) for task in history) / len(history)

        # Find fastest and slowest tasks
        sorted_by_duration = sorted(history, key=lambda x: x.get("duration", 0))
        fastest = sorted_by_duration[0] if sorted_by_duration else {}
        slowest = sorted_by_duration[-1] if sorted_by_duration else {}

        return json.dumps({
            "average_steps_per_task": avg_steps,
            "fastest_task": {
                "prompt": fastest.get("prompt", ""),
                "duration": fastest.get("duration", 0),
            },
            "slowest_task": {
                "prompt": slowest.get("prompt", ""),
                "duration": slowest.get("duration", 0),
            }
        })

    def _analyze_tool_usage(self, history: List[Dict]) -> str:
        """Analyze tool usage across tasks."""
        # This is a placeholder for tool usage analysis
        # In a real implementation, you would analyze which tools were used in each task
        return json.dumps({
            "tool_analysis": "Tool usage analytics not available in this version",
            "recommendation": "Consider tracking tool usage in task history for better analytics"
        })
