"""
Agent Factory Module

This module provides a factory for creating different types of agents.
It abstracts the creation process and provides a unified interface for
creating agents with different capabilities.
"""

from typing import Dict, Any, Type, Optional, List

from app.agent.loop.agent_loop import AgentLoop
from app.core.llm.llm import LLM
from app.utils.logging.logger import logger


class AgentFactory:
    """
    Factory class for creating different types of agents.
    
    This class provides methods for registering agent types and creating
    instances of those agents with specific configurations.
    """
    
    # Registry of available agent types
    _agent_types: Dict[str, Type[AgentLoop]] = {}
    
    @classmethod
    def register_agent_type(cls, name: str, agent_class: Type[AgentLoop]) -> None:
        """
        Register a new agent type.
        
        Args:
            name: Unique name for the agent type
            agent_class: Class for the agent type
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
        llm: Optional[LLM] = None,
        max_steps: int = 10,
        **kwargs
    ) -> AgentLoop:
        """
        Create a new agent instance.
        
        Args:
            agent_type: Type of agent to create
            name: Name for the agent instance
            description: Optional description
            llm: Optional LLM instance
            max_steps: Maximum steps for the agent loop
            **kwargs: Additional arguments for the agent constructor
            
        Returns:
            AgentLoop: The created agent instance
            
        Raises:
            ValueError: If the agent type is not registered
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
            llm=llm,
            max_steps=max_steps,
            **kwargs
        )
        
        logger.info(f"Created agent: {name} (type: {agent_type})")
        return agent
    
    @classmethod
    def get_available_agent_types(cls) -> List[str]:
        """
        Get a list of available agent types.
        
        Returns:
            List[str]: List of registered agent type names
        """
        return list(cls._agent_types.keys())
