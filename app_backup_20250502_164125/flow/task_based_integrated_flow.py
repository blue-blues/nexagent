"""
Task-based integrated flow implementation.

This module provides a TaskBasedIntegratedFlow class that integrates the task-based approach
with the existing integrated flow functionality.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from app.agent.task_based_nexagent import TaskBasedNexagent
from app.agent.web_output import WebOutputFormatter
from app.flow.base import BaseFlow
from app.flow.task_based_flow import TaskBasedFlow
from app.logger import logger
from app.tool.output_organizer import OutputOrganizer
from app.util.direct_response import is_simple_prompt, get_direct_response
from app.timeline.timeline import Timeline
from app.timeline.events import create_user_input_event, create_agent_response_event, create_system_event
from app.ui.user_input_cli import user_input_cli
from app.util.user_input_manager import input_manager


class TaskBasedIntegratedFlow(BaseFlow):
    """
    A flow that uses the TaskBasedNexagent to execute tasks based on the planner's to-do list.

    This flow provides a unified interface to task-based execution by using
    the TaskBasedNexagent as its primary agent. It automatically breaks down complex tasks
    into manageable steps and executes them using the appropriate tools.

    It also ensures that for every conversation, a new folder is created to store
    related documents and generated outputs.
    """

    def __init__(
        self, task_based_agent: Optional[TaskBasedNexagent] = None, conversation_id: Optional[str] = None, **data
    ):
        """
        Initialize the task-based integrated flow.

        Args:
            task_based_agent: An optional TaskBasedNexagent instance. If not provided,
                             a new TaskBasedNexagent will be created.
            conversation_id: An optional conversation ID. If not provided, a new ID will be generated.
            **data: Additional data to pass to the parent class.
        """
        # Create a new TaskBasedNexagent if not provided
        if task_based_agent is None:
            task_based_agent = TaskBasedNexagent()

        # Initialize with the TaskBasedNexagent as the only agent
        super().__init__({"task_based_agent": task_based_agent}, **data)

        # Set the primary agent key to the task-based agent
        self.primary_agent_key = "task_based_agent"

        # Set conversation ID and initialize output organizer as instance variables (not model fields)
        self._conversation_id = conversation_id or f"conv_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        self._output_organizer = OutputOrganizer()

    @property
    def task_based_agent(self) -> TaskBasedNexagent:
        """Get the task-based agent."""
        return self.agents["task_based_agent"]

    async def execute(self, input_text: str = None, prompt: str = None, conversation_id: Optional[str] = None, timeline: Optional[Timeline] = None, **kwargs) -> str:
        """
        Execute the task-based integrated flow with the given input.

        This method first checks if the input is a simple prompt that can be handled directly.
        If so, it returns a direct response without invoking the agent system.
        Otherwise, it delegates to the TaskBasedNexagent, which will analyze the input,
        break it down into tasks, and execute them using the appropriate tools.
        It also ensures that all outputs are saved to a dedicated folder for the conversation.

        Args:
            input_text: The input text to process
            prompt: Alternative input text parameter (used if input_text is None)
            conversation_id: Optional conversation ID to use. If provided, it will override
                           the conversation ID set during initialization.
            timeline: Optional timeline to track events. If provided, events will be added to this timeline.
            kwargs: Additional keyword arguments to pass to the agent

        Returns:
            str: The result from the task-based agent or a direct response
        """
        # Use prompt parameter if provided, otherwise use input_text
        input_text = prompt if prompt is not None else input_text

        try:
            if not self.task_based_agent:
                raise ValueError("No task-based agent available")

            # Update conversation ID if provided
            if conversation_id:
                self._conversation_id = conversation_id

            # Create a new timeline if not provided
            active_timeline = timeline or Timeline()

            # Record the user input in the timeline if not already recorded
            if not any(event.type == "user_input" for event in active_timeline.events):
                create_user_input_event(active_timeline, input_text)

            # Log the start of execution
            logger.info(f"Executing task-based integrated flow with input: {input_text[:50]}... (Conversation ID: {self._conversation_id})")

            # Start the user input CLI if not already running
            if not user_input_cli.running:
                user_input_cli.start()
                logger.info("Started user input CLI for handling interactive requests")

            # Clear any previous input requests
            input_manager.clear_all()

            # Create a system event for flow execution
            flow_event = create_system_event(
                active_timeline,
                "Task-Based Integrated Flow Execution",
                f"Processing input: {input_text[:50]}{'...' if len(input_text) > 50 else ''}"
            )

            # Set up the output organizer for this conversation
            await self._output_organizer.execute(
                action="set_active_conversation",
                conversation_id=self._conversation_id
            )

            # Check if this is a simple prompt that can be handled directly
            if is_simple_prompt(input_text):
                logger.info(f"Detected simple prompt: '{input_text}'. Providing direct response.")
                direct_response = get_direct_response(input_text)

                # Format the direct response with a clear structure
                structured_response = WebOutputFormatter.create_structured_output(
                    f"## Implementation Steps\n\nNo detailed steps required for this simple query.\n\n## Final Output\n\n{direct_response}"
                )

                # Save the structured response as an output
                await self._output_organizer.execute(
                    action="save_output",
                    output_name="direct_response",
                    output_content=structured_response,
                    output_type="document"
                )

                # Record the direct response in the timeline
                create_agent_response_event(active_timeline, structured_response)
                flow_event.mark_success()

                logger.info(f"Direct response provided for conversation {self._conversation_id}")
                return structured_response

            # For complex prompts, delegate to the task-based agent
            logger.info(f"Complex prompt detected. Delegating to task-based agent system.")

            # Pass the timeline to the task-based agent if it has a timeline parameter
            if hasattr(self.task_based_agent, "timeline"):
                self.task_based_agent.timeline = active_timeline

            # Execute the task-based agent
            result = await self.task_based_agent.run(input_text)

            # Format the result with a clear structure
            structured_result = WebOutputFormatter.create_structured_output(result)

            # Save the structured result as an output
            await self._output_organizer.execute(
                action="save_output",
                output_name="response",
                output_content=structured_result,
                output_type="document"
            )

            # Log the completion of execution
            logger.info(f"Task-based integrated flow execution completed for conversation {self._conversation_id}")

            # Record the agent response in the timeline if not already recorded
            if not any(event.type == "agent_response" for event in active_timeline.events):
                create_agent_response_event(active_timeline, structured_result)

            # Mark the flow execution event as successful
            flow_event.mark_success()

            # Clear any remaining input requests
            input_manager.clear_all()

            return structured_result
        except Exception as e:
            logger.error(f"Error in task-based integrated flow: {str(e)}")

            # Mark the flow execution event as failed
            if 'flow_event' in locals():
                flow_event.mark_error({"error": str(e)})

            # Record the error in the timeline
            if 'active_timeline' in locals():
                create_system_event(
                    active_timeline,
                    "Error",
                    f"Error in task-based integrated flow: {str(e)}",
                    metadata={"error": str(e)}
                )

            # Clear any pending input requests
            input_manager.clear_all()

            # Format the error message with a clear structure
            structured_error = WebOutputFormatter.create_structured_output(
                f"## Implementation Steps\n\nAn error occurred during execution.\n\n## Final Output\n\nI encountered an error while processing your request: {str(e)}"
            )
            return structured_error
