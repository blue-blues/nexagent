"""Collection classes for managing multiple tools."""
from typing import Any, Dict, List, Set, Tuple

from app.exceptions import ToolError
from app.logger import logger
from app.tools.base import BaseTool, ToolFailure, ToolResult
from app.tools.dependency_resolver import DependencyResolver, DependencyError

# Import tools directly to avoid circular imports
# We'll use dynamic imports in the constructor instead


class ToolCollection:
    """A collection of defined tools with dependency resolution."""

    def __init__(self, *tools: BaseTool, validate_dependencies: bool = True):
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}
        self.dependency_resolver = DependencyResolver()

        # Initialize dependency graph if requested
        if validate_dependencies and tools:
            try:
                self.dependency_resolver.build_dependency_graph(self.tool_map)
                logger.info("Tool dependency graph built successfully")
            except DependencyError as e:
                logger.warning(f"Error building dependency graph: {e}")

        # Default tools dictionary - empty by default
        # Tools will be added dynamically when needed
        self.default_tools = {}

        # Add optional tools if they exist
        try:
            from app.tools.browser import WebSearch
            if WebSearch is not None:
                self.default_tools["web_search"] = WebSearch()
        except ImportError:
            pass

        try:
            from app.tools.browser import FallbackBrowserTool
            if FallbackBrowserTool is not None:
                self.default_tools["fallback_browser"] = FallbackBrowserTool()
        except ImportError:
            pass

        try:
            from app.tools.browser import EnhancedWebBrowser
            if EnhancedWebBrowser is not None:
                self.default_tools["enhanced_web_browser"] = EnhancedWebBrowser()
        except ImportError:
            pass

    def __iter__(self):
        return iter(self.tools)

    def to_params(self) -> List[Dict[str, Any]]:
        return [tool.to_param() for tool in self.tools]

    async def execute(
        self, *, name: str, tool_input: Dict[str, Any] = None, check_dependencies: bool = True
    ) -> ToolResult:
        """Execute a tool with dependency checking.

        Args:
            name: Name of the tool to execute
            tool_input: Input parameters for the tool
            check_dependencies: Whether to check dependencies before execution

        Returns:
            Result of the tool execution
        """
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")

        # Check dependencies if requested
        if check_dependencies and hasattr(tool, 'required_tools') and tool.required_tools:
            is_valid, missing = self.validate_tool_dependencies(name)
            if not is_valid:
                missing_str = ", ".join(missing)
                return ToolFailure(
                    error=f"Tool '{name}' has missing dependencies: {missing_str}"
                )

        try:
            result = await tool(**tool_input)
            return result
        except ToolError as e:
            return ToolFailure(error=e.message)

    async def execute_all(self) -> List[ToolResult]:
        """Execute all tools in the collection sequentially."""
        results = []
        for tool in self.tools:
            try:
                result = await tool()
                results.append(result)
            except ToolError as e:
                results.append(ToolFailure(error=e.message))
        return results

    def get_tool(self, name: str) -> BaseTool:
        return self.tool_map.get(name)

    def add_tool(self, tool: BaseTool, validate_dependencies: bool = True):
        """Add a tool to the collection with optional dependency validation.

        Args:
            tool: The tool to add
            validate_dependencies: Whether to validate dependencies

        Returns:
            Self for method chaining

        Raises:
            DependencyError: If dependency validation fails and validate_dependencies is True
        """
        self.tools += (tool,)
        self.tool_map[tool.name] = tool

        # Update dependency graph
        if validate_dependencies:
            self.dependency_resolver.build_dependency_graph(self.tool_map)

        return self

    def add_tools(self, *tools: BaseTool, validate_dependencies: bool = True):
        """Add multiple tools to the collection.

        Args:
            *tools: Tools to add
            validate_dependencies: Whether to validate dependencies after adding all tools

        Returns:
            Self for method chaining
        """
        # Add tools without validation first
        for tool in tools:
            self.add_tool(tool, validate_dependencies=False)

        # Then validate all dependencies at once if requested
        if validate_dependencies:
            self.dependency_resolver.build_dependency_graph(self.tool_map)

        return self

    def validate_tool_dependencies(self, tool_name: str) -> Tuple[bool, List[str]]:
        """Check if all dependencies for a tool are available.

        Args:
            tool_name: Name of the tool to check

        Returns:
            Tuple of (is_valid, missing_dependencies)
        """
        return self.dependency_resolver.validate_dependencies(tool_name, self.tool_map)

    def get_tool_dependencies(self, tool_name: str) -> Set[str]:
        """Get all dependencies for a tool.

        Args:
            tool_name: Name of the tool to get dependencies for

        Returns:
            Set of tool names that the specified tool depends on
        """
        return self.dependency_resolver.get_dependencies(tool_name)

    def get_execution_order(self) -> List[str]:
        """Get a valid execution order for all tools based on dependencies.

        Returns:
            List of tool names in a valid execution order
        """
        return self.dependency_resolver.get_execution_order()
