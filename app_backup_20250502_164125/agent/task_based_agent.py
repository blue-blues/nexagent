"""
Task-based agent implementation that replaces the step-based execution model.

This module provides a TaskBasedAgent class that executes tasks from a plan
rather than using a fixed number of steps.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
import time

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.schema import ROLE_TYPE, AgentState, Memory, Message


class Task(BaseModel):
    """Represents a single task to be executed by the agent."""
    
    id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    dependencies: List[str] = Field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def mark_in_progress(self):
        """Mark the task as in progress."""
        self.status = "in_progress"
        self.start_time = time.time()
    
    def mark_completed(self, result: str):
        """Mark the task as completed."""
        self.status = "completed"
        self.result = result
        self.end_time = time.time()
    
    def mark_failed(self, error: str):
        """Mark the task as failed."""
        self.status = "failed"
        self.error = error
        self.end_time = time.time()
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the task execution."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class TaskBasedAgent(BaseModel, ABC):
    """Abstract base class for task-based agent execution.
    
    Instead of using a fixed number of steps, this agent executes tasks from a plan.
    """
    
    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")
    
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
    
    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses
    
    @model_validator(mode="after")
    def initialize_agent(self) -> "TaskBasedAgent":
        """Initialize agent with default settings if not provided."""
        return self
    
    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for temporarily changing agent state."""
        old_state = self.state
        self.state = new_state
        try:
            yield
        finally:
            self.state = old_state
    
    def update_memory(self, role: ROLE_TYPE, content: str, **kwargs):
        """Add a message to the agent's memory."""
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
    
    def add_task(self, task_id: str, description: str, dependencies: List[str] = None) -> Task:
        """Add a task to the agent's task list."""
        task = Task(
            id=task_id,
            description=description,
            dependencies=dependencies or []
        )
        self.tasks[task_id] = task
        return task
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next task to execute based on dependencies."""
        # Find tasks that are pending and have all dependencies completed
        for task_id, task in self.tasks.items():
            if task.status != "pending":
                continue
            
            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in task.dependencies:
                if dep_id not in self.tasks or self.tasks[dep_id].status != "completed":
                    dependencies_met = False
                    break
            
            if dependencies_met:
                return task
        
        return None
    
    async def execute_task(self, task: Task) -> str:
        """Execute a single task."""
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
            return result
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {str(e)}")
            task.mark_failed(str(e))
            return f"Failed to execute task: {str(e)}"
    
    @abstractmethod
    async def _execute_task_impl(self, task: Task) -> str:
        """Implementation of task execution. Must be implemented by subclasses."""
        pass
    
    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's tasks asynchronously.
        
        Args:
            request: Optional initial user request to process.
            
        Returns:
            A string summarizing the execution results.
            
        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")
        
        if request:
            self.update_memory("user", request)
            
            # Create initial tasks from the request if needed
            await self._create_initial_tasks(request)
        
        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            # Execute tasks until all are completed or failed
            while True:
                next_task = self.get_next_task()
                if not next_task:
                    # Check if all tasks are completed or failed
                    all_done = True
                    for task in self.tasks.values():
                        if task.status not in ["completed", "failed"]:
                            all_done = False
                            break
                    
                    if all_done or not self.tasks:
                        break
                    
                    # If there are still tasks but none can be executed,
                    # there might be a dependency cycle
                    logger.warning("No executable tasks found, but not all tasks are completed")
                    results.append("Warning: Possible dependency cycle detected in tasks")
                    break
                
                logger.info(f"Executing task: {next_task.id} - {next_task.description}")
                task_result = await self.execute_task(next_task)
                results.append(f"Task {next_task.id}: {task_result}")
        
        # Reset state
        self.current_task_id = None
        self.state = AgentState.IDLE
        
        return "\n\n".join(results) if results else "No tasks executed"
    
    async def _create_initial_tasks(self, request: str) -> None:
        """Create initial tasks from the request. Can be overridden by subclasses."""
        # Default implementation creates a single task
        self.add_task("task_1", f"Execute request: {request}")
