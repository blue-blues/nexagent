from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import asyncio
import re
import json

from pydantic import Field

from app.core.agent.toolcall import ToolCallAgent
from app.prompt.nexagent import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tools.tool_collection import ToolCollection
from app.tools.persistent_terminate import PersistentTerminate
from app.tools.enhanced_browser_tool import EnhancedBrowserTool
from app.tools.file_saver import FileSaver
from app.tools.python_execute import PythonExecute
from app.tools.task_analytics import TaskAnalytics
from app.tools.web_search import WebSearch
from app.tools.base import ToolResult
from app.tools.enhanced_web_browser import EnhancedWebBrowser


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

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            WebSearch(),
            EnhancedBrowserTool(),
            EnhancedWebBrowser(),
            FileSaver(),
            TaskAnalytics(),
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
        - Processes multiple websites from search results for more comprehensive information
        """

        # Handle web search tool to process multiple websites
        if name == "web_search":
            try:
                # Execute the web search to get a list of URLs
                search_results = await super()._execute_tool(name, **kwargs)

                # If we got search results, process multiple websites
                if isinstance(search_results, list) and len(search_results) > 0:
                    # Get the number of websites to process (up to 5 by default)
                    max_websites = min(5, len(search_results))
                    print(f"Processing {max_websites} websites from search results for comprehensive information")

                    # Use the enhanced web browser to extract data from multiple sources
                    enhanced_browser = self.available_tools.get_tool("enhanced_web_browser")
                    if enhanced_browser:
                        try:
                            # Use the first 5 URLs (or fewer if less are available)
                            urls_to_process = search_results[:max_websites]

                            # Use multi_source_extract to process all URLs
                            multi_source_result = await enhanced_browser.execute(
                                action="multi_source_extract",
                                urls=urls_to_process,
                                data_type="text",
                                validation_level="thorough"
                            )

                            if not isinstance(multi_source_result, str) and not multi_source_result.error:
                                return multi_source_result
                        except Exception as e:
                            print(f"Error processing multiple websites: {str(e)}. Falling back to standard approach.")

                # If multi-source processing failed or wasn't attempted, return the original search results
                return search_results
            except Exception as e:
                print(f"Error in web search: {str(e)}")
                return await super()._execute_tool(name, **kwargs)

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

                # Always use agentic navigation for web browsing tasks
                # This is a key improvement - we're replacing simple scraping with intelligent navigation
                if kwargs.get("action") == "navigate_and_extract":
                    # Get the context from the request or from recent messages
                    context = kwargs.get("context", "")
                    if not context and hasattr(self, "messages") and self.messages:
                        # Try to get context from the most recent user message
                        for msg in reversed(self.messages):
                            if msg.role == "user":
                                context = msg.content
                                break

                    # If no context is available, use a generic one based on the URL
                    if not context:
                        context = f"Find detailed information from {url}"

                    print(f"Using agentic navigation for {url}")

                    try:
                        # Use agentic navigation for all web browsing tasks
                        agentic_result = await self._agentic_web_navigation(url, context, max_depth=3)

                        # Format the result for the user
                        if "error" not in agentic_result:
                            pages_visited = agentic_result.get("pages_visited", 0)
                            collected_info = agentic_result.get("collected_information", [])
                            navigation_path = agentic_result.get("navigation_path", [])

                            # Compile the information from all pages
                            compiled_info = f"[AGENTIC NAVIGATION] Visited {pages_visited} pages to gather comprehensive information:\n\n"

                            # Add a summary of the navigation path
                            compiled_info += "Navigation path:\n"
                            for i, step in enumerate(navigation_path[:10]):
                                action = step.get("action", "")
                                if action == "navigate":
                                    compiled_info += f"{i+1}. Navigated to: {step.get('url', '')}\n"
                                elif action == "click_link":
                                    compiled_info += f"{i+1}. Clicked link: '{step.get('text', '')}' → {step.get('url', '')}\n"
                                elif action == "submit_form":
                                    compiled_info += f"{i+1}. Submitted form → {step.get('url', '')}\n"
                                elif action == "click_button":
                                    compiled_info += f"{i+1}. Clicked button: '{step.get('text', '')}'\n"
                                elif action == "scroll":
                                    compiled_info += f"{i+1}. Scrolled page\n"

                            if len(navigation_path) > 10:
                                compiled_info += f"...and {len(navigation_path) - 10} more steps\n"

                            compiled_info += "\n\nCompiled Information:\n"

                            # Add content from each page (limiting to avoid excessive output)
                            for page_info in collected_info:
                                page_url = page_info.get("url", "")
                                page_title = page_info.get("title", "")
                                page_content = page_info.get("content", "")

                                # Truncate content if too long
                                if len(page_content) > 1000:
                                    page_content = page_content[:1000] + "...[content truncated]"

                                compiled_info += f"\n--- From {page_title or page_url} ---\n{page_content}\n"

                            return ToolResult(output=compiled_info)
                        else:
                            # If agentic navigation failed, log the error and continue with standard approach
                            print(f"Agentic navigation error: {agentic_result.get('error')}. Falling back to standard approach.")

                    except Exception as e:
                        print(f"Error in agentic navigation: {str(e)}. Falling back to standard approach.")

                # If agentic navigation failed, proceed with standard approach
                try:
                    # First attempt - standard execution
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

    async def _process_multiple_websites(self, urls: List[str], max_websites: int = 5) -> Dict[str, Any]:
        """
        Process multiple websites and aggregate their information.

        Args:
            urls: List of URLs to process
            max_websites: Maximum number of websites to process

        Returns:
            Dictionary containing aggregated information from multiple websites
        """
        if not urls:
            return {"error": "No URLs provided"}

        # Limit the number of websites to process
        urls_to_process = urls[:max_websites]

        # Use the enhanced web browser to extract data from multiple sources
        enhanced_browser = self.available_tools.get_tool("enhanced_web_browser")
        if not enhanced_browser:
            return {"error": "Enhanced web browser tool not available"}

        try:
            # Use multi_source_extract to process all URLs
            result = await enhanced_browser.execute(
                action="multi_source_extract",
                urls=urls_to_process,
                data_type="text",
                validation_level="thorough"
            )

            if isinstance(result, str):
                return {"error": "Failed to process multiple websites", "details": result}

            if result.error:
                return {"error": "Error processing multiple websites", "details": result.error}

            # Parse the result
            try:
                data = json.loads(result.output)
                return data
            except json.JSONDecodeError:
                return {"error": "Failed to parse result as JSON", "raw_output": result.output}

        except Exception as e:
            return {"error": f"Exception processing multiple websites: {str(e)}"}

    async def _agentic_web_navigation(self, url: str, query: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Perform truly intelligent agentic navigation of a website to find relevant information.

        This method uses a sophisticated approach that mimics human browsing behavior:
        1. First navigates to the initial URL
        2. Analyzes the page structure and content to understand what's available
        3. Makes intelligent decisions about what elements to interact with (links, buttons, forms)
        4. Follows a goal-directed exploration strategy based on the query
        5. Adapts its navigation strategy based on what it finds
        6. Aggregates information from all visited pages

        Args:
            url: The starting URL to navigate from
            query: The query or information need to guide navigation
            max_depth: Maximum depth of navigation (default: 3)

        Returns:
            Dictionary containing aggregated information from navigation
        """
        # Track visited URLs to avoid cycles
        visited_urls = set()
        # Store information from each page
        collected_info = []
        # Track navigation path for reporting
        navigation_path = []
        # Track the current navigation state
        current_state = {
            "url": url,
            "depth": 0,
            "page_title": "",
            "interaction_history": []
        }

        # Get the browser tool for direct interaction
        browser_tool = self.available_tools.get_tool("enhanced_browser")
        if not browser_tool:
            return {"error": "Enhanced browser tool not available"}

        print(f"Starting agentic navigation for query: '{query}'")
        print(f"Initial URL: {url}")

        # Navigate to the initial URL
        try:
            # First enable stealth mode and other enhancements
            await browser_tool.execute(action="stealth_mode", enable=True)
            await browser_tool.execute(action="random_delay", min_delay=800, max_delay=2500)
            await browser_tool.execute(action="rotate_user_agent")

            # Navigate to the starting URL
            nav_result = await browser_tool.execute(action="navigate", url=url)
            if isinstance(nav_result, str) or (hasattr(nav_result, "error") and nav_result.error):
                error_msg = nav_result if isinstance(nav_result, str) else nav_result.error
                return {"error": f"Failed to navigate to initial URL: {error_msg}"}

            # Mark as visited
            visited_urls.add(url)
            navigation_path.append({"action": "navigate", "url": url, "depth": 0})

            # Get the page title
            title_result = await browser_tool.execute(action="execute_js", script="document.title")
            if not isinstance(title_result, str) and not title_result.error:
                current_state["page_title"] = title_result.output

            # Begin the exploration process
            for exploration_step in range(max_depth * 3):  # Allow multiple interactions per depth level
                # Get the current depth
                current_depth = current_state["depth"]
                if current_depth >= max_depth:
                    print(f"Reached maximum depth ({max_depth}). Stopping exploration.")
                    break

                # Extract the current page content
                content_result = await browser_tool.execute(action="get_text")
                if isinstance(content_result, str) or content_result.error:
                    print(f"Error getting page content: {content_result if isinstance(content_result, str) else content_result.error}")
                    continue

                current_content = content_result.output
                current_url = await browser_tool.execute(action="execute_js", script="window.location.href")
                if not isinstance(current_url, str) and not current_url.error:
                    current_url = current_url.output
                else:
                    current_url = url  # Fallback

                # Store the current page information
                page_info = {
                    "url": current_url,
                    "title": current_state["page_title"],
                    "depth": current_depth,
                    "content": current_content,
                    "visited_at": exploration_step
                }
                collected_info.append(page_info)

                # Analyze the page to determine the best interaction strategy
                interaction_strategy = await self._determine_interaction_strategy(browser_tool, query, current_content, current_depth)

                if interaction_strategy["action"] == "stop":
                    print(f"Found sufficient information. Stopping exploration.")
                    break

                elif interaction_strategy["action"] == "click_link":
                    link_text = interaction_strategy.get("link_text", "")
                    link_index = interaction_strategy.get("link_index", 0)
                    print(f"Clicking link: '{link_text}' (index: {link_index})")

                    # Click the link
                    click_result = await browser_tool.execute(action="click", index=link_index)
                    if isinstance(click_result, str) or click_result.error:
                        print(f"Error clicking link: {click_result if isinstance(click_result, str) else click_result.error}")
                        # Try an alternative approach - get the href and navigate directly
                        if "href" in interaction_strategy:
                            href = interaction_strategy["href"]
                            print(f"Trying direct navigation to: {href}")
                            nav_result = await browser_tool.execute(action="navigate", url=href)
                            if isinstance(nav_result, str) or nav_result.error:
                                print(f"Direct navigation also failed: {nav_result if isinstance(nav_result, str) else nav_result.error}")
                                continue

                    # Update state after navigation
                    new_url_result = await browser_tool.execute(action="execute_js", script="window.location.href")
                    new_url = new_url_result.output if not isinstance(new_url_result, str) and not new_url_result.error else None

                    if new_url and new_url != current_url:
                        # Successfully navigated to a new page
                        current_state["url"] = new_url
                        current_state["depth"] += 1
                        visited_urls.add(new_url)

                        # Get the new page title
                        title_result = await browser_tool.execute(action="execute_js", script="document.title")
                        if not isinstance(title_result, str) and not title_result.error:
                            current_state["page_title"] = title_result.output

                        # Record the navigation
                        navigation_path.append({
                            "action": "click_link",
                            "text": link_text,
                            "url": new_url,
                            "depth": current_state["depth"]
                        })

                        # Add a delay to allow the page to load
                        await asyncio.sleep(2)

                elif interaction_strategy["action"] == "fill_form":
                    form_fields = interaction_strategy.get("form_fields", [])
                    print(f"Filling form with {len(form_fields)} fields")

                    # Fill each form field
                    for field in form_fields:
                        field_index = field.get("index")
                        field_value = field.get("value")

                        if field_index is not None and field_value:
                            input_result = await browser_tool.execute(
                                action="input_text",
                                index=field_index,
                                text=field_value
                            )
                            if isinstance(input_result, str) or input_result.error:
                                print(f"Error filling form field: {input_result if isinstance(input_result, str) else input_result.error}")
                                continue

                    # Submit the form if a submit button was identified
                    if "submit_index" in interaction_strategy:
                        submit_index = interaction_strategy["submit_index"]
                        print(f"Submitting form (button index: {submit_index})")

                        submit_result = await browser_tool.execute(action="click", index=submit_index)
                        if isinstance(submit_result, str) or submit_result.error:
                            print(f"Error submitting form: {submit_result if isinstance(submit_result, str) else submit_result.error}")
                            continue

                        # Update state after form submission
                        await asyncio.sleep(3)  # Allow time for the form to submit and page to load

                        new_url_result = await browser_tool.execute(action="execute_js", script="window.location.href")
                        new_url = new_url_result.output if not isinstance(new_url_result, str) and not new_url_result.error else None

                        if new_url and new_url != current_url:
                            # Successfully navigated to a new page after form submission
                            current_state["url"] = new_url
                            current_state["depth"] += 1
                            visited_urls.add(new_url)

                            # Record the navigation
                            navigation_path.append({
                                "action": "submit_form",
                                "url": new_url,
                                "depth": current_state["depth"]
                            })

                elif interaction_strategy["action"] == "click_button":
                    button_text = interaction_strategy.get("button_text", "")
                    button_index = interaction_strategy.get("button_index", 0)
                    print(f"Clicking button: '{button_text}' (index: {button_index})")

                    # Click the button
                    click_result = await browser_tool.execute(action="click", index=button_index)
                    if isinstance(click_result, str) or click_result.error:
                        print(f"Error clicking button: {click_result if isinstance(click_result, str) else click_result.error}")
                        continue

                    # Record the interaction
                    current_state["interaction_history"].append({
                        "action": "click_button",
                        "text": button_text
                    })

                    # Add a delay to allow any dynamic content to load
                    await asyncio.sleep(2)

                elif interaction_strategy["action"] == "scroll":
                    scroll_amount = interaction_strategy.get("amount", 500)
                    print(f"Scrolling page by {scroll_amount} pixels")

                    # Scroll the page
                    scroll_result = await browser_tool.execute(action="scroll", scroll_amount=scroll_amount)
                    if isinstance(scroll_result, str) or scroll_result.error:
                        print(f"Error scrolling: {scroll_result if isinstance(scroll_result, str) else scroll_result.error}")
                        continue

                    # Record the interaction
                    current_state["interaction_history"].append({
                        "action": "scroll",
                        "amount": scroll_amount
                    })

                    # Add a short delay to allow any lazy-loaded content to appear
                    await asyncio.sleep(1)

                else:
                    print(f"Unknown interaction strategy: {interaction_strategy['action']}")
                    continue

                # Check if we've collected enough information
                if len(collected_info) >= 10:
                    print(f"Collected information from {len(collected_info)} pages. Stopping exploration.")
                    break

        except Exception as e:
            print(f"Error in agentic navigation: {str(e)}")
            # Even if there's an error, return any information collected so far

        # Aggregate and return the collected information
        return {
            "visited_urls": list(visited_urls),
            "pages_visited": len(visited_urls),
            "max_depth_reached": max(page["depth"] for page in collected_info) if collected_info else 0,
            "navigation_path": navigation_path,
            "collected_information": collected_info
        }

    async def _determine_interaction_strategy(self, browser_tool, query, current_content, current_depth) -> Dict[str, Any]:
        """
        Determine the best interaction strategy based on the current page content and query.

        This is where the true intelligence of the agentic navigation happens - the agent
        analyzes the page and decides what to do next based on the user's information need.

        Args:
            browser_tool: The browser tool to use for page analysis
            query: The user's query or information need
            current_content: The current page content
            current_depth: The current navigation depth

        Returns:
            Dictionary with the determined interaction strategy
        """
        # First, check if the current page already contains the information we need
        query_terms = query.lower().split()
        content_lower = current_content.lower()

        # Calculate how many query terms are found in the content
        terms_found = sum(1 for term in query_terms if term in content_lower)
        term_ratio = terms_found / len(query_terms) if query_terms else 0

        # If we've found most of the query terms and we're at a reasonable depth, we might have enough info
        if term_ratio > 0.7 and current_depth > 0:
            return {"action": "stop", "reason": "sufficient_information_found"}

        # Extract all interactive elements on the page
        try:
            # Get all links
            links_result = await browser_tool.execute(
                action="extract_structured",
                selector="a",
                extraction_type="list"
            )

            links = []
            if not isinstance(links_result, str) and not links_result.error:
                try:
                    links_data = json.loads(links_result.output)
                    for link_list in links_data:
                        for i, item in enumerate(link_list.get("items", [])):
                            link_text = item.get("text", "").lower()
                            link_url = item.get("href", "")
                            if link_text and link_url:
                                links.append({
                                    "index": i,
                                    "text": link_text,
                                    "href": link_url,
                                    "score": 0  # Will be calculated below
                                })
                except Exception as e:
                    print(f"Error parsing links: {str(e)}")

            # Get all buttons
            buttons_result = await browser_tool.execute(
                action="extract_structured",
                selector="button, input[type='button'], input[type='submit'], .btn, [role='button']",
                extraction_type="list"
            )

            buttons = []
            if not isinstance(buttons_result, str) and not buttons_result.error:
                try:
                    buttons_data = json.loads(buttons_result.output)
                    for button_list in buttons_data:
                        for i, item in enumerate(button_list.get("items", [])):
                            button_text = item.get("text", "").lower()
                            if button_text:
                                buttons.append({
                                    "index": i,
                                    "text": button_text,
                                    "score": 0  # Will be calculated below
                                })
                except Exception as e:
                    print(f"Error parsing buttons: {str(e)}")

            # Get all form fields
            form_fields_result = await browser_tool.execute(
                action="extract_structured",
                selector="input[type='text'], input[type='search'], textarea",
                extraction_type="list"
            )

            form_fields = []
            if not isinstance(form_fields_result, str) and not form_fields_result.error:
                try:
                    fields_data = json.loads(form_fields_result.output)
                    for field_list in fields_data:
                        for i, item in enumerate(field_list.get("items", [])):
                            field_placeholder = item.get("placeholder", "").lower()
                            field_name = item.get("name", "").lower()
                            field_id = item.get("id", "").lower()

                            if field_placeholder or field_name or field_id:
                                form_fields.append({
                                    "index": i,
                                    "placeholder": field_placeholder,
                                    "name": field_name,
                                    "id": field_id
                                })
                except Exception as e:
                    print(f"Error parsing form fields: {str(e)}")

            # Now, score each interactive element based on relevance to the query

            # Score links
            for link in links:
                score = 0
                link_text = link["text"]

                # Check if query terms appear in the link text
                for term in query_terms:
                    if term in link_text:
                        score += 3  # Higher weight for terms in link text

                # Check for navigation-related terms that might be useful
                nav_terms = ["details", "more", "information", "about", "learn", "view", "read", "next", "continue"]
                for term in nav_terms:
                    if term in link_text:
                        score += 1

                # Bonus for links that look like they lead to detailed content
                detail_indicators = ["article", "full", "details", "read more", "view", "open"]
                for indicator in detail_indicators:
                    if indicator in link_text:
                        score += 2

                link["score"] = score

            # Score buttons
            for button in buttons:
                score = 0
                button_text = button["text"]

                # Check if query terms appear in the button text
                for term in query_terms:
                    if term in button_text:
                        score += 2

                # Check for action-related terms
                action_terms = ["search", "submit", "find", "go", "get", "show", "view", "load"]
                for term in action_terms:
                    if term in button_text:
                        score += 2

                button["score"] = score

            # Determine if we should fill a form
            has_search_form = any("search" in field.get("placeholder", "") or
                                "search" in field.get("name", "") or
                                "search" in field.get("id", "")
                                for field in form_fields)

            submit_button = None
            if buttons:
                for button in buttons:
                    if any(term in button["text"] for term in ["search", "submit", "find", "go"]):
                        submit_button = button
                        break

            # Decision making logic

            # If there's a search form and our query is information-seeking, use the form
            if has_search_form and submit_button and any(term in query.lower() for term in ["find", "search", "look for", "information about"]):
                search_field = next((field for field in form_fields if "search" in field.get("placeholder", "") or
                                    "search" in field.get("name", "") or
                                    "search" in field.get("id", "")), None)

                if search_field:
                    return {
                        "action": "fill_form",
                        "form_fields": [
                            {"index": search_field["index"], "value": query}
                        ],
                        "submit_index": submit_button["index"]
                    }

            # If there are relevant links, follow the most relevant one
            if links:
                # Sort links by score (highest first)
                sorted_links = sorted(links, key=lambda x: x["score"], reverse=True)
                best_link = sorted_links[0]

                # Only follow if it has some relevance
                if best_link["score"] > 0:
                    return {
                        "action": "click_link",
                        "link_text": best_link["text"],
                        "link_index": best_link["index"],
                        "href": best_link["href"]
                    }

            # If there are relevant buttons, click the most relevant one
            if buttons:
                # Sort buttons by score (highest first)
                sorted_buttons = sorted(buttons, key=lambda x: x["score"], reverse=True)
                best_button = sorted_buttons[0]

                # Only click if it has some relevance
                if best_button["score"] > 0:
                    return {
                        "action": "click_button",
                        "button_text": best_button["text"],
                        "button_index": best_button["index"]
                    }

            # If we haven't found anything relevant yet, try scrolling to reveal more content
            return {
                "action": "scroll",
                "amount": 500  # Scroll down by 500 pixels
            }

        except Exception as e:
            print(f"Error determining interaction strategy: {str(e)}")
            # Default to scrolling if we encounter an error
            return {
                "action": "scroll",
                "amount": 300
            }
