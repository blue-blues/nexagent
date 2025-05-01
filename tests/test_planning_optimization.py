"""
Test script for the enhanced planning optimization system.

This script tests the TaskBasedPlanningAgent with the new task result analyzer
and plan optimizer components.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.agent.task_based_planning import TaskBasedPlanningAgent
from app.logger import logger


async def test_planning_optimization():
    """Test the planning optimization system with a simple task."""
    logger.info("Starting planning optimization test")
    
    # Create the planning agent
    agent = TaskBasedPlanningAgent()
    
    # Run the agent with a test request
    result = await agent.run("Create a simple Python web server that serves static files")
    
    logger.info(f"Agent execution completed with result: {result[:100]}...")
    
    # Check if optimization was performed
    if agent.active_plan_id:
        opt_history = agent.plan_optimizer.get_optimization_history(agent.active_plan_id)
        logger.info(f"Plan was optimized {len(opt_history)} times")
        
        # Print optimization recommendations
        for i, opt_result in enumerate(opt_history):
            logger.info(f"Optimization {i+1} recommendations:")
            for j, rec in enumerate(opt_result.recommendations, 1):
                logger.info(f"  {j}. {rec}")
    
    return result


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_planning_optimization())
    print("\nFinal result:", result)
