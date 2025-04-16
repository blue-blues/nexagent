import uuid
from datetime import datetime
from typing import Optional, Union

from app.agent.integrated_agent import IntegratedAgent
from app.flow.base import BaseFlow
from app.logger import logger
from app.memory.conversation_memory import conversation_memory
from app.tool.output_organizer import OutputOrganizer
from app.tools.conversation_file_saver import ConversationFileSaver
from app.tools.message_classifier import MessageClassifier
from app.util.direct_response import is_simple_prompt, get_direct_response
from app.timeline.timeline import Timeline
from app.timeline.events import create_user_input_event, create_agent_response_event, create_system_event
from app.tool.base import ToolResult


class IntegratedFlow(BaseFlow):
    """
    A flow that uses the IntegratedAgent to route queries between specialized agents.

    This flow provides a unified interface to multiple specialized agents by using
    the IntegratedAgent as its primary agent. The IntegratedAgent analyzes user prompts
    and delegates to the appropriate specialized agent based on content analysis.

    It also ensures that for every conversation, a new folder is created to store
    related documents and generated outputs.
    """

    def __init__(
        self, integrated_agent: Optional[IntegratedAgent] = None, conversation_id: Optional[str] = None, **data
    ):
        """
        Initialize the integrated flow with an IntegratedAgent.

        Args:
            integrated_agent: An optional IntegratedAgent instance. If not provided,
                             a new IntegratedAgent will be created.
            conversation_id: An optional conversation ID. If not provided, a new ID will be generated.
            **data: Additional data to pass to the parent class.
        """
        # Create a new IntegratedAgent if not provided
        if integrated_agent is None:
            integrated_agent = IntegratedAgent()

        # Initialize with the IntegratedAgent as the only agent
        super().__init__({"integrated_agent": integrated_agent}, **data)

        # Set the primary agent key to the integrated agent
        self.primary_agent_key = "integrated_agent"

        # Set conversation ID and initialize output organizer as instance variables (not model fields)
        self._conversation_id = conversation_id or f"conv_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        self._output_organizer = OutputOrganizer()

        # Initialize the conversation file saver
        try:
            self._file_saver = ConversationFileSaver()
            self._file_saver.set_active_conversation(self._conversation_id)
            logger.info(f"Initialized ConversationFileSaver with conversation ID: {self._conversation_id}")
        except Exception as e:
            logger.error(f"Error initializing ConversationFileSaver: {str(e)}")
            self._file_saver = None

        # Initialize the message classifier
        try:
            self._message_classifier = MessageClassifier()
            logger.info("Initialized MessageClassifier")
        except Exception as e:
            logger.error(f"Error initializing MessageClassifier: {str(e)}")
            logger.info("Falling back to simple prompt detection")
            self._message_classifier = None

    @property
    def integrated_agent(self) -> IntegratedAgent:
        """
        Get the integrated agent instance.

        Returns:
            IntegratedAgent: The integrated agent instance
        """
        return self.agents["integrated_agent"]

    async def _handle_chat_with_llm(self, input_text: str, active_timeline: Timeline) -> str:
        """
        Handle a chat message by passing it directly to the LLM for a response.

        Args:
            input_text: The user's input text
            active_timeline: The active timeline for this conversation

        Returns:
            The LLM's response
        """
        from app.llm import get_llm
        from app.util.response_formatter import format_response

        # Create a system event for LLM processing
        create_system_event(
            active_timeline,
            "LLM Direct Response",
            f"Processing chat message directly with LLM: {input_text[:50]}{'...' if len(input_text) > 50 else ''}"
        )

        # Get the LLM instance
        llm = get_llm()

        # Create a detailed system prompt
        system_prompt = """You are Nexagent, a helpful AI assistant powered by Claude 3.7 Sonnet.
        Provide direct, helpful, and accurate responses to the user's questions.

        For factual questions, provide detailed and accurate information with context.
        For math calculations, compute the result and show your work clearly.
        For questions about people, provide comprehensive biographical information.
        For questions about concepts, provide clear explanations with examples.
        For questions about yourself, explain that you are Nexagent powered by Claude 3.7 Sonnet.

        For simple questions like "5+5" or "who is elon musk", provide comprehensive answers:
        - For math: Calculate the result and explain the calculation
        - For people: Provide detailed biographical information
        - For concepts: Give thorough explanations with examples

        Your responses should be well-structured, comprehensive, and informative.
        Use paragraphs, bullet points, or numbered lists when appropriate to organize information.
        Aim to provide complete answers that fully address the user's query, even for seemingly simple questions."""

        # Create a simple user message
        user_message = input_text

        # Log the request
        logger.info(f"Sending chat message directly to LLM: {input_text[:100]}{'...' if len(input_text) > 100 else ''}")

        # Get the response from the LLM
        response = await llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,  # Use a moderate temperature for varied responses
            max_tokens=2000   # Allow for longer responses
        )

        # Extract the content from the response
        if hasattr(response, 'content'):
            response_content = response.content
        else:
            # If response doesn't have a content attribute, try to get it as a string
            response_content = str(response)

            # If the response is a dict-like object, try to get the content from it
            if hasattr(response, 'get'):
                response_content = response.get('content', response_content)

        # Format the response
        formatted_response = format_response(response_content)

        # Log the response
        logger.info(f"Received LLM response: {formatted_response[:100]}{'...' if len(formatted_response) > 100 else ''}")

        # Create a system event for the response
        create_system_event(
            active_timeline,
            "LLM Response",
            f"LLM generated response: {formatted_response[:50]}{'...' if len(formatted_response) > 50 else ''}"
        )

        return formatted_response

    def _extract_final_output(self, result: str) -> str:
        """
        Extract the final output section from the result if it exists.
        If no final output section is found, return the original result.

        Args:
            result: The result string from the agent

        Returns:
            The extracted final output or the original result
        """
        # Look for common final output section markers
        final_output_markers = [
            "## Final Output",
            "# Final Output",
            "### Final Output",
            "Final Output:",
            "Final Result:",
            "Final Answer:"
        ]

        # Try to find any of the markers in the result
        for marker in final_output_markers:
            if marker in result:
                # Split the result at the marker and take everything after it
                parts = result.split(marker, 1)
                if len(parts) > 1:
                    # Clean up the final output
                    final_output = parts[1].strip()
                    # Remove any trailing implementation steps or notes sections
                    end_markers = ["## Implementation", "## Notes", "## Next Steps", "## References"]
                    for end_marker in end_markers:
                        if end_marker in final_output:
                            final_output = final_output.split(end_marker, 1)[0].strip()
                    return final_output

        # If no final output section is found, check if there's a clear separation with multiple newlines
        if "\n\n\n" in result:
            # The last section after multiple newlines might be the final output
            sections = result.split("\n\n\n")
            if len(sections) > 1 and len(sections[-1].strip()) > 0:
                return sections[-1].strip()

        # If no clear final output section is found, return the original result
        return result

    async def execute(self, input_text: str = None, prompt: str = None, conversation_id: Optional[str] = None, timeline: Optional[Timeline] = None, **kwargs) -> Union[str, ToolResult]:
        """
        Execute the integrated flow with the given input.

        This method first checks if the input is a simple prompt that can be handled directly.
        If so, it returns a direct response without invoking the agent system.
        Otherwise, it delegates to the IntegratedAgent, which will analyze the input
        and route it to the appropriate specialized agent. It also ensures that all
        outputs are saved to a dedicated folder for the conversation.

        Args:
            input_text: The input text to process
            prompt: Alternative input text parameter (used if input_text is None)
            conversation_id: Optional conversation ID to use. If provided, it will override
                           the conversation ID set during initialization.
            timeline: Optional timeline to track events. If provided, events will be added to this timeline.
            kwargs: Additional keyword arguments to pass to the agent

        Returns:
            str: The result from the appropriate specialized agent or a direct response
        """
        # Use prompt parameter if provided, otherwise use input_text
        input_text = prompt if prompt is not None else input_text
        try:
            if not self.integrated_agent:
                raise ValueError("No integrated agent available")

            # Update conversation ID if provided
            if conversation_id:
                self._conversation_id = conversation_id
                # Update the file saver's active conversation ID if available
                if self._file_saver is not None:
                    try:
                        self._file_saver.set_active_conversation(self._conversation_id)
                    except Exception as e:
                        logger.error(f"Error updating file saver's conversation ID: {str(e)}")

            # Create a new timeline if not provided
            active_timeline = timeline or Timeline()

            # Record the user input in the timeline if not already recorded
            if not any(event.type == "user_input" for event in active_timeline.events):
                create_user_input_event(active_timeline, input_text)

            # Log the start of execution
            logger.info(f"Executing integrated flow with input: {input_text[:50]}... (Conversation ID: {self._conversation_id})")

            # Create a system event for flow execution
            flow_event = create_system_event(
                active_timeline,
                "Integrated Flow Execution",
                f"Processing input: {input_text[:50]}{'...' if len(input_text) > 50 else ''}"
            )

            # Set up the output organizer for this conversation
            await self._output_organizer.execute(
                action="set_active_conversation",
                conversation_id=self._conversation_id
            )

            # Use the message classifier to determine if this is a chat message or requires agent processing
            message_type = "chat"  # Default to chat if classifier is not available
            classification_result = None

            if self._message_classifier is not None:
                try:
                    # Clean the input text to remove common UI messages
                    cleaned_input = input_text
                    ui_messages = ["What would you like to do next?", "What can I help you with?"]
                    for msg in ui_messages:
                        if cleaned_input.startswith(msg):
                            cleaned_input = cleaned_input[len(msg):].strip()

                    # Classify the message with thresholds that favor chat classification
                    classification_result = await self._message_classifier.execute(
                        message=cleaned_input,
                        threshold_override={
                            "chat_threshold": 0.60,  # Lower threshold to classify more messages as chat
                            "agent_threshold": 0.40  # Higher threshold to require more confidence for agent routing
                        }
                    )
                    if not classification_result.error:
                        message_type = classification_result.output["classification"]
                        analysis = classification_result.output["analysis"]
                        logger.info(f"Message classified as '{message_type}' (chat_score={analysis['chat_score']:.2f}, agent_score={analysis['agent_score']:.2f})")

                        # Add classification event to timeline
                        create_system_event(
                            active_timeline,
                            "Message Classification",
                            f"Message classified as '{message_type}' (chat_score={analysis['chat_score']:.2f}, agent_score={analysis['agent_score']:.2f})"
                        )
                    else:
                        logger.warning(f"Error classifying message: {classification_result.output.get('error', 'Unknown error')}")
                except Exception as e:
                    logger.error(f"Error using message classifier: {str(e)}")
            else:
                # Fall back to simple prompt detection if classifier is not available
                message_type = "chat" if is_simple_prompt(input_text) else "agent"
                logger.info(f"Using fallback classification: '{message_type}'")

            # Handle chat messages directly
            if message_type == "chat":
                logger.info(f"Handling as chat message: '{input_text}'")
                direct_response = get_direct_response(input_text)

                # If no direct response is available, try to handle common patterns before routing to agent
                if direct_response is None:
                    # Try to handle math calculations directly
                    import re
                    # Check for "what is X+Y" format
                    math_match = re.search(r'what\s+is\s+(\d+\s*[+\-*/]\s*\d+)', input_text.lower())
                    if math_match:
                        expression = math_match.group(1).replace(' ', '')
                        try:
                            result = eval(expression)
                            direct_response = f"The result of {expression} is {result}."
                            logger.info(f"Handled math calculation directly: {expression} = {result}")
                        except Exception as e:
                            logger.warning(f"Failed to evaluate math expression: {expression}, error: {str(e)}")

                    # Check for direct math expressions like "5+5"
                    if direct_response is None:
                        direct_math_match = re.search(r'^(\d+\s*[+\-*/]\s*\d+)$', input_text.lower())
                        if direct_math_match:
                            expression = direct_math_match.group(1).replace(' ', '')
                            try:
                                result = eval(expression)
                                direct_response = f"The result of {expression} is {result}."
                                logger.info(f"Handled direct math calculation: {expression} = {result}")
                            except Exception as e:
                                logger.warning(f"Failed to evaluate direct math expression: {expression}, error: {str(e)}")

                    # Try to handle model questions directly
                    model_patterns = ["which model", "what model", "which llm", "what llm", "which ai", "what ai"]
                    if direct_response is None and any(pattern in input_text.lower() for pattern in model_patterns):
                        direct_response = "I am Nexagent, powered by Claude 3.7 Sonnet, an AI assistant developed by Anthropic. I'm designed to be helpful, harmless, and honest in my interactions."
                        logger.info(f"Handled model question directly")

                    # Try to handle Elon Musk questions directly
                    elon_patterns = ["who is elon", "who's elon", "who is elon musk", "who's elon musk"]
                    if direct_response is None and any(pattern in input_text.lower() for pattern in elon_patterns):
                        direct_response = "Elon Musk is a businessman known for his leadership of Tesla, SpaceX, and X (formerly Twitter). He is also the wealthiest person in the world."
                        logger.info(f"Handled Elon Musk question directly")

                    # If still no direct response and the message is long, route to agent
                    if direct_response is None:
                        if len(input_text.split()) > 20:
                            logger.info(f"Rerouting to agent due to complexity and no direct response: '{input_text}'")
                            message_type = "agent"  # Override to agent
                        else:
                            direct_response = "I'm not sure how to respond to that. How can I help you today?"
                            logger.warning(f"No direct response available for: '{input_text}'. Using default response.")

                # Only proceed with direct response if we're still in chat mode
                if message_type == "chat":
                    # Always use the LLM for chat messages as requested by the user
                    structured_response = await self._handle_chat_with_llm(input_text, active_timeline)

                    # Log that we're using the LLM for all chat messages
                    logger.info(f"Using LLM for all chat messages as requested: {input_text[:100]}{'...' if len(input_text) > 100 else ''}")

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

                # Only store and return the direct response if we're still in chat mode
                if message_type == "chat":
                    # Store the simple prompt in memory
                    logger.info(f"Storing simple prompt in memory for conversation {self._conversation_id}")
                    conversation_memory.add_entry(
                        user_prompt=input_text,
                        bot_response=structured_response,
                        conversation_id=self._conversation_id,
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "simple_prompt": True
                        }
                    )

                    logger.info(f"Direct response provided for conversation {self._conversation_id}")
                    return structured_response
                # If we've rerouted to agent, continue with agent processing

            # For complex prompts, delegate to the integrated agent
            logger.info(f"Complex prompt detected. Delegating to agent system.")

            # Get conversation history from memory
            previous_messages = conversation_memory.get_messages_for_llm(self._conversation_id, max_entries=3)

            # Add conversation history to the agent's memory if available
            if previous_messages:
                logger.info(f"Adding {len(previous_messages)} previous messages from conversation history")
                for message in previous_messages:
                    self.integrated_agent.memory.add_message(message)

            # Pass the timeline to the integrated agent if it has a timeline parameter
            if hasattr(self.integrated_agent, "timeline"):
                self.integrated_agent.timeline = active_timeline

            # Run the agent with the input and conversation ID
            result = await self.integrated_agent.run(input_text, conversation_id=self._conversation_id)

            # Always ensure the result has a clear final output section
            if hasattr(self.integrated_agent, 'format_output'):
                result = self.integrated_agent.format_output(result, is_final_output=True)
            else:
                # Extract just the final output section if it exists
                result = self._extract_final_output(result)

            # Save the result as an output
            await self._output_organizer.execute(
                action="save_output",
                output_name="response",
                output_content=result,
                output_type="document"
            )

            # Log the completion of execution
            logger.info(f"Integrated flow execution completed for conversation {self._conversation_id}")

            # Record the agent response in the timeline if not already recorded
            if not any(event.type == "agent_response" for event in active_timeline.events):
                create_agent_response_event(active_timeline, result)

            # Mark the flow execution event as successful
            flow_event.mark_success()

            # Store the conversation in memory
            if not is_simple_prompt(input_text):
                logger.info(f"Storing conversation in memory for conversation {self._conversation_id}")
                conversation_memory.add_entry(
                    user_prompt=input_text,
                    bot_response=result,
                    conversation_id=self._conversation_id,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "agent_id": "integrated_agent"
                    }
                )

            return result

        except Exception as e:
            error_message = f"Error in integrated flow execution: {str(e)}"
            logger.error(error_message)

            # Mark the flow execution event as failed
            if 'flow_event' in locals():
                flow_event.mark_error(str(e))

            # Try to save the error message as an output
            try:
                await self._output_organizer.execute(
                    action="save_output",
                    output_name="error",
                    output_content=error_message,
                    output_type="error"
                )
            except Exception as save_error:
                logger.error(f"Failed to save error output: {str(save_error)}")

            # Format the error message with a clear structure
            if hasattr(self.integrated_agent, 'format_output'):
                structured_error = self.integrated_agent.format_output(
                    f"## Implementation Steps\n\nAn error occurred during execution.\n\n## Final Output\n\nI encountered an error while processing your request: {str(e)}",
                    is_final_output=True
                )
                return structured_error
            else:
                # Return just the error message without implementation steps
                return f"I encountered an error while processing your request: {str(e)}"