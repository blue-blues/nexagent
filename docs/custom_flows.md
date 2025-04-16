# Developing Custom Flows with Nexagent

## Overview

Flows in Nexagent define the execution patterns and coordination between agents and tools. This guide explains how to develop custom flows that implement specialized processing patterns.

## Flow Architecture

In Nexagent, flows are responsible for:

1. Coordinating the execution of agents
2. Managing the flow of information between agents and tools
3. Implementing specialized processing patterns

All flows inherit from the `BaseFlow` class and implement the `execute` method.

## Creating a Custom Flow

### Step 1: Create a New Flow Class

Create a new Python file in the `app/flow` directory for your custom flow:

```python
# app/flow/my_custom_flow.py
from typing import Optional

from app.flow.base import BaseFlow
from app.llm import LLM

class MyCustomFlow(BaseFlow):
    """A custom flow implementing a specialized processing pattern."""
    
    def __init__(self, llm: Optional[LLM] = None):
        super().__init__(llm=llm)
        self.name = "my_custom_flow"
        self.description = "A custom flow implementing a specialized processing pattern"
        
        # Initialize flow-specific state
        self.state = {}
```

### Step 2: Implement Core Methods

Implement the core methods for your flow:

```python
# app/flow/my_custom_flow.py (continued)

async def initialize(self):
    """Initialize the flow with necessary agents and configuration."""
    from app.agent.software_dev_agent import SoftwareDevAgent
    from app.agent.manus_agent import ManusAgent
    
    # Initialize agents
    self.software_dev_agent = SoftwareDevAgent(llm=self.llm)
    self.manus_agent = ManusAgent(llm=self.llm)
    
    # Initialize agents
    await self.software_dev_agent.initialize()
    await self.manus_agent.initialize()
    
    # Mark as initialized
    self.initialized = True

async def execute(self, prompt: str) -> str:
    """Execute the flow with the provided prompt."""
    # Initialize the flow if not already initialized
    if not self.initialized:
        await self.initialize()
    
    # Implement your custom flow logic here
    # For example, a flow that processes the prompt in stages
    
    # Stage 1: Initial analysis
    analysis_prompt = f"Analyze the following request and identify key components:\n\n{prompt}"
    analysis_result = await self.manus_agent.process(analysis_prompt)
    
    # Stage 2: Process with specialized agent based on analysis
    if "code" in analysis_result.lower() or "programming" in analysis_result.lower():
        # Use software development agent for code-related tasks
        return await self.software_dev_agent.process(prompt)
    else:
        # Use general-purpose agent for other tasks
        return await self.manus_agent.process(prompt)
```

### Step 3: Implement Helper Methods

Implement helper methods for your flow:

```python
# app/flow/my_custom_flow.py (continued)

async def analyze_prompt(self, prompt: str) -> dict:
    """Analyze the prompt to determine processing strategy."""
    analysis_prompt = f"Analyze the following request and extract these components:\n\n"
    analysis_prompt += f"1. Main task type (e.g., code generation, data analysis, general question)\n"
    analysis_prompt += f"2. Key entities or concepts mentioned\n"
    analysis_prompt += f"3. Required tools or resources\n\n"
    analysis_prompt += f"Request: {prompt}\n\n"
    analysis_prompt += f"Respond in JSON format with these keys: task_type, entities, required_tools"
    
    analysis_result = await self.manus_agent.process(analysis_prompt)
    
    try:
        import json
        return json.loads(analysis_result)
    except:
        # Fallback if JSON parsing fails
        return {
            "task_type": "unknown",
            "entities": [],
            "required_tools": []
        }

async def execute_with_retry(self, agent, prompt: str, max_retries: int = 3) -> str:
    """Execute with retry logic."""
    retries = 0
    while retries < max_retries:
        try:
            return await agent.process(prompt)
        except Exception as e:
            retries += 1
            if retries >= max_retries:
                return f"Error processing request after {max_retries} attempts: {str(e)}"
```

## Integrating Your Custom Flow

### Option 1: Direct Usage

Use your custom flow directly:

```python
from app.flow.my_custom_flow import MyCustomFlow

async def main():
    flow = MyCustomFlow()
    response = await flow.execute("Your prompt here")
    print(response)
```

### Option 2: Integration with Flow Factory

Integrate your custom flow with the Flow Factory by modifying `app/flow/flow_factory.py`:

```python
# app/flow/flow_factory.py

from app.flow.my_custom_flow import MyCustomFlow

class FlowFactory:
    # ... existing code ...
    
    @staticmethod
    def create_flow(flow_type: str, llm=None):
        # ... existing flow types ...
        
        if flow_type == "my_custom_flow":
            return MyCustomFlow(llm=llm)
        
        # ... existing fallback logic ...
```

## Advanced Flow Patterns

### Pipeline Flow

Implement a pipeline flow that processes data through multiple stages:

```python
# app/flow/pipeline_flow.py

from typing import List, Optional

from app.flow.base import BaseFlow
from app.agent.base import BaseAgent
from app.llm import LLM

class PipelineFlow(BaseFlow):
    """A flow that processes data through a pipeline of agents."""
    
    def __init__(self, llm: Optional[LLM] = None):
        super().__init__(llm=llm)
        self.name = "pipeline_flow"
        self.description = "Processes data through a pipeline of agents"
        self.pipeline = []
    
    def add_stage(self, agent: BaseAgent, description: str):
        """Add a stage to the pipeline."""
        self.pipeline.append({
            "agent": agent,
            "description": description
        })
    
    async def initialize(self):
        """Initialize the flow with necessary agents and configuration."""
        # Initialize all agents in the pipeline
        for stage in self.pipeline:
            await stage["agent"].initialize()
        
        # Mark as initialized
        self.initialized = True
    
    async def execute(self, prompt: str) -> str:
        """Execute the flow with the provided prompt."""
        # Initialize the flow if not already initialized
        if not self.initialized:
            await self.initialize()
        
        # Process through the pipeline
        current_input = prompt
        results = []
        
        for i, stage in enumerate(self.pipeline):
            agent = stage["agent"]
            description = stage["description"]
            
            # Process with the current stage
            result = await agent.process(current_input)
            
            # Store the result
            results.append({
                "stage": i + 1,
                "description": description,
                "result": result
            })
            
            # Use the result as input for the next stage
            current_input = result
        
        # Return the final result
        return current_input
```

### Parallel Flow

Implement a parallel flow that processes data through multiple agents in parallel:

```python
# app/flow/parallel_flow.py

from typing import Dict, List, Optional
import asyncio

from app.flow.base import BaseFlow
from app.agent.base import BaseAgent
from app.llm import LLM

class ParallelFlow(BaseFlow):
    """A flow that processes data through multiple agents in parallel."""
    
    def __init__(self, llm: Optional[LLM] = None):
        super().__init__(llm=llm)
        self.name = "parallel_flow"
        self.description = "Processes data through multiple agents in parallel"
        self.agents = {}
    
    def add_agent(self, name: str, agent: BaseAgent):
        """Add an agent to the parallel flow."""
        self.agents[name] = agent
    
    async def initialize(self):
        """Initialize the flow with necessary agents and configuration."""
        # Initialize all agents
        for agent in self.agents.values():
            await agent.initialize()
        
        # Mark as initialized
        self.initialized = True
    
    async def execute(self, prompt: str) -> Dict[str, str]:
        """Execute the flow with the provided prompt."""
        # Initialize the flow if not already initialized
        if not self.initialized:
            await self.initialize()
        
        # Process with all agents in parallel
        tasks = {}
        for name, agent in self.agents.items():
            tasks[name] = asyncio.create_task(agent.process(prompt))
        
        # Wait for all tasks to complete
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                results[name] = f"Error: {str(e)}"
        
        return results
```

## Testing Your Custom Flow

Create tests for your custom flow:

```python
# tests/test_my_custom_flow.py

import asyncio
import unittest
from unittest.mock import patch, MagicMock

from app.flow.my_custom_flow import MyCustomFlow
from app.agent.software_dev_agent import SoftwareDevAgent
from app.agent.manus_agent import ManusAgent

class TestMyCustomFlow(unittest.TestCase):
    def setUp(self):
        self.flow = MyCustomFlow()
        self.flow.software_dev_agent = MagicMock(spec=SoftwareDevAgent)
        self.flow.manus_agent = MagicMock(spec=ManusAgent)
        self.flow.initialized = True
    
    async def async_test_execute_code_task(self):
        # Mock the manus_agent to return an analysis that indicates code
        self.flow.manus_agent.process.return_value = "This is a code-related task"
        self.flow.software_dev_agent.process.return_value = "Code solution"
        
        result = await self.flow.execute("Generate a Python function")
        
        self.assertEqual(result, "Code solution")
        self.flow.manus_agent.process.assert_called_once()
        self.flow.software_dev_agent.process.assert_called_once_with("Generate a Python function")
    
    def test_execute_code_task(self):
        asyncio.run(self.async_test_execute_code_task())
    
    async def async_test_execute_general_task(self):
        # Mock the manus_agent to return an analysis that indicates general task
        self.flow.manus_agent.process.side_effect = ["This is a general task", "General solution"]
        
        result = await self.flow.execute("What is the capital of France?")
        
        self.assertEqual(result, "General solution")
        self.assertEqual(self.flow.manus_agent.process.call_count, 2)
        self.flow.software_dev_agent.process.assert_not_called()
    
    def test_execute_general_task(self):
        asyncio.run(self.async_test_execute_general_task())

if __name__ == "__main__":
    unittest.main()
```

## Best Practices

1. **Clear Responsibility**: Each flow should have a clear, focused purpose
2. **Error Handling**: Implement robust error handling and provide clear error messages
3. **Documentation**: Document your flow's capabilities, behavior, and usage examples
4. **Testing**: Write comprehensive tests for your flow
5. **Performance**: Optimize your flow for performance, especially for resource-intensive operations
6. **Modularity**: Design your flow to be modular and reusable
7. **State Management**: Carefully manage state across multiple interactions

## Conclusion

By following this guide, you can create custom flows that implement specialized processing patterns in Nexagent. The modular architecture of Nexagent makes it easy to integrate your custom flows into the existing framework.