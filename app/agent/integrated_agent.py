from typing import Dict, List, Optional, Any
import re
from pydantic import Field

from app.agent.base import BaseAgent
from app.agent.nexagent import Nexagent
from app.agent.software_dev_agent import SoftwareDevAgent
from app.agent.web_output import WebOutputFormatter
from app.memory.conversation_memory import conversation_memory
from app.schema import AgentState, Message
from app.logger import logger
from app.timeline.timeline import Timeline
from app.timeline.events import create_system_event
from app.tools.conversation_file_saver import ConversationFileSaver

class IntegratedAgent(BaseAgent):
    """
    An integrated agent that routes queries between specialized agents based on content analysis.
    """
    name: str = "integrated_agent"
    description: str = "Routes queries to specialized agents based on content analysis"
    state: AgentState = AgentState.IDLE

    general_agent: Nexagent = Field(default_factory=Nexagent)
    dev_agent: SoftwareDevAgent = Field(default_factory=SoftwareDevAgent)
    active_agent_name: Optional[str] = None
    timeline: Optional[Timeline] = Field(default=None, description="Timeline for tracking agent events")

    # Conversation file saver for redirecting file paths
    _file_saver: Optional[ConversationFileSaver] = None

    code_keywords: List[str] = Field(default=[
        "code", "program", "function", "class", "method", "variable", "debug", "error", "exception",
        "syntax", "compile", "runtime", "algorithm", "data structure", "api", "library", "framework",
        "javascript", "python", "java", "c++", "typescript", "html", "css", "sql", "database", "query",
        "server", "client", "frontend", "backend", "web", "app", "development", "software", "git",
        "version control", "bug", "fix", "implement", "feature", "refactor", "optimize", "test",
        "unit test", "integration test", "ci/cd", "pipeline"
    ])
    code_patterns: List[str] = Field(default=[
        r"```[\w]*\n[\s\S]*?```",  # Markdown code blocks
        r"def\s+\w+\s*\([^)]*\)\s*:",  # Python function definitions with parameters
        r"class\s+\w+(?:\s*\([^)]*\))?\s*:",  # Class definitions with optional inheritance
        r"(?:async\s+)?function\s*\w*\s*\([^)]*\)",  # JavaScript function definitions (including async)
        r"\w+\s*=\s*(?:async\s+)?function\s*\([^)]*\)",  # JavaScript function assignments
        r"const\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*=>",  # JavaScript arrow functions
        r"import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+['\"][^'\"]+['\"]|['\"][^'\"]+['\"])",  # JS/TS imports
        r"<[^>]+>[\s\S]*?</\w+>",  # HTML tags with attributes
        r"SELECT\s+(?:[\w\s,*]+|\*)\s+FROM\s+\w+(?:\s+WHERE\s+)?",  # SQL queries with optional WHERE
        r"\{[\s\n]*(?:['\"]\w+['\"]|\w+)\s*:\s*[^}]*\}",  # JSON/object structures
        r"\[(?:[^\[\]]*|\[(?:[^\[\]]*|\[[^\[\]]*\])*\])*\]",  # Nested array definitions
        r"(?:public|private|protected)?\s*(?:static\s+)?(?:async\s+)?[\w<>]+\s+\w+\s*\([^)]*\)",  # Java/C# method definitions
        r"#include\s*[<\"].*[>\"]",  # C/C++ includes
        r"@\w+(?:\([^)]*\))?",  # Decorators/annotations
    ])
    routing_history: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def _is_code_related(self, prompt: str) -> bool:
        """Determines if a prompt is related to coding based on keywords and patterns."""
        prompt_lower = prompt.lower()

        if any(keyword.lower() in prompt_lower for keyword in self.code_keywords):
            logger.debug("Code-related keyword detected.")
            return True

        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in self.code_patterns):
            logger.debug("Code-related pattern detected.")
            return True

        return False

    def _select_agent(self, prompt: str) -> BaseAgent:
        """Selects the appropriate agent based on prompt analysis."""
        is_code_related = self._is_code_related(prompt)
        self.active_agent_name = "software_dev" if is_code_related else "general"
        logger.info(f"Routing to {self.active_agent_name} agent for prompt: {prompt[:50]}...")
        return self.dev_agent if is_code_related else self.general_agent

    async def step(self) -> bool:
        """Executes a single step in the agent's reasoning process."""
        return False  # Delegation is handled by `run`

    @property
    def available_tools(self):
        """Get the available tools from the active agent."""
        if self.active_agent_name == "software_dev":
            return self.dev_agent.tools
        else:
            return self.general_agent.tools

    async def run(self, prompt: str, conversation_id: Optional[str] = None) -> str:
        """Processes a user's prompt by routing it to the appropriate agent."""
        # Create a timeline if not already provided
        if self.timeline is None:
            self.timeline = Timeline()

        # Create a routing event in the timeline
        routing_event = create_system_event(
            self.timeline,
            "Agent Routing",
            "Analyzing prompt to select the appropriate agent"
        )

        try:
            logger.info(f"Processing prompt: {prompt[:50]}...")
            selected_agent = self._select_agent(prompt)

            # Record the routing decision in history
            self.routing_history.append({
                "prompt": prompt,
                "selected_agent": self.active_agent_name,
                "is_code_related": self.active_agent_name == "software_dev"
            })

            # Update the routing event with the decision
            routing_event.mark_success({
                "selected_agent": self.active_agent_name,
                "is_code_related": self.active_agent_name == "software_dev"
            })

            # Add conversation history context if available
            if conversation_id:
                # Get conversation history
                history = conversation_memory.format_recent_history(conversation_id, max_entries=3)
                if history and history != "No previous conversation history.":
                    # Add conversation history as system message
                    system_prompt = f"Previous conversation history:\n\n{history}\n\nPlease consider this context when responding to the user's current request."
                    selected_agent.memory.add_message(Message.system_message(system_prompt))
                    logger.info(f"Added conversation history context from conversation {conversation_id}")

                # Initialize the conversation file saver if needed
                try:
                    if self._file_saver is None:
                        self._file_saver = ConversationFileSaver()

                    # Set the active conversation ID
                    self._file_saver.set_active_conversation(conversation_id)

                    # Update the agent's tools to use the conversation file saver
                    if hasattr(selected_agent, 'available_tools') and hasattr(selected_agent.available_tools, 'tool_map'):
                        # Replace the file_saver tool with our conversation-aware version
                        if 'file_saver' in selected_agent.available_tools.tool_map:
                            selected_agent.available_tools.tool_map['file_saver'] = self._file_saver
                            logger.info(f"Updated agent's file_saver tool to use conversation-aware version")
                except Exception as e:
                    logger.error(f"Error setting up conversation file saver: {str(e)}")

            # Pass the timeline to the selected agent if it supports it
            if hasattr(selected_agent, "timeline"):
                selected_agent.timeline = self.timeline

            # Execute the selected agent
            result = await selected_agent.run(prompt)

            # Update the agent state
            if hasattr(selected_agent, "state"):
                self.state = selected_agent.state

            return result
        except Exception as e:
            logger.error(f"Error in IntegratedAgent: {str(e)}")
            self.state = AgentState.ERROR

            # Mark the routing event as failed
            routing_event.mark_error(str(e))

            return f"An error occurred while processing your request: {str(e)}"

    def format_output(self, output: str, is_final_output: bool = False) -> str:
        """Format the output with clear separation between implementation steps and final output.

        Args:
            output: The raw output to format
            is_final_output: Whether this is the final output

        Returns:
            Formatted output with clear sections
        """
        # Use the WebOutputFormatter to create a structured output
        return WebOutputFormatter.create_structured_output(output)
