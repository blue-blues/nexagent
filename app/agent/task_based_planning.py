"""
Task-based planning agent implementation.

This module provides a TaskBasedPlanningAgent class that creates and executes plans
as a series of tasks rather than using a fixed number of steps.
"""

import json
import uuid
from typing import Dict, List, Optional, Any

from pydantic import Field

from app.agent.task_based_toolcall import TaskBasedToolCallAgent
from app.agent.task_based_agent import Task
from app.logger import logger
from app.schema import Message, ToolChoice
from app.tools import ToolCollection
from app.tools.planning import PlanningTool
from app.tools.terminate import Terminate


class TaskBasedPlanningAgent(TaskBasedToolCallAgent):
    """
    A task-based agent that creates and manages plans to solve tasks.

    This agent uses a planning tool to create and manage structured plans,
    and automatically converts plan steps into executable tasks.
    """

    name: str = "task_based_planning"
    description: str = "A task-based agent that creates and manages plans to solve tasks"

    system_prompt: str = """You are a planning agent that creates and manages plans to solve complex tasks.
Your job is to break down complex tasks into manageable steps, create a plan, and execute it.
You can use the planning tool to create, update, and manage plans.
"""

    task_prompt: str = """Complete this task by creating and executing a plan.
If you want to stop interaction, use `terminate` tool/function call.
"""

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(PlanningTool(), Terminate())
    )

    # Planning attributes
    active_plan_id: Optional[str] = Field(
        default=None, description="ID of the active plan"
    )
    plan_to_task_map: Dict[str, str] = Field(
        default_factory=dict, description="Mapping from plan step indices to task IDs"
    )

    async def _create_initial_tasks(self, request: str) -> None:
        """Create initial tasks from the request by creating a plan."""
        # Generate a unique plan ID
        self.active_plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # Create a task to generate the initial plan
        plan_task_id = f"create_plan_{self.active_plan_id}"
        self.add_task(
            task_id=plan_task_id,
            description=f"Create a plan for: {request}"
        )

        # Execute the plan creation task
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")
        await self.execute_task(self.tasks[plan_task_id])

        # Now convert the plan steps to tasks
        await self._convert_plan_to_tasks()

    async def _convert_plan_to_tasks(self) -> None:
        """Convert the current plan steps to tasks."""
        if not self.active_plan_id:
            logger.warning("No active plan to convert to tasks")
            return

        # Get the current plan
        plan_result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id}
        )

        # Parse the plan data
        plan_data = None
        try:
            # The plan tool returns a ToolResult with an output attribute
            if hasattr(plan_result, "output"):
                # Try to extract the plan data from the output
                # This is a bit hacky, but we need to parse the formatted plan output
                plan_data = self._parse_plan_output(plan_result.output)
            else:
                logger.error(f"Unexpected plan result type: {type(plan_result)}")
                return
        except Exception as e:
            logger.error(f"Error parsing plan data: {str(e)}")
            return

        if not plan_data or "steps" not in plan_data:
            logger.warning("No steps found in plan")
            return

        # Create tasks for each step in the plan
        prev_task_id = None
        for i, step in enumerate(plan_data["steps"]):
            step_index = i + 1  # 1-based index for steps
            task_id = f"plan_{self.active_plan_id}_step_{step_index}"

            # Create a task for this step
            dependencies = []
            if prev_task_id:
                dependencies.append(prev_task_id)

            self.add_task(
                task_id=task_id,
                description=f"Execute plan step {step_index}: {step}",
                dependencies=dependencies
            )

            # Map the plan step to the task
            self.plan_to_task_map[f"{self.active_plan_id}_{step_index}"] = task_id

            # Update the previous task ID for the next iteration
            prev_task_id = task_id

    def _parse_plan_output(self, plan_output: str) -> Dict[str, Any]:
        """Parse the plan output to extract the plan data."""
        # This is a simplified implementation that extracts steps from the formatted plan output
        # In a real implementation, you would want to use a more robust parsing approach

        lines = plan_output.strip().split("\n")
        steps = []

        for line in lines:
            # Look for lines that start with a step number followed by a status icon
            if line.strip() and any(c.isdigit() for c in line[:2]):
                # Extract the step description (remove the step number and status icon)
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    step_desc = parts[2].split(" - Notes:")[0].strip()
                    steps.append(step_desc)

        return {"steps": steps}

    async def _execute_task_impl(self, task: Task) -> str:
        """Execute a task, with special handling for plan-related tasks."""
        # Check if this is a plan creation task
        if task.id.startswith("create_plan_"):
            # This is a plan creation task
            return await self._create_plan(task)

        # For regular plan step tasks, use the standard tool call execution
        return await super()._execute_task_impl(task)

    async def _create_plan(self, task: Task) -> str:
        """Create a plan for the given task."""
        # Extract the request from the task description
        request = task.description.replace("Create a plan for:", "").strip()

        # Create messages for the plan creation
        messages = [
            Message.user_message(
                f"Analyze the request and create a plan with ID {self.active_plan_id}: {request}"
            )
        ]
        self.memory.add_messages(messages)

        # Get a response with tool calls
        response = await self.llm.ask_tool(
            messages=messages,
            system_msgs=[Message.system_message(self.system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice=ToolChoice.AUTO,
        )

        # Add the assistant message to memory
        assistant_msg = Message.from_tool_calls(
            content=response.content, tool_calls=response.tool_calls
        )
        self.memory.add_message(assistant_msg)

        # Execute the planning tool call
        plan_created = False
        result = None

        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                result = await self.execute_tool(tool_call)
                logger.info(
                    f"Executed tool {tool_call.function.name} with result: {result}"
                )

                # Add tool response to memory
                tool_msg = Message.tool_message(
                    content=result,
                    tool_call_id=tool_call.id,
                    name=tool_call.function.name,
                )
                self.memory.add_message(tool_msg)
                plan_created = True
                break

        if not plan_created:
            logger.warning("No plan created from initial request")
            error_msg = "Error: Failed to create plan"
            self.memory.add_message(Message.assistant_message(error_msg))
            return error_msg

        return f"Plan created successfully: {self.active_plan_id}"

    async def update_plan_step_status(self, step_index: int, status: str, notes: Optional[str] = None) -> None:
        """Update the status of a plan step."""
        if not self.active_plan_id:
            logger.warning("No active plan to update step status")
            return

        # Update the plan step status
        await self.available_tools.execute(
            name="planning",
            tool_input={
                "command": "update_step",
                "plan_id": self.active_plan_id,
                "step_index": step_index,
                "status": status,
                "notes": notes or ""
            }
        )

    async def _on_task_completed(self, task: Task) -> None:
        """Handle task completion by updating the plan step status."""
        # Check if this is a plan step task
        for plan_step_key, task_id in self.plan_to_task_map.items():
            if task_id == task.id:
                # Extract the step index from the key
                plan_id, step_index_str = plan_step_key.rsplit("_", 1)
                step_index = int(step_index_str)

                # Update the plan step status
                await self.update_plan_step_status(
                    step_index=step_index,
                    status="completed",
                    notes=f"Completed: {task.result[:100]}..." if task.result and len(task.result) > 100 else task.result
                )
                break
