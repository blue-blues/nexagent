"""Parallel processing module for NexAgent.

This module provides classes and utilities for running multiple agent instances
concurrently using asyncio. It integrates with the existing workflow generator
and monitor components to provide efficient parallel execution of tasks.
"""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from app.agent.base import BaseAgent
from app.agent.task_based_toolcall import TaskBasedToolCallAgent
from app.core.agent.workflow_generator import WorkflowStep
from app.core.agent.workflow_monitor import WorkflowMonitor
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.schema import AgentState, Memory, Message


class AgentTaskStatus(str, Enum):
    """Status of an agent task in the parallel execution system."""

    PENDING = "pending"  # Task is waiting to be executed
    RUNNING = "running"  # Task is currently running
    COMPLETED = "completed"  # Task completed successfully
    FAILED = "failed"  # Task failed with an error
    CANCELLED = "cancelled"  # Task was cancelled
    BLOCKED = "blocked"  # Task is blocked waiting for dependencies


class AgentTask(BaseModel):
    """Represents a single task to be executed by an agent.

    This class encapsulates all the information needed to execute a task,
    including its dependencies, priority, and execution status.
    """

    task_id: str
    agent_type: str  # Type of agent to use for this task
    prompt: str  # The input prompt for the agent
    dependencies: List[str] = Field(default_factory=list)  # IDs of tasks this task depends on
    priority: int = 0  # Higher number = higher priority
    max_retries: int = 3  # Maximum number of retry attempts
    retry_count: int = 0  # Current retry count
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    result: Optional[str] = None  # Result of the task execution
    error: Optional[str] = None  # Error message if task failed
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None  # Time taken to execute in seconds
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional task metadata

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if this task is ready to be executed.

        A task is ready when all its dependencies have been completed.

        Args:
            completed_tasks: Set of task IDs that have been completed

        Returns:
            bool: True if the task is ready to be executed
        """
        return all(dep in completed_tasks for dep in self.dependencies)

    def mark_running(self) -> None:
        """Mark this task as running."""
        self.status = AgentTaskStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self, result: str) -> None:
        """Mark this task as completed with the given result.

        Args:
            result: The result of the task execution
        """
        self.status = AgentTaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def mark_failed(self, error: str) -> None:
        """Mark this task as failed with the given error.

        Args:
            error: The error message
        """
        self.status = AgentTaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def can_retry(self) -> bool:
        """Check if this task can be retried.

        Returns:
            bool: True if the task can be retried
        """
        return self.status == AgentTaskStatus.FAILED and self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment the retry count and reset the task status to pending."""
        self.retry_count += 1
        self.status = AgentTaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.execution_time = None


class ParallelAgentManager:
    """Manages the parallel execution of multiple agent tasks.

    This class is responsible for scheduling and executing multiple agent tasks
    concurrently, handling dependencies between tasks, and managing the overall
    execution flow.
    """

    def __init__(
        self,
        agent_factory: Dict[str, callable],
        max_concurrent_tasks: int = 5,
        task_timeout: int = 600,  # 10 minutes default timeout
        monitor: Optional[WorkflowMonitor] = None
    ):
        """Initialize the parallel agent manager.

        Args:
            agent_factory: Dictionary mapping agent types to factory functions
                that create agent instances
            max_concurrent_tasks: Maximum number of tasks to run concurrently
            task_timeout: Default timeout for tasks in seconds
            monitor: Optional workflow monitor for tracking execution metrics
        """
        self.agent_factory = agent_factory
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.monitor = monitor

        # Task management
        self.tasks: Dict[str, AgentTask] = {}
        self.completed_task_ids: Set[str] = set()
        self.running_tasks: Dict[str, asyncio.Task] = {}

        # Execution metrics
        self.execution_start: Optional[datetime] = None
        self.execution_end: Optional[datetime] = None
        self.total_execution_time: Optional[float] = None

    def add_task(self, task: AgentTask) -> None:
        """Add a task to the manager.

        Args:
            task: The task to add
        """
        self.tasks[task.task_id] = task
        logger.info(f"Added task {task.task_id} of type {task.agent_type}")

    def add_tasks(self, tasks: List[AgentTask]) -> None:
        """Add multiple tasks to the manager.

        Args:
            tasks: List of tasks to add
        """
        for task in tasks:
            self.add_task(task)

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Get a task by its ID.

        Args:
            task_id: The ID of the task to get

        Returns:
            Optional[AgentTask]: The task if found, None otherwise
        """
        return self.tasks.get(task_id)

    def get_ready_tasks(self) -> List[AgentTask]:
        """Get all tasks that are ready to be executed.

        A task is ready when it's in the PENDING state and all its
        dependencies have been completed.

        Returns:
            List[AgentTask]: List of tasks ready to be executed, sorted by priority
        """
        ready_tasks = [
            task for task in self.tasks.values()
            if task.status == AgentTaskStatus.PENDING and task.is_ready(self.completed_task_ids)
        ]
        # Sort by priority (higher first) and then by creation time (older first)
        return sorted(ready_tasks, key=lambda t: (-t.priority, t.created_at))

    def get_blocked_tasks(self) -> List[AgentTask]:
        """Get all tasks that are blocked by dependencies.

        Returns:
            List[AgentTask]: List of blocked tasks
        """
        return [
            task for task in self.tasks.values()
            if task.status == AgentTaskStatus.PENDING and not task.is_ready(self.completed_task_ids)
        ]

    def get_failed_tasks(self) -> List[AgentTask]:
        """Get all tasks that have failed.

        Returns:
            List[AgentTask]: List of failed tasks
        """
        return [task for task in self.tasks.values() if task.status == AgentTaskStatus.FAILED]

    def get_retryable_tasks(self) -> List[AgentTask]:
        """Get all tasks that can be retried.

        Returns:
            List[AgentTask]: List of retryable tasks
        """
        return [task for task in self.tasks.values() if task.can_retry()]

    def get_task_status_summary(self) -> Dict[str, int]:
        """Get a summary of task statuses.

        Returns:
            Dict[str, int]: Dictionary mapping status names to counts
        """
        status_counts = {status.value: 0 for status in AgentTaskStatus}
        for task in self.tasks.values():
            status_counts[task.status] += 1
        return status_counts

    async def execute_task(self, task: AgentTask) -> None:
        """Execute a single task with an agent.

        This method creates an agent instance, runs it with the task's prompt,
        and updates the task's status based on the result.

        Args:
            task: The task to execute
        """
        if task.task_id in self.running_tasks:
            logger.warning(f"Task {task.task_id} is already running")
            return

        # Mark task as running
        task.mark_running()
        logger.info(f"Starting execution of task {task.task_id}")

        try:
            # Create agent instance
            if task.agent_type not in self.agent_factory:
                raise ValueError(f"Unknown agent type: {task.agent_type}")

            agent = self.agent_factory[task.agent_type]()

            # Execute agent with timeout
            result = await asyncio.wait_for(
                agent.run(task.prompt),
                timeout=self.task_timeout
            )

            # Mark task as completed
            task.mark_completed(result)
            self.completed_task_ids.add(task.task_id)
            logger.info(f"Task {task.task_id} completed successfully")

        except asyncio.TimeoutError:
            error_msg = f"Task {task.task_id} timed out after {self.task_timeout} seconds"
            logger.error(error_msg)
            task.mark_failed(error_msg)

        except TokenLimitExceeded as e:
            error_msg = f"Token limit exceeded: {str(e)}"
            logger.error(error_msg)
            task.mark_failed(error_msg)

        except Exception as e:
            error_msg = f"Error executing task {task.task_id}: {str(e)}"
            logger.error(error_msg)
            task.mark_failed(error_msg)

        finally:
            # Remove task from running tasks
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]

    async def execute_all(self) -> Dict[str, Any]:
        """Execute all tasks in parallel, respecting dependencies and concurrency limits.

        Returns:
            Dict[str, Any]: Execution summary with results and metrics
        """
        self.execution_start = datetime.now()
        logger.info(f"Starting parallel execution of {len(self.tasks)} tasks")

        # Main execution loop
        while True:
            # Check if we're done
            pending_tasks = [t for t in self.tasks.values() if t.status in
                            [AgentTaskStatus.PENDING, AgentTaskStatus.RUNNING]]
            if not pending_tasks and not self.running_tasks:
                break

            # Get tasks that can be retried and reset them
            retryable_tasks = self.get_retryable_tasks()
            for task in retryable_tasks:
                logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count + 1}/{task.max_retries})")
                task.increment_retry()

            # Get tasks that are ready to run
            ready_tasks = self.get_ready_tasks()

            # Schedule new tasks up to the concurrency limit
            available_slots = self.max_concurrent_tasks - len(self.running_tasks)
            for task in ready_tasks[:available_slots]:
                # Create asyncio task
                asyncio_task = asyncio.create_task(self.execute_task(task))
                self.running_tasks[task.task_id] = asyncio_task

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

        # Calculate execution metrics
        self.execution_end = datetime.now()
        self.total_execution_time = (self.execution_end - self.execution_start).total_seconds()

        # Prepare execution summary
        summary = {
            "total_tasks": len(self.tasks),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == AgentTaskStatus.COMPLETED]),
            "failed_tasks": len([t for t in self.tasks.values() if t.status == AgentTaskStatus.FAILED]),
            "execution_time": self.total_execution_time,
            "status_summary": self.get_task_status_summary(),
            "results": {task_id: task.result for task_id, task in self.tasks.items()
                      if task.status == AgentTaskStatus.COMPLETED},
            "errors": {task_id: task.error for task_id, task in self.tasks.items()
                     if task.status == AgentTaskStatus.FAILED}
        }

        logger.info(f"Parallel execution completed in {self.total_execution_time:.2f} seconds")
        logger.info(f"Status summary: {summary['status_summary']}")

        return summary

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            bool: True if the task was cancelled, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            logger.warning(f"Cannot cancel task {task_id}: task not found")
            return False

        if task.status != AgentTaskStatus.RUNNING:
            logger.warning(f"Cannot cancel task {task_id}: task is not running (status: {task.status})")
            return False

        if task_id in self.running_tasks:
            # Cancel the asyncio task
            asyncio_task = self.running_tasks[task_id]
            asyncio_task.cancel()
            del self.running_tasks[task_id]

        # Mark task as cancelled
        task.status = AgentTaskStatus.CANCELLED
        logger.info(f"Task {task_id} cancelled")
        return True

    def cancel_all_tasks(self) -> int:
        """Cancel all running tasks.

        Returns:
            int: Number of tasks cancelled
        """
        cancelled_count = 0
        for task_id in list(self.running_tasks.keys()):
            if self.cancel_task(task_id):
                cancelled_count += 1
        return cancelled_count
