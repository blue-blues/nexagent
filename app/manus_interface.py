"""User interface for the Manus-like agent.

This module provides a clean, intuitive interface for users to submit tasks,
view results, and toggle the visibility of the thinking process.
"""

from typing import Dict, List, Optional, Union, Any
import asyncio
from enum import Enum

from pydantic import BaseModel, Field

from app.agent.manus_agent import ManusAgent
from app.schema import Message
from app.logger import logger


class TaskCategory(str, Enum):
    """Categories for tasks that can be submitted to the Manus agent."""
    
    RESEARCH = "research"
    DATA_ANALYSIS = "data_analysis"
    TRAVEL_PLANNING = "travel_planning"
    CONTENT_GENERATION = "content_generation"
    GENERAL = "general"


class TaskResult(BaseModel):
    """Result of a task processed by the Manus agent."""
    
    task_id: str
    category: TaskCategory
    summary: str
    details: str
    thinking_process: Optional[List[Dict[str, Any]]] = None
    created_at: str
    completed_at: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed


class TaskRequest(BaseModel):
    """Request to submit a task to the Manus agent."""
    
    task_description: str
    category: TaskCategory = TaskCategory.GENERAL
    show_thinking: bool = True
    priority: int = 1  # 1 (highest) to 5 (lowest)


class ManusInterface:
    """Interface for interacting with the Manus agent.
    
    This class provides methods for submitting tasks, retrieving results,
    and controlling the visibility of the thinking process.
    """
    
    def __init__(self):
        """Initialize the Manus interface."""
        self.agent = ManusAgent()
        self.tasks: Dict[str, TaskResult] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.is_processing: bool = False
        
    async def initialize(self):
        """Initialize the interface and start the task processor."""
        # Start the task processor
        asyncio.create_task(self._process_tasks())
        logger.info("ManusInterface initialized and ready to process tasks")
        
    async def submit_task(self, request: TaskRequest) -> str:
        """Submit a task to the Manus agent.
        
        Args:
            request: The task request
            
        Returns:
            str: The task ID
        """
        # Generate a unique task ID
        import uuid
        import datetime
        
        task_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        
        # Create a task result object
        task_result = TaskResult(
            task_id=task_id,
            category=request.category,
            summary="Task submitted",
            details=request.task_description,
            created_at=created_at,
            status="pending"
        )
        
        # Store the task result
        self.tasks[task_id] = task_result
        
        # Add the task to the queue
        await self.task_queue.put((task_id, request))
        
        logger.info(f"Task {task_id} submitted: {request.task_description}")
        
        return task_id
        
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the result of a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            Optional[TaskResult]: The task result, or None if not found
        """
        return self.tasks.get(task_id)
        
    async def get_all_tasks(self) -> List[TaskResult]:
        """Get all tasks.
        
        Returns:
            List[TaskResult]: All tasks
        """
        return list(self.tasks.values())
        
    async def toggle_thinking_visibility(self, task_id: str, show: bool) -> bool:
        """Toggle the visibility of the thinking process for a task.
        
        Args:
            task_id: The task ID
            show: Whether to show the thinking process
            
        Returns:
            bool: True if successful, False otherwise
        """
        if task_id not in self.tasks:
            return False
            
        # If the task is in progress, update the agent's setting
        if self.tasks[task_id].status == "in_progress":
            await self.agent.toggle_thinking_visibility(show)
            
        return True
        
    async def _process_tasks(self):
        """Process tasks from the queue."""
        while True:
            # Get the next task from the queue
            task_id, request = await self.task_queue.get()
            
            # Update the task status
            if task_id in self.tasks:
                self.tasks[task_id].status = "in_progress"
                
            try:
                # Configure the agent
                await self.agent.toggle_thinking_visibility(request.show_thinking)
                
                # Process the task
                logger.info(f"Processing task {task_id}: {request.task_description}")
                result = await self.agent.run(request.task_description)
                
                # Update the task result
                import datetime
                
                if task_id in self.tasks:
                    self.tasks[task_id].summary = "Task completed"
                    self.tasks[task_id].details = result
                    self.tasks[task_id].thinking_process = self.agent.thought_history
                    self.tasks[task_id].completed_at = datetime.datetime.now().isoformat()
                    self.tasks[task_id].status = "completed"
                    
                logger.info(f"Task {task_id} completed")
                
            except Exception as e:
                # Update the task result with the error
                if task_id in self.tasks:
                    self.tasks[task_id].summary = "Task failed"
                    self.tasks[task_id].details = f"Error: {str(e)}"
                    self.tasks[task_id].status = "failed"
                    
                logger.error(f"Error processing task {task_id}: {str(e)}")
                
            finally:
                # Mark the task as done in the queue
                self.task_queue.task_done()
                
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.
        
        Args:
            task_id: The task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if task_id not in self.tasks:
            return False
            
        # Can only cancel pending tasks
        if self.tasks[task_id].status != "pending":
            return False
            
        # Update the task status
        self.tasks[task_id].status = "cancelled"
        
        return True