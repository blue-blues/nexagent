"""API server for the Manus-like agent.

This module provides a REST API for interacting with the Manus-like agent,
allowing users to submit tasks, retrieve results, and control the visibility
of the thinking process.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.manus_interface import ManusInterface, TaskRequest, TaskResult, TaskCategory


# Create a router for the Manus API
router = APIRouter(prefix="/manus", tags=["manus"])

# Global interface instance
manus_interface = None


async def get_interface() -> ManusInterface:
    """Get the Manus interface instance.
    
    Returns:
        ManusInterface: The Manus interface instance
    """
    global manus_interface
    if manus_interface is None:
        manus_interface = ManusInterface()
        await manus_interface.initialize()
    return manus_interface


class TaskSubmissionResponse(BaseModel):
    """Response for task submission."""
    
    task_id: str
    message: str


class ThinkingVisibilityRequest(BaseModel):
    """Request to toggle thinking visibility."""
    
    show: bool


@router.post("/tasks", response_model=TaskSubmissionResponse)
async def submit_task(
    task_request: TaskRequest,
    background_tasks: BackgroundTasks,
    interface: ManusInterface = Depends(get_interface)
) -> TaskSubmissionResponse:
    """Submit a task to the Manus agent.
    
    Args:
        task_request: The task request
        background_tasks: FastAPI background tasks
        interface: The Manus interface
        
    Returns:
        TaskSubmissionResponse: The response with task ID
    """
    task_id = await interface.submit_task(task_request)
    
    return TaskSubmissionResponse(
        task_id=task_id,
        message="Task submitted successfully"
    )


@router.get("/tasks/{task_id}", response_model=TaskResult)
async def get_task(
    task_id: str,
    interface: ManusInterface = Depends(get_interface)
) -> TaskResult:
    """Get a task result.
    
    Args:
        task_id: The task ID
        interface: The Manus interface
        
    Returns:
        TaskResult: The task result
    """
    task_result = await interface.get_task_result(task_id)
    
    if task_result is None:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return task_result


@router.get("/tasks", response_model=List[TaskResult])
async def get_all_tasks(
    category: Optional[TaskCategory] = None,
    status: Optional[str] = None,
    interface: ManusInterface = Depends(get_interface)
) -> List[TaskResult]:
    """Get all tasks, optionally filtered by category and status.
    
    Args:
        category: Optional category filter
        status: Optional status filter
        interface: The Manus interface
        
    Returns:
        List[TaskResult]: The filtered tasks
    """
    tasks = await interface.get_all_tasks()
    
    # Apply filters if provided
    if category:
        tasks = [task for task in tasks if task.category == category]
        
    if status:
        tasks = [task for task in tasks if task.status == status]
        
    return tasks


@router.post("/tasks/{task_id}/thinking", response_model=dict)
async def toggle_thinking_visibility(
    task_id: str,
    request: ThinkingVisibilityRequest,
    interface: ManusInterface = Depends(get_interface)
) -> dict:
    """Toggle the visibility of the thinking process for a task.
    
    Args:
        task_id: The task ID
        request: The visibility request
        interface: The Manus interface
        
    Returns:
        dict: A success message
    """
    success = await interface.toggle_thinking_visibility(task_id, request.show)
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {"message": f"Thinking visibility set to {request.show}"}


@router.delete("/tasks/{task_id}", response_model=dict)
async def cancel_task(
    task_id: str,
    interface: ManusInterface = Depends(get_interface)
) -> dict:
    """Cancel a pending task.
    
    Args:
        task_id: The task ID
        interface: The Manus interface
        
    Returns:
        dict: A success message
    """
    success = await interface.cancel_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Task not found or cannot be cancelled"
        )
        
    return {"message": "Task cancelled successfully"}


@router.get("/categories", response_model=List[str])
async def get_categories() -> List[str]:
    """Get all available task categories.
    
    Returns:
        List[str]: The available categories
    """
    return [category.value for category in TaskCategory]