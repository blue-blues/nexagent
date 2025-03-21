"""Example script demonstrating the self-improving parallel flow.

This script shows how to create and use the self-improving parallel flow
with multiple agents to solve a task while automatically detecting and
resolving issues during execution.
"""

import asyncio
import logging
from typing import Dict, List

from app.agent.base import BaseAgent
from app.agent.toolcall import ToolCallAgent
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.flow.self_improving import SelfImprovingParallelFlow
from app.logger import logger

# Configure logging
logging.basicConfig(level=logging.INFO)


class SimpleAgent(BaseAgent):
    """A simple agent implementation for demonstration purposes."""
    
    async def step(self) -> str:
        """Execute a single step in the agent's workflow."""
        # Simulate processing
        await asyncio.sleep(1)
        
        # Return a simple response
        return f"Agent {self.name} processed: {self.memory.messages[-1].content if self.memory.messages else 'No input'}"


class ErrorProneAgent(BaseAgent):
    """An agent that occasionally produces errors for testing self-improvement."""
    
    async def step(self) -> str:
        """Execute a single step that may produce errors."""
        # Simulate processing with potential errors
        await asyncio.sleep(1)
        
        # Simulate an error condition (every third call)
        if self.current_step % 3 == 0:
            raise ValueError(f"Simulated error in {self.name} at step {self.current_step}")
        
        return f"Agent {self.name} processed step {self.current_step}"


class SlowAgent(BaseAgent):
    """An agent that takes a long time to process, potentially triggering timeouts."""
    
    async def step(self) -> str:
        """Execute a slow step."""
        # Simulate slow processing
        await asyncio.sleep(5)
        
        return f"Agent {self.name} completed slow processing"


async def main():
    """Run the self-improving parallel flow example."""
    # Create different types of agents
    agents = {
        "fast_agent": SimpleAgent(name="FastAgent"),
        "error_agent": ErrorProneAgent(name="ErrorProneAgent"),
        "slow_agent": SlowAgent(name="SlowAgent"),
    }
    
    # Create a self-improving parallel flow
    flow = FlowFactory.create_flow(
        flow_type="self_improving_parallel",  # Use string instead of enum for demonstration
        agents=agents,
        max_concurrent_tasks=3,
        task_timeout=10,  # 10 seconds timeout
        enable_self_improvement=True,
        monitoring_interval=2.0,  # Check for issues every 2 seconds
        max_auto_fixes=5,  # Maximum number of automatic fixes to apply
    )
    
    # Execute the flow with a test input
    logger.info("Starting self-improving parallel flow execution")
    result = await flow.execute("Process this test input with multiple agents")
    
    # Print the result
    logger.info("\nExecution Result:\n%s", result)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())