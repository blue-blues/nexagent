"""
Nexagent Application Package

This package contains the core functionality of the Nexagent application.
"""

# Export the get_llm function from the llm module
from app.llm import get_llm

__all__ = ["get_llm"]