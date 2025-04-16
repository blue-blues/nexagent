"""
Task-based flow implementation.

This module provides a TaskBasedFlow class that executes tasks using the planner's to-do list
rather than using a fixed number of steps.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Type

from pydantic import BaseModel, Field

from app.agent.task_based_agent import TaskBasedAgent
from app.agent.task_based_nexagent import TaskBasedNexagent
from app.agent.task_based_planning import TaskBasedPlanningAgent
from app.flow.base import BaseFlow, FlowType
from app.logger import logger
from app.timeline.timeline import Timeline


class TaskBasedFlow(BaseFlow):
    """
    A flow that executes tasks using the planner's to-do list.

    This flow automatically breaks down complex tasks into manageable steps
    and executes them using the appropriate agents.
    """

    name: str = "task_based"
    description: str = "A flow that executes tasks using the planner's to-do list"
    flow_type: FlowType = FlowType.INTEGRATED

    # Agent management
    primary_agent: Optional[TaskBasedAgent] = None
    agents: Dict[str, TaskBasedAgent] = Field(default_factory=dict)

    # Timeline for tracking events
    timeline: Optional[Timeline] = None

    def __init__(self, **data):
        """Initialize the task-based flow."""
        super().__init__(**data)

        # Initialize agents if not provided
        if not self.agents:
            self._initialize_default_agents()

    def _initialize_default_agents(self):
        """Initialize default agents for the flow."""
        # Create a Nexagent as the primary agent
        self.primary_agent = TaskBasedNexagent()
        self.agents["nexagent"] = self.primary_agent

        # Add a planning agent
        self.agents["planning"] = TaskBasedPlanningAgent()

    def add_agent(self, agent_type: str, agent: TaskBasedAgent):
        """Add an agent to the flow."""
        self.agents[agent_type] = agent

        # If this is the first agent, make it the primary agent
        if not self.primary_agent:
            self.primary_agent = agent

    def get_agent(self, agent_type: Optional[str] = None) -> TaskBasedAgent:
        """Get an agent by type, or the primary agent if no type is specified."""
        if agent_type and agent_type in self.agents:
            return self.agents[agent_type]

        return self.primary_agent

    async def execute(self, input_text: str, conversation_id: Optional[str] = None, timeline: Optional[Timeline] = None) -> str:
        """
        Execute the flow with the given input.

        Args:
            input_text: The input text to process
            conversation_id: Optional conversation ID
            timeline: Optional timeline for tracking events

        Returns:
            The result of the flow execution
        """
        # Set the timeline if provided
        if timeline:
            self.timeline = timeline

        # Generate a conversation ID if not provided
        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4().hex[:8]}"

        try:
            # Log the start of execution
            logger.info(f"Executing task-based flow with input: {input_text[:50]}... (Conversation ID: {conversation_id})")

            # Check if this is a simple prompt that can be handled directly
            if self._is_simple_prompt(input_text):
                logger.info(f"Detected simple prompt: '{input_text}'. Providing direct response.")
                response = self._handle_simple_prompt(input_text)

                # Log the completion of execution
                logger.info(f"Direct response provided for conversation {conversation_id}")

                return response

            # For complex prompts, delegate to the agent system
            logger.info(f"Complex prompt detected. Delegating to agent system.")

            # Select the appropriate agent for the task
            agent = self._select_agent_for_task(input_text)

            # Execute the agent
            result = await agent.run(input_text)

            # Log the completion of execution
            logger.info(f"Task-based flow execution completed for conversation {conversation_id}")

            return result
        except Exception as e:
            logger.error(f"Error executing task-based flow: {str(e)}")
            return f"Error: {str(e)}"

    def _is_simple_prompt(self, input_text: str) -> bool:
        """Check if the input is a simple prompt that can be handled directly."""
        # Simple prompts are short and don't require complex processing
        simple_prompts = ["hello", "hi", "hey", "help", "?"]

        # Check if the input is a simple prompt
        return input_text.lower() in simple_prompts

    def _handle_simple_prompt(self, input_text: str) -> str:
        """Handle a simple prompt directly."""
        # Simple responses for simple prompts
        responses = {
            "hello": "Hello! How can I assist you today?",
            "hi": "Hi there! How can I help you?",
            "hey": "Hey! What can I do for you?",
            "help": "I'm here to help! You can ask me to perform tasks like research, coding, data analysis, and more.",
            "?": "I'm an AI assistant that can help with various tasks. What would you like me to do?"
        }

        # Return the response for the input
        return responses.get(input_text.lower(), "Hello! How can I assist you today?")

    def _select_agent_for_task(self, input_text: str) -> TaskBasedAgent:
        """Select the appropriate agent for the task."""
        # For now, just use the primary agent
        # In a more advanced implementation, you could analyze the input
        # and select a specialized agent based on the task type
        return self.primary_agent
