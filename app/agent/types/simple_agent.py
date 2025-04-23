"""
Simple Agent Module

This module implements a simple agent that can respond to user queries.
"""

from typing import List, Optional, Dict, Any

from app.agent.loop.agent_loop import AgentLoop
from app.core.schema.schema import Message, Role
from app.utils.logging.logger import logger


class SimpleAgent(AgentLoop):
    """
    A simple agent that can respond to user queries.
    
    This agent uses the LLM directly to generate responses without complex
    reasoning or tool use.
    """
    
    async def step(self) -> str:
        """
        Execute a single step in the agent's workflow.
        
        In this simple agent, each step just processes the latest message
        in the conversation history.
        
        Returns:
            str: Result of the step execution
        """
        # Check if we have a message to process
        if not self.memory.get("messages"):
            return "No messages to process"
        
        messages = self.memory["messages"]
        
        # Get the latest message
        latest_message = messages[-1]
        
        # Log the message
        logger.info(f"Processing message: {latest_message.content}")
        
        # Generate a response using the LLM
        if self.llm is None:
            return "LLM not initialized"
        
        try:
            # Create a system message
            system_message = Message(
                role=Role.SYSTEM,
                content="You are a helpful assistant. Provide concise and accurate responses."
            )
            
            # Generate a response
            response = await self.llm.ask(
                messages=[system_message] + messages,
                temperature=0.7
            )
            
            # Add the response to the conversation history
            assistant_message = Message(
                role=Role.ASSISTANT,
                content=response
            )
            self.memory["messages"].append(assistant_message)
            
            # Return the response
            return response
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def add_message(self, content: str, role: str = Role.USER) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            content: Content of the message
            role: Role of the message sender
        """
        # Initialize messages list if it doesn't exist
        if "messages" not in self.memory:
            self.memory["messages"] = []
        
        # Create a message
        message = Message(
            role=role,
            content=content
        )
        
        # Add the message to the conversation history
        self.memory["messages"].append(message)
        
        # Log the message
        logger.info(f"Added message: {content}")
    
    async def chat(self, message: str) -> str:
        """
        Chat with the agent.
        
        This is a convenience method that adds a user message and runs
        a single step to generate a response.
        
        Args:
            message: User message
            
        Returns:
            str: Agent's response
        """
        # Add the user message
        self.add_message(message)
        
        # Run a single step
        return await self.step()
