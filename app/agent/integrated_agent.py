from typing import Dict, List, Optional, Union, Any
import re
from pydantic import Field

from app.agent.base import BaseAgent
from app.agent.nexagent import Nexagent
from app.agent.software_dev_agent import SoftwareDevAgent
from app.schema import AgentState, Message
from app.logger import logger

class IntegratedAgent(BaseAgent):
    """
    An integrated agent that routes queries between specialized agents based on content analysis.
    """
    name: str = "integrated_agent"
    description: str = "Routes queries to specialized agents based on content analysis"
    
    general_agent: Nexagent = Field(default_factory=Nexagent)
    dev_agent: SoftwareDevAgent = Field(default_factory=SoftwareDevAgent)
    active_agent_name: Optional[str] = None
    
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
    
    async def run(self, prompt: str) -> str:
        """Processes a user's prompt by routing it to the appropriate agent."""
        try:
            logger.info(f"Processing prompt: {prompt[:50]}...")
            selected_agent = self._select_agent(prompt)
            
            self.routing_history.append({
                "prompt": prompt,
                "selected_agent": self.active_agent_name,
                "is_code_related": self.active_agent_name == "software_dev"
            })
            
            result = await selected_agent.run(prompt)
            
            if hasattr(selected_agent, "state"):
                self.state = selected_agent.state
            
            return result
        except Exception as e:
            logger.error(f"Error in IntegratedAgent: {str(e)}")
            self.state = AgentState.ERROR
            return f"An error occurred while processing your request: {str(e)}"
