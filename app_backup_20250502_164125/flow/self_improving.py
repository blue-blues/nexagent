"""Self-improving parallel flow module for NexAgent.

This module provides an enhanced parallel flow implementation that can
detect its own limitations and automatically apply corrective measures
during execution.
"""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from pydantic import Field, BaseModel

from app.agent.base import BaseAgent
from app.agent.parallel import AgentTask, ParallelAgentManager, AgentTaskStatus
from app.flow.parallel import ParallelFlow
from app.logger import logger
from app.schema import AgentState


class SelfImprovingParallelFlow(ParallelFlow):
    """An enhanced parallel flow with self-improvement capabilities.

    This flow extends the standard ParallelFlow with the ability to detect
    issues during execution and automatically apply corrective measures.
    """

    max_concurrent_tasks: int = Field(default=5)
    task_timeout: int = Field(default=600)  # 10 minutes default timeout
    enable_self_improvement: bool = Field(default=True)
    monitoring_interval: float = Field(default=5.0)  # Check for issues every 5 seconds
    max_auto_fixes: int = Field(default=10)  # Maximum number of automatic fixes to apply

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # Initialize with parent's init
        super().__init__(agents, **data)

        # Initialize the reasoning module
        self.reasoning = AgentReasoningModule()

        # Execution metrics
        self.auto_fixes_applied = 0
        self.detected_issues_count = 0
        self.monitoring_task = None

    async def execute(self, input_text: str) -> str:
        """Execute the self-improving parallel flow with the given input.

        This method extends the standard parallel flow execution with
        continuous monitoring and automatic issue resolution.

        Args:
            input_text: The input text to process

        Returns:
            str: The combined results of all agent executions with improvement metrics
        """
        try:
            if not self.agents:
                raise ValueError("No agents available for execution")

            # Create tasks for each agent (same as in ParallelFlow)
            tasks = []
            for i, (key, agent) in enumerate(self.agents.items()):
                task = AgentTask(
                    task_id=f"task_{i}_{key}",
                    agent_type=key,
                    prompt=input_text,
                    priority=i,  # Higher index = lower priority
                )
                tasks.append(task)

            # Add tasks to the manager
            self.manager.add_tasks(tasks)

            # Start monitoring if self-improvement is enabled
            if self.enable_self_improvement:
                self.monitoring_task = asyncio.create_task(
                    self._monitor_execution()
                )

            # Execute all tasks in parallel
            logger.info(f"Starting self-improving parallel execution of {len(tasks)} tasks")
            execution_summary = await self.manager.execute_all()

            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass

            # Add self-improvement metrics to the summary
            execution_summary["self_improvement_metrics"] = {
                "detected_issues": self.detected_issues_count,
                "auto_fixes_applied": self.auto_fixes_applied,
                "issues_by_type": self._count_issues_by_type(),
                "fix_success_rate": self._calculate_fix_success_rate()
            }

            # Format the results
            result = self._format_results(execution_summary)

            return result

        except Exception as e:
            logger.error(f"Error in self-improving parallel flow execution: {str(e)}")
            return f"Self-improving parallel flow execution failed: {str(e)}"

    async def _monitor_execution(self) -> None:
        """Continuously monitor execution and apply fixes as needed.

        This method runs in the background during execution, periodically
        checking for issues and applying fixes automatically.
        """
        try:
            while True:
                # Wait for the monitoring interval
                await asyncio.sleep(self.monitoring_interval)

                # Get current execution metrics
                execution_metrics = {
                    "total_tasks": len(self.manager.tasks),
                    "completed_tasks": len([t for t in self.manager.tasks.values()
                                         if t.status == AgentTaskStatus.COMPLETED]),
                    "failed_tasks": len([t for t in self.manager.tasks.values()
                                      if t.status == AgentTaskStatus.FAILED]),
                }

                # Detect issues
                detected_issues = await self.reasoning.detect_issues(
                    self.manager.tasks, execution_metrics
                )

                # Update issue count
                self.detected_issues_count += len(detected_issues)

                # Process each detected issue
                for issue in detected_issues:
                    logger.info(f"Detected issue: {issue.issue_type} - {issue.description}")

                    # Skip if we've reached the maximum number of auto-fixes
                    if self.auto_fixes_applied >= self.max_auto_fixes:
                        logger.warning("Maximum number of auto-fixes reached, skipping further fixes")
                        continue

                    # Suggest fixes for the issue
                    suggested_fixes = await self.reasoning.suggest_fixes(issue)

                    if suggested_fixes:
                        # Apply the first suggested fix
                        fix = suggested_fixes[0]
                        logger.info(f"Applying fix: {fix['description']}")

                        # Apply the fix
                        fix_result = await self.reasoning.apply_fix(issue, fix, self.manager)

                        # Update fix count
                        if fix_result.success:
                            self.auto_fixes_applied += 1
                            logger.info(f"Fix applied successfully: {fix_result.description}")
                        else:
                            logger.warning(f"Fix failed: {fix_result.description}")

                # Check if execution is complete
                pending_or_running = [t for t in self.manager.tasks.values()
                                    if t.status in [AgentTaskStatus.PENDING, AgentTaskStatus.RUNNING]]
                if not pending_or_running:
                    logger.info("Execution complete, stopping monitoring")
                    break

                # Additional safety check - if all tasks are in terminal states
                # This prevents the monitoring task from getting stuck
                terminal_states = [AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED]
                if all(t.status in terminal_states for t in self.manager.tasks.values()):
                    logger.info("All tasks in terminal states, stopping monitoring")
                    break

        except asyncio.CancelledError:
            logger.info("Monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in execution monitoring: {str(e)}")

    def _count_issues_by_type(self) -> Dict[str, int]:
        """Count detected issues by type.

        Returns:
            Dict[str, int]: Count of issues by type
        """
        counts = {issue_type.value: 0 for issue_type in IssueType}

        for issue in self.reasoning.detected_issues.values():
            counts[issue.issue_type] += 1

        return counts

    def _calculate_fix_success_rate(self) -> float:
        """Calculate the success rate of applied fixes.

        Returns:
            float: Success rate as a percentage
        """
        if not self.reasoning.applied_fixes:
            return 0.0

        successful_fixes = sum(1 for fix in self.reasoning.applied_fixes.values() if fix.success)
        return (successful_fixes / len(self.reasoning.applied_fixes)) * 100

    def _format_results(self, execution_summary: Dict) -> str:
        """Format the execution results into a readable string.

        Args:
            execution_summary: The execution summary from the manager

        Returns:
            str: Formatted results string
        """
        # Create a summary header
        result = f"Self-Improving Parallel Execution Summary:\n"
        result += f"Total tasks: {execution_summary['total_tasks']}\n"
        result += f"Completed tasks: {execution_summary['completed_tasks']}\n"
        result += f"Failed tasks: {execution_summary['failed_tasks']}\n"
        result += f"Total execution time: {execution_summary['execution_time']:.2f} seconds\n"

        # Add self-improvement metrics
        if "self_improvement_metrics" in execution_summary:
            metrics = execution_summary["self_improvement_metrics"]
            result += f"\nSelf-Improvement Metrics:\n"
            result += f"Detected issues: {metrics['detected_issues']}\n"
            result += f"Auto-fixes applied: {metrics['auto_fixes_applied']}\n"
            result += f"Fix success rate: {metrics['fix_success_rate']:.2f}%\n"

            # Add issue counts by type
            if metrics["issues_by_type"]:
                result += f"\nIssues by type:\n"
                for issue_type, count in metrics["issues_by_type"].items():
                    if count > 0:
                        result += f"  {issue_type}: {count}\n"

        # Add individual task results
        result += "\nTask Results:\n"
        for task_id, task_result in execution_summary['results'].items():
            result += f"\n--- {task_id} ---\n{task_result}\n"

        # Add errors if any
        if execution_summary['errors']:
            result += "\nErrors:\n"
            for task_id, error in execution_summary['errors'].items():
                result += f"{task_id}: {error}\n"

        return result


class SelfImprovingParallelWorkflowFlow(SelfImprovingParallelFlow):
    """A self-improving flow that executes multiple workflows in parallel.

    This flow extends SelfImprovingParallelFlow to handle workflow-specific execution,
    where each workflow consists of multiple dependent tasks with self-improvement.
    """

    async def execute(self, input_text: str) -> str:
        """Execute multiple workflows in parallel with self-improvement.

        This method creates a workflow for each agent and executes them
        in parallel, respecting dependencies between tasks within each workflow
        and applying self-improvement techniques.

        Args:
            input_text: The input text to process

        Returns:
            str: The combined results of all workflow executions with improvement metrics
        """
        try:
            if not self.agents:
                raise ValueError("No agents available for workflow execution")

            # Create a task for the planner to generate workflows
            planner_task = AgentTask(
                task_id="task_planner",
                agent_type=self.primary_agent_key,
                prompt=f"Generate a workflow plan for: {input_text}",
                priority=10,  # Highest priority
            )

            # Add planner task to the manager
            self.manager.add_task(planner_task)

            # Start monitoring if self-improvement is enabled
            if self.enable_self_improvement:
                self.monitoring_task = asyncio.create_task(
                    self._monitor_execution()
                )

            # Execute planner task
            planner_summary = await self.manager.execute_all()

            # Check if planner task completed successfully
            if "task_planner" not in planner_summary['results']:
                raise ValueError("Failed to generate workflow plan")

            # Parse workflow plan from planner result
            workflow_plan = self._parse_workflow_plan(planner_summary['results']['task_planner'])

            # Create tasks for each step in the workflow
            tasks = []
            for i, step in enumerate(workflow_plan):
                task = AgentTask(
                    task_id=f"task_{i}_{step['agent_type']}",
                    agent_type=step['agent_type'],
                    prompt=step['prompt'],
                    dependencies=step['dependencies'],
                    priority=step.get('priority', 0),
                )
                tasks.append(task)

            # Add workflow tasks to the manager
            self.manager.add_tasks(tasks)

            # Execute all workflow tasks in parallel
            logger.info(f"Starting self-improving parallel execution of {len(tasks)} workflow tasks")
            execution_summary = await self.manager.execute_all()

            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass

            # Add self-improvement metrics to the summary
            execution_summary["self_improvement_metrics"] = {
                "detected_issues": self.detected_issues_count,
                "auto_fixes_applied": self.auto_fixes_applied,
                "issues_by_type": self._count_issues_by_type(),
                "fix_success_rate": self._calculate_fix_success_rate()
            }

            # Format the results
            result = self._format_results(execution_summary)

            return result

        except Exception as e:
            logger.error(f"Error in self-improving parallel workflow execution: {str(e)}")
            return f"Self-improving parallel workflow execution failed: {str(e)}"

    def _parse_workflow_plan(self, plan_result: str) -> List[Dict]:
        """Parse the workflow plan from the planner result.

        Args:


class IssueType(str, Enum):
    """Types of issues that can be detected during execution."""

    TIMEOUT = "timeout"  # Task took too long to complete
    ERROR = "error"  # Task failed with an error
    RESOURCE_LIMIT = "resource_limit"  # Task exceeded resource limits
    PERFORMANCE = "performance"  # Task performed poorly
    STUCK = "stuck"  # Task is stuck in a loop or not making progress
    TOKEN_LIMIT = "token_limit"  # Task exceeded token limits
    DEPENDENCY_FAILURE = "dependency_failure"  # Task's dependency failed


class IssueDetection(BaseModel):
    """Represents a detected issue during execution."""

    issue_id: str
    task_id: str
    issue_type: IssueType
    timestamp: datetime = Field(default_factory=datetime.now)
    description: str
    severity: int = 1  # 1-5, with 5 being most severe
    metrics: Dict[str, Any] = Field(default_factory=dict)
    suggested_fixes: List[Dict[str, Any]] = Field(default_factory=list)


class FixResult(BaseModel):
    """Result of applying a fix to an issue."""

    issue_id: str
    fix_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool
    description: str
    metrics_before: Dict[str, Any] = Field(default_factory=dict)
    metrics_after: Dict[str, Any] = Field(default_factory=dict)


class AgentReasoningModule:
    """Module for detecting issues and reasoning about fixes.

    This module analyzes execution metrics and task results to identify
    issues and automatically apply corrective measures.
    """

    def __init__(self):
        self.detected_issues: Dict[str, IssueDetection] = {}
        self.applied_fixes: Dict[str, FixResult] = {}
        self.performance_thresholds = {
            "timeout_ms": 30000,  # 30 seconds
            "error_rate": 0.2,  # 20% error rate
            "max_retries": 3,
            "token_limit": 4000,
            "memory_threshold": 0.9,  # 90% memory usage
            "cpu_threshold": 0.8,  # 80% CPU usage
            "stuck_detection_time": 60,  # 60 seconds with no progress
        }
        self.fix_strategies = {
            IssueType.TIMEOUT: self._fix_timeout,
            IssueType.ERROR: self._fix_error,
            IssueType.RESOURCE_LIMIT: self._fix_resource_limit,
            IssueType.PERFORMANCE: self._fix_performance,
            IssueType.STUCK: self._fix_stuck,
            IssueType.TOKEN_LIMIT: self._fix_token_limit,
            IssueType.DEPENDENCY_FAILURE: self._fix_dependency_failure,
        }

    async def detect_issues(self, tasks: Dict[str, AgentTask],
                          execution_metrics: Dict[str, Any]) -> List[IssueDetection]:
        """Detect issues in the current execution state.

        Args:
            tasks: Dictionary of tasks being executed
            execution_metrics: Current execution metrics

        Returns:
            List of detected issues
        """
        detected = []

        # Check for timeouts
        for task_id, task in tasks.items():
            if task.status == AgentTaskStatus.RUNNING:
                if task.started_at and (datetime.now() - task.started_at).total_seconds() > \
                   self.performance_thresholds["timeout_ms"] / 1000:
                    issue = IssueDetection(
                        issue_id=f"timeout_{task_id}_{int(time.time())}",
                        task_id=task_id,
                        issue_type=IssueType.TIMEOUT,
                        description=f"Task {task_id} has been running for too long",
                        severity=3,
                        metrics={"running_time": (datetime.now() - task.started_at).total_seconds()}
                    )
                    self.detected_issues[issue.issue_id] = issue
                    detected.append(issue)

            # Check for errors
            elif task.status == AgentTaskStatus.FAILED:
                issue = IssueDetection(
                    issue_id=f"error_{task_id}_{int(time.time())}",
                    task_id=task_id,
                    issue_type=IssueType.ERROR,
                    description=f"Task {task_id} failed: {task.error}",
                    severity=4,
                    metrics={"error": task.error, "retry_count": task.retry_count}
                )
                self.detected_issues[issue.issue_id] = issue
                detected.append(issue)

            # Check for stuck tasks
            elif task.status == AgentTaskStatus.RUNNING and task.started_at:
                running_time = (datetime.now() - task.started_at).total_seconds()
                if running_time > self.performance_thresholds["stuck_detection_time"]:
                    # Additional logic could check for actual progress indicators
                    issue = IssueDetection(
                        issue_id=f"stuck_{task_id}_{int(time.time())}",
                        task_id=task_id,
                        issue_type=IssueType.STUCK,
                        description=f"Task {task_id} appears to be stuck",
                        severity=3,
                        metrics={"running_time": running_time}
                    )
                    self.detected_issues[issue.issue_id] = issue
                    detected.append(issue)

        # Check for dependency failures
        for task_id, task in tasks.items():
            if task.status == AgentTaskStatus.PENDING and task.dependencies:
                failed_deps = [dep for dep in task.dependencies
                              if dep in tasks and tasks[dep].status == AgentTaskStatus.FAILED]
                if failed_deps:
                    issue = IssueDetection(
                        issue_id=f"dep_failure_{task_id}_{int(time.time())}",
                        task_id=task_id,
                        issue_type=IssueType.DEPENDENCY_FAILURE,
                        description=f"Task {task_id} has failed dependencies: {failed_deps}",
                        severity=4,
                        metrics={"failed_dependencies": failed_deps}
                    )
                    self.detected_issues[issue.issue_id] = issue
                    detected.append(issue)

        # Check overall performance metrics
        error_rate = execution_metrics.get("failed_tasks", 0) / max(1, execution_metrics.get("total_tasks", 1))
        if error_rate > self.performance_thresholds["error_rate"]:
            issue = IssueDetection(
                issue_id=f"performance_error_rate_{int(time.time())}",
                task_id="global",
                issue_type=IssueType.PERFORMANCE,
                description=f"High error rate detected: {error_rate:.2f}",
                severity=3,
                metrics={"error_rate": error_rate}
            )
            self.detected_issues[issue.issue_id] = issue
            detected.append(issue)

        return detected

    async def suggest_fixes(self, issue: IssueDetection) -> List[Dict[str, Any]]:
        """Suggest fixes for a detected issue.

        Args:
            issue: The detected issue

        Returns:
            List of suggested fixes
        """
        fixes = []

        # Generic fixes based on issue type
        if issue.issue_type == IssueType.TIMEOUT:
            fixes.append({
                "fix_id": f"fix_timeout_{issue.task_id}_{int(time.time())}",
                "description": "Increase timeout for the task",
                "action": "increase_timeout",
                "params": {"task_id": issue.task_id, "timeout_factor": 1.5}
            })
            fixes.append({
                "fix_id": f"fix_timeout_retry_{issue.task_id}_{int(time.time())}",
                "description": "Retry the task with simplified parameters",
                "action": "retry_simplified",
                "params": {"task_id": issue.task_id}
            })

        elif issue.issue_type == IssueType.ERROR:
            fixes.append({
                "fix_id": f"fix_error_retry_{issue.task_id}_{int(time.time())}",
                "description": "Retry the task",
                "action": "retry",
                "params": {"task_id": issue.task_id}
            })

            # Analyze error message for specific fixes
            error_msg = issue.metrics.get("error", "")
            if "token limit" in error_msg.lower():
                fixes.append({
                    "fix_id": f"fix_token_limit_{issue.task_id}_{int(time.time())}",
                    "description": "Split task into smaller chunks",
                    "action": "split_task",
                    "params": {"task_id": issue.task_id}
                })
            elif "memory" in error_msg.lower():
                fixes.append({
                    "fix_id": f"fix_memory_{issue.task_id}_{int(time.time())}",
                    "description": "Reduce memory usage",
                    "action": "reduce_memory",
                    "params": {"task_id": issue.task_id}
                })

        elif issue.issue_type == IssueType.STUCK:
            fixes.append({
                "fix_id": f"fix_stuck_cancel_{issue.task_id}_{int(time.time())}",
                "description": "Cancel and restart the task",
                "action": "cancel_restart",
                "params": {"task_id": issue.task_id}
            })

        elif issue.issue_type == IssueType.DEPENDENCY_FAILURE:
            fixes.append({
                "fix_id": f"fix_dep_skip_{issue.task_id}_{int(time.time())}",
                "description": "Skip failed dependencies and proceed",
                "action": "skip_dependencies",
                "params": {"task_id": issue.task_id, "dependencies": issue.metrics.get("failed_dependencies", [])}
            })
            fixes.append({
                "fix_id": f"fix_dep_alt_{issue.task_id}_{int(time.time())}",
                "description": "Use alternative approach that doesn't require failed dependencies",
                "action": "use_alternative_approach",
                "params": {"task_id": issue.task_id}
            })

        # Update the issue with suggested fixes
        issue.suggested_fixes = fixes
        return fixes

    async def apply_fix(self, issue: IssueDetection, fix: Dict[str, Any],
                       manager: ParallelAgentManager) -> FixResult:
        """Apply a fix to an issue.

        Args:
            issue: The detected issue
            fix: The fix to apply
            manager: The parallel agent manager

        Returns:
            Result of applying the fix
        """
        fix_strategy = self.fix_strategies.get(issue.issue_type)
        if not fix_strategy:
            return FixResult(
                issue_id=issue.issue_id,
                fix_id=fix["fix_id"],
                success=False,
                description=f"No fix strategy available for issue type {issue.issue_type}"
            )

        # Collect metrics before applying fix
        metrics_before = self._collect_metrics(issue.task_id, manager)

        # Apply the fix
        try:
            result = await fix_strategy(issue, fix, manager)

            # Collect metrics after applying fix
            metrics_after = self._collect_metrics(issue.task_id, manager)

            fix_result = FixResult(
                issue_id=issue.issue_id,
                fix_id=fix["fix_id"],
                success=result["success"],
                description=result["description"],
                metrics_before=metrics_before,
                metrics_after=metrics_after
            )

            # Store the fix result
            self.applied_fixes[fix["fix_id"]] = fix_result
            return fix_result

        except Exception as e:
            logger.error(f"Error applying fix {fix['fix_id']}: {str(e)}")
            return FixResult(
                issue_id=issue.issue_id,
                fix_id=fix["fix_id"],
                success=False,
                description=f"Error applying fix: {str(e)}"
            )

    def _collect_metrics(self, task_id: str, manager: ParallelAgentManager) -> Dict[str, Any]:
        """Collect current metrics for a task.

        Args:
            task_id: ID of the task
            manager: The parallel agent manager

        Returns:
            Dictionary of metrics
        """
        metrics = {}

        # Get task if it exists
        task = manager.get_task(task_id)
        if task:
            metrics["status"] = task.status
            metrics["retry_count"] = task.retry_count
            if task.started_at:
                metrics["running_time"] = (datetime.now() - task.started_at).total_seconds()
            if task.execution_time:
                metrics