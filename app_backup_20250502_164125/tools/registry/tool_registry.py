"""
Tool Registry Module

This module provides a registry for tools that can be used by agents.
It allows for dynamic registration and discovery of tools.
"""

from typing import Dict, Any, Callable, List, Optional, Type, Union
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """Definition of a tool that can be used by agents"""
    
    name: str = Field(..., description="Unique name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool")
    function: Callable = Field(..., description="Function that implements the tool")
    category: str = Field("general", description="Category of the tool")
    requires_auth: bool = Field(False, description="Whether the tool requires authentication")
    is_async: bool = Field(True, description="Whether the tool is async")


class ToolRegistry:
    """
    Registry for tools that can be used by agents.
    
    This class provides methods for registering tools and retrieving
    tools by name or category.
    """
    
    # Registry of available tools
    _tools: Dict[str, ToolDefinition] = {}
    
    @classmethod
    def register_tool(cls, tool_def: ToolDefinition) -> None:
        """
        Register a new tool.
        
        Args:
            tool_def: Definition of the tool
            
        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool_def.name in cls._tools:
            raise ValueError(f"Tool already registered: {tool_def.name}")
        
        cls._tools[tool_def.name] = tool_def
    
    @classmethod
    def register_function_as_tool(
        cls,
        name: str,
        description: str,
        function: Callable,
        parameters: Optional[Dict[str, Any]] = None,
        category: str = "general",
        requires_auth: bool = False,
        is_async: bool = True,
    ) -> None:
        """
        Register a function as a tool.
        
        Args:
            name: Unique name for the tool
            description: Description of what the tool does
            function: Function that implements the tool
            parameters: Optional parameters for the tool
            category: Category of the tool
            requires_auth: Whether the tool requires authentication
            is_async: Whether the tool is async
            
        Raises:
            ValueError: If a tool with the same name is already registered
        """
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters or {},
            function=function,
            category=category,
            requires_auth=requires_auth,
            is_async=is_async,
        )
        cls.register_tool(tool_def)
    
    @classmethod
    def get_tool(cls, name: str) -> ToolDefinition:
        """
        Get a tool by name.
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            ToolDefinition: The requested tool
            
        Raises:
            ValueError: If the tool is not found
        """
        if name not in cls._tools:
            raise ValueError(f"Tool not found: {name}")
        
        return cls._tools[name]
    
    @classmethod
    def get_tools_by_category(cls, category: str) -> List[ToolDefinition]:
        """
        Get all tools in a specific category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List[ToolDefinition]: List of tools in the category
        """
        return [tool for tool in cls._tools.values() if tool.category == category]
    
    @classmethod
    def get_all_tools(cls) -> List[ToolDefinition]:
        """
        Get all registered tools.
        
        Returns:
            List[ToolDefinition]: List of all registered tools
        """
        return list(cls._tools.values())
    
    @classmethod
    def get_tool_schema(cls, name: str) -> Dict[str, Any]:
        """
        Get the OpenAI-compatible schema for a tool.
        
        Args:
            name: Name of the tool
            
        Returns:
            Dict[str, Any]: Schema for the tool
            
        Raises:
            ValueError: If the tool is not found
        """
        tool = cls.get_tool(name)
        
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
        }
    
    @classmethod
    def get_all_tool_schemas(cls) -> List[Dict[str, Any]]:
        """
        Get OpenAI-compatible schemas for all registered tools.
        
        Returns:
            List[Dict[str, Any]]: List of schemas for all tools
        """
        return [cls.get_tool_schema(tool.name) for tool in cls.get_all_tools()]
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered tools."""
        cls._tools = {}
