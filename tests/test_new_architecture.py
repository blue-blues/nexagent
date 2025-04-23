"""
Tests for the new architecture.

This module contains tests for the new architecture components.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.schema.schema import Message, Role
from app.core.schema.exceptions import NexagentException
from app.tools.registry.tool_registry import ToolRegistry, ToolDefinition


class TestToolRegistry(unittest.TestCase):
    """Tests for the ToolRegistry class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Clear the registry before each test
        ToolRegistry.clear_registry()
    
    def test_register_tool(self):
        """Test registering a tool."""
        # Create a mock tool function
        def mock_tool_function(arg1, arg2):
            return f"{arg1} {arg2}"
        
        # Create a tool definition
        tool_def = ToolDefinition(
            name="mock_tool",
            description="A mock tool for testing",
            function=mock_tool_function,
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "string"}
                },
                "required": ["arg1", "arg2"]
            }
        )
        
        # Register the tool
        ToolRegistry.register_tool(tool_def)
        
        # Check that the tool was registered
        self.assertIn("mock_tool", [tool.name for tool in ToolRegistry.get_all_tools()])
        
        # Get the tool and check its properties
        tool = ToolRegistry.get_tool("mock_tool")
        self.assertEqual(tool.name, "mock_tool")
        self.assertEqual(tool.description, "A mock tool for testing")
        self.assertEqual(tool.function, mock_tool_function)
    
    def test_register_function_as_tool(self):
        """Test registering a function as a tool."""
        # Create a mock tool function
        def mock_tool_function(arg1, arg2):
            return f"{arg1} {arg2}"
        
        # Register the function as a tool
        ToolRegistry.register_function_as_tool(
            name="mock_function_tool",
            description="A mock function tool for testing",
            function=mock_tool_function,
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "string"}
                },
                "required": ["arg1", "arg2"]
            }
        )
        
        # Check that the tool was registered
        self.assertIn("mock_function_tool", [tool.name for tool in ToolRegistry.get_all_tools()])
        
        # Get the tool and check its properties
        tool = ToolRegistry.get_tool("mock_function_tool")
        self.assertEqual(tool.name, "mock_function_tool")
        self.assertEqual(tool.description, "A mock function tool for testing")
        self.assertEqual(tool.function, mock_tool_function)
    
    def test_get_tool_schema(self):
        """Test getting a tool schema."""
        # Create a mock tool function
        def mock_tool_function(arg1, arg2):
            return f"{arg1} {arg2}"
        
        # Register the function as a tool
        ToolRegistry.register_function_as_tool(
            name="schema_tool",
            description="A tool for testing schemas",
            function=mock_tool_function,
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "string"}
                },
                "required": ["arg1", "arg2"]
            }
        )
        
        # Get the tool schema
        schema = ToolRegistry.get_tool_schema("schema_tool")
        
        # Check the schema
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "schema_tool")
        self.assertEqual(schema["function"]["description"], "A tool for testing schemas")
        self.assertEqual(
            schema["function"]["parameters"],
            {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "string"}
                },
                "required": ["arg1", "arg2"]
            }
        )


class TestMessage(unittest.TestCase):
    """Tests for the Message class."""
    
    def test_message_creation(self):
        """Test creating a message."""
        # Create a message
        message = Message(role=Role.USER, content="Hello, world!")
        
        # Check the message properties
        self.assertEqual(message.role, "user")
        self.assertEqual(message.content, "Hello, world!")
        self.assertIsNone(message.tool_calls)
        self.assertIsNone(message.name)
        self.assertIsNone(message.tool_call_id)
    
    def test_message_addition(self):
        """Test adding messages."""
        # Create messages
        message1 = Message(role=Role.USER, content="Hello")
        message2 = Message(role=Role.ASSISTANT, content="World")
        
        # Add messages
        messages = message1 + message2
        
        # Check the result
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].content, "Hello")
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[1].content, "World")
    
    def test_message_addition_with_list(self):
        """Test adding a message to a list."""
        # Create a message and a list
        message = Message(role=Role.USER, content="Hello")
        message_list = [Message(role=Role.ASSISTANT, content="World")]
        
        # Add the message to the list
        messages = message + message_list
        
        # Check the result
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].content, "Hello")
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[1].content, "World")


if __name__ == "__main__":
    unittest.main()
