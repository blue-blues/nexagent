# Tool Dependency Resolution System

The Tool Dependency Resolution System allows tools to declare dependencies on other tools and ensures that these dependencies are available before execution.

## Overview

Tools in NexAgent can depend on other tools to function properly. For example, a web research tool might depend on both a web search tool and a browser tool. The dependency resolution system ensures that:

1. All required tools are available before execution
2. Dependencies are validated when tools are added to a collection
3. Circular dependencies are detected and prevented
4. Tools can be executed in a valid order based on their dependencies

## Using the Dependency System

### Declaring Dependencies

To declare dependencies for a tool, specify the `required_tools` attribute in your tool class:

```python
class WebResearchTool(BaseTool):
    name: str = "web_research"
    description: str = "Performs comprehensive web research"
    required_tools: list = ["web_search", "enhanced_browser"]
    
    # ... rest of the tool implementation
```

You can also specify optional dependencies using the `optional_tools` attribute:

```python
class AdvancedAnalysisTool(BaseTool):
    name: str = "advanced_analysis"
    description: str = "Performs advanced data analysis"
    required_tools: list = ["data_processor"]
    optional_tools: list = ["visualization_tool", "statistics_tool"]
    
    # ... rest of the tool implementation
```

### Validating Dependencies

The `ToolCollection` class automatically validates dependencies when tools are added:

```python
# Create a collection with basic tools
tools = ToolCollection(
    WebSearch(),
    EnhancedBrowserTool(),
    Terminal()
)

# Add a tool with dependencies - validation happens automatically
data_processor = DataProcessingTool()
tools.add_tool(data_processor)

# You can also add a tool without validation
tools.add_tool(some_tool, validate_dependencies=False)
```

### Checking Dependencies Before Execution

When executing a tool, dependencies are checked by default:

```python
# Execute with dependency checking (default)
result = await tools.execute(name="web_research", tool_input={"query": "example"})

# Execute without dependency checking
result = await tools.execute(
    name="web_research", 
    tool_input={"query": "example"},
    check_dependencies=False
)
```

### Getting Dependency Information

You can get information about tool dependencies:

```python
# Check if a tool's dependencies are satisfied
is_valid, missing = tools.validate_tool_dependencies("web_research")

# Get all dependencies for a tool (including transitive dependencies)
dependencies = tools.get_tool_dependencies("web_research")

# Get a valid execution order for all tools
execution_order = tools.get_execution_order()
```

## Implementation Details

The dependency resolution system consists of:

1. **BaseTool Extensions**: Added `required_tools` and `optional_tools` attributes to the `BaseTool` class
2. **DependencyResolver**: A class that builds and analyzes the dependency graph
3. **ToolCollection Integration**: Updated to validate and check dependencies

The system uses a directed graph to represent dependencies and performs topological sorting to determine a valid execution order.

## Error Handling

The system provides specific error types for dependency issues:

- `DependencyError`: Base class for all dependency-related errors
- `CircularDependencyError`: Raised when circular dependencies are detected
- `MissingDependencyError`: Raised when a required dependency is missing

## Example

Here's a complete example of using the dependency system:

```python
from app.tool.base import BaseTool, ToolResult
from app.tool.tool_collection import ToolCollection
from app.tool.web_search import WebSearch
from app.tool.enhanced_browser_tool import EnhancedBrowserTool

# Define a tool with dependencies
class WebResearchTool(BaseTool):
    name: str = "web_research"
    description: str = "Performs web research"
    required_tools: list = ["web_search", "enhanced_browser"]
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        # Implementation that uses the required tools
        return ToolResult(output=f"Research results for: {query}")

# Create a tool collection with the required dependencies
tools = ToolCollection(
    WebSearch(),
    EnhancedBrowserTool()
)

# Add the tool with dependencies
tools.add_tool(WebResearchTool())

# Execute the tool - dependencies will be checked automatically
result = await tools.execute(
    name="web_research", 
    tool_input={"query": "dependency resolution"}
)
```

See the `examples/dependency_resolution_demo.py` file for a complete demonstration of the dependency resolution system.
