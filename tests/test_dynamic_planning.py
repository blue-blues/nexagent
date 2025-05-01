"""
Test script for the dynamic planning system.

This script tests the TaskBasedPlanningAgent with the new dynamic task generation
approach where each next step is determined by the planner rather than following
a predefined sequence.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.agent.task_based_planning import TaskBasedPlanningAgent
from app.logger import logger


async def test_dynamic_planning():
    """Test the dynamic planning system with a task that requires adaptive planning."""
    logger.info("Starting dynamic planning test")
    
    # Create the planning agent
    agent = TaskBasedPlanningAgent()
    
    # Run the agent with a test request that requires adaptive planning
    result = await agent.run(
        "Create a data analysis report on a CSV file. The steps should be determined dynamically based on the content of the file."
    )
    
    logger.info(f"Agent execution completed with result: {result[:100]}...")
    
    # Check dynamic planning metrics
    logger.info(f"Total steps executed: {agent.current_step_index}")
    logger.info(f"Total tasks created: {len(agent.plan_to_task_map)}")
    
    if agent.current_plan_data and "steps" in agent.current_plan_data:
        logger.info(f"Final plan had {len(agent.current_plan_data['steps'])} steps")
    
    # Print the task execution sequence
    logger.info("Task execution sequence:")
    for i, task in enumerate(agent.completed_tasks, 1):
        logger.info(f"  {i}. {task.description} -> {task.status}")
    
    return result


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_dynamic_planning())
    print("\nFinal result:", result)
