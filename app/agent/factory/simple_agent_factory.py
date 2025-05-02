"""
Simplified Agent Factory Module to avoid import issues.
"""

from typing import Dict, Any, Type, Optional, List

from app.logger import logger


class AgentLoop:
    """Base class for agent loops."""
    
    def __init__(self, name: str, description: Optional[str] = None, **kwargs):
        self.name = name
        self.description = description
        
    async def run(self, prompt: str) -> str:
        """Run the agent loop."""
        return f"Running agent {self.name} with prompt: {prompt}"


class AgentFactory:
    """
    Factory class for creating different types of agents.
    """
    
    # Registry of available agent types
    _agent_types: Dict[str, Type[AgentLoop]] = {}
    
    @classmethod
    def register_agent_type(cls, name: str, agent_class: Type[AgentLoop]) -> None:
        """
        Register a new agent type.
        """
        if name in cls._agent_types:
            logger.warning(f"Overwriting existing agent type: {name}")
        
        cls._agent_types[name] = agent_class
        logger.info(f"Registered agent type: {name}")
    
    @classmethod
    def create_agent(
        cls, 
        agent_type: str, 
        name: str, 
        description: Optional[str] = None,
        max_steps: int = 10,
        **kwargs
    ) -> AgentLoop:
        """
        Create a new agent instance.
        """
        if agent_type not in cls._agent_types:
            available_types = ", ".join(cls._agent_types.keys())
            raise ValueError(
                f"Unknown agent type: {agent_type}. Available types: {available_types}"
            )
        
        agent_class = cls._agent_types[agent_type]
        
        # Create the agent instance
        agent = agent_class(
            name=name,
            description=description,
            max_steps=max_steps,
            **kwargs
        )
        
        logger.info(f"Created agent: {name} (type: {agent_type})")
        return agent
    
    @classmethod
    def get_available_agent_types(cls) -> List[str]:
        """
        Get a list of available agent types.
        """
        return list(cls._agent_types.keys())
