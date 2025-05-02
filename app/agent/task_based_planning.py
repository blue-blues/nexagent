"""
Task-based planning agent implementation.

This module provides a TaskBasedPlanningAgent class that creates and executes plans
as a series of tasks rather than using a fixed number of steps. The agent uses a
planning tool to create structured plans and automatically converts plan steps into
executable tasks with proper dependency management.

Key features:
- Dynamic plan creation and execution
- Plan step to task conversion
- Plan optimization based on task results
- Progress tracking and reporting
- Automatic plan adjustment based on execution feedback

Copyright (c) 2023-2024 Nexagent
"""

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
from app.planning.task_result_analyzer import TaskResultAnalyzer
from app.planning.plan_optimizer import PlanOptimizer


class TaskBasedPlanningAgent(TaskBasedToolCallAgent):
    """
    A task-based agent that creates and manages plans to solve complex tasks.

    This agent extends the TaskBasedToolCallAgent with planning capabilities,
    allowing it to create structured plans, convert plan steps into executable tasks,
    and dynamically adjust plans based on execution feedback.

    The agent implements a dynamic planning approach where tasks are generated
    on-the-fly as previous tasks are completed, rather than creating all tasks
    upfront. This allows the agent to adapt to changing circumstances and
    incorporate feedback from task execution into the planning process.

    Key features:
    - Plan creation and management
    - Dynamic task generation based on plan steps
    - Plan optimization based on task execution results
    - Progress tracking and reporting
    - Automatic plan adjustment based on execution feedback

    Attributes:
        name: Unique name of the agent
        description: Description of the agent
        system_prompt: System-level instruction prompt
        task_prompt: Prompt for executing a task
        available_tools: Collection of tools available to the agent
        active_plan_id: ID of the currently active plan
        plan_to_task_map: Mapping from plan step indices to task IDs
        task_analyzer: Component for analyzing task execution results
        plan_optimizer: Component for optimizing plans based on feedback
        completed_tasks: List of completed tasks for analysis
        current_plan_data: Current plan data for dynamic task generation
        current_step_index: Current step index in the plan
    """

    name: str = "task_based_planning"
    description: str = "A task-based agent that creates and manages plans to solve complex tasks"
    version: str = "1.0.0"

    system_prompt: str = """You are a planning agent that creates and manages plans to solve complex tasks.
Your job is to break down complex tasks into manageable steps, create a plan, and execute it.
You can use the planning tool to create, update, and manage plans.

When creating plans:
1. Break down complex tasks into clear, actionable steps
2. Ensure each step has a well-defined outcome
3. Consider dependencies between steps
4. Adapt the plan based on execution feedback
5. Optimize the plan as you learn more about the task

Always think carefully about the most efficient way to accomplish the goal.
"""

    task_prompt: str = """Complete this task by creating and executing a plan.
First, analyze the task to understand what needs to be done.
Then, create a structured plan with clear steps.
Finally, execute the plan step by step, adapting as needed.
If you want to stop interaction, use the `terminate` tool/function call.
"""

    # Tool configuration
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(PlanningTool(), Terminate()),
        description="Collection of tools available to the agent"
    )

    # Planning attributes
    active_plan_id: Optional[str] = Field(
        default=None,
        description="ID of the active plan"
    )
    plan_to_task_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from plan step indices to task IDs"
    )

    # Optimization components
    task_analyzer: TaskResultAnalyzer = Field(
        default_factory=TaskResultAnalyzer,
        description="Analyzer for task execution results"
    )
    plan_optimizer: PlanOptimizer = Field(
        default_factory=lambda: PlanOptimizer(),
        description="Optimizer for plans based on task feedback"
    )
    completed_tasks: List[Task] = Field(
        default_factory=list,
        description="List of completed tasks for analysis"
    )

    # Dynamic planning components
    current_plan_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Current plan data for dynamic task generation"
    )
    current_step_index: int = Field(
        default=0,
        description="Current step index in the plan"
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
        """Convert the current plan to a dynamic to-do list of tasks.

        Instead of creating all tasks at once with fixed dependencies,
        this method creates only the first task and will dynamically
        determine the next tasks based on planner feedback.
        """
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

        # Create only the first task from the plan
        # The rest will be created dynamically as tasks are completed
        if plan_data["steps"]:
            first_step = plan_data["steps"][0]
            first_task_id = f"plan_{self.active_plan_id}_step_1"

            # Create the first task
            self.add_task(
                task_id=first_task_id,
                description=f"Execute plan step 1: {first_step}"
            )

            # Map the plan step to the task
            self.plan_to_task_map[f"{self.active_plan_id}_1"] = first_task_id

            # Store the plan data for future reference
            self.current_plan_data = plan_data

            logger.info(f"Created initial task from plan: {first_step}")
        else:
            logger.warning("Plan has no steps to execute")

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
        """
        Handle task completion by updating the plan step status, optimizing the plan,
        and dynamically generating the next task based on planner feedback.
        """
        # Add the completed task to our list for analysis
        self.completed_tasks.append(task)

        # Check if this is a plan step task
        step_index = None
        for plan_step_key, task_id in self.plan_to_task_map.items():
            if task_id == task.id:
                # Extract the step index from the key
                _, step_index_str = plan_step_key.rsplit("_", 1)
                step_index = int(step_index_str)

                # Update the plan step status
                await self.update_plan_step_status(
                    step_index=step_index,
                    status="completed",
                    notes=f"Completed: {task.result[:100]}..." if task.result and len(task.result) > 100 else task.result
                )

                # Update current step index
                self.current_step_index = step_index
                break

        # Analyze the task and optimize the plan
        await self._analyze_and_optimize_plan(task, step_index)

        # Generate the next task dynamically based on planner feedback
        await self._generate_next_task(task)

    async def _generate_next_task(self, completed_task: Task, _step_index: Optional[int] = None) -> None:
        """
        Dynamically generate the next task based on the completed task and planner feedback.

        This method consults the planner to determine the next step rather than
        following a predefined sequence of steps.

        Args:
            completed_task: The task that was just completed
            _step_index: Optional step index in the plan (unused but kept for API compatibility)
        """
        if not self.active_plan_id:
            logger.warning("No active plan to generate next task")
            return

        # Skip for plan creation tasks
        if completed_task.id.startswith("create_plan_"):
            return

        # Get the latest plan data with any optimizations
        plan_result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id}
        )

        # Parse the updated plan
        try:
            if hasattr(plan_result, "output"):
                updated_plan = self._parse_plan_output(plan_result.output)
                if updated_plan and "steps" in updated_plan:
                    self.current_plan_data = updated_plan
            else:
                logger.error(f"Unexpected plan result type: {type(plan_result)}")
                return
        except Exception as e:
            logger.error(f"Error parsing updated plan data: {str(e)}")
            return

        # If we don't have plan data, we can't continue
        if not self.current_plan_data or "steps" not in self.current_plan_data:
            logger.warning("No plan data available to generate next task")
            return

        # Determine the next step index
        next_step_index = self.current_step_index + 1

        # Check if there are more steps in the plan
        if next_step_index <= len(self.current_plan_data["steps"]):
            next_step = self.current_plan_data["steps"][next_step_index - 1]
            next_task_id = f"plan_{self.active_plan_id}_step_{next_step_index}"

            # Create the next task
            self.add_task(
                task_id=next_task_id,
                description=f"Execute plan step {next_step_index}: {next_step}"
            )

            # Map the plan step to the task
            self.plan_to_task_map[f"{self.active_plan_id}_{next_step_index}"] = next_task_id

            logger.info(f"Generated next task: {next_step}")
        else:
            # We've completed all steps in the current plan
            # Ask the planner if we need additional steps
            await self._check_for_additional_steps(completed_task)

    async def _check_for_additional_steps(self, completed_task: Task) -> None:
        """
        Check with the planner if additional steps are needed based on task results.
        """
        if not self.active_plan_id:
            return

        # Create a message asking if additional steps are needed
        messages = [
            Message.user_message(
                f"I've completed all steps in plan {self.active_plan_id}. "
                f"Based on the results of the last task: \"{completed_task.result[:200]}...\", "
                f"are additional steps needed to complete the overall goal? "
                f"If yes, please update the plan with new steps."
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

        # Check if the planner added new steps
        plan_updated = False
        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                result = await self.execute_tool(tool_call)
                logger.info(f"Executed tool {tool_call.function.name} with result: {result}")

                # Add tool response to memory
                tool_msg = Message.tool_message(
                    content=result,
                    tool_call_id=tool_call.id,
                    name=tool_call.function.name,
                )
                self.memory.add_message(tool_msg)
                plan_updated = True
                break

        if plan_updated:
            # Get the updated plan
            plan_result = await self.available_tools.execute(
                name="planning",
                tool_input={"command": "get", "plan_id": self.active_plan_id}
            )

            # Parse the updated plan and check for new steps
            try:
                if hasattr(plan_result, "output"):
                    updated_plan = self._parse_plan_output(plan_result.output)
                    if updated_plan and "steps" in updated_plan:
                        # If there are more steps than our current index, create the next task
                        if len(updated_plan["steps"]) > self.current_step_index:
                            self.current_plan_data = updated_plan
                            await self._generate_next_task(completed_task)
            except Exception as e:
                logger.error(f"Error checking for additional steps: {str(e)}")

    async def _analyze_and_optimize_plan(self, completed_task: Task, step_index: Optional[int] = None) -> None:
        """Analyze the completed task and optimize the plan based on the results."""
        if not self.active_plan_id:
            logger.warning("No active plan to optimize")
            return

        # Skip plan creation tasks
        if completed_task.id.startswith("create_plan_"):
            return

        # Get the current plan
        plan_result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id}
        )

        # Parse the plan data
        plan_data = None
        try:
            if hasattr(plan_result, "output"):
                plan_data = self._parse_plan_output(plan_result.output)
            else:
                logger.error(f"Unexpected plan result type: {type(plan_result)}")
                return
        except Exception as e:
            logger.error(f"Error parsing plan data: {str(e)}")
            return

        if not plan_data:
            logger.warning("No plan data available for optimization")
            return

        # Analyze the completed tasks
        task_analyses = []
        for task in self.completed_tasks:
            analysis = self.task_analyzer.analyze_task(task)
            task_analyses.append(analysis)

        # Optimize the plan based on the analyses
        optimization_result = self.plan_optimizer.optimize_plan(
            plan_id=self.active_plan_id,
            plan_data=plan_data,
            task_analyses=task_analyses
        )

        # Log optimization results
        if optimization_result.recommendations:
            logger.info(f"Plan optimization recommendations for {self.active_plan_id}:")
            for i, rec in enumerate(optimization_result.recommendations, 1):
                logger.info(f"  {i}. {rec}")

        # Update the plan with optimization notes if we have a specific step
        if step_index and optimization_result.recommendations:
            # Add optimization notes to the step
            optimization_notes = "Optimization suggestions:\n- " + "\n- ".join(optimization_result.recommendations[:3])

            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "update_step",
                    "plan_id": self.active_plan_id,
                    "step_index": step_index,
                    "notes": optimization_notes
                }
            )

        # Update overall plan progress
        await self._update_plan_progress()

    async def _update_plan_progress(self) -> None:
        """Update the overall plan progress based on completed tasks."""
        if not self.active_plan_id:
            return

        # Calculate progress statistics
        total_tasks = len(self.tasks)
        completed_count = len([t for t in self.tasks.values() if t.status == "completed"])
        failed_count = len([t for t in self.tasks.values() if t.status == "failed"])
        in_progress_count = len([t for t in self.tasks.values() if t.status == "in_progress"])
        pending_count = len([t for t in self.tasks.values() if t.status == "pending"])

        # Calculate completion percentage
        completion_percentage = (completed_count / total_tasks) * 100 if total_tasks > 0 else 0

        # Calculate progress metrics (used in progress_notes below)
        _ = {
            "total_tasks": total_tasks,
            "completed": completed_count,
            "failed": failed_count,
            "in_progress": in_progress_count,
            "pending": pending_count,
            "completion_percentage": f"{completion_percentage:.1f}%",
            "optimization_count": len(self.plan_optimizer.get_optimization_history(self.active_plan_id))
        }

        # Get optimization recommendations
        all_recommendations = []
        for opt_result in self.plan_optimizer.get_optimization_history(self.active_plan_id):
            all_recommendations.extend(opt_result.recommendations)

        # Get the most recent recommendations (up to 5)
        recent_recommendations = all_recommendations[-5:] if all_recommendations else []

        # Update the plan with progress information
        progress_notes = (
            f"Progress: {completion_percentage:.1f}% ({completed_count}/{total_tasks} tasks)\n"
            f"Status: {completed_count} completed, {in_progress_count} in progress, "
            f"{failed_count} failed, {pending_count} pending\n"
        )

        if recent_recommendations:
            progress_notes += "\nRecent optimization recommendations:\n- "
            progress_notes += "\n- ".join(recent_recommendations)

        # Update the plan description with progress
        try:
            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "update",
                    "plan_id": self.active_plan_id,
                    "description": f"Plan Progress: {completion_percentage:.1f}% complete"
                }
            )

            # Add a progress note to the plan
            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "add_note",
                    "plan_id": self.active_plan_id,
                    "note": progress_notes
                }
            )

            logger.info(f"Updated plan progress: {completion_percentage:.1f}% complete")
        except Exception as e:
            logger.error(f"Error updating plan progress: {str(e)}")

    async def run(self, request: str = "") -> str:
        """
        Run the agent with enhanced planning capabilities.

        This overrides the parent run method to add plan optimization and progress tracking.

        Args:
            request: The user request to process

        Returns:
            The result of executing the plan
        """
        # Reset dynamic planning components
        self.completed_tasks = []
        self.current_plan_data = None
        self.current_step_index = 0
        self.plan_to_task_map = {}
        self.active_plan_id = None

        # Run the standard task-based agent
        result = await super().run(request)

        # Perform final plan optimization and progress update
        if self.active_plan_id and self.completed_tasks:
            try:
                # Get final plan data (not used directly but ensures plan exists)
                _ = await self.available_tools.execute(
                    name="planning",
                    tool_input={"command": "get", "plan_id": self.active_plan_id}
                )

                # Create final summary
                final_summary = (
                    f"Plan execution completed with {len(self.completed_tasks)} tasks.\n\n"
                    f"Final result: {result[:200]}...\n\n"
                )

                # Add optimization insights
                if self.plan_optimizer.optimization_history.get(self.active_plan_id):
                    opt_count = len(self.plan_optimizer.optimization_history[self.active_plan_id])
                    final_summary += f"Plan was optimized {opt_count} times during execution.\n"

                    # Add key recommendations
                    all_recommendations = []
                    for opt_result in self.plan_optimizer.optimization_history[self.active_plan_id]:
                        all_recommendations.extend(opt_result.recommendations)

                    if all_recommendations:
                        final_summary += "\nKey optimization insights:\n- "
                        final_summary += "\n- ".join(all_recommendations[-5:])

                # Add dynamic planning insights
                final_summary += f"\n\nDynamic Planning Insights:\n"
                final_summary += f"- Total steps executed: {self.current_step_index}\n"
                final_summary += f"- Total tasks created: {len(self.plan_to_task_map)}\n"

                if self.current_plan_data and "steps" in self.current_plan_data:
                    final_summary += f"- Final plan had {len(self.current_plan_data['steps'])} steps\n"

                # Add final summary to plan
                await self.available_tools.execute(
                    name="planning",
                    tool_input={
                        "command": "add_note",
                        "plan_id": self.active_plan_id,
                        "note": final_summary
                    }
                )

                logger.info(f"Added final summary to plan {self.active_plan_id}")
            except Exception as e:
                logger.error(f"Error adding final summary to plan: {str(e)}")

        return result
