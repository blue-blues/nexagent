# Developing Custom Agents with Nexagent

## Overview

Nexagent's architecture is designed to be extensible, allowing developers to create custom agents for specialized tasks. This guide explains how to develop custom agents that integrate seamlessly with the Nexagent framework.

## Agent Architecture

In Nexagent, agents are responsible for processing user requests and generating responses. They can use tools to perform specific actions and maintain state across multiple interactions.

### Agent Components

1. **Base Agent Class**: All agents inherit from the `BaseAgent` class
2. **Prompt Templates**: Define how the agent communicates with the LLM
3. **Tool Integration**: Define which tools the agent can use
4. **State Management**: Manage agent state across interactions

## Creating a Custom Agent

### Step 1: Create a New Agent Class

Create a new Python file in the `app/agent` directory for your custom agent:

```python
# app/agent/my_custom_agent.py
from app.agent.base import BaseAgent
from app.llm import LLM
from app.tool.base import ToolResult

class MyCustomAgent(BaseAgent):
    """A custom agent for specialized tasks."""
    
    def __init__(self, llm: LLM = None):
        super().__init__(llm=llm)
        self.name = "my_custom_agent"
        self.description = "A custom agent for specialized tasks"
        
        # Initialize agent-specific state
        self.state = {}
```

### Step 2: Define Prompt Templates

Create prompt templates for your agent in the `app/prompt` directory:

```python
# app/prompt/my_custom_agent.py

SYSTEM_PROMPT = """
You are a specialized agent designed to perform specific tasks.

Your capabilities include:
1. [Describe capability 1]
2. [Describe capability 2]
3. [Describe capability 3]

When responding to user requests, follow these guidelines:
- [Guideline 1]
- [Guideline 2]
- [Guideline 3]

{tools_description}
"""

USER_PROMPT = """
{user_input}
"""
```

### Step 3: Implement Core Methods

Implement the core methods for your agent:

```python
# app/agent/my_custom_agent.py (continued)

async def initialize(self):
    """Initialize the agent with necessary tools and configuration."""
    from app.tool.terminal import TerminalTool
    from app.tool.enhanced_browser_tool import EnhancedBrowserTool
    
    # Add tools that your agent will use
    self.add_tool(TerminalTool())
    self.add_tool(EnhancedBrowserTool())
    
    # Load prompt templates
    from app.prompt.my_custom_agent import SYSTEM_PROMPT, USER_PROMPT
    self.system_prompt_template = SYSTEM_PROMPT
    self.user_prompt_template = USER_PROMPT

async def process(self, user_input: str) -> str:
    """Process user input and generate a response."""
    # Initialize the agent if not already initialized
    if not self.initialized:
        await self.initialize()
    
    # Format prompts
    system_prompt = self.format_system_prompt()
    user_prompt = self.format_user_prompt(user_input=user_input)
    
    # Generate response using the LLM
    response = await self.llm.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        functions=self.get_tool_schemas(),
        function_call="auto"
    )
    
    # Process the response
    if response.function_call:
        # Execute the tool and process the result
        tool_result = await self.execute_tool(response.function_call)
        return await self.process_tool_result(user_input, tool_result)
    else:
        # Return the direct response
        return response.content

async def process_tool_result(self, user_input: str, tool_result: ToolResult) -> str:
    """Process the result of a tool execution."""
    # Format prompts with tool result
    system_prompt = self.format_system_prompt()
    user_prompt = self.format_user_prompt(
        user_input=user_input,
        tool_result=tool_result
    )
    
    # Generate response using the LLM
    response = await self.llm.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        functions=self.get_tool_schemas(),
        function_call="auto"
    )
    
    # Process the response
    if response.function_call:
        # Execute another tool and process the result
        new_tool_result = await self.execute_tool(response.function_call)
        return await self.process_tool_result(user_input, new_tool_result)
    else:
        # Return the direct response
        return response.content
```

### Step 4: Implement Helper Methods

Implement helper methods for your agent:

```python
# app/agent/my_custom_agent.py (continued)

def format_system_prompt(self) -> str:
    """Format the system prompt with tools description."""
    tools_description = self.get_tools_description()
    return self.system_prompt_template.format(tools_description=tools_description)

def format_user_prompt(self, user_input: str, tool_result: ToolResult = None) -> str:
    """Format the user prompt with input and optional tool result."""
    if tool_result:
        return self.user_prompt_template.format(
            user_input=user_input,
            tool_name=tool_result.tool_name,
            tool_result=tool_result.output
        )
    else:
        return self.user_prompt_template.format(user_input=user_input)
```

## Integrating Your Custom Agent

### Option 1: Direct Usage

Use your custom agent directly:

```python
from app.agent.my_custom_agent import MyCustomAgent

async def main():
    agent = MyCustomAgent()
    response = await agent.process("Your user input here")
    print(response)
```

### Option 2: Integration with IntegratedFlow

Integrate your custom agent with the IntegratedFlow by modifying `app/flow/integrated_flow.py`:

```python
# app/flow/integrated_flow.py

from app.agent.my_custom_agent import MyCustomAgent

class IntegratedFlow(BaseFlow):
    # ... existing code ...
    
    async def initialize(self):
        # ... existing initialization ...
        
        # Add your custom agent
        self.my_custom_agent = MyCustomAgent(llm=self.llm)
        
        # ... rest of initialization ...
    
    async def execute(self, prompt: str) -> str:
        # ... existing routing logic ...
        
        # Add logic to route to your custom agent when appropriate
        if self._should_use_custom_agent(prompt):
            return await self.my_custom_agent.process(prompt)
        
        # ... existing routing logic ...
    
    def _should_use_custom_agent(self, prompt: str) -> bool:
        """Determine if the custom agent should handle this prompt."""
        # Implement your routing logic here
        return "custom keyword" in prompt.lower()
```

## Advanced Agent Features

### Memory and Context Management

Implement memory and context management for your agent:

```python
# app/agent/my_custom_agent.py (continued)

class MyCustomAgent(BaseAgent):
    # ... existing code ...
    
    def __init__(self, llm: LLM = None):
        super().__init__(llm=llm)
        # ... existing initialization ...
        
        # Initialize memory
        self.memory = []
    
    def add_to_memory(self, user_input: str, response: str):
        """Add an interaction to memory."""
        self.memory.append({
            "user_input": user_input,
            "response": response,
            "timestamp": time.time()
        })
        
        # Keep memory within a reasonable size
        if len(self.memory) > 10:
            self.memory = self.memory[-10:]
    
    def get_memory_context(self) -> str:
        """Get a formatted string of memory context."""
        if not self.memory:
            return ""
        
        context = "Previous interactions:\n"
        for i, entry in enumerate(self.memory):
            context += f"User: {entry['user_input']}\n"
            context += f"Assistant: {entry['response']}\n\n"
        
        return context
    
    def format_system_prompt(self) -> str:
        """Format the system prompt with tools description and memory context."""
        tools_description = self.get_tools_description()
        memory_context = self.get_memory_context()
        
        return self.system_prompt_template.format(
            tools_description=tools_description,
            memory_context=memory_context
        )
    
    async def process(self, user_input: str) -> str:
        # ... existing process method ...
        
        # Store the final response in memory before returning
        final_response = response.content  # or the result of process_tool_result
        self.add_to_memory(user_input, final_response)
        
        return final_response
```

### Specialized Capabilities

Implement specialized capabilities for your agent:

```python
# app/agent/my_custom_agent.py (continued)

class MyCustomAgent(BaseAgent):
    # ... existing code ...
    
    async def analyze_data(self, data: str) -> dict:
        """Analyze data using specialized logic."""
        # Implement your specialized data analysis logic
        result = {}
        
        # Example analysis
        result["word_count"] = len(data.split())
        result["sentiment"] = await self._analyze_sentiment(data)
        
        return result
    
    async def _analyze_sentiment(self, text: str) -> str:
        """Analyze the sentiment of text using the LLM."""
        prompt = f"Analyze the sentiment of the following text and respond with only 'positive', 'neutral', or 'negative':\n\n{text}"
        
        response = await self.llm.generate_response(
            system_prompt="You are a sentiment analysis assistant. Respond with only 'positive', 'neutral', or 'negative'.",
            user_prompt=prompt
        )
        
        return response.content.strip().lower()
```

## Testing Your Custom Agent

Create tests for your custom agent:

```python
# tests/test_my_custom_agent.py

import asyncio
import unittest
from unittest.mock import patch, MagicMock

from app.agent.my_custom_agent import MyCustomAgent
from app.llm import LLM
from app.tool.base import ToolResult

class TestMyCustomAgent(unittest.TestCase):
    def setUp(self):
        self.llm = MagicMock(spec=LLM)
        self.agent = MyCustomAgent(llm=self.llm)
    
    def test_initialization(self):
        self.assertEqual(self.agent.name, "my_custom_agent")
        self.assertEqual(self.agent.description, "A custom agent for specialized tasks")
    
    async def async_test_process(self):
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "Test response"
        mock_response.function_call = None
        
        self.llm.generate_response.return_value = mock_response
        
        # Test process method
        response = await self.agent.process("Test input")
        
        self.assertEqual(response, "Test response")
        self.llm.generate_response.assert_called_once()
    
    def test_process(self):
        asyncio.run(self.async_test_process())
    
    # Add more tests for other methods

if __name__ == "__main__":
    unittest.main()
```

## Best Practices

1. **Separation of Concerns**: Keep your agent focused on a specific domain or task
2. **Prompt Engineering**: Carefully design your prompts to guide the LLM effectively
3. **Error Handling**: Implement robust error handling for tool execution and LLM responses
4. **Testing**: Write comprehensive tests for your agent
5. **Documentation**: Document your agent's capabilities, limitations, and usage examples
6. **Performance Optimization**: Optimize your agent for performance, especially for memory-intensive operations
7. **Security**: Be mindful of security implications, especially when executing tools

## Conclusion

By following this guide, you can create custom agents that extend Nexagent's capabilities to address specialized tasks and domains. The modular architecture of Nexagent makes it easy to integrate your custom agents into the existing framework.