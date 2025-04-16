# Nexagent Tools Reference

## Overview

Nexagent provides a powerful set of tools that agents can use to perform various tasks. This document provides a comprehensive reference for all available tools, their capabilities, and usage examples.

## Browser Tools

### EnhancedBrowserTool

The core data extraction component with advanced capabilities for navigating and extracting content from web pages.

#### Key Actions

| Action | Description |
|--------|-------------|
| `navigate` | Navigate to a URL |
| `navigate_and_extract` | Navigate and extract content in one step |
| `stealth_mode` | Enable/disable stealth operation |
| `random_delay` | Set random delays between actions |
| `extract_structured` | Extract structured data from the source |
| `get_text` | Get text content from the current source |
| `get_html` | Get HTML content from the current source |

#### Example Usage

```python
from nexagent.tool.enhanced_browser_tool import EnhancedBrowserTool

async def extract_data():
    browser = EnhancedBrowserTool()

    try:
        # Enable stealth mode to avoid detection
        await browser.execute(action="stealth_mode", enable=True)

        # Navigate to a URL
        result = await browser.execute(
            action="navigate_and_extract",
            url="https://example.com",
            extract_type="comprehensive"
        )

        print(result.output)
    finally:
        await browser.close()
```

### FallbackBrowserTool

A fallback browser implementation that can be used when the primary browser encounters issues.

### WebUIBrowserTool

A browser tool specifically designed for interacting with web UIs, with capabilities for form filling, button clicking, and other UI interactions.

## Terminal Tools

### TerminalTool

Allows execution of shell commands.

#### Example Usage

```python
from nexagent.tool.terminal import TerminalTool

async def run_command():
    terminal = TerminalTool()

    result = await terminal.execute(
        command="ls -la"
    )

    print(result.output)
```

### EnhancedTerminalTool

An enhanced version of the terminal tool with additional capabilities for handling complex command sequences and output processing.

### LongRunningCommandTool

Specialized tool for executing long-running commands with progress monitoring and graceful termination.

## Code Analysis Tools

### CodeAnalyzerTool

Provides code analysis capabilities, including code quality assessment, test suggestion, and refactoring recommendations.

#### Key Features

- Code quality analysis
- Test suggestion
- Refactoring recommendations
- Security vulnerability detection

## Data Processing Tools

### DataProcessorTool

Provides data processing capabilities, including data transformation, filtering, and analysis.

### FileSaverTool

Allows saving data to files in various formats.

### FinancialDataExtractorTool

Specialized tool for extracting and processing financial data.

## Planning Tools

### PlanningTool

Provides planning capabilities for breaking down complex tasks into manageable steps.

#### Key Commands

| Command | Description |
|---------|-------------|
| `create` | Create a new execution plan |
| `get` | Get the details of an existing plan |
| `update` | Update an existing plan |
| `set_active` | Set a plan as the active plan |

#### Example Usage

```python
from nexagent.tool.planning import PlanningTool

async def create_task_plan():
    planning = PlanningTool()

    result = await planning.execute(
        command="create_plan",
        task="Build a web scraper for product information",
        steps=[
            "Set up the project structure",
            "Install required dependencies",
            "Create the main scraper class",
            "Implement navigation logic",
            "Implement data extraction logic",
            "Add error handling and retries",
            "Test the scraper on target website"
        ]
    )

    plan_id = result.output.split("Plan ID: ")[1].split("\n")[0]
    print(f"Created plan with ID: {plan_id}")
```

## Search Tools

### WebSearchTool

Provides web search capabilities using various search engines.

## Utility Tools

### ConversationManagerTool

Manages conversation history and context.

### ErrorHandlerTool

Provides error handling and recovery capabilities.

### TaskAnalyticsTool

Provides analytics on task execution performance.

## Tool Collection

The `ToolCollection` class provides a way to group and manage multiple tools as a single unit.

```python
from nexagent.tool.tool_collection import ToolCollection
from nexagent.tool.terminal import TerminalTool
from nexagent.tool.enhanced_browser_tool import EnhancedBrowserTool

async def use_tool_collection():
    tools = ToolCollection([
        TerminalTool(),
        EnhancedBrowserTool()
    ])

    # Use the terminal tool from the collection
    result = await tools.execute(
        tool_name="terminal",
        command="ls -la"
    )

    print(result.output)
```

## Creating Custom Tools

You can create custom tools by extending the `BaseTool` class:

```python
from nexagent.tool.base import BaseTool, ToolResult

class MyCustomTool(BaseTool):
    name = "my_custom_tool"
    description = "A custom tool for specific tasks"

    async def _execute(self, **kwargs):
        # Implement your tool logic here
        result = "Custom tool execution result"
        return ToolResult(output=result)
```

## Best Practices

- **Tool Selection**: Choose the most appropriate tool for the task at hand
- **Error Handling**: Always handle potential errors from tool execution
- **Resource Management**: Close resources (like browsers) when done using them
- **Timeout Management**: Set appropriate timeouts for operations that might take a long time
- **Fallback Mechanisms**: Implement fallback mechanisms for critical operations