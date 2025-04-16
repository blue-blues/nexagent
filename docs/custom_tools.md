# Developing Custom Tools for Nexagent

## Overview

Tools are a fundamental component of the Nexagent framework, allowing agents to perform specific actions. This guide explains how to develop custom tools that extend Nexagent's capabilities.

## Tool Architecture

In Nexagent, tools are modular components that:

1. Receive parameters from agents
2. Execute specific actions
3. Return results to agents

All tools inherit from the `BaseTool` class and implement the `_execute` method.

## Creating a Custom Tool

### Step 1: Create a New Tool Class

Create a new Python file in the `app/tool` directory for your custom tool:

```python
# app/tool/my_custom_tool.py
from typing import Any, Dict, Optional

from app.tool.base import BaseTool, ToolResult

class MyCustomTool(BaseTool):
    """A custom tool for specialized tasks."""
    
    name = "my_custom_tool"
    description = "Performs specialized tasks with the provided parameters."
    
    # Define the schema for the tool parameters
    schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute"
            },
            "parameters": {
                "type": "object",
                "description": "Additional parameters for the command"
            }
        },
        "required": ["command"]
    }
    
    async def _execute(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Execute the tool with the provided parameters."""
        try:
            # Implement your tool logic here
            result = f"Executed command '{command}' with parameters {parameters}"
            
            # Return the result
            return ToolResult(output=result)
        except Exception as e:
            # Handle errors
            error_message = f"Error executing {self.name}: {str(e)}"
            return ToolResult(output=error_message, error=True)
```

### Step 2: Implement Tool Logic

Implement the specific logic for your tool:

```python
# app/tool/my_custom_tool.py (continued)

async def _execute(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> ToolResult:
    """Execute the tool with the provided parameters."""
    try:
        # Initialize parameters if not provided
        if parameters is None:
            parameters = {}
        
        # Handle different commands
        if command == "analyze_text":
            return await self._analyze_text(parameters.get("text", ""))
        elif command == "generate_report":
            return await self._generate_report(
                parameters.get("data", {}),
                parameters.get("format", "text")
            )
        else:
            return ToolResult(
                output=f"Unknown command: {command}",
                error=True
            )
    except Exception as e:
        # Handle errors
        error_message = f"Error executing {self.name}: {str(e)}"
        return ToolResult(output=error_message, error=True)

async def _analyze_text(self, text: str) -> ToolResult:
    """Analyze the provided text."""
    # Implement text analysis logic
    word_count = len(text.split())
    char_count = len(text)
    
    result = {
        "word_count": word_count,
        "character_count": char_count,
        "average_word_length": char_count / word_count if word_count > 0 else 0
    }
    
    return ToolResult(output=str(result))

async def _generate_report(self, data: Dict[str, Any], format: str) -> ToolResult:
    """Generate a report from the provided data."""
    # Implement report generation logic
    if format == "text":
        report = "Report:\n"
        for key, value in data.items():
            report += f"{key}: {value}\n"
    elif format == "json":
        import json
        report = json.dumps(data, indent=2)
    elif format == "html":
        report = "<html><body><h1>Report</h1><ul>"
        for key, value in data.items():
            report += f"<li><strong>{key}:</strong> {value}</li>"
        report += "</ul></body></html>"
    else:
        return ToolResult(
            output=f"Unsupported format: {format}",
            error=True
        )
    
    return ToolResult(output=report)
```

### Step 3: Add Documentation

Add comprehensive documentation for your tool:

```python
# app/tool/my_custom_tool.py (continued)

class MyCustomTool(BaseTool):
    """A custom tool for specialized tasks.
    
    This tool provides capabilities for text analysis and report generation.
    
    Commands:
        - analyze_text: Analyzes the provided text and returns statistics
        - generate_report: Generates a report from the provided data
    
    Examples:
        To analyze text:
        ```
        result = await tool.execute(
            command="analyze_text",
            parameters={"text": "Sample text to analyze"}
        )
        ```
        
        To generate a report:
        ```
        result = await tool.execute(
            command="generate_report",
            parameters={
                "data": {"key1": "value1", "key2": "value2"},
                "format": "json"
            }
        )
        ```
    """
    
    # ... rest of the class ...
```

## Integrating Your Custom Tool

### Option 1: Direct Usage

Use your custom tool directly:

```python
from app.tool.my_custom_tool import MyCustomTool

async def main():
    tool = MyCustomTool()
    
    result = await tool.execute(
        command="analyze_text",
        parameters={"text": "Sample text to analyze"}
    )
    
    print(result.output)
```

### Option 2: Integration with an Agent

Integrate your custom tool with an agent:

```python
# app/agent/my_agent.py

from app.agent.base import BaseAgent
from app.tool.my_custom_tool import MyCustomTool

class MyAgent(BaseAgent):
    async def initialize(self):
        # ... existing initialization ...
        
        # Add your custom tool
        self.add_tool(MyCustomTool())
        
        # ... rest of initialization ...
```

## Advanced Tool Features

### Asynchronous Operations

Implement asynchronous operations in your tool:

```python
# app/tool/my_custom_tool.py (continued)

import aiohttp

class MyCustomTool(BaseTool):
    # ... existing code ...
    
    async def _fetch_data(self, url: str) -> str:
        """Fetch data from a URL asynchronously."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    
    async def _analyze_web_content(self, url: str) -> ToolResult:
        """Analyze content from a web page."""
        try:
            content = await self._fetch_data(url)
            return await self._analyze_text(content)
        except Exception as e:
            return ToolResult(
                output=f"Error fetching or analyzing content from {url}: {str(e)}",
                error=True
            )
```

### State Management

Implement state management in your tool:

```python
# app/tool/my_custom_tool.py (continued)

class MyCustomTool(BaseTool):
    # ... existing code ...
    
    def __init__(self):
        super().__init__()
        self.cache = {}
    
    async def _execute(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> ToolResult:
        # ... existing code ...
        
        if command == "store_data":
            return await self._store_data(
                parameters.get("key", ""),
                parameters.get("value", None)
            )
        elif command == "retrieve_data":
            return await self._retrieve_data(parameters.get("key", ""))
        
        # ... existing code ...
    
    async def _store_data(self, key: str, value: Any) -> ToolResult:
        """Store data in the tool's cache."""
        if not key:
            return ToolResult(
                output="Error: Key cannot be empty",
                error=True
            )
        
        self.cache[key] = value
        return ToolResult(output=f"Data stored with key: {key}")
    
    async def _retrieve_data(self, key: str) -> ToolResult:
        """Retrieve data from the tool's cache."""
        if not key:
            return ToolResult(
                output="Error: Key cannot be empty",
                error=True
            )
        
        if key not in self.cache:
            return ToolResult(
                output=f"Error: No data found for key: {key}",
                error=True
            )
        
        return ToolResult(output=str(self.cache[key]))
```

### Resource Management

Implement resource management in your tool:

```python
# app/tool/my_custom_tool.py (continued)

class MyCustomTool(BaseTool):
    # ... existing code ...
    
    def __init__(self):
        super().__init__()
        self.resources = {}
    
    async def initialize(self):
        """Initialize resources needed by the tool."""
        # Initialize resources
        self.resources["database"] = await self._connect_to_database()
    
    async def cleanup(self):
        """Clean up resources used by the tool."""
        # Clean up resources
        if "database" in self.resources:
            await self.resources["database"].close()
    
    async def _connect_to_database(self):
        """Connect to a database."""
        # Implement database connection logic
        return {"connection": "mock_connection"}
```

## Testing Your Custom Tool

Create tests for your custom tool:

```python
# tests/test_my_custom_tool.py

import asyncio
import unittest
from unittest.mock import patch, MagicMock

from app.tool.my_custom_tool import MyCustomTool
from app.tool.base import ToolResult

class TestMyCustomTool(unittest.TestCase):
    def setUp(self):
        self.tool = MyCustomTool()
    
    async def async_test_analyze_text(self):
        result = await self.tool.execute(
            command="analyze_text",
            parameters={"text": "This is a test"}
        )
        
        self.assertFalse(result.error)
        self.assertIn("word_count", result.output)
        self.assertIn("character_count", result.output)
    
    def test_analyze_text(self):
        asyncio.run(self.async_test_analyze_text())
    
    async def async_test_generate_report(self):
        result = await self.tool.execute(
            command="generate_report",
            parameters={
                "data": {"key1": "value1", "key2": "value2"},
                "format": "json"
            }
        )
        
        self.assertFalse(result.error)
        self.assertIn("key1", result.output)
        self.assertIn("value1", result.output)
    
    def test_generate_report(self):
        asyncio.run(self.async_test_generate_report())
    
    # Add more tests for other methods

if __name__ == "__main__":
    unittest.main()
```

## Best Practices

1. **Single Responsibility**: Each tool should have a clear, focused purpose
2. **Error Handling**: Implement robust error handling and provide clear error messages
3. **Documentation**: Document your tool's capabilities, parameters, and usage examples
4. **Resource Management**: Properly initialize and clean up resources
5. **Testing**: Write comprehensive tests for your tool
6. **Performance**: Optimize your tool for performance, especially for resource-intensive operations
7. **Security**: Be mindful of security implications, especially when handling user input

## Conclusion

By following this guide, you can create custom tools that extend Nexagent's capabilities to address specialized tasks and domains. The modular architecture of Nexagent makes it easy to integrate your custom tools into the existing framework.