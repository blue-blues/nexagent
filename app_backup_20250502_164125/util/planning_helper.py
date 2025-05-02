"""
Planning Helper

This module provides helper functions for working with the PlanningTool.
"""

import uuid
from typing import Optional, List, Dict, Any

from app.tools.planning import PlanningTool
from app.tool.base import ToolResult
from app.logger import logger


async def create_plan(
    planning_tool: PlanningTool,
    title: str,
    description: Optional[str] = None,
    steps: Optional[List[str]] = None,
    step_dependencies: Optional[List[List[int]]] = None,
    plan_id: Optional[str] = None
) -> ToolResult:
    """
    Create a new plan with the given title and optional details.
    
    Args:
        planning_tool: The PlanningTool instance to use
        title: Title for the plan
        description: Optional detailed description of the plan
        steps: Optional list of steps for the plan
        step_dependencies: Optional dependencies between steps
        plan_id: Optional plan ID (will be auto-generated if not provided)
        
    Returns:
        ToolResult with the result of the operation
    """
    # Generate a plan ID if not provided
    if not plan_id:
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        logger.info(f"Auto-generated plan ID: {plan_id}")
    
    try:
        # Call the planning tool with the create command
        result = await planning_tool.execute(
            command="create",
            plan_id=plan_id,
            title=title,
            description=description,
            steps=steps,
            step_dependencies=step_dependencies
        )
        return result
    except Exception as e:
        logger.error(f"Error creating plan: {str(e)}")
        return ToolResult(error=f"Failed to create plan: {str(e)}")


async def update_plan(
    planning_tool: PlanningTool,
    plan_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    steps: Optional[List[str]] = None,
    step_dependencies: Optional[List[List[int]]] = None
) -> ToolResult:
    """
    Update an existing plan with new details.
    
    Args:
        planning_tool: The PlanningTool instance to use
        plan_id: ID of the plan to update
        title: Optional new title for the plan
        description: Optional new description for the plan
        steps: Optional new list of steps for the plan
        step_dependencies: Optional new dependencies between steps
        
    Returns:
        ToolResult with the result of the operation
    """
    try:
        # Call the planning tool with the update command
        result = await planning_tool.execute(
            command="update",
            plan_id=plan_id,
            title=title,
            description=description,
            steps=steps,
            step_dependencies=step_dependencies
        )
        return result
    except Exception as e:
        logger.error(f"Error updating plan: {str(e)}")
        return ToolResult(error=f"Failed to update plan: {str(e)}")


async def get_active_plan(planning_tool: PlanningTool) -> ToolResult:
    """
    Get the currently active plan.
    
    Args:
        planning_tool: The PlanningTool instance to use
        
    Returns:
        ToolResult with the active plan details or an error message
    """
    try:
        # Call the planning tool with the get command (no plan_id to get active plan)
        result = await planning_tool.execute(command="get")
        return result
    except Exception as e:
        logger.error(f"Error getting active plan: {str(e)}")
        return ToolResult(error=f"Failed to get active plan: {str(e)}")


async def list_plans(planning_tool: PlanningTool) -> ToolResult:
    """
    List all available plans.
    
    Args:
        planning_tool: The PlanningTool instance to use
        
    Returns:
        ToolResult with the list of plans
    """
    try:
        # Call the planning tool with the list command
        result = await planning_tool.execute(command="list")
        return result
    except Exception as e:
        logger.error(f"Error listing plans: {str(e)}")
        return ToolResult(error=f"Failed to list plans: {str(e)}")
