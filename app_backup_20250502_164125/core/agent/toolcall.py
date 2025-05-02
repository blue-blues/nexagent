import json
from typing import Any, List, Optional, Union

from pydantic import Field

from app.agent.react import ReActAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tool import CreateChatCompletion, Terminate, ToolCollection


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    # Track thought history for loop detection
    thought_history: List[str] = Field(default_factory=list)
    max_thought_repetitions: int = 3
    
    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        try:
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=[Message.system_message(self.system_prompt)]
                if self.system_prompt
                else None,
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        # Validate thought content
        if not self._validate_thought_content(response.content):
            # If thought is empty or too generic, try to get a better response
            logger.warning(f"🤔 {self.name}'s thought is empty or too generic. Requesting clarification...")
            try:
                # Request a more detailed thought
                clarification_msg = Message.user_message(
                    "Please provide more detailed reasoning about the current task and what specific actions should be taken."
                )
                self.messages.append(clarification_msg)
                
                # Get a new response with more detailed thought
                response = await self.llm.ask_tool(
                    messages=self.messages,
                    system_msgs=[Message.system_message(self.system_prompt)]
                    if self.system_prompt
                    else None,
                    tools=self.available_tools.to_params(),
                    tool_choice=self.tool_choices,
                )
                
                # Remove the clarification message to avoid cluttering the history
                self.messages.pop()
            except Exception as e:
                logger.error(f"Error getting clarification: {e}")
                # Continue with original response if clarification fails
        
        self.tool_calls = response.tool_calls

        # Check for tool selection issues
        if not self.tool_calls and self._should_use_tools(response.content):
            logger.warning(f"⚠️ {self.name} should have selected tools based on content but didn't")
            try:
                # Request explicit tool selection
                tool_msg = Message.user_message(
                    "Based on your analysis, please select specific tools to accomplish this task."
                )
                self.messages.append(tool_msg)
                
                # Get a new response with tool selection
                response = await self.llm.ask_tool(
                    messages=self.messages,
                    system_msgs=[Message.system_message(self.system_prompt)]
                    if self.system_prompt
                    else None,
                    tools=self.available_tools.to_params(),
                    tool_choice=self.tool_choices,
                )
                
                # Update tool calls with new response
                self.tool_calls = response.tool_calls
                
                # Remove the tool selection message to avoid cluttering the history
                self.messages.pop()
            except Exception as e:
                logger.error(f"Error getting tool selection: {e}")
                # Continue with original response if tool selection fails

        # Log response info
        logger.info(f"✨ {self.name}'s thoughts: {response.content}")
        logger.info(
            f"🛠️ {self.name} selected {len(response.tool_calls) if response.tool_calls else 0} tools to use"
        )
        if response.tool_calls:
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in response.tool_calls]}"
            )

        # Track thought for loop detection
        self._update_thought_history(response.content)
        
        # Check if we're stuck in a loop
        if self._is_in_thought_loop():
            logger.warning(f"🔄 {self.name} appears to be stuck in a thought loop. Attempting to break out...")
            # Add a message to break the loop
            loop_break_msg = Message.user_message(
                "You seem to be repeating similar thoughts without making progress. Please try a completely different approach to solve this task."
            )
            self.messages.append(loop_break_msg)
            # Clear thought history to reset loop detection
            self.thought_history.clear()

        try:
            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if response.tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if response.content:
                    self.memory.add_message(Message.assistant_message(response.content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(
                    content=response.content, tool_calls=self.tool_calls
                )
                if self.tool_calls
                else Message.assistant_message(response.content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(response.content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            result = await self.execute_tool(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result, tool_call_id=command.id, name=command.function.name
            )
            self.memory.add_message(tool_msg)
            results.append(result)

        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Execute the tool
            logger.info(f"🔧 Activating tool: '{name}'...")
            result = await self.available_tools.execute(name=name, tool_input=args)

            # Format result for display
            raw_observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )
            
            # Apply web formatting if enabled
            observation = self.format_tool_result(raw_observation) if hasattr(self, 'format_tool_result') else raw_observation

            # Handle special tools like `finish`
            await self._handle_special_tool(name=name, result=result)

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        # For the terminate tool, we still want to set the agent state to finished
        # but we don't want to terminate the session completely
        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]
        
    def _validate_thought_content(self, content: Optional[str]) -> bool:
        """Validate if thought content is meaningful and not empty"""
        if not content:
            return False
            
        # Check if content is too short or generic
        if len(content.strip()) < 10:
            return False
            
        # Check for generic, non-informative responses
        generic_phrases = [
            "I'll help you with that",
            "I can assist with this",
            "Let me think about this",
            "I need more information",
            "I'll do my best"
        ]
        
        # If content is just a generic phrase without specifics, it's not meaningful
        if any(content.strip().lower().startswith(phrase.lower()) for phrase in generic_phrases) and len(content.strip()) < 50:
            return False
            
        return True
        
    def _should_use_tools(self, content: Optional[str]) -> bool:
        """Determine if tools should be used based on thought content"""
        if not content:
            return False
            
        # Keywords that suggest tool usage is needed
        tool_indicators = [
            "search", "find", "look up", "browse", "navigate", "execute", 
            "run", "calculate", "analyze", "process", "extract", "save", 
            "create", "generate", "check", "verify", "compare", "download",
            "need to", "should", "could", "would", "will", "let's", "let me"
        ]
        
        # If content contains action words but no tools were selected, likely needs tools
        return any(indicator in content.lower() for indicator in tool_indicators)
        
    def _update_thought_history(self, content: Optional[str]) -> None:
        """Update thought history for loop detection"""
        if not content:
            return
            
        # Keep history limited to prevent memory growth
        if len(self.thought_history) >= 10:
            self.thought_history.pop(0)
            
        self.thought_history.append(content)
        
        # Broadcast thought to websocket clients
        if self.websocket:
            self.websocket.broadcast({
                'type': 'thought_update',
                'content': content,
                'timestamp': datetime.now().isoformat()
            })
        
    def _is_in_thought_loop(self) -> bool:
        """Detect if agent is stuck in a thought loop"""
        if len(self.thought_history) < 3:
            return False
            
        # Check for exact repetition
        last_thought = self.thought_history[-1]
        repetition_count = 0
        
        for thought in reversed(self.thought_history[:-1]):
            # Check similarity - exact match or high similarity
            if thought == last_thought:
                repetition_count += 1
                if repetition_count >= self.max_thought_repetitions:
                    return True
            # Check for semantic similarity (simplified version)
            elif self._calculate_similarity(thought, last_thought) > 0.8:
                repetition_count += 1
                if repetition_count >= self.max_thought_repetitions:
                    return True
            else:
                # Reset counter if we find a different thought
                repetition_count = 0
                
        return False
        
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two text strings
        
        This is a simplified version that doesn't require external libraries.
        Returns a value between 0 (completely different) and 1 (identical).
        """
        # Convert to lowercase and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        if not words1 or not words2:
            return 0.0
            
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
