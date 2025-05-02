import asyncio
import json
import random
from typing import Optional, List, Dict

from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.dom.service import DomService
from pydantic import Field

from app.config import config
from app.tools.base import ToolResult
from app.tools.browser.browser_use_tool import BrowserUseTool
from app.tools.data_processor import DataProcessor
from app.logger import logger
from app.tools.browser.structured_data_extractor import StructuredDataExtractor


class EnhancedBrowserTool(BrowserUseTool):
    """
    An enhanced browser tool that extends BrowserUseTool with additional capabilities
    to handle websites with anti-scraping protections.
    """

    name: str = "enhanced_browser"
    description: str = """
    Enhanced browser tool with advanced capabilities to handle websites with anti-scraping measures.
    Supports all standard browser actions plus:
    - 'stealth_mode': Enable stealth mode to avoid detection
    - 'random_delay': Add random delays between actions to mimic human behavior
    - 'rotate_user_agent': Use a different user agent
    - 'bypass_cloudflare': Attempt to bypass Cloudflare protection
    - 'extract_structured': Extract structured data from the page
    - 'navigate_and_extract': Navigate to URL and extract content in one step
    - 'agentic_browse': Intelligently browse a website to find specific information
    - 'multi_page_extract': Extract data from multiple pages in a website
    - 'follow_pagination': Follow pagination links to extract data from all pages
    """

    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "click",
                    "input_text",
                    "screenshot",
                    "get_html",
                    "get_text",
                    "execute_js",
                    "scroll",
                    "switch_tab",
                    "new_tab",
                    "close_tab",
                    "refresh",
                    "stealth_mode",
                    "random_delay",
                    "rotate_user_agent",
                    "bypass_cloudflare",
                    "extract_structured",
                    "extract_structured_data",
                    "navigate_and_extract",
                    "agentic_browse",
                    "multi_page_extract",
                    "follow_pagination",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'navigate' or 'new_tab' actions",
            },
            "index": {
                "type": "integer",
                "description": "Element index for 'click' or 'input_text' actions",
            },
            "text": {"type": "string", "description": "Text for 'input_text' action"},
            "script": {
                "type": "string",
                "description": "JavaScript code for 'execute_js' action",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive for down, negative for up) for 'scroll' action",
            },
            "tab_id": {
                "type": "integer",
                "description": "Tab ID for 'switch_tab' action",
            },
            "enable": {
                "type": "boolean",
                "description": "Enable/disable for 'stealth_mode' action",
            },
            "min_delay": {
                "type": "integer",
                "description": "Minimum delay in ms for 'random_delay' action",
            },
            "max_delay": {
                "type": "integer",
                "description": "Maximum delay in ms for 'random_delay' action",
            },
            "user_agent": {
                "type": "string",
                "description": "User agent string for 'rotate_user_agent' action",
            },
            "selector": {
                "type": "string",
                "description": "CSS selector for 'extract_structured' action",
            },
            "extraction_type": {
                "type": "string",
                "description": "Type of data to extract (table, list, etc.) for 'extract_structured' action",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in milliseconds for actions (default: 30000)",
            },
            "extract_type": {
                "type": "string",
                "description": "Type of content to extract for 'navigate_and_extract' action (text, links, tables)",
            },
            "query": {
                "type": "string",
                "description": "Search query or information to find for 'agentic_browse' action",
            },
            "max_pages": {
                "type": "integer",
                "description": "Maximum number of pages to process for 'multi_page_extract' and 'follow_pagination' actions",
            },
            "page_limit": {
                "type": "integer",
                "description": "Maximum number of pages to visit for 'agentic_browse' action",
            },

            "pagination_selector": {
                "type": "string",
                "description": "CSS selector for pagination links for 'follow_pagination' action",
            },
            "next_page_text": {
                "type": "string",
                "description": "Text content of the 'next page' link for 'follow_pagination' action",
            },
        },
        "required": ["action"],
    }

    # Additional state for enhanced features
    stealth_mode_enabled: bool = Field(default=False)
    random_delay_config: Dict[str, int] = Field(default_factory=lambda: {"min": 500, "max": 2000})
    current_user_agent: str = Field(default="")
    default_timeout: int = Field(default=30000)  # 30 seconds default timeout

    # Common user agents for rotation
    user_agents: List[str] = Field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    ])

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[int] = None,
        text: Optional[str] = None,
        script: Optional[str] = None,
        scroll_amount: Optional[int] = None,
        tab_id: Optional[int] = None,
        enable: Optional[bool] = None,
        min_delay: Optional[int] = None,
        max_delay: Optional[int] = None,
        user_agent: Optional[str] = None,
        selector: Optional[str] = None,
        extraction_type: Optional[str] = None,
        timeout: Optional[int] = None,
        extract_type: Optional[str] = None,
        query: Optional[str] = None,
        max_pages: Optional[int] = None,
        page_limit: Optional[int] = None,
        pagination_selector: Optional[str] = None,
        next_page_text: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a specified browser action with enhanced capabilities.
        """
        actual_timeout = timeout or self.default_timeout

        async with self.lock:
            try:
                # Apply random delay if enabled
                if self.random_delay_config and action not in ["stealth_mode", "random_delay", "rotate_user_agent"]:
                    delay_ms = random.randint(
                        self.random_delay_config["min"],
                        self.random_delay_config["max"]
                    )
                    await asyncio.sleep(delay_ms / 1000)  # Convert to seconds

                context = await self._ensure_browser_initialized()

                # Handle enhanced actions
                if action == "stealth_mode":
                    if enable is not None:
                        self.stealth_mode_enabled = enable
                        if enable:
                            # Apply enhanced stealth mode JavaScript
                            stealth_script = """
                            // Overwrite the navigator properties
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => false,
                            });

                            // Clear automation-related properties
                            delete navigator.__proto__.webdriver;

                            // Add plugins to appear more like a regular browser
                            Object.defineProperty(navigator, 'plugins', {
                                get: () => [
                                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format' },
                                    { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
                                ],
                            });

                            // Add plugin mimetype
                            Object.defineProperty(navigator, 'mimeTypes', {
                                get: () => [
                                    { type: 'application/pdf', suffixes: 'pdf', description: '', enabledPlugin: { name: 'Chrome PDF Plugin' } },
                                    { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: { name: 'Chrome PDF Viewer' } },
                                    { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable', enabledPlugin: { name: 'Native Client' } }
                                ],
                            });

                            // Modify the user agent if needed
                            Object.defineProperty(navigator, 'userAgent', {
                                get: () => navigator.userAgent.replace('Headless', ''),
                            });

                            // More extensive anti-detection measures
                            // Hide automation-related properties
                            const originalQuery = navigator.permissions.query;
                            navigator.permissions.query = (parameters) => (
                                parameters.name === 'notifications' ?
                                Promise.resolve({ state: Notification.permission }) :
                                originalQuery(parameters)
                            );

                            // Add language properties
                            Object.defineProperty(navigator, 'languages', {
                                get: () => ['en-US', 'en'],
                            });

                            // Set proper dimensions for window.screen
                            Object.defineProperties(screen, {
                                availWidth: { value: 1920 },
                                availHeight: { value: 1080 },
                                width: { value: 1920 },
                                height: { value: 1080 },
                                colorDepth: { value: 24 },
                                pixelDepth: { value: 24 }
                            });

                            // Override WebGL fingerprinting
                            const getParameter = WebGLRenderingContext.prototype.getParameter;
                            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                                // UNMASKED_VENDOR_WEBGL
                                if (parameter === 37445) {
                                    return 'Intel Inc.';
                                }
                                // UNMASKED_RENDERER_WEBGL
                                if (parameter === 37446) {
                                    return 'Intel Iris OpenGL Engine';
                                }
                                return getParameter.apply(this, arguments);
                            };

                            // Override canvas fingerprinting
                            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                            HTMLCanvasElement.prototype.toDataURL = function(type) {
                                if (this.width > 16 && this.height > 16) {
                                    // Add slight noise to the canvas
                                    const ctx = this.getContext('2d');
                                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                                    const pixels = imageData.data;
                                    for (let i = 0; i < pixels.length; i += 4) {
                                        // Add very slight noise to the alpha channel
                                        pixels[i + 3] = pixels[i + 3] > 0 ? pixels[i + 3] - 1 : 0;
                                    }
                                    ctx.putImageData(imageData, 0, 0);
                                }
                                return originalToDataURL.apply(this, arguments);
                            };
                            """
                            await context.execute_javascript(stealth_script)
                        return ToolResult(output=f"Stealth mode {'enabled' if enable else 'disabled'}")

                elif action == "random_delay":
                    if min_delay is not None and max_delay is not None:
                        self.random_delay_config = {"min": min_delay, "max": max_delay}
                        return ToolResult(output=f"Random delay set to {min_delay}-{max_delay}ms")
                    return ToolResult(error="Both min_delay and max_delay are required")

                elif action == "rotate_user_agent":
                    if user_agent:
                        self.current_user_agent = user_agent
                    else:
                        self.current_user_agent = random.choice(self.user_agents)

                    # Apply the user agent
                    await context.execute_javascript(f"""
                    Object.defineProperty(navigator, 'userAgent', {{
                        get: () => '{self.current_user_agent}'
                    }});
                    """)
                    return ToolResult(output=f"User agent set to: {self.current_user_agent}")

                elif action == "bypass_cloudflare":
                    # Attempt to bypass Cloudflare protection
                    bypass_script = """
                    // Wait for Cloudflare challenge to complete
                    function waitForCloudflare() {
                        return new Promise((resolve) => {
                            const checkInterval = setInterval(() => {
                                if (!document.querySelector('#cf-spinner') &&
                                    !document.querySelector('.cf-browser-verification') &&
                                    !document.querySelector('#cf-please-wait')) {
                                    clearInterval(checkInterval);
                                    resolve(true);
                                }
                            }, 500);

                            // Timeout after 30 seconds
                            setTimeout(() => {
                                clearInterval(checkInterval);
                                resolve(false);
                            }, 30000);
                        });
                    }

                    return await waitForCloudflare();
                    """
                    result = await context.execute_javascript(bypass_script)
                    if result:
                        return ToolResult(output="Successfully bypassed Cloudflare protection")
                    else:
                        return ToolResult(error="Failed to bypass Cloudflare protection or timed out")

                elif action == "extract_structured_data":
                    # Get the HTML content of the page
                    try:
                        html = await context.execute_javascript("document.documentElement.outerHTML")
                        current_url = await context.execute_javascript("window.location.href")

                        # Use the structured data extractor
                        extractor = StructuredDataExtractor()
                        result = await extractor.execute(
                            html=html,
                            url=current_url,
                            extraction_type=extraction_type or "all"
                        )

                        return result
                    except Exception as e:
                        return ToolResult(error=f"Error extracting structured data: {str(e)}")

                elif action == "extract_structured":
                    if not selector or not extraction_type:
                        return ToolResult(error="Both selector and extraction_type are required")

                    # First check if the selector exists on the page
                    try:
                        element_exists = await context.execute_javascript(f"""
                            (function() {{
                                const elements = document.querySelectorAll('{selector}');
                                return elements.length > 0;
                            }})();
                        """)

                        if not element_exists:
                            return ToolResult(error=f"No elements found with selector: '{selector}'. Please check the selector or try a different one.")
                    except Exception as e:
                        return ToolResult(error=f"Error checking selector '{selector}': {str(e)}")

                    # Use the simpler extract functions that are less likely to have syntax errors
                    if extraction_type == "table":
                        try:
                            # Simpler table extraction
                            data = await self._extract_tables(context, selector)
                            if data:
                                return ToolResult(output=json.dumps(data, ensure_ascii=False))
                            else:
                                return ToolResult(error=f"No table data found with selector: '{selector}'. The element exists but may not be a table or contain table data.")
                        except Exception as e:
                            return ToolResult(error=f"Error extracting tables: {str(e)}")

                    elif extraction_type == "list":
                        try:
                            # Simpler list extraction
                            data = await self._extract_lists(context, selector)
                            if data:
                                return ToolResult(output=json.dumps(data, ensure_ascii=False))
                            else:
                                return ToolResult(error=f"No list data found with selector: '{selector}'. The element exists but may not be a list or contain list items.")
                        except Exception as e:
                            return ToolResult(error=f"Error extracting lists: {str(e)}")

                    elif extraction_type == "fullpage":
                        try:
                            # Attempt to extract all content with formatting preserved
                            data = await self._extract_full_page(context)
                            if data:
                                return ToolResult(output=json.dumps(data, ensure_ascii=False))
                            else:
                                return ToolResult(error="No content found on the page or extraction failed.")
                        except Exception as e:
                            return ToolResult(error=f"Error extracting full page: {str(e)}")

                    else:
                        # Generic element extraction
                        try:
                            data = await self._extract_elements(context, selector)
                            if data:
                                return ToolResult(output=json.dumps(data, ensure_ascii=False))
                            else:
                                return ToolResult(error=f"No data could be extracted from elements with selector: '{selector}'. The elements may be empty or not contain the expected data.")
                        except Exception as e:
                            return ToolResult(error=f"Error extracting elements: {str(e)}")

                elif action == "navigate_and_extract":
                    if not url:
                        return ToolResult(error="URL is required for 'navigate_and_extract' action")

                    try:
                        # Navigate to the URL
                        await asyncio.wait_for(
                            context.navigate_to(url),
                            timeout=actual_timeout / 1000  # Convert to seconds
                        )

                        # Wait for page to load more completely
                        await asyncio.sleep(3)

                        # Check for infinite scroll or lazy loading and scroll if needed
                        await self._handle_infinite_scroll(context)

                        # Extract content based on the specified type
                        extract_type = extract_type or "comprehensive"

                        if extract_type == "text":
                            content = await self._extract_page_text(context)
                            return ToolResult(output=f"Successfully navigated to {url} and extracted text content:\n\n{content}")

                        elif extract_type == "links":
                            links = await self._extract_page_links(context)
                            return ToolResult(output=f"Successfully navigated to {url} and extracted links:\n\n{json.dumps(links, ensure_ascii=False)}")

                        elif extract_type == "tables":
                            tables = await self._extract_all_tables(context)
                            return ToolResult(output=f"Successfully navigated to {url} and extracted tables:\n\n{json.dumps(tables, ensure_ascii=False)}")

                        elif extract_type == "comprehensive":
                            # Most thorough extraction that gets everything possible
                            # First scroll to get any lazy-loaded content
                            for _ in range(3):
                                await context.execute_javascript("window.scrollTo(0, document.body.scrollHeight * 0.8);")
                                await asyncio.sleep(1)

                            # Reset scroll position
                            await context.execute_javascript("window.scrollTo(0, 0);")

                            # Assemble a comprehensive result
                            result = {}

                            # Get metadata first
                            result["metadata"] = await self._extract_page_metadata(context)

                            # Extract text content (main content)
                            result["text"] = await self._extract_page_text(context)

                            # Extract all links
                            result["links"] = await self._extract_page_links(context)

                            # Extract all tables
                            result["tables"] = await self._extract_all_tables(context)

                            # Extract images
                            result["images"] = await self._extract_page_images(context)

                            # Check for pagination
                            pagination_info = await self._detect_pagination(context)
                            if pagination_info:
                                result["pagination"] = pagination_info

                            # Return full comprehensive data
                            # Store captured data
                            if self.data_collection_enabled:
                                try:
                                    processor = DataProcessor()
                                    output_path = processor.process(result, url, "text/html")
                                    self.collected_data.append(str(output_path))
                                except Exception as e:
                                    logger.error(f"Ethical data processing failed: {str(e)}")
                                    raise

                            return ToolResult(output=f"Successfully navigated to {url} and extracted comprehensive content:\n\n{json.dumps(result, ensure_ascii=False)}")

                        elif extract_type == "all":
                            # Handle the 'all' extract_type explicitly
                            try:
                                result = {}
                                # First scroll to get any lazy-loaded content
                                for _ in range(2):
                                    await context.execute_javascript("window.scrollTo(0, document.body.scrollHeight * 0.7);")
                                    await asyncio.sleep(1)

                                # Reset scroll position
                                await context.execute_javascript("window.scrollTo(0, 0);")

                                # Extract text content (main content)
                                result["text"] = await self._extract_page_text(context)

                                # Extract all links
                                result["links"] = await self._extract_page_links(context)

                                # Extract all tables
                                result["tables"] = await self._extract_all_tables(context)

                                return ToolResult(output=f"Successfully navigated to {url} and extracted all content:\n\n{json.dumps(result, ensure_ascii=False)}")
                            except Exception as e:
                                return ToolResult(error=f"Error extracting 'all' content from {url}: {str(e)}")
                        else:
                            # Default to extracting everything for any other extract_type
                            try:
                                result = {}
                                result["text"] = await self._extract_page_text(context)
                                result["links"] = await self._extract_page_links(context)
                                result["tables"] = await self._extract_all_tables(context)

                                return ToolResult(output=f"Successfully navigated to {url} and extracted content:\n\n{json.dumps(result, ensure_ascii=False)}")
                            except Exception as e:
                                return ToolResult(error=f"Error extracting content from {url}: {str(e)}")

                    except asyncio.TimeoutError:
                        return ToolResult(error=f"Navigation to {url} timed out after {actual_timeout/1000} seconds")
                    except Exception as e:
                        return ToolResult(error=f"Error during navigate_and_extract to {url}: {str(e)}")

                # Handle the navigate action with timeout
                elif action == "navigate":
                    if not url:
                        return ToolResult(error="URL is required for 'navigate' action")

                    # Navigation with timeout
                    try:
                        await asyncio.wait_for(
                            context.navigate_to(url),
                            timeout=actual_timeout / 1000  # Convert to seconds
                        )

                        # Add a short delay after navigation to ensure the page is loaded
                        await asyncio.sleep(2)

                        # Check if navigation was successful by getting the current URL
                        current_url = await context.execute_javascript("window.location.href")

                        return ToolResult(output=f"Navigated to {current_url}")
                    except asyncio.TimeoutError:
                        return ToolResult(error=f"Navigation to {url} timed out after {actual_timeout/1000} seconds")
                    except Exception as e:
                        return ToolResult(error=f"Error navigating to {url}: {str(e)}")

                # Handle the get_text action with timeout
                elif action == "get_text":
                    try:
                        text = await self._extract_page_text(context)
                        return ToolResult(output=text or "No text content found on page")
                    except asyncio.TimeoutError:
                        return ToolResult(error=f"Getting text content timed out after {actual_timeout/1000} seconds")
                    except Exception as e:
                        return ToolResult(error=f"Error getting text content: {str(e)}")

                # Handle agentic browsing
                elif action == "agentic_browse":
                    if not url:
                        return ToolResult(error="URL is required for 'agentic_browse' action")
                    if not query:
                        return ToolResult(error="Query is required for 'agentic_browse' action")

                    try:
                        # Set default values for parameters
                        page_limit_val = page_limit or 5

                        # Navigate to the initial URL
                        await asyncio.wait_for(
                            context.navigate_to(url),
                            timeout=actual_timeout / 1000  # Convert to seconds
                        )

                        # Wait for page to load
                        await asyncio.sleep(3)

                        # Get the initial page content and links
                        initial_content = await self._extract_page_text(context)
                        initial_links = await self._extract_page_links(context)

                        # Check if the information is already on the current page
                        if query.lower() in initial_content.lower():
                            # Information found on the first page
                            result = {
                                "found": True,
                                "pages_visited": 1,
                                "current_url": url,
                                "content": initial_content,
                                "query": query
                            }
                            return ToolResult(output=json.dumps(result, ensure_ascii=False))

                        # Information not found on first page, start intelligent browsing
                        visited_urls = {url}
                        pages_visited = 1
                        to_visit = []

                        # Prioritize links that might contain the information
                        for link in initial_links:
                            if link.get("isVisible", False) and not link.get("isNavigation", False):
                                link_text = link.get("text", "").lower()
                                link_href = link.get("href", "")

                                # Skip non-http links, anchors, etc.
                                if not link_href.startswith(("http://", "https://")):
                                    continue

                                # Skip external links (not on the same domain)
                                if not self._is_same_domain(url, link_href):
                                    continue

                                # Calculate relevance score based on query terms in link text
                                relevance = 0
                                query_terms = query.lower().split()
                                for term in query_terms:
                                    if term in link_text:
                                        relevance += 1

                                to_visit.append((link_href, relevance))

                        # Sort by relevance score (highest first)
                        to_visit.sort(key=lambda x: x[1], reverse=True)
                        to_visit = [url for url, _ in to_visit]

                        # Start browsing through prioritized links
                        for i in range(min(len(to_visit), page_limit_val - 1)):  # -1 because we already visited the first page
                            next_url = to_visit[i]
                            if next_url in visited_urls:
                                continue

                            # Navigate to the next URL
                            try:
                                await asyncio.wait_for(
                                    context.navigate_to(next_url),
                                    timeout=actual_timeout / 1000  # Convert to seconds
                                )

                                # Wait for page to load
                                await asyncio.sleep(2)

                                # Mark as visited
                                visited_urls.add(next_url)
                                pages_visited += 1

                                # Get the page content
                                page_content = await self._extract_page_text(context)

                                # Check if the information is on this page
                                if query.lower() in page_content.lower():
                                    # Information found
                                    result = {
                                        "found": True,
                                        "pages_visited": pages_visited,
                                        "current_url": next_url,
                                        "content": page_content,
                                        "query": query
                                    }
                                    return ToolResult(output=json.dumps(result, ensure_ascii=False))
                            except Exception as e:
                                logger.error(f"Error navigating to {next_url}: {str(e)}")
                                continue

                        # If we get here, we didn't find the information
                        result = {
                            "found": False,
                            "pages_visited": pages_visited,
                            "visited_urls": list(visited_urls),
                            "query": query
                        }
                        return ToolResult(output=json.dumps(result, ensure_ascii=False))
                    except asyncio.TimeoutError:
                        return ToolResult(error=f"Agentic browsing timed out after {actual_timeout/1000} seconds")
                    except Exception as e:
                        return ToolResult(error=f"Error during agentic browsing: {str(e)}")

                # Handle multi-page extraction
                elif action == "multi_page_extract":
                    if not url:
                        return ToolResult(error="URL is required for 'multi_page_extract' action")

                    try:
                        # Set default values for parameters
                        max_pages_val = max_pages or 3

                        # Navigate to the initial URL
                        await asyncio.wait_for(
                            context.navigate_to(url),
                            timeout=actual_timeout / 1000  # Convert to seconds
                        )

                        # Wait for page to load
                        await asyncio.sleep(3)

                        # Get all links from the page
                        all_links = await self._extract_page_links(context)

                        # Filter links to only include those on the same domain
                        same_domain_links = [
                            link.get("href") for link in all_links
                            if link.get("isVisible", False) and
                            link.get("href") and
                            self._is_same_domain(url, link.get("href"))
                        ]

                        # Remove duplicates
                        same_domain_links = list(set(same_domain_links))

                        # Limit to max_pages
                        links_to_visit = same_domain_links[:max_pages_val - 1]  # -1 because we already visited the first page

                        # Extract content from the first page
                        results = [{
                            "url": url,
                            "content": await self._extract_page_text(context),
                            "links": await self._extract_page_links(context),
                            "tables": await self._extract_all_tables(context)
                        }]

                        # Visit each link and extract content
                        for link_url in links_to_visit:
                            try:
                                # Navigate to the link
                                await asyncio.wait_for(
                                    context.navigate_to(link_url),
                                    timeout=actual_timeout / 1000  # Convert to seconds
                                )

                                # Wait for page to load
                                await asyncio.sleep(2)

                                # Extract content
                                page_result = {
                                    "url": link_url,
                                    "content": await self._extract_page_text(context),
                                    "links": await self._extract_page_links(context),
                                    "tables": await self._extract_all_tables(context)
                                }

                                # Add to results
                                results.append(page_result)
                            except Exception as e:
                                logger.error(f"Error extracting content from {link_url}: {str(e)}")
                                continue

                        return ToolResult(output=json.dumps({
                            "pages_visited": len(results),
                            "results": results
                        }, ensure_ascii=False))
                    except asyncio.TimeoutError:
                        return ToolResult(error=f"Multi-page extraction timed out after {actual_timeout/1000} seconds")
                    except Exception as e:
                        return ToolResult(error=f"Error during multi-page extraction: {str(e)}")

                # Handle pagination following
                elif action == "follow_pagination":
                    if not url:
                        return ToolResult(error="URL is required for 'follow_pagination' action")

                    try:
                        # Set default values for parameters
                        max_pages_val = max_pages or 3

                        # Navigate to the initial URL
                        await asyncio.wait_for(
                            context.navigate_to(url),
                            timeout=actual_timeout / 1000  # Convert to seconds
                        )

                        # Wait for page to load
                        await asyncio.sleep(3)

                        # Extract content from the first page
                        results = [{
                            "url": url,
                            "content": await self._extract_page_text(context),
                            "tables": await self._extract_all_tables(context)
                        }]

                        # Follow pagination for specified number of pages
                        current_page = 1
                        while current_page < max_pages_val:
                            # Find the next page link
                            next_page_url = await self._find_next_page_link(context, pagination_selector, next_page_text)

                            if not next_page_url:
                                # No more pages found
                                break

                            try:
                                # Navigate to the next page
                                await asyncio.wait_for(
                                    context.navigate_to(next_page_url),
                                    timeout=actual_timeout / 1000  # Convert to seconds
                                )

                                # Wait for page to load
                                await asyncio.sleep(2)

                                # Extract content
                                page_result = {
                                    "url": next_page_url,
                                    "content": await self._extract_page_text(context),
                                    "tables": await self._extract_all_tables(context)
                                }

                                # Add to results
                                results.append(page_result)
                                current_page += 1
                            except Exception as e:
                                logger.error(f"Error extracting content from pagination page {next_page_url}: {str(e)}")
                                break

                        return ToolResult(output=json.dumps({
                            "pages_visited": len(results),
                            "results": results
                        }, ensure_ascii=False))
                    except asyncio.TimeoutError:
                        return ToolResult(error=f"Pagination following timed out after {actual_timeout/1000} seconds")
                    except Exception as e:
                        return ToolResult(error=f"Error during pagination following: {str(e)}")

                # For other standard actions, call the parent class implementation with a timeout wrapper
                try:
                    return await asyncio.wait_for(
                        super().execute(
                            action=action,
                            url=url,
                            index=index,
                            text=text,
                            script=script,
                            scroll_amount=scroll_amount,
                            tab_id=tab_id,
                            **kwargs
                        ),
                        timeout=actual_timeout / 1000  # Convert to seconds
                    )
                except asyncio.TimeoutError:
                    return ToolResult(error=f"Action '{action}' timed out after {actual_timeout/1000} seconds")
                except Exception as e:
                    return ToolResult(error=f"Error executing action '{action}': {str(e)}")

            except Exception as e:
                return ToolResult(error=f"Error executing browser action: {str(e)}")

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """Ensure browser and context are initialized with enhanced settings."""
        if self.browser is None:
            browser_config_kwargs = {
                "headless": False,
                "disable_security": True,
            }

            # Add additional arguments for anti-detection
            extra_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-web-security",
                "--disable-popup-blocking",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]

            if config.browser_config and hasattr(config.browser_config, "extra_chromium_args"):
                if config.browser_config.extra_chromium_args:
                    extra_args.extend(config.browser_config.extra_chromium_args)

            browser_config_kwargs["extra_chromium_args"] = extra_args

            if config.browser_config:
                from browser_use.browser.browser import ProxySettings

                # handle proxy settings.
                if config.browser_config.proxy and config.browser_config.proxy.server:
                    browser_config_kwargs["proxy"] = ProxySettings(
                        server=config.browser_config.proxy.server,
                        username=config.browser_config.proxy.username,
                        password=config.browser_config.proxy.password,
                    )

                browser_attrs = [
                    "headless",
                    "disable_security",
                    "chrome_instance_path",
                    "wss_url",
                    "cdp_url",
                ]

                for attr in browser_attrs:
                    value = getattr(config.browser_config, attr, None)
                    if value is not None:
                        if not isinstance(value, list) or value:
                            browser_config_kwargs[attr] = value

            self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))

        if self.context is None:
            context_config = BrowserContextConfig()

            # if there is context config in the config, use it.
            if (
                config.browser_config
                and hasattr(config.browser_config, "new_context_config")
                and config.browser_config.new_context_config
            ):
                context_config = config.browser_config.new_context_config

            # Set default timeout for context navigation
            if not hasattr(context_config, "default_timeout"):
                context_config.default_timeout = self.default_timeout

            self.context = await self.browser.new_context(context_config)
            self.dom_service = DomService(await self.context.get_current_page())

            # Apply stealth mode if enabled
            if self.stealth_mode_enabled:
                stealth_script = """
                // Overwrite the navigator properties
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });

                // Clear automation-related properties
                delete navigator.__proto__.webdriver;

                // Add plugins to appear more like a regular browser
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // Modify the user agent if needed
                Object.defineProperty(navigator, 'userAgent', {
                    get: () => navigator.userAgent.replace('Headless', ''),
                });

                // Override permissions
                navigator.permissions.query = ({ name }) => {
                    return Promise.resolve({ state: 'granted' });
                };
                """
                try:
                    await self.context.execute_javascript(stealth_script)
                except Exception:
                    pass  # Ignore errors in stealth mode initialization

            # Apply user agent if set
            if self.current_user_agent:
                try:
                    await self.context.execute_javascript(f"""
                    Object.defineProperty(navigator, 'userAgent', {{
                        get: () => '{self.current_user_agent}'
                    }});
                    """)
                except Exception:
                    pass  # Ignore errors in user agent setting

        return self.context

    async def _extract_page_text(self, context: BrowserContext) -> str:
        """Extract text from the page using multiple methods to maximize chances of success."""
        try:
            # First try a comprehensive extraction that focuses on main content
            text = await context.execute_javascript("""
                (function() {
                    function getMainContent() {
                        // Try to find main content area - looking for common containers
                        const mainSelectors = [
                            'main',
                            'article',
                            '#content',
                            '.content',
                            '.main',
                            '.post',
                            '.article',
                            '[role="main"]'
                        ];

                        for (const selector of mainSelectors) {
                            const mainElement = document.querySelector(selector);
                            if (mainElement && mainElement.innerText.trim().length > 200) {
                                return mainElement.innerText.trim();
                            }
                        }

                        // If no main content found, use the body but try to filter out navigation and footer
                        const bodyText = Array.from(document.body.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, td, th, div:not(nav):not(footer):not(header):not(.menu):not(.navigation)'))
                            .filter(el => {
                                // Filter out likely non-content elements
                                const text = el.innerText.trim();
                                if (text.length < 10) return false;  // too short
                                if (el.closest('nav') || el.closest('footer') || el.closest('header')) return false;
                                if (el.querySelectorAll('a').length > 5) return false;  // likely a menu
                                return true;
                            })
                            .map(el => el.innerText.trim())
                            .join('\\n\\n');

                        return bodyText || document.body.innerText.trim();
                    }

                    return getMainContent();
                })();
            """)

            # If no text found, try a more comprehensive approach
            if not text or len(text.strip()) < 50:
                text = await context.execute_javascript(
                    """(function() {
                        return Array.from(document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, td, th, a, span, div'))
                           .filter(el => el.innerText && el.innerText.trim().length > 0)
                           .map(el => el.innerText.trim())
                           .join('\\n\\n');
                    })()"""
                )

            return text or "No text content found on page"
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    async def _extract_page_links(self, context: BrowserContext) -> List[Dict[str, str]]:
        """Extract all links from the page."""
        try:
            links_data = await context.execute_javascript("""
                function getAllLinks() {
                    return Array.from(document.querySelectorAll('a[href]')).map(a => {
                        // Get the bounding rectangle to determine if link is visible
                        const rect = a.getBoundingClientRect();
                        const isVisible = (
                            rect.width > 0 &&
                            rect.height > 0 &&
                            window.getComputedStyle(a).visibility !== 'hidden' &&
                            window.getComputedStyle(a).display !== 'none'
                        );

                        // Determine if this is a navigation link
                        const isNav = (
                            a.closest('nav') !== null ||
                            a.closest('header') !== null ||
                            a.closest('.menu') !== null ||
                            a.closest('.navigation') !== null
                        );

                        return {
                            text: a.innerText.trim(),
                            href: a.href,
                            title: a.title || '',
                            isVisible: isVisible,
                            isNavigation: isNav,
                            hasImage: a.querySelector('img') !== null
                        };
                    }).filter(link => link.href && !link.href.startsWith('javascript:'));
                }

                return getAllLinks();
            """)
            return links_data or []
        except Exception as e:
            print(f"Error extracting links: {str(e)}")
            return []

    async def _extract_page_images(self, context: BrowserContext) -> List[Dict[str, str]]:
        """Extract all significant images from the page."""
        try:
            images_data = await context.execute_javascript("""
                function getAllImages() {
                    return Array.from(document.querySelectorAll('img')).map(img => {
                        // Get bounding rect to determine visibility and size
                        const rect = img.getBoundingClientRect();
                        const isVisible = (
                            rect.width > 5 &&
                            rect.height > 5 &&
                            window.getComputedStyle(img).visibility !== 'hidden' &&
                            window.getComputedStyle(img).display !== 'none'
                        );

                        // Only include significant images (filter out icons, etc.)
                        if (isVisible && rect.width >= 100 && rect.height >= 50) {
                            return {
                                src: img.src,
                                alt: img.alt || '',
                                width: rect.width,
                                height: rect.height,
                                isVisible: isVisible
                            };
                        }
                        return null;
                    }).filter(img => img !== null);
                }

                return getAllImages();
            """)
            return images_data or []
        except Exception as e:
            print(f"Error extracting images: {str(e)}")
            return []

    async def _extract_all_tables(self, context: BrowserContext) -> List[Dict]:
        """Extract all tables from the page."""
        try:
            # A simpler table extraction script that's less likely to have syntax errors
            tables_data = await context.execute_javascript("""
                const results = [];
                const tables = document.querySelectorAll('table');

                for (let i = 0; i < tables.length; i++) {
                    const table = tables[i];
                    const tableData = {
                        tableIndex: i,
                        headers: [],
                        rows: []
                    };

                    // Extract headers from th elements, if any
                    const headerElements = table.querySelectorAll('th');
                    for (let j = 0; j < headerElements.length; j++) {
                        tableData.headers.push(headerElements[j].innerText.trim());
                    }

                    // Extract rows from tr elements
                    const rows = table.querySelectorAll('tr');
                    for (let j = 0; j < rows.length; j++) {
                        const row = [];
                        const cells = rows[j].querySelectorAll('td');
                        for (let k = 0; k < cells.length; k++) {
                            row.push(cells[k].innerText.trim());
                        }
                        if (row.length > 0) {
                            tableData.rows.push(row);
                        }
                    }

                    results.push(tableData);
                }

                return results;
            """)
            return tables_data or []
        except Exception as e:
            print(f"Error extracting tables: {str(e)}")
            return []

    async def _detect_pagination(self, context: BrowserContext) -> Dict:
        """Detect pagination on the page and extract pagination information."""
        try:
            pagination_info = await context.execute_javascript("""
                function detectPagination() {
                    const result = {
                        hasPagination: false,
                        currentPage: null,
                        totalPages: null,
                        paginationLinks: []
                    };

                    // Look for common pagination containers
                    const paginationContainers = document.querySelectorAll(
                        '.pagination, .pager, nav[aria-label*="pagination"], ul.page-numbers, .page-navigation, .wp-pagenavi'
                    );

                    if (paginationContainers.length > 0) {
                        result.hasPagination = true;

                        // Try to find the current page and total pages
                        for (const container of paginationContainers) {
                            // Look for an active or current page indicator
                            const currentPageElement = container.querySelector(
                                '.active, .current, [aria-current="page"], .selected, .is-active'
                            );

                            if (currentPageElement) {
                                result.currentPage = parseInt(currentPageElement.textContent.trim()) || null;
                            }

                            // Get all pagination links
                            const links = Array.from(container.querySelectorAll('a')).map(a => {
                                const text = a.textContent.trim();
                                return {
                                    text: text,
                                    href: a.href,
                                    isNumeric: /^\\d+$/.test(text),
                                    isNext: /next|›|»|forward|→/i.test(text) || a.getAttribute('rel') === 'next',
                                    isPrevious: /prev|previous|‹|«|back|←/i.test(text) || a.getAttribute('rel') === 'prev'
                                };
                            });

                            result.paginationLinks = links;

                            // Try to determine total pages
                            const numericLinks = links.filter(l => l.isNumeric);
                            if (numericLinks.length > 0) {
                                const pageNumbers = numericLinks.map(l => parseInt(l.text)).filter(n => !isNaN(n));
                                if (pageNumbers.length > 0) {
                                    result.totalPages = Math.max(...pageNumbers);
                                }
                            }
                        }
                    }

                    // If we couldn't find pagination via containers, look for URL patterns
                    if (!result.hasPagination) {
                        const url = window.location.href;
                        const pagePatterns = [
                            /[?&]page=(\\d+)/,
                            /[?&]p=(\\d+)/,
                            /\\/page\\/(\\d+)/,
                            /\\/p\\/(\\d+)/
                        ];

                        for (const pattern of pagePatterns) {
                            const match = url.match(pattern);
                            if (match) {
                                result.hasPagination = true;
                                result.currentPage = parseInt(match[1]);
                                break;
                            }
                        }
                    }

                    return result;
                }

                return detectPagination();
            """)

            return pagination_info if pagination_info.get('hasPagination') else None
        except Exception as e:
            print(f"Error detecting pagination: {str(e)}")
            return None

    async def _find_next_page_link(self, context: BrowserContext, pagination_selector: Optional[str] = None, next_page_text: Optional[str] = None) -> Optional[str]:
        """Find the next page link on the current page."""
        try:
            # Build a JavaScript function to find the next page link
            js_code = """
                function findNextPageLink(paginationSelector, nextPageText) {
                    // First try using the provided selector if available
                    if (paginationSelector) {
                        const container = document.querySelector(paginationSelector);
                        if (container) {
                            // If next_page_text is provided, look for a link with that text
                            if (nextPageText) {
                                const links = Array.from(container.querySelectorAll('a'));
                                for (const link of links) {
                                    if (link.innerText.trim().toLowerCase().includes(nextPageText.toLowerCase())) {
                                        return link.href;
                                    }
                                }
                            }

                            // Look for a link with common "next page" indicators
                            const nextLink = container.querySelector('a[rel="next"], a.next, a.pagination-next, a[aria-label="Next page"]');
                            if (nextLink) {
                                return nextLink.href;
                            }

                            // Look for links with common "next" text patterns
                            const links = Array.from(container.querySelectorAll('a'));
                            for (const link of links) {
                                const text = link.innerText.trim().toLowerCase();
                                if (/next|›|»|forward|→/i.test(text)) {
                                    return link.href;
                                }
                            }
                        }
                    }

                    // If no selector provided or no link found with the selector, try common patterns

                    // Try rel="next" attribute (common standard)
                    const relNext = document.querySelector('a[rel="next"]');
                    if (relNext) {
                        return relNext.href;
                    }

                    // Try common class names and attributes
                    const commonSelectors = [
                        'a.next',
                        'a.pagination-next',
                        'a[aria-label="Next page"]',
                        '.pagination a.next',
                        '.pagination a:last-child',
                        '.pager a.next',
                        '.wp-pagenavi a.nextpostslink',
                        '.page-navigation a.next'
                    ];

                    for (const selector of commonSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.href) {
                            return element.href;
                        }
                    }

                    // Try links with common "next" text patterns
                    const allLinks = Array.from(document.querySelectorAll('a'));
                    for (const link of allLinks) {
                        const text = link.innerText.trim().toLowerCase();
                        if (nextPageText && text.includes(nextPageText.toLowerCase())) {
                            return link.href;
                        }
                        if (/^next( page)?$|^›$|^»$|^forward$|^→$/i.test(text)) {
                            return link.href;
                        }
                    }

                    // Try to find links with page numbers
                    const currentUrl = window.location.href;
                    const pagePatterns = [
                        /[?&]page=(\\d+)/,
                        /[?&]p=(\\d+)/,
                        /\\/page\\/(\\d+)/,
                        /\\/p\\/(\\d+)/
                    ];

                    for (const pattern of pagePatterns) {
                        const match = currentUrl.match(pattern);
                        if (match) {
                            const currentPage = parseInt(match[1]);
                            const nextPage = currentPage + 1;

                            // Try to find a link with the next page number
                            for (const link of allLinks) {
                                const text = link.innerText.trim();
                                if (text === nextPage.toString()) {
                                    return link.href;
                                }
                            }

                            // Try to construct the next page URL
                            if (pattern.toString().includes('[?&]')) {
                                // For query parameter patterns
                                const paramName = pattern.toString().includes('page=') ? 'page' : 'p';
                                const baseUrl = currentUrl.replace(new RegExp(`[?&]${paramName}=\\d+`), '');
                                const separator = baseUrl.includes('?') ? '&' : '?';
                                return `${baseUrl}${separator}${paramName}=${nextPage}`;
                            } else {
                                // For path patterns
                                const pathPart = pattern.toString().includes('/page/') ? '/page/' : '/p/';
                                return currentUrl.replace(new RegExp(`${pathPart}\\d+`), `${pathPart}${nextPage}`);
                            }
                        }
                    }

                    return null;
                }

                return findNextPageLink(arguments[0], arguments[1]);
            """

            # Execute the JavaScript function
            next_page_url = await context.execute_javascript(js_code, pagination_selector, next_page_text)
            return next_page_url
        except Exception as e:
            logger.error(f"Error finding next page link: {str(e)}")
            return None

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are on the same domain."""
        try:
            from urllib.parse import urlparse

            # Parse the URLs
            parsed_url1 = urlparse(url1)
            parsed_url2 = urlparse(url2)

            # Extract the domains
            domain1 = parsed_url1.netloc
            domain2 = parsed_url2.netloc

            # Remove 'www.' prefix if present
            if domain1.startswith('www.'):
                domain1 = domain1[4:]
            if domain2.startswith('www.'):
                domain2 = domain2[4:]

            # Compare the domains
            return domain1 == domain2
        except Exception as e:
            logger.error(f"Error comparing domains: {str(e)}")
            return False

    async def _extract_full_page(self, context: BrowserContext) -> Dict:
        """Extract a complete representation of the page with structure preserved."""
        try:
            page_data = await context.execute_javascript("""
                function extractFullPage() {
                    const result = {
                        metadata: {
                            title: document.title,
                            url: window.location.href,
                            language: document.documentElement.lang || 'unknown'
                        },
                        content: []
                    };

                    // Extract meta tags
                    const metaTags = {};
                    document.querySelectorAll('meta').forEach(meta => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property');
                        const content = meta.getAttribute('content');
                        if (name && content) {
                            metaTags[name] = content;
                        }
                    });
                    result.metadata.meta = metaTags;

                    // Process the main elements
                    function extractSection(element, depth = 0) {
                        // Skip invisible elements and common non-content areas
                        if (!element ||
                            !element.tagName ||
                            window.getComputedStyle(element).display === 'none' ||
                            window.getComputedStyle(element).visibility === 'hidden') {
                            return null;
                        }

                        // Skip script, style, noscript tags
                        if (['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(element.tagName)) {
                            return null;
                        }

                        const tag = element.tagName.toLowerCase();

                        // Special handling for certain tags
                        if (tag === 'img' && element.src) {
                            const rect = element.getBoundingClientRect();
                            if (rect.width >= 50 && rect.height >= 50) {
                                return {
                                    type: 'image',
                                    src: element.src,
                                    alt: element.alt || '',
                                    width: rect.width,
                                    height: rect.height
                                };
                            }
                            return null;
                        }

                        if (tag === 'a' && element.href) {
                            return {
                                type: 'link',
                                href: element.href,
                                text: element.innerText.trim(),
                                title: element.title || ''
                            };
                        }

                        if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tag)) {
                            return {
                                type: 'heading',
                                level: parseInt(tag.substring(1)),
                                text: element.innerText.trim()
                            };
                        }

                        if (tag === 'p') {
                            const text = element.innerText.trim();
                            if (text.length > 0) {
                                return {
                                    type: 'paragraph',
                                    text: text
                                };
                            }
                            return null;
                        }

                        if (tag === 'ul' || tag === 'ol') {
                            const items = Array.from(element.querySelectorAll('li'))
                                .map(li => li.innerText.trim())
                                .filter(text => text.length > 0);

                            if (items.length > 0) {
                                return {
                                    type: 'list',
                                    listType: tag === 'ul' ? 'bullet' : 'numbered',
                                    items: items
                                };
                            }
                            return null;
                        }

                        if (tag === 'table') {
                            const tableData = {
                                type: 'table',
                                headers: [],
                                rows: []
                            };

                            // Extract headers
                            const headerElements = element.querySelectorAll('th');
                            for (const th of headerElements) {
                                tableData.headers.push(th.innerText.trim());
                            }

                            // Extract rows
                            const rows = element.querySelectorAll('tr');
                            for (const row of rows) {
                                const cells = row.querySelectorAll('td');
                                if (cells.length > 0) {
                                    const rowData = [];
                                    for (const cell of cells) {
                                        rowData.push(cell.innerText.trim());
                                    }
                                    tableData.rows.push(rowData);
                                }
                            }

                            if (tableData.rows.length > 0) {
                                return tableData;
                            }
                            return null;
                        }

                        // For div, article, section, main - explore children
                        if (['div', 'article', 'section', 'main', 'aside', 'header', 'footer'].includes(tag) &&
                            element.children.length > 0) {
                            const children = [];
                            for (const child of element.children) {
                                const childData = extractSection(child, depth + 1);
                                if (childData) {
                                    children.push(childData);
                                }
                            }

                            if (children.length > 0) {
                                return {
                                    type: 'container',
                                    tag: tag,
                                    id: element.id || null,
                                    classes: element.className || null,
                                    children: children
                                };
                            }

                            // If no structured content found but there's text content
                            const text = element.innerText.trim();
                            if (text.length > 0 && !element.children.length) {
                                return {
                                    type: 'text',
                                    text: text
                                };
                            }
                        }

                        return null;
                    }

                    // Start with main content areas
                    const mainContentSelectors = [
                        'main', 'article', '#content', '.content', '.main', '.post', '.article', '[role="main"]'
                    ];

                    let mainContent = null;
                    for (const selector of mainContentSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            mainContent = extractSection(element);
                            if (mainContent) {
                                result.content.push({
                                    type: 'main_content',
                                    content: mainContent
                                });
                                break;
                            }
                        }
                    }

                    // If no main content found, try the body
                    if (!mainContent) {
                        // Look for significant sections in the body
                        for (const child of document.body.children) {
                            const content = extractSection(child);
                            if (content) {
                                result.content.push(content);
                            }
                        }
                    }

                    return result;
                }

                return extractFullPage();
            """)

            return page_data
        except Exception as e:
            print(f"Error extracting full page: {str(e)}")
            return {"error": str(e)}

    async def _extract_tables(self, context: BrowserContext, selector: str) -> List[Dict]:
        """Extract tables matching the given selector."""
        try:
            tables_data = await context.execute_javascript(f"""
                const results = [];
                const tables = document.querySelectorAll('{selector}');

                for (let i = 0; i < tables.length; i++) {{
                    const table = tables[i];
                    const tableData = {{
                        tableIndex: i,
                        headers: [],
                        rows: []
                    }};

                    // Extract headers from th elements, if any
                    const headerElements = table.querySelectorAll('th');
                    for (let j = 0; j < headerElements.length; j++) {{
                        tableData.headers.push(headerElements[j].innerText.trim());
                    }}

                    // Extract rows from tr elements
                    const rows = table.querySelectorAll('tr');
                    for (let j = 0; j < rows.length; j++) {{
                        const row = [];
                        const cells = rows[j].querySelectorAll('td');
                        for (let k = 0; k < cells.length; k++) {{
                            row.push(cells[k].innerText.trim());
                        }}
                        if (row.length > 0) {{
                            tableData.rows.push(row);
                        }}
                    }}

                    results.push(tableData);
                }}

                return results;
            """)
            return tables_data or []
        except Exception as e:
            print(f"Error extracting tables with selector '{selector}': {str(e)}")
            return []

    async def _extract_lists(self, context: BrowserContext, selector: str) -> List[Dict]:
        """Extract lists matching the given selector."""
        try:
            lists_data = await context.execute_javascript(f"""
                const results = [];
                const lists = document.querySelectorAll('{selector}');

                for (let i = 0; i < lists.length; i++) {{
                    const list = lists[i];
                    const listData = {{
                        listIndex: i,
                        items: []
                    }};

                    // Extract items from li elements
                    const items = list.querySelectorAll('li');
                    for (let j = 0; j < items.length; j++) {{
                        listData.items.push(items[j].innerText.trim());
                    }}

                    results.push(listData);
                }}

                return results;
            """)
            return lists_data or []
        except Exception as e:
            print(f"Error extracting lists with selector '{selector}': {str(e)}")
            return []

    async def _extract_elements(self, context: BrowserContext, selector: str) -> List[Dict]:
        """Extract elements matching the given selector."""
        try:
            elements_data = await context.execute_javascript(f"""
                const results = [];
                const elements = document.querySelectorAll('{selector}');

                for (let i = 0; i < elements.length; i++) {{
                    const el = elements[i];
                    results.push({{
                        index: i,
                        text: el.innerText.trim(),
                        tagName: el.tagName.toLowerCase()
                    }});
                }}

                return results;
            """)
            return elements_data or []
        except Exception as e:
            print(f"Error extracting elements with selector '{selector}': {str(e)}")
            return []

    async def _handle_infinite_scroll(self, context: BrowserContext) -> bool:
        """
        Detect and handle infinite scroll or lazy loading on a page.
        Returns True if infinite scroll was detected and handled.
        """
        try:
            # Check if the page might have infinite scroll or lazy loading
            scroll_detection_script = """
            // Check for common scroll event listeners
            const hasScrollListeners = !!window.onscroll ||
                                      document.addEventListener.toString().includes('scroll') ||
                                      document.body.onscroll;

            // Check for common infinite scroll libraries or patterns
            const hasInfiniteScrollIndicators =
                document.querySelector('.infinite-scroll') ||
                document.querySelector('[data-infinite-scroll]') ||
                document.querySelector('.lazy-load') ||
                document.querySelector('.load-more') ||
                !!window.InfiniteScroll ||
                !!window.infiniteScroll;

            // Check for large number of similar elements that might be loaded dynamically
            const potentialDynamicElements = document.querySelectorAll('div > div > div').length > 20 ||
                                            document.querySelectorAll('li').length > 30;

            return {
                hasScrollListeners,
                hasInfiniteScrollIndicators,
                potentialDynamicElements,
                viewportHeight: window.innerHeight,
                documentHeight: document.body.scrollHeight
            };
            """

            scroll_info = await context.execute_javascript(scroll_detection_script)

            # Determine if we should attempt infinite scroll handling
            has_infinite_scroll = (
                scroll_info.get('hasScrollListeners', False) or
                scroll_info.get('hasInfiniteScrollIndicators', False) or
                scroll_info.get('potentialDynamicElements', False)
            )

            if has_infinite_scroll:
                print("Potential infinite scroll detected, attempting to load more content...")

                # Get initial document height
                initial_height = await context.execute_javascript("return document.body.scrollHeight")

                # Perform gradual scrolling to trigger content loading
                for i in range(5):  # Try 5 scroll attempts
                    # Scroll down gradually
                    scroll_position = (i + 1) * 0.2 * initial_height
                    await context.execute_javascript(f"window.scrollTo(0, {scroll_position})")
                    await asyncio.sleep(1)  # Wait for content to load

                    # Check if new content was loaded
                    new_height = await context.execute_javascript("return document.body.scrollHeight")
                    if new_height > initial_height * 1.1:  # Height increased by at least 10%
                        print(f"New content loaded after scrolling ({initial_height} -> {new_height})")
                        initial_height = new_height

                        # If we found new content, do a few more scrolls
                        for j in range(3):
                            scroll_position = (j + 6) * 0.15 * initial_height
                            await context.execute_javascript(f"window.scrollTo(0, {scroll_position})")
                            await asyncio.sleep(1.5)  # Longer wait for content loading

                # Scroll back to top
                await context.execute_javascript("window.scrollTo(0, 0)")
                return True

            return False
        except Exception as e:
            print(f"Error during infinite scroll detection: {str(e)}")
            return False

    async def _extract_page_metadata(self, context: BrowserContext) -> Dict:
        """Extract metadata from the page."""
        try:
            metadata = await context.execute_javascript("""
                function getMetadata() {
                    const metadata = {};

                    // Extract basic metadata
                    metadata.title = document.title || '';
                    metadata.url = window.location.href;

                    // Get meta tags
                    const metaTags = {};
                    document.querySelectorAll('meta').forEach(meta => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property');
                        const content = meta.getAttribute('content');
                        if (name && content) {
                            metaTags[name] = content;
                        }
                    });
                    metadata.meta = metaTags;

                    // Get canonical URL
                    const canonical = document.querySelector('link[rel="canonical"]');
                    if (canonical) {
                        metadata.canonical = canonical.getAttribute('href');
                    }

                    // Get language
                    metadata.language = document.documentElement.lang || 'unknown';

                    return metadata;
                }

                return getMetadata();
            """)
            return metadata or {}
        except Exception as e:
            print(f"Error extracting page metadata: {str(e)}")
            return {"error": str(e)}