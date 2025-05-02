"""
Agent Factory Package

This package provides a factory for creating different types of agents.
"""

from app.agent.factory.simple_agent_factory import AgentFactory, AgentLoop

# Create a simple agent class
class SimpleAgent(AgentLoop):
    """Simple agent implementation."""
    pass

# Create a nexagent class
class Nexagent(AgentLoop):
    """Nexagent implementation."""
    pass

# Register the agents
AgentFactory.register_agent_type("simple", SimpleAgent)
AgentFactory.register_agent_type("nexagent", Nexagent)

__all__ = ["AgentFactory"]