"""
Context-Aware Tool Module

This module provides a base class for tools that are aware of context.
It allows tools to read from and write to context.
"""

from typing import Any, Dict, List, Optional, Union
import json
from datetime import datetime
import inspect

from app.core.context import (
    ContextEntry,
    ContextProtocol,
    VersionedContextProtocol,
    ContextManager
)


class ContextAwareTool:
    """
    A base class for tools that are aware of context.
    This class can be used to extend any tool with context management capabilities.
    """
    
    def __init__(
        self,
        tool,
        context: Optional[ContextProtocol] = None,
        auto_add_results: bool = True,
        result_importance: float = 1.0
    ):
        """
        Initialize a context-aware tool.
        
        Args:
            tool: The tool to extend
            context: The context to use
            auto_add_results: Whether to automatically add results to context
            result_importance: The importance to assign to results
        """
        self.tool = tool
        self.context = context
        self.auto_add_results = auto_add_results
        self.result_importance = result_importance
        
        # Get the tool's name
        self.tool_name = getattr(tool, "name", tool.__class__.__name__)
        
        # Wrap the tool's methods
        self._wrap_methods()
    
    def _wrap_methods(self):
        """Wrap the tool's methods to add context awareness."""
        # Get all public methods of the tool
        methods = inspect.getmembers(
            self.tool,
            predicate=lambda x: inspect.ismethod(x) and not x.__name__.startswith('_')
        )
        
        # Wrap each method
        for name, method in methods:
            setattr(self, name, self._create_wrapper(name, method))
    
    def _create_wrapper(self, name, method):
        """Create a wrapper for a method that adds context awareness."""
        def wrapper(*args, **kwargs):
            # Extract context from kwargs if provided
            context = kwargs.pop('context', self.context)
            
            # Call the original method
            result = method(*args, **kwargs)
            
            # Add the result to context if auto_add_results is enabled
            if self.auto_add_results and context:
                self.add_result_to_context(
                    context=context,
                    method_name=name,
                    args=args,
                    kwargs=kwargs,
                    result=result
                )
            
            return result
        
        return wrapper
    
    def add_result_to_context(
        self,
        context: ContextProtocol,
        method_name: str,
        args: tuple,
        kwargs: dict,
        result: Any,
        importance: Optional[float] = None
    ) -> str:
        """
        Add a method result to context.
        
        Args:
            context: The context to add to
            method_name: The name of the method
            args: The arguments passed to the method
            kwargs: The keyword arguments passed to the method
            result: The result of the method
            importance: The importance to assign to the result
            
        Returns:
            The ID of the added entry
        """
        # Convert result to string if it's not already
        if not isinstance(result, str):
            try:
                result_str = json.dumps(result, indent=2)
            except (TypeError, ValueError):
                result_str = str(result)
        else:
            result_str = result
        
        # Create metadata
        metadata = {
            "tool_name": self.tool_name,
            "method_name": method_name,
            "args": [str(arg) for arg in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()}
        }
        
        # Create entry
        entry = ContextEntry(
            content=result_str,
            source=self.tool_name,
            entry_type="tool_result",
            importance=importance or self.result_importance,
            metadata=metadata
        )
        
        # Add to context
        return context.add_entry(entry)
    
    def get_relevant_context(
        self,
        context: ContextProtocol,
        query: str,
        max_entries: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get context entries relevant to a query.
        This is a simple implementation that just returns recent entries.
        In a real implementation, you would use a more sophisticated retrieval method.
        
        Args:
            context: The context to search
            query: The query to search for
            max_entries: Maximum number of entries to return
            
        Returns:
            A list of relevant entries
        """
        # Get recent entries
        entries = context.get_recent_entries(count=max_entries)
        
        # Convert to dictionaries
        return [
            {
                "entry_id": entry.entry_id,
                "content": entry.content,
                "source": entry.source,
                "entry_type": entry.entry_type,
                "timestamp": entry.timestamp.isoformat(),
                "importance": entry.importance,
                "metadata": entry.metadata
            }
            for entry in entries
        ]
