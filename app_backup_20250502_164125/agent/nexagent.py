from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import re
import json

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.nexagent import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tools import ToolCollection
from app.tools.persistent_terminate import PersistentTerminate
from app.tools.enhanced_browser_tool import EnhancedBrowserTool
from app.tools.file_saver import FileSaver
from app.tools.code import PythonExecute, CodeAnalyzer, StrReplaceEditor
from app.tools.task_analytics import TaskAnalytics
from app.tools.browser import WebSearch, BrowserUseTool
from app.tools.terminal import Terminal, EnhancedTerminal
from app.tools.data_processor import DataProcessor
from app.tools.output_formatter import OutputFormatter
from app.tools.message_notification import MessageNotifyUser, MessageAskUser
from app.tools.planning import Planning
from app.tools.long_running_command import LongRunningCommand
from app.tools.base import ToolResult


class Nexagent(ToolCallAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends PlanningAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "Nexagent"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 3000  # Increased from 2000 to allow for more comprehensive observations
    # max_steps is now dynamically set based on task complexity

    # Task history tracking
    task_history: List[Dict] = Field(default_factory=list)

    # Add websocket attribute with default None to prevent attribute errors
    websocket: Optional[Any] = None

    # Add comprehensive tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            # Code tools
            PythonExecute(),
            CodeAnalyzer(),
            StrReplaceEditor(),

            # Browser tools
            WebSearch(),
            EnhancedBrowserTool(),
            BrowserUseTool(),

            # File and data tools
            FileSaver(),
            DataProcessor(),
            OutputFormatter(),

            # Terminal tools
            Terminal(),
            EnhancedTerminal(),
            LongRunningCommand(),

            # User interaction tools
            MessageNotifyUser(),
            MessageAskUser(),

            # Planning and analytics tools
            Planning(),
            TaskAnalytics(),

            # System tools
            PersistentTerminate()
        )
    )

    def _validate_required_inputs(self, prompt: str) -> Optional[str]:
        """Validate if all required inputs are present in the prompt.

        Args:
            prompt: The user's input prompt

        Returns:
            str: Error message if validation fails, None if validation passes
        """
        # Check for keywords that indicate required inputs
        required_input_indicators = [
            "add to cart", "order", "buy", "purchase", "select",
            "choose", "pick", "get", "find", "search for"
        ]

        if any(indicator in prompt.lower() for indicator in required_input_indicators):
            # Look for specific items or quantities
            if not any(char.isdigit() or item in prompt.lower() for char in prompt for item in ["item", "product", "list"]):
                return "Please provide specific items or quantities needed for this task."

        return None

    def format_output(self, output: str, is_final_output: bool = False) -> str:
        """
        Format the agent's output to ensure it has a clear structure with a final output section.

        Args:
            output: The raw output from the agent
            is_final_output: Whether this is the final output to be shown to the user

        Returns:
            The formatted output
        """
        # If this is the final output to be shown to the user, extract just the final output section
        if is_final_output:
            # Look for common final output section markers
            final_output_markers = [
                "## Final Output",
                "# Final Output",
                "### Final Output",
                "Final Output:",
                "Final Result:",
                "Final Answer:"
            ]

            # Try to find any of the markers in the output
            for marker in final_output_markers:
                if marker in output:
                    # Split the output at the marker and take everything after it
                    parts = output.split(marker, 1)
                    if len(parts) > 1:
                        # Clean up the final output
                        final_output = parts[1].strip()
                        # Remove any trailing implementation steps or notes sections
                        end_markers = ["## Implementation", "## Notes", "## Next Steps", "## References"]
                        for end_marker in end_markers:
                            if end_marker in final_output:
                                final_output = final_output.split(end_marker, 1)[0].strip()
                        return final_output

            # If no final output section is found, return the original output
            return output

        # If this is not the final output, ensure it has a clear structure
        if "## Final Output" not in output and "# Final Output" not in output:
            # Add a final output section if none exists
            if "\n\n" in output:
                # Try to identify the last paragraph as the final output
                parts = output.split("\n\n")
                implementation = "\n\n".join(parts[:-1])
                final_output = parts[-1]
                return f"## Implementation Steps\n\n{implementation}\n\n## Final Output\n\n{final_output}"
            else:
                # If there's no clear structure, wrap the entire output as the final output
                return f"## Implementation Steps\n\nNo detailed steps provided.\n\n## Final Output\n\n{output}"

        # If it already has a final output section, return as is
        return output

    async def run(self, prompt: str) -> str:
        """Run the agent with the given prompt and track task history."""
        # Validate required inputs first
        error_message = self._validate_required_inputs(prompt)
        if error_message:
            return error_message

        start_time = datetime.now()

        # Dynamically set max_steps based on task complexity
        self.max_steps = self._calculate_max_steps(prompt)

        # Print for debugging
        print(f"Task complexity assessment - Dynamic max_steps set to: {self.max_steps}")

        result = await super().run(prompt)
        end_time = datetime.now()

        # Format the result to ensure it has a clear structure
        result = self.format_output(result)

        # Record task in history
        self.task_history.append({
            "prompt": prompt,
            "start_time": start_time,
            "end_time": end_time,
            "duration": (end_time - start_time).total_seconds(),
            "steps_taken": len(self.history) if hasattr(self, "history") else 0,
            "max_steps_allowed": self.max_steps,
        })

        return result

    def _calculate_max_steps(self, prompt: str) -> int:
        """
        Dynamically calculate maximum steps based on task complexity.

        This analyzes the input prompt to determine how complex the task is
        and sets an appropriate step limit.
        """
        # Base step count
        base_steps = 20

        # Count complexity factors in the prompt
        complexity_score = 0

        # Check for indicators of complexity
        web_scraping_indicators = [
            "scrape", "extract", "browse", "website", "web page", "data from",
            "get information", "navigate", "crawl", "fetch data"
        ]

        multi_step_indicators = [
            "then", "after that", "next", "subsequently", "finally", "lastly",
            "first", "second", "third", "step", "steps", "stages", "phases"
        ]

        data_processing_indicators = [
            "analyze", "process", "calculate", "compute", "transform",
            "convert", "clean", "filter", "sort", "compare"
        ]

        # Count matches for each indicator type
        web_complexity = sum(1 for indicator in web_scraping_indicators if indicator.lower() in prompt.lower())
        step_complexity = sum(1 for indicator in multi_step_indicators if indicator.lower() in prompt.lower())
        data_complexity = sum(1 for indicator in data_processing_indicators if indicator.lower() in prompt.lower())

        # Adjust score based on indicator counts
        if web_complexity > 0:
            complexity_score += min(web_complexity * 5, 25)  # Cap at 25

        if step_complexity > 0:
            complexity_score += min(step_complexity * 3, 30)  # Cap at 30

        if data_complexity > 0:
            complexity_score += min(data_complexity * 4, 20)  # Cap at 20

        # Check for specific keywords that indicate very complex tasks
        very_complex_indicators = [
            "comprehensive", "detailed", "extensive", "thorough", "complete",
            "all possible", "exhaustive", "full", "in-depth", "everything"
        ]

        if any(indicator.lower() in prompt.lower() for indicator in very_complex_indicators):
            complexity_score += 30

        # Adjust for prompt length (longer prompts often indicate more complexity)
        if len(prompt) > 200:
            complexity_score += 10
        if len(prompt) > 500:
            complexity_score += 15

        # Calculate final step count
        final_steps = base_steps + complexity_score

        # Cap at a reasonable maximum to prevent excessive steps
        return min(final_steps, 100)  # Maximum of 100 steps for any task

    def get_task_history(self) -> List[Dict]:
        """Return the complete task history."""
        return self.task_history

    def get_last_task(self) -> Dict:
        """Return the most recent task if available."""
        if self.task_history:
            return self.task_history[-1]
        return {}

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        if not self._is_special_tool(name):
            return
        else:
            await self.available_tools.get_tool(EnhancedBrowserTool().name).cleanup()
            await super()._handle_special_tool(name, result, **kwargs)

    async def _execute_tool(self, name: str, **kwargs) -> Any:
        """
        Override to add enhanced capabilities and fallback mechanisms.

        - For web scraping tasks, automatically enables stealth mode
        - For navigation failures, tries different approaches before falling back to search
        - Implements automatic pagination handling for comprehensive scraping
        """
        tool = self.available_tools.get_tool(name)

        # If the tool is the enhanced browser
        if name == "enhanced_browser":
            # Automatically enable comprehensive scraping for navigation and extraction
            if kwargs.get("action") in ["navigate", "navigate_and_extract"]:
                browser_tool = self.available_tools.get_tool("enhanced_browser")

                # First ensure stealth mode is enabled
                if not hasattr(browser_tool, "stealth_mode_enabled") or not browser_tool.stealth_mode_enabled:
                    try:
                        await browser_tool.execute(action="stealth_mode", enable=True)
                        await browser_tool.execute(action="random_delay", min_delay=800, max_delay=2500)
                        await browser_tool.execute(action="rotate_user_agent")
                    except Exception:
                        # If enabling stealth mode fails, continue anyway
                        pass

                # For navigate_and_extract, enhance to get as much data as possible
                if kwargs.get("action") == "navigate_and_extract":
                    try:
                        url = kwargs.get("url", "")
                        # Use the "all" extract type by default for most comprehensive data
                        kwargs["extract_type"] = kwargs.get("extract_type", "all")

                        # Try to execute with the comprehensive settings
                        result = await super()._execute_tool(name, **kwargs)

                        # Additional logic to handle potential pagination
                        if isinstance(result, ToolResult) and not result.error:
                            # Look for pagination patterns in the extracted content
                            content = result.output
                            if "next page" in content.lower() or "page 1" in content.lower() or "pagination" in content.lower():
                                # Try to find and follow pagination links for more complete data
                                try:
                                    # First get links to check for pagination
                                    links_result = await browser_tool.execute(action="extract_structured",
                                                                            selector="a",
                                                                            extraction_type="list")

                                    # Look for pagination links
                                    pagination_links = []
                                    if not isinstance(links_result, str) and not links_result.error:
                                        links_data = json.loads(links_result.output)
                                        # Look for links with pagination keywords
                                        pagination_patterns = ["next", "page", "2", "3", ">", "»"]
                                        for link_list in links_data:
                                            for item in link_list.get("items", []):
                                                if any(pattern in item.lower() for pattern in pagination_patterns):
                                                    # Found a potential pagination link
                                                    pagination_links.append(item)

                                    # If pagination links found, we can optionally follow them for more complete scraping
                                    if pagination_links:
                                        # Just note that pagination is available but don't automatically follow
                                        # to avoid excessive steps - the agent can decide to follow if needed
                                        result.output += "\n\n[PAGINATION DETECTED] Found potential pagination links: " + ", ".join(pagination_links[:3])
                                except Exception:
                                    # If pagination extraction fails, continue with the original result
                                    pass

                        return result
                    except Exception as e:
                        # Handle exceptions and continue to fallback mechanisms
                        pass

            # Handle browser navigation with multiple fallback attempts
            if kwargs.get("action") in ["navigate", "get_text", "get_html", "navigate_and_extract"]:
                url = kwargs.get("url", "")

                # First attempt - standard execution
                try:
                    result = await super()._execute_tool(name, **kwargs)

                    # Check if the browser action failed
                    if isinstance(result, ToolResult) and result.error and ("timed out" in result.error or "timeout" in result.error):
                        print(f"First attempt to access {url} failed with timeout, trying with different settings...")

                        # Second attempt - try with different browser settings
                        try:
                            # Rotate user agent and adjust timeout
                            await browser_tool.execute(action="rotate_user_agent")

                            # Retry with longer timeout
                            longer_timeout = kwargs.get("timeout", 30000) * 2
                            kwargs["timeout"] = longer_timeout

                            # Retry the action
                            result = await super()._execute_tool(name, **kwargs)

                            # If still failed, try a different approach
                            if isinstance(result, ToolResult) and result.error:
                                print(f"Second attempt failed, trying simplified approach...")

                                # Third attempt - try with simpler extraction method
                                if kwargs.get("action") == "navigate_and_extract":
                                    # Try just navigating first, then extracting text separately
                                    nav_result = await browser_tool.execute(action="navigate", url=url, timeout=longer_timeout)

                                    if not isinstance(nav_result, str) and not nav_result.error:
                                        # Navigation succeeded, now try to get text
                                        text_result = await browser_tool.execute(action="get_text")

                                        if not isinstance(text_result, str) and not text_result.error:
                                            return ToolResult(output=f"Successfully accessed {url} with fallback approach:\n\n{text_result.output}")
                        except Exception:
                            # If second attempt fails, continue to web search fallback
                            pass

                    # If all browser attempts succeeded or had non-timeout errors, return the result
                    if not isinstance(result, ToolResult) or not result.error or "timed out" not in result.error:
                        return result

                    # Final fallback - web search
                    # Extract the domain for search
                    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                    domain = domain_match.group(1) if domain_match else ""

                    # Create a search query from the URL
                    search_query = f"information from {domain}" if domain else f"information about {url}"

                    # Log the fallback attempt
                    print(f"All browser attempts failed for {url}, falling back to web search for: {search_query}")

                    # Attempt to get information via web search instead
                    web_search_tool = self.available_tools.get_tool("web_search")
                    if web_search_tool:
                        fallback_result = await web_search_tool.execute(search_term=search_query)
                        if isinstance(fallback_result, str):
                            return fallback_result
                        return f"[BROWSER FALLBACK] Failed to access {url} after multiple attempts. Here are search results instead:\n\n{fallback_result.output}"

                    # If web search also fails, return the original error
                    return result

                except Exception as e:
                    # Fallback to web search on any exception
                    url = kwargs.get("url", "")
                    search_query = f"information from {url}"
                    print(f"Exception in browser tool: {str(e)}. Falling back to web search for: {search_query}")

                    try:
                        web_search_tool = self.available_tools.get_tool("web_search")
                        if web_search_tool:
                            fallback_result = await web_search_tool.execute(search_term=search_query)
                            if isinstance(fallback_result, str):
                                return fallback_result
                            return f"[BROWSER FALLBACK] Exception occurred. Here are search results instead:\n\n{fallback_result.output}"
                    except Exception as search_error:
                        return f"Both browser and fallback search failed. Browser error: {str(e)}. Search error: {str(search_error)}"

        # For all other tools or actions, use the default implementation
        return await super()._execute_tool(name, **kwargs)
