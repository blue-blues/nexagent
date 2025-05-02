"""
Agent Factory Package

This package provides a factory for creating different types of agents.
"""

from app.agent.factory.agent_factory import AgentFactory
from app.agent.types.simple_agent import SimpleAgent
from app.agent.nexagent import Nexagent

# Register the agents
AgentFactory.register_agent_type("simple", SimpleAgent)
AgentFactory.register_agent_type("nexagent", Nexagent)

__all__ = ["AgentFactory"]