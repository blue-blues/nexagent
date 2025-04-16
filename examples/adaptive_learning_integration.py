"""
Example of integrating the Adaptive Learning System with Nexagent.

This script demonstrates how to integrate the Adaptive Learning System
with the main Nexagent application.
"""

import os
import sys
import time
import json
import asyncio
from typing import Dict, Any, List, Optional

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.learning import AdaptiveLearningSystem
from app.flow.integrated_flow import IntegratedFlow
from app.agent.toolcall import ToolCallAgent
from app.tool.tool_collection import ToolCollection
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.web_search import WebSearch
from app.tool.enhanced_browser_tool import EnhancedBrowserTool
from app.tool.planning import PlanningTool
from app.tool.code_generation import CodeGenerationTool
from app.tool.keyword_extraction import KeywordExtractionTool
from app.tool.self_healing import SelfHealingTool
from app.timeline.timeline import Timeline


class AdaptiveNexagent:
    """
    Enhanced Nexagent with Adaptive Learning capabilities.
    
    This class integrates the Adaptive Learning System with the main
    Nexagent application, allowing the bot to learn from past interactions
    and continuously improve its performance.
    """
    
    def __init__(self):
        """Initialize the Adaptive Nexagent."""
        # Create the Adaptive Learning System
        self.learning_system = AdaptiveLearningSystem()
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create agents
        self.agents = self._create_agents()
        
        # Create the integrated flow
        self.flow = IntegratedFlow(agents=self.agents)
        
        # Create a timeline
        self.timeline = Timeline()
        
        # Track conversation history
        self.conversation_history = []
    
    def _create_tools(self) -> ToolCollection:
        """
        Create the tools for the agents.
        
        Returns:
            ToolCollection with the created tools
        """
        # Create basic tools
        create_chat_completion = CreateChatCompletion()
        web_search = WebSearch()
        enhanced_browser = EnhancedBrowserTool()
        planning_tool = PlanningTool()
        
        # Create enhanced tools
        code_generation = CodeGenerationTool()
        keyword_extraction = KeywordExtractionTool()
        self_healing = SelfHealingTool()
        
        # Add dependencies
        code_generation.get_tool = lambda name: tools.get_tool(name)
        self_healing.get_tool = lambda name: tools.get_tool(name)
        
        # Create the tool collection
        tools = ToolCollection([
            create_chat_completion,
            web_search,
            enhanced_browser,
            planning_tool,
            code_generation,
            keyword_extraction,
            self_healing
        ])
        
        return tools
    
    def _create_agents(self) -> Dict[str, ToolCallAgent]:
        """
        Create the agents for the integrated flow.
        
        Returns:
            Dictionary of agents
        """
        # Create the main agent
        main_agent = ToolCallAgent(
            name="main",
            description="Main agent for handling user requests",
            system_prompt="You are Nexagent, an AI assistant that can help with a wide range of tasks.",
            available_tools=self.tools
        )
        
        # Create specialized agents
        planning_agent = ToolCallAgent(
            name="planning",
            description="Agent specialized in planning and breaking down complex tasks",
            system_prompt="You are a planning agent that specializes in breaking down complex tasks into manageable steps.",
            available_tools=self.tools
        )
        
        research_agent = ToolCallAgent(
            name="research",
            description="Agent specialized in research and information gathering",
            system_prompt="You are a research agent that specializes in gathering information from various sources.",
            available_tools=self.tools
        )
        
        coding_agent = ToolCallAgent(
            name="coding",
            description="Agent specialized in code generation and review",
            system_prompt="You are a coding agent that specializes in generating and reviewing code.",
            available_tools=self.tools
        )
        
        return {
            "main": main_agent,
            "planning": planning_agent,
            "research": research_agent,
            "coding": coding_agent
        }
    
    def _detect_task_type(self, prompt: str) -> str:
        """
        Detect the type of task from a user prompt.
        
        Args:
            prompt: The user's input prompt
            
        Returns:
            The detected task type
        """
        # This is a simple rule-based detection
        # In a real implementation, this would use more sophisticated techniques
        
        prompt_lower = prompt.lower()
        
        if "code" in prompt_lower or "function" in prompt_lower or "program" in prompt_lower:
            return "code_generation"
        elif "plan" in prompt_lower or "steps" in prompt_lower or "how to" in prompt_lower:
            return "planning"
        elif "what" in prompt_lower or "who" in prompt_lower or "when" in prompt_lower or "where" in prompt_lower:
            return "question_answering"
        elif "search" in prompt_lower or "find" in prompt_lower or "look up" in prompt_lower:
            return "web_search"
        else:
            return "general"
    
    def _select_agent(self, task_type: str) -> str:
        """
        Select the best agent for a task type.
        
        Args:
            task_type: The type of task
            
        Returns:
            The ID of the selected agent
        """
        if task_type == "code_generation":
            return "coding"
        elif task_type == "planning":
            return "planning"
        elif task_type == "web_search" or task_type == "question_answering":
            return "research"
        else:
            return "main"
    
    async def process_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Process a user prompt with adaptive learning.
        
        Args:
            prompt: The user's input prompt
            
        Returns:
            Dictionary with the response and metadata
        """
        start_time = time.time()
        
        # Detect the task type
        task_type = self._detect_task_type(prompt)
        
        # Find similar past interactions
        similar_interactions = self.learning_system.find_similar_interactions(
            prompt=prompt,
            limit=3
        )
        
        # Find applicable templates
        templates = self.learning_system.find_applicable_templates(
            prompt=prompt,
            task_type=task_type
        )
        
        # Select a strategy based on the task type
        strategy = self.learning_system.select_strategy(
            task_type=task_type
        )
        
        # Apply strategy parameters
        # In a real implementation, this would modify the agent's behavior
        # For now, we'll just print the strategy
        print(f"Using strategy for {task_type}: {json.dumps(strategy, indent=2)}")
        
        # Select the best agent for the task
        agent_id = self._select_agent(task_type)
        
        # Process the prompt with the selected agent
        try:
            # Execute the flow
            response = await self.flow.execute(
                prompt=prompt,
                agent_id=agent_id,
                timeline=self.timeline
            )
            
            success = True
            error_message = None
        except Exception as e:
            response = f"Error: {str(e)}"
            success = False
            error_message = str(e)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Get the tools used from the timeline
        tools_used = []
        for event in self.timeline.events:
            if event.type == "tool" and event.data.get("tool_name"):
                tool_name = event.data["tool_name"]
                if tool_name not in tools_used:
                    tools_used.append(tool_name)
        
        # Record the interaction
        interaction = self.learning_system.record_interaction(
            user_prompt=prompt,
            bot_response=response,
            task_type=task_type,
            tools_used=tools_used,
            success=success,
            execution_time=execution_time,
            error_message=error_message,
            metadata={
                "agent_id": agent_id,
                "strategy": strategy
            }
        )
        
        # Update strategy performance
        self.learning_system.update_strategy_performance(
            task_type=task_type,
            success=success,
            execution_time=execution_time
        )
        
        # If there was an error, try to self-heal
        if not success and error_message:
            self_healing_tool = self.tools.get_tool("self_healing")
            if self_healing_tool:
                # Detect the error
                detection_result = await self_healing_tool.execute(
                    command="detect",
                    error_message=error_message,
                    tool_name=tools_used[0] if tools_used else None
                )
                
                # Suggest fixes
                suggestion_result = await self_healing_tool.execute(
                    command="suggest",
                    error_message=error_message,
                    tool_name=tools_used[0] if tools_used else None
                )
                
                # Include self-healing information in the response
                response += f"\n\nError detected: {detection_result.output}\n\nSuggested fixes: {suggestion_result.output}"
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })
        
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # Infer implicit feedback if this is not the first interaction
        if len(self.conversation_history) > 2:
            previous_interaction_id = None
            for prev_interaction in self.learning_system.memory_store.search_interactions(limit=1):
                if prev_interaction.id != interaction.id:
                    previous_interaction_id = prev_interaction.id
                    break
            
            if previous_interaction_id:
                implicit_feedback = self.learning_system.infer_feedback(
                    current_interaction_id=interaction.id,
                    previous_interaction_id=previous_interaction_id,
                    user_action=prompt
                )
        
        return {
            "response": response,
            "task_type": task_type,
            "agent_id": agent_id,
            "execution_time": execution_time,
            "success": success,
            "tools_used": tools_used,
            "interaction_id": interaction.id
        }
    
    def record_feedback(
        self,
        interaction_id: str,
        content: str,
        rating: Optional[int] = None,
        positive: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Record explicit feedback from a user.
        
        Args:
            interaction_id: ID of the interaction the feedback is for
            content: Feedback content
            rating: Optional numerical rating (e.g., 1-5)
            positive: Optional boolean indicating if the feedback is positive
            
        Returns:
            Dictionary with the created feedback record
        """
        feedback = self.learning_system.record_feedback(
            interaction_id=interaction_id,
            content=content,
            rating=rating,
            positive=positive
        )
        
        return feedback
    
    def generate_performance_report(self) -> str:
        """
        Generate a comprehensive performance report.
        
        Returns:
            Formatted report as a string
        """
        return self.learning_system.generate_performance_report()
    
    def generate_feedback_report(self) -> str:
        """
        Generate a comprehensive feedback report.
        
        Returns:
            Formatted report as a string
        """
        return self.learning_system.generate_feedback_report()
    
    def save_state(self, directory: str) -> None:
        """
        Save the state of the learning system to files.
        
        Args:
            directory: Directory to save the state to
        """
        self.learning_system.save_state(directory)
    
    def load_state(self, directory: str) -> None:
        """
        Load the state of the learning system from files.
        
        Args:
            directory: Directory to load the state from
        """
        self.learning_system.load_state(directory)


async def main():
    """Run an example conversation with Adaptive Nexagent."""
    print("=== Adaptive Nexagent Example ===")
    
    # Create the Adaptive Nexagent
    nexagent = AdaptiveNexagent()
    
    # Process some prompts
    prompts = [
        "What is the capital of France?",
        "Write a Python function to calculate the factorial of a number.",
        "Create a plan for building a personal website.",
        "What is the capital of Germany?",
        "Can you improve the factorial function to handle negative numbers?"
    ]
    
    for i, prompt in enumerate(prompts):
        print(f"\n=== Prompt {i+1}: {prompt} ===")
        
        result = await nexagent.process_prompt(prompt)
        
        print(f"Response: {result['response']}")
        print(f"Task Type: {result['task_type']}")
        print(f"Agent: {result['agent_id']}")
        print(f"Execution Time: {result['execution_time']:.2f} seconds")
        print(f"Success: {result['success']}")
        print(f"Tools Used: {', '.join(result['tools_used'])}")
        
        # Add some feedback
        if i == 0:
            feedback = nexagent.record_feedback(
                interaction_id=result['interaction_id'],
                content="Great answer, thank you!",
                rating=5,
                positive=True
            )
            print(f"Recorded positive feedback: {feedback}")
        elif i == 1:
            feedback = nexagent.record_feedback(
                interaction_id=result['interaction_id'],
                content="The code works, but it could be more efficient.",
                rating=3,
                positive=None
            )
            print(f"Recorded neutral feedback: {feedback}")
    
    # Generate reports
    print("\n=== Performance Report ===")
    performance_report = nexagent.generate_performance_report()
    print(performance_report)
    
    print("\n=== Feedback Report ===")
    feedback_report = nexagent.generate_feedback_report()
    print(feedback_report)
    
    # Save the state
    state_dir = "nexagent_state"
    print(f"\nSaving state to {state_dir}...")
    nexagent.save_state(state_dir)
    
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
