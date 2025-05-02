import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import Field, BaseModel

from app.tools.base import BaseTool
from app.logger import logger


class BrowserTelemetry(BaseModel):
    """Model for browser-specific telemetry data."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    page_loads: int = 0
    requests_made: int = 0
    errors_encountered: int = 0
    response_times: List[float] = Field(default_factory=list)
    memory_usage: List[float] = Field(default_factory=list)
    cpu_usage: List[float] = Field(default_factory=list)
    network_bytes: int = 0
    stealth_mode_active: bool = False
    user_agent_rotations: int = 0

class TaskAnalytics(BaseTool):
    """Tool for analyzing task execution history and providing insights."""

    name: str = "TaskAnalytics"
    description: str = "Analyze task history and generate insights with enhanced browser telemetry"
    browser_sessions: Dict[str, BrowserTelemetry] = Field(default_factory=dict)

    def __init__(self):
        super().__init__()

    async def execute(self, **kwargs) -> Any:
        """Execute the task analytics tool. This implements the abstract method from BaseTool."""
        return await self._run(**kwargs)

    async def _run(
        self,
        command: str = "",
        agent_history: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        telemetry_data: Optional[Dict] = None,
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

        if telemetry_data and session_id:
            await self._update_browser_telemetry(session_id, telemetry_data)

        if command == "summary":
            return self._generate_summary(agent_history)
        elif command == "performance":
            return self._generate_performance_metrics(agent_history)
        elif command == "common_tools":
            return self._analyze_tool_usage(agent_history)
        elif command == "browser_analytics":
            return self._generate_browser_analytics(session_id)
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
        """Analyze tool usage across tasks with enhanced browser metrics."""
        tool_usage = {}
        browser_usage = {
            "total_sessions": len(self.browser_sessions),
            "total_page_loads": sum(session.page_loads for session in self.browser_sessions.values()),
            "total_errors": sum(session.errors_encountered for session in self.browser_sessions.values()),
            "stealth_mode_usage": sum(1 for session in self.browser_sessions.values() if session.stealth_mode_active),
            "user_agent_rotations": sum(session.user_agent_rotations for session in self.browser_sessions.values())
        }

        for task in history:
            for tool in task.get("tools_used", []):
                tool_name = tool.get("name", "unknown")
                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

        return json.dumps({
            "tool_usage_frequency": tool_usage,
            "browser_metrics": browser_usage,
            "recommendations": self._generate_optimization_recommendations(tool_usage, browser_usage)
        })

    async def _update_browser_telemetry(self, session_id: str, data: Dict) -> None:
        """Update browser telemetry data for a session."""
        if session_id not in self.browser_sessions:
            self.browser_sessions[session_id] = BrowserTelemetry(
                session_id=session_id,
                start_time=datetime.now()
            )

        session = self.browser_sessions[session_id]
        session.page_loads += data.get("page_loads", 0)
        session.requests_made += data.get("requests_made", 0)
        session.errors_encountered += data.get("errors", 0)
        
        if "response_time" in data:
            session.response_times.append(data["response_time"])
        if "memory_usage" in data:
            session.memory_usage.append(data["memory_usage"])
        if "cpu_usage" in data:
            session.cpu_usage.append(data["cpu_usage"])
            
        session.network_bytes += data.get("network_bytes", 0)
        session.stealth_mode_active = data.get("stealth_mode", session.stealth_mode_active)
        session.user_agent_rotations += data.get("user_agent_rotations", 0)

        logger.info(f"Updated telemetry for session {session_id}")

    def _generate_browser_analytics(self, session_id: Optional[str] = None) -> str:
        """Generate analytics for browser sessions."""
        if session_id and session_id in self.browser_sessions:
            session = self.browser_sessions[session_id]
            return json.dumps({
                "session_metrics": {
                    "duration": (session.end_time or datetime.now() - session.start_time).total_seconds(),
                    "page_loads": session.page_loads,
                    "errors": session.errors_encountered,
                    "avg_response_time": sum(session.response_times) / len(session.response_times) if session.response_times else 0,
                    "avg_memory_usage": sum(session.memory_usage) / len(session.memory_usage) if session.memory_usage else 0,
                    "avg_cpu_usage": sum(session.cpu_usage) / len(session.cpu_usage) if session.cpu_usage else 0,
                    "network_usage_bytes": session.network_bytes,
                    "stealth_mode": session.stealth_mode_active,
                    "user_agent_changes": session.user_agent_rotations
                }
            })

        all_sessions_metrics = {
            "total_sessions": len(self.browser_sessions),
            "active_sessions": sum(1 for s in self.browser_sessions.values() if not s.end_time),
            "total_page_loads": sum(s.page_loads for s in self.browser_sessions.values()),
            "total_errors": sum(s.errors_encountered for s in self.browser_sessions.values()),
            "avg_session_duration": sum((s.end_time or datetime.now() - s.start_time).total_seconds() 
                                      for s in self.browser_sessions.values()) / len(self.browser_sessions) 
                                      if self.browser_sessions else 0
        }

        return json.dumps({
            "global_metrics": all_sessions_metrics,
            "performance_summary": self._generate_performance_summary()
        })

    def _generate_optimization_recommendations(self, tool_usage: Dict[str, int], browser_metrics: Dict) -> List[str]:
        """Generate optimization recommendations based on usage patterns."""
        recommendations = []

        # Analyze error rates
        error_rate = browser_metrics["total_errors"] / browser_metrics["total_page_loads"] if browser_metrics["total_page_loads"] > 0 else 0
        if error_rate > 0.1:
            recommendations.append("High error rate detected. Consider implementing additional error handling and retry mechanisms.")

        # Analyze stealth mode usage
        stealth_mode_ratio = browser_metrics["stealth_mode_usage"] / browser_metrics["total_sessions"]
        if stealth_mode_ratio < 0.5:
            recommendations.append("Consider increasing stealth mode usage to improve scraping success rate.")

        # Analyze user agent rotation
        if browser_metrics["user_agent_rotations"] < browser_metrics["total_page_loads"] / 2:
            recommendations.append("Increase user agent rotation frequency to avoid detection.")

        return recommendations

    def _generate_performance_summary(self) -> Dict:
        """Generate a summary of browser performance metrics."""
        all_response_times = []
        all_memory_usage = []
        all_cpu_usage = []

        for session in self.browser_sessions.values():
            all_response_times.extend(session.response_times)
            all_memory_usage.extend(session.memory_usage)
            all_cpu_usage.extend(session.cpu_usage)

        return {
            "response_time_metrics": {
                "avg": sum(all_response_times) / len(all_response_times) if all_response_times else 0,
                "min": min(all_response_times) if all_response_times else 0,
                "max": max(all_response_times) if all_response_times else 0
            },
            "resource_usage": {
                "avg_memory": sum(all_memory_usage) / len(all_memory_usage) if all_memory_usage else 0,
                "avg_cpu": sum(all_cpu_usage) / len(all_cpu_usage) if all_cpu_usage else 0
            }
        }
