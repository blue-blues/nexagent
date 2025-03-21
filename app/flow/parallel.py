\"""Parallel flow module for NexAgent.

This module provides a flow implementation that enables parallel execution
of multiple agents or workflows concurrently using the ParallelAgentManager.
"""

import asyncio
from typing import Dict, List, Optional, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.agent.parallel import AgentTask, ParallelAgentManager
from app.flow.base import BaseFlow
from app.logger import logger
from app.schema import AgentState


class ParallelFlow(BaseFlow):
    """A flow that executes multiple agents or workflows in parallel.
    
    This flow uses the ParallelAgentManager to run multiple agent instances
    concurrently, handling dependencies between tasks and managing the overall
    execution flow.
    """
    
    max_concurrent_tasks: int = Field(default=5)
    task_timeout: int = Field(default=600)  # 10 minutes default timeout
    
    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # Initialize with parent's init
        super().__init__(agents, **data)
        
        # Create agent factory dictionary
        self.agent_factory = {}
        for key, agent in self.agents.items():
            # Create a factory function that returns a new instance of the agent
            agent_class = agent.__class__
            self.agent_factory[key] = lambda: agent_class()
        
        # Initialize the parallel agent manager
        self.manager = ParallelAgentManager(
            agent_factory=self.agent_factory,
            max_concurrent_tasks=self.max_concurrent_tasks,
            task_timeout=self.task_timeout
        )
    
    async def execute(self, input_text: str) -> str:
        """Execute the parallel flow with the given input.
        
        This method creates tasks for each agent and executes them in parallel
        using the ParallelAgentManager.
        
        Args:
            input_text: The input text to process
            
        Returns:
            str: The combined results of all agent executions
        """
        try:
            if not self.agents:
                raise ValueError("No agents available for execution")
            
            # Create tasks for each agent
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
            
            # Execute all tasks in parallel
            logger.info(f"Starting parallel execution of {len(tasks)} tasks")
            execution_summary = await self.manager.execute_all()
            
            # Format the results
            result = self._format_results(execution_summary)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in parallel flow execution: {str(e)}")
            return f"Parallel flow execution failed: {str(e)}"
    
    def _format_results(self, execution_summary: Dict) -> str:
        """Format the execution results into a readable string.
        
        Args:
            execution_summary: The execution summary from the manager
            
        Returns:
            str: Formatted results string
        """
        # Create a summary header
        result = f"Parallel Execution Summary:\n"
        result += f"Total tasks: {execution_summary['total_tasks']}\n"
        result += f"Completed tasks: {execution_summary['completed_tasks']}\n"
        result += f"Failed tasks: {execution_summary['failed_tasks']}\n"
        result += f"Total execution time: {execution_summary['execution_time']:.2f} seconds\n\n"
        
        # Add individual task results
        result += "Task Results:\n"
        for task_id, task_result in execution_summary['results'].items():
            result += f"\n--- {task_id} ---\n{task_result}\n"
        
        # Add errors if any
        if execution_summary['errors']:
            result += "\nErrors:\n"
            for task_id, error in execution_summary['errors'].items():
                result += f"{task_id}: {error}\n"
        
        return result


class ParallelWorkflowFlow(ParallelFlow):
    """A flow that executes multiple workflows in parallel.
    
    This flow extends ParallelFlow to handle workflow-specific execution,
    where each workflow consists of multiple dependent tasks.
    """
    
    async def execute(self, input_text: str) -> str:
        """Execute multiple workflows in parallel.
        
        This method creates a workflow for each agent and executes them
        in parallel, respecting dependencies between tasks within each workflow.
        
        Args:
            input_text: The input text to process
            
        Returns:
            str: The combined results of all workflow executions
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
            logger.info(f"Starting parallel execution of {len(tasks)} workflow tasks")
            execution_summary = await self.manager.execute_all()
            
            # Format the results
            result = self._format_results(execution_summary)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in parallel workflow execution: {str(e)}")
            return f"Parallel workflow execution failed: {str(e)}"
    
    def _parse_workflow_plan(self, plan_result: str) -> List[Dict]:
        """Parse the workflow plan from the planner result.
        
        Args:
            plan_result: The result from the planner task
            
        Returns:
            List[Dict]: List of workflow steps with dependencies
        """
        # This is a simplified implementation that would need to be expanded
        # based on the actual format of the planner output
        try:
            # For now, assume the planner returns a simple list of steps
            # In a real implementation, this would parse a structured output
            workflow_steps = []
            lines = plan_result.strip().split('\n')
            
            current_step = None
            for line in lines:
                if line.startswith('Step '):
                    # Start a new step
                    if current_step:
                        workflow_steps.append(current_step)
                    
                    # Parse step information
                    parts = line.split(':')
                    if len(parts) >= 2:
                        step_num = parts[0].replace('Step ', '').strip()
                        step_desc = parts[1].strip()
                        
                        # Create a new step dictionary
                        current_step = {
                            'agent_type': self.primary_agent_key,  # Default to primary agent
                            'prompt': step_desc,
                            'dependencies': [],
                            'priority': int(step_num),
                        }
                elif line.startswith('Dependencies:') and current_step:
                    # Parse dependencies
                    deps = line.replace('Dependencies:', '').strip()
                    if deps:
                        current_step['dependencies'] = [d.strip() for d in deps.split(',')]
                elif line.startswith('Agent:') and current_step:
                    # Parse agent type
                    agent = line.replace('Agent:', '').strip()
                    if agent in self.agents:
                        current_step['agent_type'] = agent
            
            # Add the last step if it exists
            if current_step:
                workflow_steps.append(current_step)
            
            return workflow_steps
            
        except Exception as e:
            logger.error(f"Error parsing workflow plan: {str(e)}")
            # Return a simple default workflow using the primary agent
            return [{
                'agent_type': self.primary_agent_key,
                'prompt': plan_result,
                'dependencies': [],
                'priority': 0,
            }]