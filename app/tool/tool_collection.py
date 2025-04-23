"""Collection classes for managing multiple tools."""
from typing import Any, Dict, List, Set, Tuple

from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool, ToolFailure, ToolResult
from app.tool.dependency_resolver import DependencyResolver, DependencyError
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.code_analyzer import CodeAnalyzer
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.data_processor import DataProcessor
from app.tool.output_formatter import OutputFormatter
from app.tool.enhanced_browser_tool import EnhancedBrowserTool
from app.tool.fallback_browser_tool import FallbackBrowserTool
from app.tool.enhanced_web_browser import EnhancedWebBrowser
from app.tool.enhanced_terminal import EnhancedTerminal
from app.tool.error_handler import ErrorHandler
from app.tool.error_handler_integration import ErrorHandlerIntegration
from app.tool.file_saver import FileSaver
from app.tool.financial_data_extractor import FinancialDataExtractor
from app.tool.long_running_command import LongRunningCommand

from app.tool.persistent_terminate import PersistentTerminate
from app.tool.planning import Planning
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.task_analytics import TaskAnalytics
from app.tool.terminal import Terminal
from app.tool.terminate import Terminate
from app.tool.web_search import WebSearch
from app.tool.conversation_manager import ConversationManager
from app.tool.message_notification import MessageNotifyUser, MessageAskUser


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

        # Default tools dictionary
        self.default_tools = {
        "bash": Bash(),
        "browser_use": BrowserUseTool(),
        "code_analyzer": CodeAnalyzer(),
        "create_chat_completion": CreateChatCompletion(),
        "data_processor": DataProcessor(),
        "output_formatter": OutputFormatter(),
        "enhanced_browser": EnhancedBrowserTool(),

        "fallback_browser": FallbackBrowserTool(),
        "enhanced_web_browser": EnhancedWebBrowser(),
        "enhanced_terminal": EnhancedTerminal(),
        "error_handler": ErrorHandler(),
        "error_handler_integration": ErrorHandlerIntegration(),
        "file_saver": FileSaver(),
        "financial_data_extractor": FinancialDataExtractor(),
        "long_running_command": LongRunningCommand(),

        "persistent_terminate": PersistentTerminate(),
        "planning": Planning(),
        "python_execute": PythonExecute(),
        "str_replace_editor": StrReplaceEditor(),
        "task_analytics": TaskAnalytics(),
        "terminal": Terminal(),
        "terminate": Terminate(),
        "web_search": WebSearch(),
        "conversation_manager": ConversationManager(),
        "message_notify_user": MessageNotifyUser(),
        "message_ask_user": MessageAskUser(),
        }

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
