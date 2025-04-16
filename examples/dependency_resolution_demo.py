"""
Dependency Resolution System Demo

This example demonstrates how to use the tool dependency resolution system
to manage dependencies between tools and ensure they are available before execution.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import the app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tool.base import BaseTool, ToolResult
from app.tool.tool_collection import ToolCollection
from app.tool.web_search import WebSearch
from app.tool.enhanced_browser_tool import EnhancedBrowserTool
from app.tool.terminal import Terminal
from app.tool.examples.dependent_tool import WebResearchTool
from app.logger import logger


# Define a simple tool with dependencies for demonstration
class DataProcessingTool(BaseTool):
    """A tool that processes data from multiple sources."""
    
    name: str = "data_processor"
    description: str = "Processes data from terminal and web sources"
    required_tools: list = ["terminal", "web_search"]
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "data_source": {
                "type": "string",
                "description": "The source of the data to process",
            },
        },
        "required": ["data_source"],
    }
    
    async def execute(self, data_source: str, **kwargs) -> ToolResult:
        """Process data from the specified source."""
        return ToolResult(output=f"Processed data from {data_source}")


# Define a tool with circular dependency (for demonstration)
class CircularDependencyTool(BaseTool):
    """A tool with circular dependency for testing."""
    
    name: str = "circular_tool"
    description: str = "This tool has a circular dependency"
    required_tools: list = ["dependent_circular_tool"]
    
    parameters: dict = {}
    
    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(output="This should not execute due to circular dependency")


class DependentCircularTool(BaseTool):
    """A tool that depends on CircularDependencyTool, creating a circular dependency."""
    
    name: str = "dependent_circular_tool"
    description: str = "This tool depends on circular_tool, creating a circular dependency"
    required_tools: list = ["circular_tool"]
    
    parameters: dict = {}
    
    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(output="This should not execute due to circular dependency")


async def run_demo():
    """Run the dependency resolution demo."""
    print("=== Tool Dependency Resolution System Demo ===\n")
    
    # Create a collection with basic tools
    tools = ToolCollection(
        WebSearch(),
        EnhancedBrowserTool(),
        Terminal()
    )
    
    print("1. Basic tool collection created with WebSearch, EnhancedBrowserTool, and Terminal")
    
    # Add a tool with dependencies
    data_processor = DataProcessingTool()
    tools.add_tool(data_processor)
    print(f"2. Added DataProcessingTool with dependencies: {data_processor.required_tools}")
    
    # Check dependencies
    is_valid, missing = tools.validate_tool_dependencies("data_processor")
    print(f"   Dependencies valid: {is_valid}, Missing: {missing}")
    
    # Execute the tool
    print("\n3. Executing DataProcessingTool:")
    result = await tools.execute(name="data_processor", tool_input={"data_source": "local_file"})
    print(f"   Result: {result}")
    
    # Add the WebResearchTool which depends on both WebSearch and EnhancedBrowserTool
    web_research = WebResearchTool()
    tools.add_tool(web_research)
    print(f"\n4. Added WebResearchTool with dependencies: {web_research.required_tools}")
    
    # Check dependencies
    is_valid, missing = tools.validate_tool_dependencies("web_research")
    print(f"   Dependencies valid: {is_valid}, Missing: {missing}")
    
    # Try to execute with a missing dependency
    print("\n5. Creating a new collection with missing dependencies:")
    incomplete_tools = ToolCollection(WebSearch(), Terminal())
    incomplete_tools.add_tool(web_research, validate_dependencies=False)  # Add without validation
    
    # Check dependencies
    is_valid, missing = incomplete_tools.validate_tool_dependencies("web_research")
    print(f"   Dependencies valid: {is_valid}, Missing: {missing}")
    
    # Try to execute
    print("   Executing WebResearchTool with missing dependency:")
    result = await incomplete_tools.execute(
        name="web_research", 
        tool_input={"query": "dependency resolution in software"}
    )
    print(f"   Result: {result}")
    
    # Demonstrate circular dependency detection
    print("\n6. Testing circular dependency detection:")
    try:
        circular_tools = ToolCollection(
            CircularDependencyTool(),
            DependentCircularTool(),
            validate_dependencies=True  # This should trigger the circular dependency detection
        )
        print("   Circular dependency not detected (unexpected)")
    except Exception as e:
        print(f"   Circular dependency detected: {e}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(run_demo())
