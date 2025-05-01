"""
Plan Optimizer for enhancing plans based on task execution feedback.

This module provides functionality to optimize plans based on task execution
results and feedback from the task result analyzer.
"""

import json
import time
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field

from app.logger import logger
from app.planning.task_result_analyzer import TaskResultAnalyzer, TaskAnalysisResult


class PlanOptimizationResult(BaseModel):
    """Result of plan optimization with changes and recommendations."""
    
    plan_id: str
    timestamp: float = Field(default_factory=time.time)
    changes_made: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    optimization_score: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanOptimizer:
    """
    Optimizes plans based on task execution feedback.
    
    This class takes feedback from the TaskResultAnalyzer and uses it to
    optimize plans by adjusting dependencies, reordering steps, or suggesting
    alternative approaches.
    """
    
    def __init__(self, task_analyzer: Optional[TaskResultAnalyzer] = None):
        """
        Initialize the plan optimizer.
        
        Args:
            task_analyzer: Optional TaskResultAnalyzer instance
        """
        self.task_analyzer = task_analyzer or TaskResultAnalyzer()
        self.optimization_history: Dict[str, List[PlanOptimizationResult]] = {}
    
    def optimize_plan(
        self, 
        plan_id: str, 
        plan_data: Dict[str, Any],
        task_analyses: List[TaskAnalysisResult]
    ) -> PlanOptimizationResult:
        """
        Optimize a plan based on task execution analyses.
        
        Args:
            plan_id: ID of the plan to optimize
            plan_data: Current plan data
            task_analyses: List of task analysis results
            
        Returns:
            PlanOptimizationResult with optimization details
        """
        # Initialize optimization result
        optimization_result = PlanOptimizationResult(plan_id=plan_id)
        
        # Skip if no analyses provided
        if not task_analyses:
            optimization_result.recommendations.append("No task analyses provided for optimization")
            return optimization_result
        
        # Apply optimizations
        self._optimize_dependencies(plan_data, task_analyses, optimization_result)
        self._optimize_step_order(plan_data, task_analyses, optimization_result)
        self._optimize_resource_allocation(plan_data, task_analyses, optimization_result)
        self._suggest_plan_improvements(plan_data, task_analyses, optimization_result)
        
        # Calculate optimization score (simple average of successful optimizations)
        if len(optimization_result.changes_made) > 0:
            optimization_result.optimization_score = min(1.0, len(optimization_result.changes_made) / 10.0)
        
        # Store optimization result in history
        if plan_id not in self.optimization_history:
            self.optimization_history[plan_id] = []
        self.optimization_history[plan_id].append(optimization_result)
        
        return optimization_result
    
    def _optimize_dependencies(
        self, 
        plan_data: Dict[str, Any],
        task_analyses: List[TaskAnalysisResult],
        optimization_result: PlanOptimizationResult
    ) -> None:
        """Optimize task dependencies based on execution feedback."""
        # Check if plan has steps
        if "steps" not in plan_data:
            return
        
        # Identify problematic dependencies
        problematic_deps = set()
        for analysis in task_analyses:
            for dep_id, feedback in analysis.dependencies_feedback.items():
                if "unnecessary" in feedback.lower():
                    problematic_deps.add(dep_id)
        
        # If we found problematic dependencies, suggest removing them
        if problematic_deps:
            deps_list = ", ".join(problematic_deps)
            optimization_result.recommendations.append(
                f"Consider removing potentially unnecessary dependencies: {deps_list}"
            )
    
    def _optimize_step_order(
        self, 
        plan_data: Dict[str, Any],
        task_analyses: List[TaskAnalysisResult],
        optimization_result: PlanOptimizationResult
    ) -> None:
        """Optimize the order of steps in the plan."""
        # Check if plan has steps
        if "steps" not in plan_data or len(plan_data["steps"]) <= 1:
            return
        
        # Look for long-running tasks that could be parallelized
        long_running_tasks = []
        for analysis in task_analyses:
            if analysis.execution_time and analysis.execution_time > 5.0:  # Arbitrary threshold
                long_running_tasks.append(analysis.task_id)
        
        # If we found long-running tasks, suggest parallelization
        if long_running_tasks:
            tasks_list = ", ".join(long_running_tasks)
            optimization_result.recommendations.append(
                f"Consider parallelizing long-running tasks: {tasks_list}"
            )
    
    def _optimize_resource_allocation(
        self, 
        plan_data: Dict[str, Any],
        task_analyses: List[TaskAnalysisResult],
        optimization_result: PlanOptimizationResult
    ) -> None:
        """Optimize resource allocation for tasks."""
        # Check for resource-intensive tasks
        resource_intensive_tasks = []
        for analysis in task_analyses:
            if any("resource-intensive" in insight.lower() for insight in analysis.key_insights):
                resource_intensive_tasks.append(analysis.task_id)
        
        # If we found resource-intensive tasks, suggest resource optimization
        if resource_intensive_tasks:
            tasks_list = ", ".join(resource_intensive_tasks)
            optimization_result.recommendations.append(
                f"Consider optimizing resources for intensive tasks: {tasks_list}"
            )
    
    def _suggest_plan_improvements(
        self, 
        plan_data: Dict[str, Any],
        task_analyses: List[TaskAnalysisResult],
        optimization_result: PlanOptimizationResult
    ) -> None:
        """Suggest overall improvements to the plan."""
        # Collect all optimization suggestions
        all_suggestions = []
        for analysis in task_analyses:
            all_suggestions.extend(analysis.optimization_suggestions)
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        for suggestion in all_suggestions:
            if suggestion not in unique_suggestions:
                unique_suggestions.append(suggestion)
        
        # Add unique suggestions to recommendations
        for suggestion in unique_suggestions:
            if suggestion not in optimization_result.recommendations:
                optimization_result.recommendations.append(suggestion)
        
        # Check success rate
        completed_analyses = [a for a in task_analyses if a.success]
        success_rate = len(completed_analyses) / len(task_analyses) if task_analyses else 0
        
        # Add general recommendations based on success rate
        if success_rate < 0.7:  # Arbitrary threshold
            optimization_result.recommendations.append(
                f"Low success rate ({success_rate:.0%}). Consider simplifying plan or adding error handling."
            )
        
        # Check for plan complexity
        if "steps" in plan_data and len(plan_data["steps"]) > 10:  # Arbitrary threshold
            optimization_result.recommendations.append(
                "Plan has many steps. Consider breaking it into sub-plans."
            )
    
    def get_optimization_history(self, plan_id: str) -> List[PlanOptimizationResult]:
        """
        Get the optimization history for a specific plan.
        
        Args:
            plan_id: ID of the plan
            
        Returns:
            List of PlanOptimizationResult objects for the plan
        """
        return self.optimization_history.get(plan_id, [])
