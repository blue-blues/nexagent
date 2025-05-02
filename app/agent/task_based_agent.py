"""
Task-based agent implementation that replaces the step-based execution model.

This module provides a TaskBasedAgent class that executes tasks from a plan
rather than using a fixed number of steps. The task-based approach offers more
flexibility, better dependency management, and improved progress tracking.

Copyright (c) 2023-2024 Nexagent
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
import time
import uuid
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, model_validator, ConfigDict

from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Memory, Message


class TaskStatus(str, Enum):
    """Enumeration of possible task statuses."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(int, Enum):
    """Task priority levels from highest (1) to lowest (5)."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class Task(BaseModel):
    """
    Represents a single task to be executed by the agent.

    A task is the fundamental unit of work in the task-based execution system.
    Each task has a unique ID, description, status, and optional dependencies
    on other tasks.

    Attributes:
        id: Unique identifier for the task
        description: Human-readable description of the task
        status: Current execution status
        dependencies: List of task IDs that must complete before this task can execute
        result: Output produced by the task execution
        error: Error message if the task failed
        priority: Execution priority (lower number = higher priority)
        created_at: When the task was created
        start_time: When the task execution started
        end_time: When the task execution completed or failed
        requires_tools: Whether this task requires tool calls to execute
        complexity: Estimated complexity on a scale of 1-10
        subtasks: List of child tasks if this is a complex task
        parent_id: ID of the parent task if this is a subtask
        metadata: Additional task-specific data
        max_retries: Maximum number of retry attempts
        retry_count: Current retry count
    """

    # Core attributes
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    description: str
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    dependencies: List[str] = Field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None

    # Scheduling attributes
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    created_at: datetime = Field(default_factory=datetime.now)
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    # Advanced attributes
    requires_tools: bool = Field(default=False)
    complexity: int = Field(default=1, ge=1, le=10)
    subtasks: List["Task"] = Field(default_factory=list)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Retry mechanism
    max_retries: int = Field(default=3, ge=0)
    retry_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )

    def mark_in_progress(self) -> None:
        """
        Mark the task as in progress.

        Sets the status to IN_PROGRESS and records the start time.
        """
        self.status = TaskStatus.IN_PROGRESS
        self.start_time = time.time()
        logger.debug(f"Task {self.id} marked as in progress")

    def mark_completed(self, result: str) -> None:
        """
        Mark the task as completed with the given result.

        Args:
            result: The output produced by the task execution
        """
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.end_time = time.time()
        logger.debug(f"Task {self.id} marked as completed")

    def mark_failed(self, error: str) -> None:
        """
        Mark the task as failed with the given error.

        Args:
            error: The error message describing why the task failed
        """
        self.status = TaskStatus.FAILED
        self.error = error
        self.end_time = time.time()
        logger.debug(f"Task {self.id} marked as failed: {error}")

    def mark_cancelled(self, reason: Optional[str] = None) -> None:
        """
        Mark the task as cancelled.

        Args:
            reason: Optional reason for cancellation
        """
        self.status = TaskStatus.CANCELLED
        if reason:
            self.error = f"Cancelled: {reason}"
        self.end_time = time.time()
        logger.debug(f"Task {self.id} marked as cancelled")

    def mark_blocked(self, reason: str) -> None:
        """
        Mark the task as blocked.

        Args:
            reason: The reason why the task is blocked
        """
        self.status = TaskStatus.BLOCKED
        self.error = f"Blocked: {reason}"
        logger.debug(f"Task {self.id} marked as blocked: {reason}")

    def can_retry(self) -> bool:
        """
        Check if the task can be retried.

        Returns:
            True if the task can be retried, False otherwise
        """
        return (
            self.status == TaskStatus.FAILED and
            self.retry_count < self.max_retries
        )

    def increment_retry(self) -> None:
        """Increment the retry count and reset the task status to pending."""
        self.retry_count += 1
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.error = None
        logger.debug(f"Task {self.id} retry attempt {self.retry_count}/{self.max_retries}")

    @property
    def duration(self) -> Optional[float]:
        """
        Get the duration of the task execution in seconds.

        Returns:
            The duration in seconds, or None if the task hasn't completed
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_complete(self) -> bool:
        """Check if the task is completed."""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if the task has failed."""
        return self.status == TaskStatus.FAILED

    @property
    def is_active(self) -> bool:
        """Check if the task is currently active (pending or in progress)."""
        return self.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)

    @property
    def has_subtasks(self) -> bool:
        """Check if the task has subtasks."""
        return len(self.subtasks) > 0

    def add_subtask(self, description: str, **kwargs) -> "Task":
        """
        Add a subtask to this task.

        Args:
            description: Description of the subtask
            **kwargs: Additional task attributes

        Returns:
            The created subtask
        """
        subtask = Task(
            description=description,
            parent_id=self.id,
            **kwargs
        )
        self.subtasks.append(subtask)
        return subtask

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary representation.

        Returns:
            Dictionary representation of the task
        """
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "duration": self.duration,
            "complexity": self.complexity,
            "requires_tools": self.requires_tools,
            "parent_id": self.parent_id,
            "has_subtasks": self.has_subtasks,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


class TaskBasedAgent(BaseModel, ABC):
    """
    Abstract base class for task-based agent execution.

    Instead of using a fixed number of steps, this agent executes tasks from a plan.
    Tasks are executed based on their dependencies, allowing for more flexible and
    natural execution flows.

    This class provides the core functionality for managing and executing tasks,
    including dependency tracking, task selection, and execution. Subclasses must
    implement the _execute_task_impl method to define how tasks are executed.

    Attributes:
        name: Unique name of the agent
        description: Optional description of the agent
        system_prompt: System-level instruction prompt
        task_prompt: Prompt for executing a task
        llm: Language model instance
        memory: Agent's memory store
        state: Current agent state
        tasks: Dictionary of tasks to execute
        current_task_id: ID of the task currently being executed
        max_concurrent_tasks: Maximum number of tasks to execute concurrently
        execution_stats: Statistics about task execution
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")
    version: str = Field("1.0.0", description="Agent version")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    task_prompt: Optional[str] = Field(
        None, description="Prompt for executing a task"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Task management
    tasks: Dict[str, Task] = Field(default_factory=dict, description="Tasks to execute")
    current_task_id: Optional[str] = Field(None, description="Current task being executed")
    max_concurrent_tasks: int = Field(1, description="Maximum number of tasks to execute concurrently")

    # Statistics
    execution_stats: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_execution_time": 0.0,
            "avg_task_duration": 0.0,
            "start_time": None,
            "end_time": None
        },
        description="Statistics about task execution"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow"  # Allow extra fields for flexibility in subclasses
    )

    @model_validator(mode="after")
    def initialize_agent(self) -> "TaskBasedAgent":
        """
        Initialize agent with default settings if not provided.

        Returns:
            The initialized agent instance
        """
        # Initialize memory with system prompt if provided
        if self.system_prompt and not self.memory.messages:
            self.memory.add_message(Message.system_message(self.system_prompt))

        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """
        Context manager for temporarily changing agent state.

        Args:
            new_state: The state to set during the context

        Yields:
            Control back to the caller within the context
        """
        old_state = self.state
        self.state = new_state
        try:
            yield
        finally:
            self.state = old_state

    def update_memory(self, role: str, content: str, **kwargs) -> None:
        """
        Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool)
            content: The message content
            **kwargs: Additional message parameters

        Raises:
            ValueError: If the role is not supported
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        msg_factory = message_map[role]
        msg = msg_factory(content, **kwargs) if role == "tool" else msg_factory(content)
        self.memory.add_message(msg)

    @property
    def messages(self) -> List[Message]:
        """
        Get the messages from the agent's memory.

        Returns:
            List of messages from memory
        """
        return self.memory.messages

    def add_task(self, task_id: str, description: str, dependencies: Optional[List[str]] = None, **kwargs) -> Task:
        """
        Add a task to the agent's task list.

        Args:
            task_id: Unique identifier for the task
            description: Human-readable description of the task
            dependencies: List of task IDs that must complete before this task can execute
            **kwargs: Additional task attributes

        Returns:
            The created task

        Raises:
            ValueError: If a task with the same ID already exists
        """
        if task_id in self.tasks:
            raise ValueError(f"Task with ID '{task_id}' already exists")

        task = Task(
            id=task_id,
            description=description,
            dependencies=dependencies or [],
            **kwargs
        )
        self.tasks[task_id] = task
        self.execution_stats["total_tasks"] += 1
        logger.debug(f"Added task {task_id}: {description}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID.

        Args:
            task_id: The ID of the task to retrieve

        Returns:
            The task if found, None otherwise
        """
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks.

        Returns:
            List of all tasks
        """
        return list(self.tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        Get tasks with the specified status.

        Args:
            status: The status to filter by

        Returns:
            List of tasks with the specified status
        """
        return [task for task in self.tasks.values() if task.status == status]

    def get_next_task(self) -> Optional[Task]:
        """
        Get the next task to execute based on dependencies and priority.

        Returns:
            The next task to execute, or None if no tasks are ready
        """
        eligible_tasks = []

        # Find tasks that are pending and have all dependencies completed
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in task.dependencies:
                if dep_id not in self.tasks or not self.tasks[dep_id].is_complete:
                    dependencies_met = False
                    break

            if dependencies_met:
                eligible_tasks.append(task)

        if not eligible_tasks:
            return None

        # Sort by priority (lower number = higher priority)
        eligible_tasks.sort(key=lambda t: t.priority.value)
        return eligible_tasks[0]

    def detect_dependency_cycles(self) -> List[List[str]]:
        """
        Detect cycles in the task dependency graph.

        Returns:
            List of cycles, where each cycle is a list of task IDs
        """
        cycles = []
        visited = set()
        path = []

        def dfs(task_id: str) -> None:
            if task_id in path:
                # Found a cycle
                cycle_start = path.index(task_id)
                cycles.append(path[cycle_start:] + [task_id])
                return

            if task_id in visited:
                return

            visited.add(task_id)
            path.append(task_id)

            task = self.tasks.get(task_id)
            if task:
                for dep_id in task.dependencies:
                    dfs(dep_id)

            path.pop()

        # Start DFS from each task
        for task_id in self.tasks:
            dfs(task_id)

        return cycles

    async def execute_task(self, task_id: str) -> str:
        """
        Execute a single task by its ID.

        Args:
            task_id: The ID of the task to execute

        Returns:
            The result of the task execution

        Raises:
            ValueError: If the task is not found
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task with ID '{task_id}' not found")

        return await self._execute_task(task)

    async def _execute_task(self, task: Task) -> str:
        """
        Execute a single task.

        Args:
            task: The task to execute

        Returns:
            The result of the task execution
        """
        logger.info(f"Executing task: {task.id} - {task.description}")
        task.mark_in_progress()
        self.current_task_id = task.id

        try:
            # Prepare task prompt
            task_prompt = f"Task: {task.description}\n\n{self.task_prompt or ''}"
            self.update_memory("user", task_prompt)

            # Execute the task
            result = await self._execute_task_impl(task)

            # Mark task as completed
            task.mark_completed(result)
            self.execution_stats["completed_tasks"] += 1

            if task.duration:
                self.execution_stats["total_execution_time"] += task.duration
                self.execution_stats["avg_task_duration"] = (
                    self.execution_stats["total_execution_time"] /
                    self.execution_stats["completed_tasks"]
                )

            return result
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {str(e)}")
            task.mark_failed(str(e))
            self.execution_stats["failed_tasks"] += 1
            return f"Failed to execute task: {str(e)}"

    @abstractmethod
    async def _execute_task_impl(self, task: Task) -> str:
        """
        Implementation of task execution. Must be implemented by subclasses.

        Args:
            task: The task to execute

        Returns:
            The result of the task execution
        """
        pass

    async def execute_all_tasks(self) -> List[Task]:
        """
        Execute all tasks in dependency order.

        Returns:
            List of completed tasks
        """
        if not self.tasks:
            logger.warning("No tasks to execute")
            return []

        # Check for dependency cycles
        cycles = self.detect_dependency_cycles()
        if cycles:
            cycle_str = ", ".join(" -> ".join(cycle) for cycle in cycles)
            logger.error(f"Dependency cycles detected: {cycle_str}")
            raise ValueError(f"Dependency cycles detected: {cycle_str}")

        completed_tasks = []

        # Start execution timer
        self.execution_stats["start_time"] = time.time()

        async with self.state_context(AgentState.RUNNING):
            # Execute tasks until all are completed or failed
            while True:
                next_task = self.get_next_task()
                if not next_task:
                    # Check if all tasks are completed or failed
                    all_done = True
                    for task in self.tasks.values():
                        if task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                            all_done = False
                            break

                    if all_done or not self.tasks:
                        break

                    # If there are still tasks but none can be executed,
                    # there might be a dependency issue
                    logger.warning("No executable tasks found, but not all tasks are completed")
                    break

                await self._execute_task(next_task)
                if next_task.is_complete:
                    completed_tasks.append(next_task)

        # End execution timer
        self.execution_stats["end_time"] = time.time()

        # Reset state
        self.current_task_id = None
        self.state = AgentState.IDLE

        return completed_tasks

    async def run(self, request: Optional[str] = None) -> str:
        """
        Execute the agent's tasks asynchronously.

        Args:
            request: Optional initial user request to process

        Returns:
            A string summarizing the execution results

        Raises:
            RuntimeError: If the agent is not in IDLE state at start
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            self.update_memory("user", request)

            # Create initial tasks from the request if needed
            await self._create_initial_tasks(request)

        if not self.tasks:
            return "No tasks to execute"

        # Execute all tasks
        await self.execute_all_tasks()

        # Generate summary
        results = []
        for task in self.tasks.values():
            if task.is_complete:
                results.append(f"✅ Task {task.id}: {task.description}\n   Result: {task.result}")
            elif task.is_failed:
                results.append(f"❌ Task {task.id}: {task.description}\n   Error: {task.error}")
            else:
                results.append(f"⏸️ Task {task.id}: {task.description}\n   Status: {task.status.value}")

        # Add execution statistics
        if self.execution_stats["start_time"] and self.execution_stats["end_time"]:
            total_time = self.execution_stats["end_time"] - self.execution_stats["start_time"]
            stats = (
                f"\n\n📊 Execution Statistics:\n"
                f"Total tasks: {self.execution_stats['total_tasks']}\n"
                f"Completed: {self.execution_stats['completed_tasks']}\n"
                f"Failed: {self.execution_stats['failed_tasks']}\n"
                f"Total execution time: {total_time:.2f}s\n"
                f"Average task duration: {self.execution_stats['avg_task_duration']:.2f}s"
            )
            results.append(stats)

        return "\n\n".join(results)

    async def _create_initial_tasks(self, request: str) -> None:
        """
        Create initial tasks from the request. Can be overridden by subclasses.

        Args:
            request: The user request to process
        """
        # Default implementation creates a single task
        self.add_task("task_1", f"Execute request: {request}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the agent to a dictionary representation.

        Returns:
            Dictionary representation of the agent
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "state": self.state.value,
            "current_task_id": self.current_task_id,
            "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            "execution_stats": self.execution_stats
        }
