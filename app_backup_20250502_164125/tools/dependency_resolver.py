"""Tool dependency resolution system for NexAgent.

This module provides classes and functions for managing dependencies between tools,
ensuring that all required tools are available before execution, and resolving
dependency chains.
"""

from typing import Dict, List, Optional, Set, Tuple
import networkx as nx

from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool


class DependencyError(ToolError):
    """Error raised when a tool dependency cannot be satisfied."""
    pass


class CircularDependencyError(DependencyError):
    """Error raised when circular dependencies are detected."""
    pass


class MissingDependencyError(DependencyError):
    """Error raised when a required dependency is missing."""
    pass


class DependencyResolver:
    """Resolves dependencies between tools and ensures they are available."""

    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        
    def build_dependency_graph(self, tools: Dict[str, BaseTool]) -> nx.DiGraph:
        """Build a directed graph of tool dependencies.
        
        Args:
            tools: Dictionary mapping tool names to tool instances
            
        Returns:
            A directed graph representing tool dependencies
            
        Raises:
            CircularDependencyError: If circular dependencies are detected
        """
        # Clear existing graph
        self.dependency_graph.clear()
        
        # Add all tools as nodes
        for tool_name in tools:
            self.dependency_graph.add_node(tool_name)
        
        # Add edges for dependencies
        for tool_name, tool in tools.items():
            if hasattr(tool, 'required_tools') and tool.required_tools:
                for dep_name in tool.required_tools:
                    if dep_name in tools:
                        self.dependency_graph.add_edge(tool_name, dep_name)
                    else:
                        logger.warning(f"Tool '{tool_name}' depends on '{dep_name}', but it's not available")
        
        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            if cycles:
                cycle_str = " -> ".join(cycles[0] + [cycles[0][0]])
                raise CircularDependencyError(f"Circular dependency detected: {cycle_str}")
        except nx.NetworkXNoCycle:
            pass
            
        return self.dependency_graph
    
    def get_dependencies(self, tool_name: str) -> Set[str]:
        """Get all dependencies for a tool, including transitive dependencies.
        
        Args:
            tool_name: Name of the tool to get dependencies for
            
        Returns:
            Set of tool names that the specified tool depends on
        """
        if tool_name not in self.dependency_graph:
            return set()
            
        dependencies = set()
        for dep in self.dependency_graph.successors(tool_name):
            dependencies.add(dep)
            dependencies.update(self.get_dependencies(dep))
            
        return dependencies
    
    def get_execution_order(self) -> List[str]:
        """Get a valid execution order for all tools based on dependencies.
        
        Returns:
            List of tool names in a valid execution order
            
        Raises:
            CircularDependencyError: If circular dependencies prevent ordering
        """
        try:
            # Reverse topological sort gives dependency-first order
            return list(reversed(list(nx.topological_sort(self.dependency_graph))))
        except nx.NetworkXUnfeasible:
            raise CircularDependencyError("Cannot determine execution order due to circular dependencies")
    
    def validate_dependencies(self, tool_name: str, available_tools: Dict[str, BaseTool]) -> Tuple[bool, List[str]]:
        """Check if all dependencies for a tool are available.
        
        Args:
            tool_name: Name of the tool to check dependencies for
            available_tools: Dictionary of available tools
            
        Returns:
            Tuple of (is_valid, missing_dependencies)
        """
        if tool_name not in self.dependency_graph:
            return True, []
            
        dependencies = self.get_dependencies(tool_name)
        missing = [dep for dep in dependencies if dep not in available_tools]
        
        return len(missing) == 0, missing
