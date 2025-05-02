"""
Simplified tool collection class to avoid import issues.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.exceptions import ToolError
from app.logger import logger


class BaseTool:
    """Base class for all tools."""
    
    name: str = "base_tool"
    description: str = "Base tool class"
    
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with the given parameters."""
        raise NotImplementedError("Tool must implement execute method")
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the schema for the tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }


class ToolResult:
    """Result of a tool execution."""
    
    def __init__(self, output: Any = None, error: Optional[str] = None):
        self.output = output
        self.error = error
    
    def __str__(self) -> str:
        if self.error:
            return f"Error: {self.error}"
        return str(self.output)


class ToolFailure(ToolResult):
    """Failure result of a tool execution."""
    
    def __init__(self, error: str):
        super().__init__(None, error)


class ToolCollection:
    """Collection of tools."""
    
    def __init__(self, *tools: BaseTool):
        """Initialize the tool collection with the given tools."""
        self.tools: Dict[str, BaseTool] = {}
        
        # Add the provided tools
        for tool in tools:
            self.add_tool(tool)
    
    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the collection."""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get the schema for all tools."""
        return [tool.get_schema() for tool in self.tools.values()]
    
    def get_available_tool_names(self) -> List[str]:
        """Get the names of all available tools."""
        return list(self.tools.keys())
