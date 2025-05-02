"""
Adaptive Nexagent Integration Module.

This module integrates the Adaptive Learning System with the main Nexagent application,
allowing the bot to learn from past interactions and continuously improve its performance.
"""

import time
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from app.logger import logger

# Import learning system if available
try:
    from app.learning import AdaptiveLearningSystem
except ImportError:
    # Create a stub class for AdaptiveLearningSystem
    class AdaptiveLearningSystem:
        def __init__(self):
            pass

        def load_state(self, directory: str) -> None:
            """Stub implementation of load_state."""
            logger.warning(f"Stub implementation of load_state called with directory: {directory}")

        def save_state(self, directory: str) -> None:
            """Stub implementation of save_state."""
            logger.warning(f"Stub implementation of save_state called with directory: {directory}")

from app.flow.integrated_flow import IntegratedFlow
from app.flow.modular_coordination import ModularCoordinationFlow
from app.flow.base import FlowType, BaseFlow
from app.flow.flow_factory import FlowFactory
from app.agent.base import BaseAgent
from app.agent.toolcall import ToolCallAgent
from app.tools import ToolCollection
from app.timeline.timeline import Timeline
from app.timeline.events import create_system_event


class AdaptiveNexagentIntegration:
    """
    Integration between the Adaptive Learning System and Nexagent.

    This class provides methods for:
    1. Recording interactions in the learning system
    2. Selecting optimal strategies based on task type
    3. Applying learned knowledge to improve responses
    4. Collecting and processing user feedback
    5. Generating performance and feedback reports
    """

    def __init__(
        self,
        flow: Optional[BaseFlow] = None,
        agents: Optional[Dict[str, BaseAgent]] = None,
        tools: Optional[ToolCollection] = None,
        flow_type: Optional[FlowType] = None,
        learning_system: Optional[AdaptiveLearningSystem] = None,
        state_directory: Optional[str] = None
    ):
        """
        Initialize the Adaptive Nexagent Integration.

        Args:
            agents: Dictionary of agents to use
            tools: Tool collection to use
            flow_type: Type of flow to use
            learning_system: Optional learning system to use. If None, a new one is created.
            state_directory: Optional directory to load state from
        """
        # Create or use the provided learning system
        try:
            self.learning_system = learning_system or AdaptiveLearningSystem()
            logger.info(f"Created learning system: {type(self.learning_system).__name__}")

            # Check if the learning system has the required methods
            has_load_state = hasattr(self.learning_system, 'load_state')
            has_save_state = hasattr(self.learning_system, 'save_state')

            logger.info(f"Learning system has load_state: {has_load_state}")
            logger.info(f"Learning system has save_state: {has_save_state}")

            # Load state if a directory is provided
            if state_directory:
                try:
                    if has_load_state:
                        logger.info(f"Calling load_state with directory: {state_directory}")
                        self.learning_system.load_state(state_directory)
                        logger.info(f"Loaded learning system state from {state_directory}")
                    else:
                        logger.warning(f"Learning system does not have load_state method")
                except Exception as e:
                    logger.error(f"Error loading learning system state: {str(e)}")
        except Exception as e:
            logger.error(f"Error initializing learning system: {str(e)}")
            # Create a stub learning system as a fallback
            self.learning_system = AdaptiveLearningSystem()

        # Use provided flow or create a new one
        if flow is not None:
            self.flow = flow
            self.agents = flow.agents
            # Try to get tools from the flow if not provided
            if tools is None and hasattr(flow, 'integrated_agent') and hasattr(flow.integrated_agent, 'available_tools'):
                self.tools = flow.integrated_agent.available_tools
            else:
                self.tools = tools or {}
        else:
            # Store agents and tools
            self.agents = agents or {}
            self.tools = tools or {}

        # Convert tools to ToolCollection if it's a dict
        if isinstance(self.tools, dict):
            from app.tools import ToolCollection
            # Create an empty ToolCollection if tools is an empty dict
            if not self.tools:
                self.tools = ToolCollection()
            # Otherwise, convert the dict to a ToolCollection
            else:
                tool_list = list(self.tools.values())
                self.tools = ToolCollection(*tool_list)

            # Create the flow if flow_type is provided
            if flow_type is not None:
                self.flow = FlowFactory.create_flow(
                    flow_type=flow_type,
                    agents=self.agents
                )
            else:
                # Default to IntegratedFlow
                self.flow = IntegratedFlow()

        # Create a timeline
        self.timeline = Timeline()

        # Track conversation history
        self.conversation_history = []

        # Track the current conversation ID
        self.conversation_id = f"conv_{int(time.time())}"

        # Track the last interaction ID
        self.last_interaction_id = None

        logger.info("Initialized Adaptive Nexagent Integration")

    def detect_task_type(self, prompt: str) -> str:
        """
        Detect the type of task from a user prompt.

        Args:
            prompt: The user's input prompt

        Returns:
            The detected task type
        """
        # Use the keyword extraction tool if available
        keyword_tool = self.tools.get_tool("keyword_extraction")
        if keyword_tool:
            try:
                # Extract keywords from the prompt
                result = asyncio.run(keyword_tool.execute(
                    command="extract",
                    text=prompt,
                    extraction_method="auto"
                ))

                if not result.error:
                    # Parse the keywords
                    keywords = json.loads(result.output)["keywords"]

                    # Detect task type based on keywords
                    if any(kw in ["code", "function", "program", "script", "class", "method"] for kw in keywords):
                        return "code_generation"
                    elif any(kw in ["plan", "steps", "how to", "process", "workflow"] for kw in keywords):
                        return "planning"
                    elif any(kw in ["what", "who", "when", "where", "why", "how", "explain"] for kw in keywords):
                        return "question_answering"
                    elif any(kw in ["search", "find", "look up", "browse", "research"] for kw in keywords):
                        return "web_search"
            except Exception as e:
                logger.error(f"Error detecting task type with keyword extraction: {str(e)}")

        # Fall back to simple rule-based detection
        prompt_lower = prompt.lower()

        if any(term in prompt_lower for term in ["code", "function", "program", "script", "class", "method"]):
            return "code_generation"
        elif any(term in prompt_lower for term in ["plan", "steps", "how to", "process", "workflow"]):
            return "planning"
        elif any(term in prompt_lower for term in ["what", "who", "when", "where", "why", "how", "explain"]):
            return "question_answering"
        elif any(term in prompt_lower for term in ["search", "find", "look up", "browse", "research"]):
            return "web_search"
        else:
            return "general"

    def select_agent(self, task_type: str) -> str:
        """
        Select the best agent for a task type.

        Args:
            task_type: The type of task

        Returns:
            The ID of the selected agent
        """
        # Check if we have analytics capability and performance data for this task type
        task_analysis = {}
        try:
            if hasattr(self.learning_system, 'analytics') and hasattr(self.learning_system.analytics, 'analyze'):
                task_analysis = self.learning_system.analytics.analyze(task_type=task_type)
        except Exception as e:
            logger.error(f"Error analyzing task performance: {str(e)}")

        # If we have tool usage data, use it to select the best agent
        if task_analysis and "tool_usage" in task_analysis:
            # Get the tools with the highest success rates for this task type
            tool_success_rates = task_analysis["tool_usage"]["tool_success_rates"]
            if tool_success_rates:
                # Sort tools by success rate
                sorted_tools = sorted(tool_success_rates.items(), key=lambda x: x[1], reverse=True)
                best_tools = [tool for tool, _ in sorted_tools[:3]]

                # Find agents that have these tools
                for agent_id, agent in self.agents.items():
                    if hasattr(agent, "available_tools") and agent.available_tools:
                        agent_tools = set(agent.available_tools.tool_map.keys())
                        if any(tool in agent_tools for tool in best_tools):
                            return agent_id

        # Fall back to simple rule-based selection
        if task_type == "code_generation":
            for agent_id, agent in self.agents.items():
                if "code" in agent.name.lower() or "developer" in agent.name.lower():
                    return agent_id
        elif task_type == "planning":
            for agent_id, agent in self.agents.items():
                if "plan" in agent.name.lower() or "organizer" in agent.name.lower():
                    return agent_id
        elif task_type in ["web_search", "question_answering"]:
            for agent_id, agent in self.agents.items():
                if "research" in agent.name.lower() or "search" in agent.name.lower():
                    return agent_id

        # If no specific agent is found, return the first agent
        return next(iter(self.agents.keys()))

    async def enhance_prompt(self, prompt: str, task_type: str) -> str:
        """
        Enhance a prompt with learned knowledge.

        Args:
            prompt: The original user prompt
            task_type: The detected task type

        Returns:
            The enhanced prompt
        """
        # Find similar past interactions if the method exists
        similar_interactions = []
        try:
            if hasattr(self.learning_system, 'find_similar_interactions') and callable(self.learning_system.find_similar_interactions):
                similar_interactions = self.learning_system.find_similar_interactions(
                    prompt=prompt,
                    limit=3
                )
        except Exception as e:
            logger.error(f"Error finding similar interactions: {str(e)}")

        # Find applicable templates if the method exists
        templates = []
        try:
            if hasattr(self.learning_system, 'find_applicable_templates') and callable(self.learning_system.find_applicable_templates):
                templates = self.learning_system.find_applicable_templates(
                    prompt=prompt,
                    task_type=task_type
                )
        except Exception as e:
            logger.error(f"Error finding applicable templates: {str(e)}")

        # If we have similar successful interactions, use them as examples
        if similar_interactions:
            successful_examples = [
                interaction for interaction in similar_interactions
                if interaction.success
            ]

            if successful_examples:
                # Add examples to the prompt
                enhanced_prompt = f"{prompt}\n\nHere are some examples of similar tasks:\n\n"

                for i, example in enumerate(successful_examples[:2]):
                    enhanced_prompt += f"Example {i+1}:\nUser: {example.user_prompt}\nAssistant: {example.bot_response}\n\n"

                return enhanced_prompt

        # If we have applicable templates, use the best one
        if templates:
            try:
                best_template = templates[0]

                # Apply the template if the method exists
                if hasattr(self.learning_system, 'apply_template') and callable(self.learning_system.apply_template):
                    template_result = self.learning_system.apply_template(
                        template_id=best_template.id,
                        prompt=prompt
                    )

                    if template_result:
                        # Add the template result to the prompt
                        enhanced_prompt = f"{prompt}\n\nBased on similar tasks, consider this approach:\n\n{template_result}"
                        return enhanced_prompt
            except Exception as e:
                logger.error(f"Error applying template: {str(e)}")

        # If no enhancement is possible, return the original prompt
        return prompt

    async def apply_strategy(
        self,
        task_type: str,
        agent_id: str,
        prompt: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Apply a strategy to a task.

        Args:
            task_type: The type of task
            agent_id: The ID of the agent to use
            prompt: The user prompt

        Returns:
            Tuple of (strategy parameters, context for execution)
        """
        # Select a strategy based on the task type if the method exists
        try:
            if hasattr(self.learning_system, 'select_strategy') and callable(self.learning_system.select_strategy):
                strategy = self.learning_system.select_strategy(
                    task_type=task_type,
                    context={"agent_id": agent_id}
                )
            else:
                # Use default strategies based on task type
                default_strategies = {
                    "general": {
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "tools": ["web_search", "enhanced_browser", "python_execute"]
                    },
                    "coding": {
                        "model": "gpt-4",
                        "temperature": 0.2,
                        "max_tokens": 3000,
                        "tools": ["python_execute", "file_saver", "enhanced_browser"]
                    },
                    "research": {
                        "model": "gpt-4",
                        "temperature": 0.5,
                        "max_tokens": 4000,
                        "tools": ["web_search", "enhanced_browser", "keyword_extraction"]
                    },
                    "writing": {
                        "model": "gpt-4",
                        "temperature": 0.8,
                        "max_tokens": 3000,
                        "tools": ["web_search", "enhanced_browser"]
                    },
                    "analysis": {
                        "model": "gpt-4",
                        "temperature": 0.3,
                        "max_tokens": 4000,
                        "tools": ["web_search", "enhanced_browser", "python_execute"]
                    },
                    "planning": {
                        "model": "gpt-4",
                        "temperature": 0.4,
                        "max_tokens": 3000,
                        "tools": ["planning", "web_search"]
                    },
                    "creative": {
                        "model": "gpt-4",
                        "temperature": 0.9,
                        "max_tokens": 3000,
                        "tools": ["web_search", "enhanced_browser"]
                    }
                }
                strategy = default_strategies.get(task_type, default_strategies["general"])
        except Exception as e:
            logger.error(f"Error selecting strategy: {str(e)}")
            # Use a default strategy
            strategy = {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "tools": ["web_search", "enhanced_browser", "python_execute"]
            }

        # Create execution context
        context = {
            "agent_id": agent_id,
            "task_type": task_type
        }

        # Apply strategy parameters
        if "model" in strategy:
            context["model"] = strategy["model"]

        if "temperature" in strategy:
            context["temperature"] = strategy["temperature"]

        if "max_tokens" in strategy:
            context["max_tokens"] = strategy["max_tokens"]

        if "tools" in strategy:
            # Ensure the agent has access to these tools
            agent = self.agents.get(agent_id)
            try:
                if agent and hasattr(agent, "available_tools") and agent.available_tools:
                    # Check which tools are available
                    if hasattr(agent.available_tools, 'tool_map') and isinstance(agent.available_tools.tool_map, dict):
                        available_tools = set(agent.available_tools.tool_map.keys())
                        strategy_tools = set(strategy["tools"])

                        # Log which tools are being used
                        context["tools_to_use"] = list(strategy_tools.intersection(available_tools))
                    elif isinstance(agent.available_tools, dict):
                        available_tools = set(agent.available_tools.keys())
                        strategy_tools = set(strategy["tools"])

                        # Log which tools are being used
                        context["tools_to_use"] = list(strategy_tools.intersection(available_tools))
            except Exception as e:
                logger.error(f"Error processing tools in strategy: {str(e)}")

        return strategy, context

    async def process_prompt(
        self,
        prompt: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user prompt with adaptive learning.

        Args:
            prompt: The user's input prompt
            conversation_id: Optional ID for the conversation
            context: Optional additional context

        Returns:
            Dictionary with the response and metadata
        """
        start_time = time.time()

        # Update conversation ID if provided
        if conversation_id:
            self.conversation_id = conversation_id

        # Create a system event for the prompt processing
        prompt_event = create_system_event(
            self.timeline,
            "Process Prompt",
            f"Processing prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        )

        try:
            # Detect the task type
            task_type = self.detect_task_type(prompt)

            # Select the best agent for the task
            agent_id = self.select_agent(task_type)

            # Enhance the prompt with learned knowledge
            enhanced_prompt = await self.enhance_prompt(prompt, task_type)

            # Apply a strategy
            strategy, exec_context = await self.apply_strategy(task_type, agent_id, enhanced_prompt)

            # Merge with provided context
            if context:
                exec_context.update(context)

            # Process the prompt with the selected agent and strategy
            try:
                # Execute the flow
                # Check if agent_id is already in exec_context to avoid duplicate keyword argument
                if 'agent_id' not in exec_context:
                    exec_context['agent_id'] = agent_id

                # Add timeline to exec_context
                exec_context['timeline'] = self.timeline

                # Execute the flow
                response = await self.flow.execute(
                    prompt=enhanced_prompt,
                    **exec_context
                )

                success = True
                error_message = None
            except Exception as e:
                logger.error(f"Error processing prompt: {str(e)}")
                response = f"I encountered an error while processing your request: {str(e)}"
                success = False
                error_message = str(e)

                # Try to self-heal
                response = await self._attempt_self_healing(response, error_message)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Get the tools used from the timeline
            tools_used = self._extract_tools_from_timeline()

            # Record the interaction if the method exists
            try:
                if hasattr(self.learning_system, 'record_interaction') and callable(self.learning_system.record_interaction):
                    interaction = self.learning_system.record_interaction(
                        user_prompt=prompt,
                        bot_response=response,
                        task_type=task_type,
                        tools_used=tools_used,
                        success=success,
                        execution_time=execution_time,
                        error_message=error_message,
                        metadata={
                            "agent_id": agent_id,
                            "strategy": strategy,
                            "conversation_id": self.conversation_id,
                            "enhanced_prompt": enhanced_prompt != prompt
                        }
                    )
                else:
                    # Create a simple interaction object if the method doesn't exist
                    interaction_id = f"interaction_{int(time.time())}"
                    interaction = type('obj', (object,), {
                        'id': interaction_id,
                        'metadata': {
                            "user_prompt": prompt,
                            "bot_response": response,
                            "task_type": task_type,
                            "tools_used": tools_used,
                            "success": success,
                            "execution_time": execution_time,
                            "error_message": error_message,
                            "agent_id": agent_id,
                            "conversation_id": self.conversation_id,
                            "enhanced_prompt": enhanced_prompt != prompt
                        }
                    })
            except Exception as e:
                logger.error(f"Error recording interaction: {str(e)}")
                # Create a simple interaction object if there's an error
                interaction_id = f"interaction_{int(time.time())}"
                interaction = type('obj', (object,), {
                    'id': interaction_id,
                    'metadata': {
                        "user_prompt": prompt,
                        "error": str(e)
                    }
                })

            # Update the last interaction ID
            self.last_interaction_id = interaction.id

            # Update strategy performance if the method exists
            try:
                if hasattr(self.learning_system, 'update_strategy_performance') and callable(self.learning_system.update_strategy_performance):
                    self.learning_system.update_strategy_performance(
                        task_type=task_type,
                        success=success,
                        execution_time=execution_time
                    )
            except Exception as e:
                logger.error(f"Error updating strategy performance: {str(e)}")

            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": prompt
            })

            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })

            # Infer implicit feedback if this is not the first interaction and we have conversation history
            if hasattr(self, 'conversation_history') and isinstance(self.conversation_history, list) and len(self.conversation_history) > 2:
                await self._infer_implicit_feedback(prompt, interaction.id)

            # Mark the prompt event as successful if it has the method
            if hasattr(prompt_event, 'mark_success') and callable(prompt_event.mark_success):
                prompt_event.mark_success({
                    "task_type": task_type,
                    "agent_id": agent_id,
                    "execution_time": execution_time,
                    "success": success
                })

            return {
                "response": response,
                "task_type": task_type,
                "agent_id": agent_id,
                "execution_time": execution_time,
                "success": success,
                "tools_used": tools_used,
                "interaction_id": interaction.id,
                "conversation_id": self.conversation_id
            }

        except Exception as e:
            logger.error(f"Error in process_prompt: {str(e)}")

            # Mark the prompt event as failed if it has the method
            if hasattr(prompt_event, 'mark_error') and callable(prompt_event.mark_error):
                prompt_event.mark_error({
                    "error": str(e)
                })

            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "success": False,
                "error": str(e),
                "conversation_id": self.conversation_id
            }

    async def _attempt_self_healing(self, response: str, error_message: str) -> str:
        """
        Attempt to self-heal from an error.

        Args:
            response: The current response
            error_message: The error message

        Returns:
            The updated response
        """
        try:
            # Try to get the self-healing tool
            self_healing_tool = None

            # Always use get_tool if available
            if hasattr(self.tools, 'get_tool') and callable(self.tools.get_tool):
                try:
                    self_healing_tool = self.tools.get_tool("self_healing")
                except Exception as e:
                    logger.error(f"Error getting self_healing tool: {str(e)}")
            # Fallback to dict access if tools is a dict
            elif isinstance(self.tools, dict) and "self_healing" in self.tools:
                self_healing_tool = self.tools["self_healing"]

            if not self_healing_tool:
                return response
        except Exception as e:
            logger.error(f"Error in self-healing attempt: {str(e)}")
            return response

        try:
            # Check if the tool has an execute method
            if hasattr(self_healing_tool, 'execute') and callable(self_healing_tool.execute):
                # Detect the error
                detection_result = await self_healing_tool.execute(
                    command="detect",
                    error_message=error_message
                )

                if hasattr(detection_result, 'error') and detection_result.error:
                    return response

                # Parse the detection result if it has output
                if hasattr(detection_result, 'output'):
                    try:
                        detection = eval(detection_result.output)

                        # If the error is recoverable, try to fix it
                        if isinstance(detection, dict) and detection.get("recoverable", False):
                            # Suggest fixes
                            suggestion_result = await self_healing_tool.execute(
                                command="suggest",
                                error_message=error_message
                            )

                            if hasattr(suggestion_result, 'error') and suggestion_result.error:
                                return response

                            # Parse the suggestion result
                            try:
                                suggestions = eval(suggestion_result.output)

                                # If there are suggestions, try to apply them
                                if suggestions:
                                    # Try to fix the error
                                    fix_result = await self_healing_tool.execute(
                                        command="fix",
                                        error_message=error_message,
                                        auto_fix=True
                                    )

                                    if not hasattr(fix_result, 'error') or not fix_result.error:
                                        # Parse the fix result
                                        try:
                                            fix = eval(fix_result.output)

                                            if isinstance(fix, dict) and fix.get("success", False):
                                                # Update the response with the fix information
                                                response += f"\n\nI encountered an error but was able to fix it: {fix.get('message', 'Unknown fix')}"
                                                return response
                                        except Exception as e:
                                            logger.error(f"Error parsing fix result: {str(e)}")

                                # If we couldn't fix the error, update the response with the suggestions
                                response += "\n\nI encountered an error and couldn't fix it automatically. Here are some suggestions:\n"
                                for suggestion in suggestions[:3]:
                                    if isinstance(suggestion, dict):
                                        response += f"- {suggestion.get('description', 'Unknown suggestion')}\n"
                            except Exception as e:
                                logger.error(f"Error processing suggestions: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error parsing detection result: {str(e)}")
                        return response
            # If the tool has a run method instead
            elif hasattr(self_healing_tool, 'run') and callable(self_healing_tool.run):
                healing_result = await self_healing_tool.run(error_message=error_message)
                if healing_result and hasattr(healing_result, 'success') and healing_result.success:
                    return f"I encountered an error but was able to recover: {healing_result.result}"
                return response

            return response

        except Exception as e:
            logger.error(f"Error in _attempt_self_healing: {str(e)}")
            return response

    def _extract_tools_from_timeline(self) -> List[str]:
        """
        Extract the tools used from the timeline.

        Returns:
            List of tool names
        """
        tools_used = []
        try:
            if hasattr(self, 'timeline') and self.timeline is not None and hasattr(self.timeline, 'events'):
                for event in self.timeline.events:
                    if hasattr(event, 'type') and event.type == "tool" and hasattr(event, 'data'):
                        if isinstance(event.data, dict) and event.data.get("tool_name"):
                            tool_name = event.data["tool_name"]
                            if tool_name not in tools_used:
                                tools_used.append(tool_name)
        except Exception as e:
            logger.error(f"Error extracting tools from timeline: {str(e)}")

        return tools_used

    async def _infer_implicit_feedback(self, prompt: str, current_interaction_id: str) -> None:
        """
        Infer implicit feedback from a user prompt.

        Args:
            prompt: The user prompt
            current_interaction_id: The ID of the current interaction
        """
        try:
            # Check if memory_store exists and has search_interactions method
            if not hasattr(self.learning_system, 'memory_store') or not hasattr(self.learning_system.memory_store, 'search_interactions'):
                logger.warning("Memory store not available for implicit feedback")
                return

            # Get the previous interaction ID
            previous_interaction_id = None
            for interaction in self.learning_system.memory_store.search_interactions(
                limit=10,
                offset=0
            ):
                if interaction.id != current_interaction_id and hasattr(interaction, 'metadata') and \
                   isinstance(interaction.metadata, dict) and interaction.metadata.get("conversation_id") == self.conversation_id:
                    previous_interaction_id = interaction.id
                    break

            if not previous_interaction_id:
                return
        except Exception as e:
            logger.error(f"Error searching for previous interactions: {str(e)}")
            return

        # Determine the user action
        user_action = ""

        # Check for corrections
        if any(term in prompt.lower() for term in ["that's not what I meant", "that's incorrect", "you misunderstood", "I meant", "actually", "instead", "correction", "wrong", "not right"]):
            user_action = "correction"
        # Check for repetitions
        elif any(term in prompt.lower() for term in ["repeat", "again", "one more time", "try again"]):
            user_action = "repetition"
        # Check for abandonment
        elif any(term in prompt.lower() for term in ["nevermind", "forget it", "cancel", "stop", "abort"]):
            user_action = "abandonment"
        # Check for continuation
        elif any(term in prompt.lower() for term in ["continue", "next", "go on", "proceed", "more"]):
            user_action = "continuation"

        # If we determined a user action, infer feedback
        if user_action:
            try:
                if hasattr(self.learning_system, 'infer_feedback') and callable(self.learning_system.infer_feedback):
                    self.learning_system.infer_feedback(
                        current_interaction_id=current_interaction_id,
                        previous_interaction_id=previous_interaction_id,
                        user_action=user_action
                    )
                else:
                    logger.warning("infer_feedback method not available")
            except Exception as e:
                logger.error(f"Error inferring feedback: {str(e)}")

    def record_explicit_feedback(
        self,
        interaction_id: str,
        content: str,
        rating: Optional[int] = None,
        positive: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Record explicit feedback from a user.

        Args:
            interaction_id: ID of the interaction the feedback is for
            content: Feedback content
            rating: Optional numerical rating (e.g., 1-5)
            positive: Optional boolean indicating if the feedback is positive

        Returns:
            Dictionary with the created feedback record
        """
        try:
            # Check if the method exists
            if hasattr(self.learning_system, 'record_feedback') and callable(self.learning_system.record_feedback):
                # Record the feedback
                feedback = self.learning_system.record_feedback(
                    interaction_id=interaction_id,
                    content=content,
                    rating=rating,
                    positive=positive
                )
                return feedback
            else:
                logger.warning("record_feedback method not available")
                return {"status": "error", "message": "Feedback recording not available"}
        except Exception as e:
            logger.error(f"Error recording explicit feedback: {str(e)}")
            return {"status": "error", "message": str(e)}

    def generate_performance_report(self) -> str:
        """
        Generate a comprehensive performance report.

        Returns:
            Formatted report as a string
        """
        try:
            if hasattr(self.learning_system, 'generate_performance_report'):
                return self.learning_system.generate_performance_report()
            else:
                return "Performance reporting is not available in this version."
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return f"Error generating performance report: {str(e)}"

    def generate_feedback_report(self) -> str:
        """
        Generate a comprehensive feedback report.

        Returns:
            Formatted report as a string
        """
        try:
            if hasattr(self.learning_system, 'generate_feedback_report'):
                return self.learning_system.generate_feedback_report()
            else:
                return "Feedback reporting is not available in this version."
        except Exception as e:
            logger.error(f"Error generating feedback report: {str(e)}")
            return f"Error generating feedback report: {str(e)}"

    def save_state(self, directory: str) -> None:
        """
        Save the state of the learning system to files.

        Args:
            directory: Directory to save the state to
        """
        try:
            # Check if the learning system has the save_state method
            has_save_state = hasattr(self.learning_system, 'save_state')
            logger.info(f"Learning system has save_state: {has_save_state}")

            if has_save_state:
                logger.info(f"Calling save_state with directory: {directory}")
                self.learning_system.save_state(directory)
                logger.info(f"Saved learning system state to {directory}")
            else:
                logger.warning(f"Learning system does not have save_state method")
        except Exception as e:
            logger.error(f"Error saving learning system state: {str(e)}")

    def load_state(self, directory: str) -> None:
        """
        Load the state of the learning system from files.

        Args:
            directory: Directory to load the state from
        """
        try:
            # Check if the learning system has the load_state method
            has_load_state = hasattr(self.learning_system, 'load_state')
            logger.info(f"Learning system has load_state: {has_load_state}")

            if has_load_state:
                logger.info(f"Calling load_state with directory: {directory}")
                self.learning_system.load_state(directory)
                logger.info(f"Loaded learning system state from {directory}")
            else:
                logger.warning(f"Learning system does not have load_state method")
        except Exception as e:
            logger.error(f"Error loading learning system state: {str(e)}")

    def get_improvement_priorities(self) -> Dict[str, Any]:
        """
        Get improvement priorities based on feedback.

        Returns:
            Dictionary with improvement priorities
        """
        return self.learning_system.get_improvement_priorities()

    def adapt_strategies(self) -> List[Dict[str, Any]]:
        """
        Adapt strategies based on performance data.

        Returns:
            List of adaptations made
        """
        return self.learning_system.adapt_strategies()

    def extract_knowledge(self) -> Dict[str, Any]:
        """
        Extract knowledge from past interactions.

        Returns:
            Dictionary with extraction results
        """
        return self.learning_system.extract_knowledge()
