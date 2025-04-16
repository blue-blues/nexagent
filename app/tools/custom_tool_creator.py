"""
Custom Tool Creator for Nexagent.

This module provides functionality for creating custom tools dynamically
based on user specifications.
"""

import json
import os
import re
import inspect
from typing import Dict, List, Optional, Any, Union, Callable
from pathlib import Path

from pydantic import Field, create_model

from app.tool.base import BaseTool, ToolResult
from app.logger import logger


class CustomToolCreator(BaseTool):
    """
    A tool for creating custom tools dynamically based on user specifications.
    
    This tool provides functionality for:
    1. Creating custom tools with specified parameters and behavior
    2. Validating tool definitions
    3. Generating documentation for custom tools
    4. Managing tool collections
    """
    
    name: str = "custom_tool_creator"
    description: str = """
    Creates custom tools dynamically based on user specifications.
    Supports validation, documentation generation, and tool management.
    """
    
    # Dependencies
    required_tools: List[str] = ["create_chat_completion"]
    
    # Storage for created tools
    created_tools: Dict[str, BaseTool] = Field(default_factory=dict)
    
    # Tool templates
    tool_templates: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize tool templates."""
        self.tool_templates = {
            "simple": {
                "description": "A simple tool template with basic functionality",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "Input for the tool"
                        }
                    },
                    "required": ["input"]
                },
                "code_template": """
async def execute(self, *, input: str, **kwargs) -> ToolResult:
    # Process the input
    result = f"Processed: {input}"
    
    return ToolResult(output=result)
"""
            },
            "data_processor": {
                "description": "A tool template for processing data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "description": "Data to process"
                        },
                        "operation": {
                            "type": "string",
                            "description": "Operation to perform on the data"
                        }
                    },
                    "required": ["data", "operation"]
                },
                "code_template": """
async def execute(self, *, data: Dict[str, Any], operation: str, **kwargs) -> ToolResult:
    # Process the data based on the operation
    if operation == "summarize":
        result = f"Summary of data with {len(data)} keys"
    elif operation == "analyze":
        result = f"Analysis of data: {json.dumps(data)}"
    else:
        return ToolResult(error=f"Unknown operation: {operation}")
    
    return ToolResult(output=result)
"""
            },
            "web_utility": {
                "description": "A tool template for web-related utilities",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to process"
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to perform on the URL"
                        }
                    },
                    "required": ["url", "action"]
                },
                "code_template": """
async def execute(self, *, url: str, action: str, **kwargs) -> ToolResult:
    # Process the URL based on the action
    if action == "validate":
        # Simple URL validation
        if url.startswith(("http://", "https://")):
            result = f"Valid URL: {url}"
        else:
            result = f"Invalid URL: {url}"
    elif action == "parse":
        # Parse URL components
        components = {
            "scheme": url.split("://")[0] if "://" in url else "",
            "domain": url.split("://")[1].split("/")[0] if "://" in url else url.split("/")[0],
            "path": "/" + "/".join(url.split("://")[1].split("/")[1:]) if "://" in url and "/" in url.split("://")[1] else "/"
        }
        result = json.dumps(components)
    else:
        return ToolResult(error=f"Unknown action: {action}")
    
    return ToolResult(output=result)
"""
            }
        }
    
    async def execute(
        self,
        *,
        command: str,
        tool_name: Optional[str] = None,
        tool_description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        template: Optional[str] = None,
        custom_code: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        **kwargs
    ) -> ToolResult:
        """
        Execute the custom tool creator.
        
        Args:
            command: The operation to perform (create, list, get, delete, validate, document)
            tool_name: Name of the tool to create or manage
            tool_description: Description of the tool
            parameters: Parameters schema for the tool
            template: Template to use for the tool
            custom_code: Custom code for the tool's execute method
            dependencies: List of tool dependencies
            
        Returns:
            ToolResult with operation result
        """
        try:
            if command == "create":
                if not tool_name:
                    return ToolResult(error="Tool name is required")
                
                if not tool_description:
                    return ToolResult(error="Tool description is required")
                
                result = await self._create_tool(
                    tool_name=tool_name,
                    tool_description=tool_description,
                    parameters=parameters,
                    template=template,
                    custom_code=custom_code,
                    dependencies=dependencies
                )
                return result
            
            elif command == "list":
                result = self._list_tools()
                return result
            
            elif command == "get":
                if not tool_name:
                    return ToolResult(error="Tool name is required")
                
                result = self._get_tool(tool_name)
                return result
            
            elif command == "delete":
                if not tool_name:
                    return ToolResult(error="Tool name is required")
                
                result = self._delete_tool(tool_name)
                return result
            
            elif command == "validate":
                if not tool_name and not custom_code:
                    return ToolResult(error="Either tool name or custom code is required")
                
                result = await self._validate_tool(
                    tool_name=tool_name,
                    custom_code=custom_code
                )
                return result
            
            elif command == "document":
                if not tool_name:
                    return ToolResult(error="Tool name is required")
                
                result = await self._document_tool(tool_name)
                return result
            
            elif command == "list_templates":
                result = self._list_templates()
                return result
            
            else:
                return ToolResult(error=f"Unknown command: {command}. Supported commands: create, list, get, delete, validate, document, list_templates")
        
        except Exception as e:
            logger.error(f"Error in CustomToolCreator: {str(e)}")
            return ToolResult(error=f"Error executing custom tool creator: {str(e)}")
    
    async def _create_tool(
        self,
        tool_name: str,
        tool_description: str,
        parameters: Optional[Dict[str, Any]] = None,
        template: Optional[str] = None,
        custom_code: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ) -> ToolResult:
        """
        Create a custom tool.
        
        Args:
            tool_name: Name of the tool to create
            tool_description: Description of the tool
            parameters: Parameters schema for the tool
            template: Template to use for the tool
            custom_code: Custom code for the tool's execute method
            dependencies: List of tool dependencies
            
        Returns:
            ToolResult with creation result
        """
        # Check if the tool already exists
        if tool_name in self.created_tools:
            return ToolResult(error=f"Tool '{tool_name}' already exists")
        
        # Normalize tool name
        tool_name = tool_name.lower().replace(" ", "_")
        
        # Get the code for the execute method
        if template:
            if template not in self.tool_templates:
                return ToolResult(error=f"Template '{template}' not found")
            
            execute_code = self.tool_templates[template]["code_template"]
            
            # If no parameters are provided, use the template's parameters
            if not parameters:
                parameters = self.tool_templates[template]["parameters"]
        elif custom_code:
            execute_code = custom_code
        else:
            # Use a simple default implementation
            execute_code = """
async def execute(self, **kwargs) -> ToolResult:
    return ToolResult(output="Custom tool executed successfully")
"""
        
        # Create the tool class dynamically
        try:
            # Create a namespace for the execute method
            namespace = {}
            exec(f"from typing import Dict, List, Optional, Any\nfrom app.tool.base import ToolResult\nimport json\n{execute_code}", namespace)
            execute_method = namespace["execute"]
            
            # Create the tool class
            tool_class = type(
                f"Custom{tool_name.title().replace('_', '')}Tool",
                (BaseTool,),
                {
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": parameters,
                    "required_tools": dependencies or [],
                    "execute": execute_method
                }
            )
            
            # Create an instance of the tool
            tool_instance = tool_class()
            
            # Store the tool
            self.created_tools[tool_name] = tool_instance
            
            return ToolResult(
                output=json.dumps({
                    "success": True,
                    "message": f"Tool '{tool_name}' created successfully",
                    "tool": {
                        "name": tool_name,
                        "description": tool_description,
                        "parameters": parameters,
                        "dependencies": dependencies or []
                    }
                })
            )
        
        except Exception as e:
            logger.error(f"Error creating tool: {str(e)}")
            return ToolResult(error=f"Error creating tool: {str(e)}")
    
    def _list_tools(self) -> ToolResult:
        """
        List all created tools.
        
        Returns:
            ToolResult with list of tools
        """
        tools = []
        for name, tool in self.created_tools.items():
            tools.append({
                "name": name,
                "description": tool.description,
                "parameters": tool.parameters,
                "dependencies": tool.required_tools
            })
        
        return ToolResult(
            output=json.dumps({
                "tools": tools,
                "count": len(tools)
            })
        )
    
    def _get_tool(self, tool_name: str) -> ToolResult:
        """
        Get a specific tool.
        
        Args:
            tool_name: Name of the tool to get
            
        Returns:
            ToolResult with tool details
        """
        if tool_name not in self.created_tools:
            return ToolResult(error=f"Tool '{tool_name}' not found")
        
        tool = self.created_tools[tool_name]
        
        return ToolResult(
            output=json.dumps({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "dependencies": tool.required_tools
            })
        )
    
    def _delete_tool(self, tool_name: str) -> ToolResult:
        """
        Delete a specific tool.
        
        Args:
            tool_name: Name of the tool to delete
            
        Returns:
            ToolResult with deletion result
        """
        if tool_name not in self.created_tools:
            return ToolResult(error=f"Tool '{tool_name}' not found")
        
        del self.created_tools[tool_name]
        
        return ToolResult(
            output=json.dumps({
                "success": True,
                "message": f"Tool '{tool_name}' deleted successfully"
            })
        )
    
    async def _validate_tool(
        self,
        tool_name: Optional[str] = None,
        custom_code: Optional[str] = None
    ) -> ToolResult:
        """
        Validate a tool.
        
        Args:
            tool_name: Name of the tool to validate
            custom_code: Custom code to validate
            
        Returns:
            ToolResult with validation result
        """
        if tool_name:
            if tool_name not in self.created_tools:
                return ToolResult(error=f"Tool '{tool_name}' not found")
            
            tool = self.created_tools[tool_name]
            
            # Validate the tool by calling it with minimal arguments
            try:
                # Create a minimal set of arguments based on the tool's parameters
                args = {}
                if tool.parameters and "properties" in tool.parameters:
                    for param_name, param_info in tool.parameters["properties"].items():
                        if param_info.get("type") == "string":
                            args[param_name] = "test"
                        elif param_info.get("type") == "number":
                            args[param_name] = 0
                        elif param_info.get("type") == "boolean":
                            args[param_name] = False
                        elif param_info.get("type") == "object":
                            args[param_name] = {}
                        elif param_info.get("type") == "array":
                            args[param_name] = []
                
                # Call the tool with minimal arguments
                result = await tool.execute(**args)
                
                return ToolResult(
                    output=json.dumps({
                        "success": True,
                        "message": f"Tool '{tool_name}' validated successfully",
                        "result": str(result)
                    })
                )
            
            except Exception as e:
                logger.error(f"Error validating tool: {str(e)}")
                return ToolResult(error=f"Error validating tool: {str(e)}")
        
        elif custom_code:
            # Validate the custom code by executing it in a controlled environment
            try:
                # Create a namespace for the execute method
                namespace = {}
                exec(f"from typing import Dict, List, Optional, Any\nfrom app.tool.base import ToolResult\nimport json\n{custom_code}", namespace)
                
                if "execute" not in namespace:
                    return ToolResult(error="Custom code must define an 'execute' method")
                
                execute_method = namespace["execute"]
                
                # Check if the execute method has the correct signature
                sig = inspect.signature(execute_method)
                if "self" not in sig.parameters:
                    return ToolResult(error="Execute method must have 'self' as the first parameter")
                
                return ToolResult(
                    output=json.dumps({
                        "success": True,
                        "message": "Custom code validated successfully"
                    })
                )
            
            except Exception as e:
                logger.error(f"Error validating custom code: {str(e)}")
                return ToolResult(error=f"Error validating custom code: {str(e)}")
        
        else:
            return ToolResult(error="Either tool_name or custom_code is required")
    
    async def _document_tool(self, tool_name: str) -> ToolResult:
        """
        Generate documentation for a tool.
        
        Args:
            tool_name: Name of the tool to document
            
        Returns:
            ToolResult with documentation
        """
        if tool_name not in self.created_tools:
            return ToolResult(error=f"Tool '{tool_name}' not found")
        
        tool = self.created_tools[tool_name]
        
        # Use the LLM to generate documentation
        create_chat_completion = self.get_tool("create_chat_completion")
        if not create_chat_completion:
            return ToolResult(error="create_chat_completion tool not available")
        
        # Prepare the prompt
        prompt = f"""
        Generate comprehensive documentation for the following custom tool:
        
        Tool Name: {tool.name}
        Description: {tool.description}
        Parameters: {json.dumps(tool.parameters, indent=2) if tool.parameters else "None"}
        Dependencies: {tool.required_tools if tool.required_tools else "None"}
        
        Please include:
        1. A high-level overview of what the tool does
        2. Detailed parameter descriptions
        3. Usage examples
        4. Any dependencies or requirements
        
        Format the documentation in Markdown.
        """
        
        # Generate the documentation
        result = await create_chat_completion.execute(
            messages=[{"role": "user", "content": prompt}]
        )
        
        if result.error:
            return ToolResult(error=f"Error generating documentation: {result.error}")
        
        # Extract the documentation from the response
        response = json.loads(result.output)
        documentation = response["choices"][0]["message"]["content"]
        
        return ToolResult(output=documentation)
    
    def _list_templates(self) -> ToolResult:
        """
        List all available tool templates.
        
        Returns:
            ToolResult with list of templates
        """
        templates = []
        for name, template in self.tool_templates.items():
            templates.append({
                "name": name,
                "description": template["description"],
                "parameters": template["parameters"]
            })
        
        return ToolResult(
            output=json.dumps({
                "templates": templates,
                "count": len(templates)
            })
        )
