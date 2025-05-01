"""
Task Result Analyzer for optimizing planning based on task execution results.

This module provides functionality to analyze task execution results and provide
feedback to the planning system for optimization of future tasks and plans.
"""

import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.logger import logger
from app.agent.task_based_agent import Task


class TaskAnalysisResult(BaseModel):
    """Result of task analysis with optimization suggestions."""

    task_id: str
    success: bool
    execution_time: Optional[float] = None
    key_insights: List[str] = Field(default_factory=list)
    optimization_suggestions: List[str] = Field(default_factory=list)
    dependencies_feedback: Dict[str, str] = Field(default_factory=dict)
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResultAnalyzer:
    """
    Analyzes task execution results to provide feedback for plan optimization.

    This class examines completed tasks, extracts insights, and generates
    optimization suggestions that can be fed back to the planning system.
    """

    def __init__(self):
        """Initialize the task result analyzer."""
        self.analysis_history: List[TaskAnalysisResult] = []

    def analyze_task(self, task: Task) -> TaskAnalysisResult:
        """
        Analyze a completed task and generate optimization insights.

        Args:
            task: The completed task to analyze

        Returns:
            TaskAnalysisResult with insights and optimization suggestions
        """
        # Skip analysis for tasks that aren't completed or failed
        if task.status not in ["completed", "failed"]:
            logger.warning(f"Cannot analyze task {task.id} with status {task.status}")
            return TaskAnalysisResult(
                task_id=task.id,
                success=False,
                key_insights=["Task not completed or failed"]
            )

        # Calculate execution time
        execution_time = None
        if task.start_time and task.end_time:
            execution_time = task.end_time - task.start_time

        # Initialize analysis result
        analysis = TaskAnalysisResult(
            task_id=task.id,
            success=task.status == "completed",
            execution_time=execution_time
        )

        # Extract key insights from task result
        if task.result:
            analysis.key_insights = self._extract_key_insights(task)

        # Generate optimization suggestions
        analysis.optimization_suggestions = self._generate_optimization_suggestions(task)

        # Analyze dependencies
        if task.dependencies:
            analysis.dependencies_feedback = self._analyze_dependencies(task)

        # Store analysis in history
        self.analysis_history.append(analysis)

        return analysis

    def _extract_key_insights(self, task: Task) -> List[str]:
        """Extract key insights from task result."""
        insights = []

        if not task.result:
            return insights

        # Extract insights based on task result content
        result = task.result.lower()

        # Look for success indicators
        if any(term in result for term in ["success", "completed", "done"]):
            insights.append("Task completed successfully")

        # Look for partial success
        if any(term in result for term in ["partial", "incomplete", "partially"]):
            insights.append("Task partially completed")

        # Look for challenges
        if any(term in result for term in ["challenge", "difficult", "issue", "problem"]):
            insights.append("Task encountered challenges")

        # Look for resource usage indicators
        if any(term in result for term in ["time-consuming", "resource", "memory", "cpu"]):
            insights.append("Task may be resource-intensive")

        # Add generic insight if none found
        if not insights:
            insights.append("Task completed with no specific insights detected")

        return insights

    def _generate_optimization_suggestions(self, task: Task) -> List[str]:
        """Generate optimization suggestions based on task execution."""
        suggestions = []

        # Suggest optimizations based on task status
        if task.status == "completed":
            if task.start_time and task.end_time:
                execution_time = task.end_time - task.start_time
                if execution_time > 10:  # Arbitrary threshold
                    suggestions.append(f"Consider breaking down this task (took {execution_time:.2f}s)")
        elif task.status == "failed":
            suggestions.append("Consider adding error handling or retry logic")
            if task.error and "timeout" in task.error.lower():
                suggestions.append("Task may need more time or resources")

        # Suggest dependency optimizations
        if len(task.dependencies) > 3:
            suggestions.append("Consider reducing the number of dependencies")

        return suggestions

    def _analyze_dependencies(self, task: Task) -> Dict[str, str]:
        """Analyze task dependencies for optimization opportunities."""
        feedback = {}

        # Simple dependency analysis
        for dep_id in task.dependencies:
            feedback[dep_id] = "Required dependency"

        return feedback

    def get_plan_optimization_feedback(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Generate comprehensive feedback for plan optimization based on multiple tasks.

        Args:
            tasks: List of tasks to analyze

        Returns:
            Dictionary with plan optimization feedback
        """
        # Analyze each task
        task_analyses = [self.analyze_task(task) for task in tasks]

        # Aggregate insights and suggestions
        all_insights = []
        all_suggestions = []
        for analysis in task_analyses:
            all_insights.extend(analysis.key_insights)
            all_suggestions.extend(analysis.optimization_suggestions)

        # Remove duplicates while preserving order
        unique_insights = []
        unique_suggestions = []
        for item in all_insights:
            if item not in unique_insights:
                unique_insights.append(item)
        for item in all_suggestions:
            if item not in unique_suggestions:
                unique_suggestions.append(item)

        # Calculate success rate
        completed_tasks = sum(1 for task in tasks if task.status == "completed")
        success_rate = completed_tasks / len(tasks) if tasks else 0

        # Calculate average execution time
        execution_times = [
            task.end_time - task.start_time
            for task in tasks
            if task.status == "completed" and task.start_time and task.end_time
        ]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else None

        # Generate overall feedback
        return {
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "key_insights": unique_insights,
            "optimization_suggestions": unique_suggestions,
            "task_count": len(tasks),
            "completed_task_count": completed_tasks,
            "timestamp": time.time()
        }
