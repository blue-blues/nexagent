"""
Agent Factory Package

This package provides a factory for creating different types of agents.
"""

from app.agent.factory.agent_factory import AgentFactory
from app.agent.types.simple_agent import SimpleAgent

# Register the simple agent
AgentFactory.register_agent_type("simple", SimpleAgent)

__all__ = ["AgentFactory"]