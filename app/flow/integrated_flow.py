from typing import Dict, List, Optional, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.agent.integrated_agent import IntegratedAgent
from app.flow.base import BaseFlow
from app.logger import logger


class IntegratedFlow(BaseFlow):
    """
    A flow that uses the IntegratedAgent to route queries between specialized agents.
    
    This flow provides a unified interface to multiple specialized agents by using
    the IntegratedAgent as its primary agent. The IntegratedAgent analyzes user prompts
    and delegates to the appropriate specialized agent based on content analysis.
    """
    
    def __init__(
        self, integrated_agent: Optional[IntegratedAgent] = None, **data
    ):
        """
        Initialize the integrated flow with an IntegratedAgent.
        
        Args:
            integrated_agent: An optional IntegratedAgent instance. If not provided,
                             a new IntegratedAgent will be created.
            **data: Additional data to pass to the parent class.
        """
        # Create a new IntegratedAgent if not provided
        if integrated_agent is None:
            integrated_agent = IntegratedAgent()
        
        # Initialize with the IntegratedAgent as the only agent
        super().__init__({"integrated_agent": integrated_agent}, **data)
        
        # Set the primary agent key to the integrated agent
        self.primary_agent_key = "integrated_agent"
    
    @property
    def integrated_agent(self) -> IntegratedAgent:
        """
        Get the integrated agent instance.
        
        Returns:
            IntegratedAgent: The integrated agent instance
        """
        return self.agents["integrated_agent"]
    
    async def execute(self, input_text: str) -> str:
        """
        Execute the integrated flow with the given input.
        
        This method delegates to the IntegratedAgent, which will analyze the input
        and route it to the appropriate specialized agent.
        
        Args:
            input_text: The input text to process
            
        Returns:
            str: The result from the appropriate specialized agent
        """
        try:
            if not self.integrated_agent:
                raise ValueError("No integrated agent available")
            
            # Log the start of execution
            logger.info(f"Executing integrated flow with input: {input_text[:50]}...")
            
            # Delegate to the integrated agent
            result = await self.integrated_agent.run(input_text)
            
            # Log the completion of execution
            logger.info("Integrated flow execution completed")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in integrated flow execution: {str(e)}")
            return f"Integrated flow execution failed: {str(e)}"