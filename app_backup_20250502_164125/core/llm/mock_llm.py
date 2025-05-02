"""
Mock LLM for testing purposes.

This module provides a mock LLM implementation that can be used for testing
without requiring an actual API key.
"""

from typing import List, Optional, Union, Dict, Any

from app.core.schema.schema import Message
from app.utils.logging.logger import logger


class MockLLM:
    """
    A mock LLM implementation for testing purposes.
    
    This class provides a simple implementation of the LLM interface that
    returns predefined responses for testing without requiring an actual API key.
    """
    
    def __init__(self, **kwargs):
        """Initialize the mock LLM."""
        self.responses = {
            "hello": "Hello! How can I help you today?",
            "who are you": "I am a mock LLM for testing purposes. I'm part of the Nexagent architecture.",
            "help": "I can help you test the Nexagent architecture without requiring an actual API key.",
        }
        self.default_response = "I'm a mock LLM. I can only respond to a few predefined queries for testing purposes."
        logger.info("Initialized MockLLM")
    
    async def ask(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Mock implementation of the ask method.
        
        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            stream: Whether to stream the response
            temperature: Sampling temperature for the response
            
        Returns:
            str: A predefined response based on the input
        """
        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user" and msg.get("content"):
                last_message = msg.get("content")
                break
            elif hasattr(msg, "role") and msg.role == "user" and msg.content:
                last_message = msg.content
                break
        
        if not last_message:
            return "I didn't receive a message to respond to."
        
        # Check for predefined responses
        for key, response in self.responses.items():
            if key.lower() in last_message.lower():
                logger.info(f"MockLLM returning response for '{key}'")
                return response
        
        # Return default response
        logger.info("MockLLM returning default response")
        return self.default_response
    
    async def ask_tool(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        timeout: int = 300,
        tools: Optional[List[dict]] = None,
        tool_choice: str = "auto",
        temperature: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Mock implementation of the ask_tool method.
        
        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            timeout: Request timeout in seconds
            tools: List of tools to use
            tool_choice: Tool choice strategy
            temperature: Sampling temperature for the response
            **kwargs: Additional completion arguments
            
        Returns:
            Dict[str, Any]: A mock response with a message
        """
        response = await self.ask(messages, system_msgs, False, temperature)
        
        # Return a mock message
        return {
            "role": "assistant",
            "content": response
        }
