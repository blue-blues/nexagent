"""
Agent Loop Module

This module defines the core agent loop that drives the agent's execution.
The agent loop is responsible for managing the agent's state, executing steps,
and handling errors.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from app.core.schema.schema import AgentState, Message
from app.core.schema.exceptions import AgentExecutionError
from app.utils.logging.logger import logger

# Import for type hints only
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.llm.llm import LLM


class AgentLoop(BaseModel, ABC):
    """
    Abstract base class for the agent execution loop.

    The agent loop is responsible for managing the agent's state, executing steps,
    and handling errors. Subclasses must implement the `step` method to define
    the specific behavior of each step in the loop.
    """

    # Allow arbitrary types for fields like LLM
    model_config = {
        "arbitrary_types_allowed": True,
    }

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # State management
    state: AgentState = Field(default=AgentState.IDLE, description="Current agent state")
    current_step: int = Field(default=0, description="Current step in the execution")
    max_steps: int = Field(default=10, description="Maximum number of steps to execute")

    # LLM and memory
    llm: Optional[Any] = Field(default=None, description="LLM instance for the agent")
    memory: Dict[str, Any] = Field(default_factory=dict, description="Agent memory store")

    # Execution history
    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of agent actions and results"
    )

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for temporarily changing agent state"""
        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Agent error: {str(e)}")
            raise AgentExecutionError(f"Error in agent execution: {str(e)}")
        finally:
            if self.state != AgentState.ERROR:
                self.state = previous_state

    async def run(self) -> str:
        """
        Execute the agent loop until completion or max steps reached.

        Returns:
            str: Summary of execution results
        """
        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")

                try:
                    step_result = await self.step()
                    self.history.append({
                        "step": self.current_step,
                        "action": "step_execution",
                        "result": step_result
                    })
                    results.append(f"Step {self.current_step}: {step_result}")
                except Exception as e:
                    error_msg = f"Error in step {self.current_step}: {str(e)}"
                    logger.error(error_msg)
                    self.history.append({
                        "step": self.current_step,
                        "action": "step_execution",
                        "error": str(e)
                    })
                    results.append(error_msg)
                    break

            if self.current_step >= self.max_steps and self.state != AgentState.FINISHED:
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        return "\n".join(results) if results else "No steps executed"

    @abstractmethod
    async def step(self) -> str:
        """
        Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.

        Returns:
            str: Result of the step execution
        """
        pass

    def is_stuck(self) -> bool:
        """
        Check if the agent is stuck in a loop.

        Returns:
            bool: True if the agent is stuck, False otherwise
        """
        # Simple implementation - can be enhanced in subclasses
        if len(self.history) < 3:
            return False

        # Check if the last 3 results are identical
        last_results = [
            entry.get("result", "")
            for entry in self.history[-3:]
            if "result" in entry
        ]

        return len(last_results) == 3 and all(r == last_results[0] for r in last_results)

    def handle_stuck_state(self) -> None:
        """
        Handle the case when the agent is stuck in a loop.
        """
        logger.warning(f"Agent {self.name} appears to be stuck in a loop")
        self.history.append({
            "step": self.current_step,
            "action": "stuck_detection",
            "result": "Agent detected stuck state and is attempting recovery"
        })

    def reset(self) -> None:
        """
        Reset the agent state to initial values.
        """
        self.state = AgentState.IDLE
        self.current_step = 0
        self.history = []
        logger.info(f"Agent {self.name} has been reset")
