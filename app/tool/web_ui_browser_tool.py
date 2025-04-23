import asyncio
import json
import random
from typing import Optional, List, Dict, Any

from pydantic import Field

from app.config import config
from app.tool.base import BaseTool, ToolResult
from app.tool.enhanced_browser_tool import EnhancedBrowserTool


class WebUIBrowserTool(BaseTool):
    """
    Alternative browser tool using browser-use/web-ui for when regular scraping fails.
    This tool serves as a fallback mechanism when the EnhancedBrowserTool encounters
    anti-scraping measures or other failures.
    """

    name: str = "web_ui_browser"
    description: str = """
    Alternative browser tool using browser-use/web-ui for handling websites with strong anti-scraping measures.
    This tool is used as a fallback when regular browser automation fails.
    It provides a more robust approach to accessing websites that actively block automated access.
    """

    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "get_content",
                    "extract_data",
                    "screenshot",
                    "click",
                    "input_text",
                    "execute_js",
                    "scroll",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL to navigate to",
            },
            "selector": {
                "type": "string",
                "description": "CSS selector for extracting specific content or interacting with elements",
            },
            "text": {
                "type": "string",
                "description": "Text to input for 'input_text' action",
            },
            "script": {
                "type": "string",
                "description": "JavaScript code for 'execute_js' action",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive for down, negative for up) for 'scroll' action",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in milliseconds (default: 60000)",
            },
        },
        "required": ["action"],
    }

    # Configuration for the web-ui browser
    web_ui_url: str = Field(default="http://localhost:3000")
    default_timeout: int = Field(default=60000)  # 60 seconds default timeout

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        timeout: Optional[int] = None,
        text: Optional[str] = None,
        script: Optional[str] = None,
        scroll_amount: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a specified browser action using the web-ui interface.
        """
        actual_timeout = timeout or self.default_timeout

        try:
            # Import here to avoid dependency issues if the package is not installed
            try:
                from browser_use_web_ui import WebUIBrowser
                from browser_use_web_ui.config import WebUIConfig
            except ImportError:
                return ToolResult(error="browser-use/web-ui package is not installed. Please install it with 'pip install browser-use-web-ui'.")

            # Initialize the web-ui browser
            config_params = {
                "base_url": self.web_ui_url,
                "timeout": actual_timeout,
            }

            # Add browser configuration from config file if available
            if config.browser_config:
                if hasattr(config.browser_config, "headless"):
                    config_params["headless"] = config.browser_config.headless
                if hasattr(config.browser_config, "proxy") and config.browser_config.proxy:
                    config_params["proxy"] = {
                        "server": config.browser_config.proxy.server,
                        "username": config.browser_config.proxy.username,
                        "password": config.browser_config.proxy.password,
                    }

            browser_config = WebUIConfig(**config_params)
            browser = WebUIBrowser(browser_config)

            # Execute the requested action
            if action == "navigate":
                if not url:
                    return ToolResult(error="URL is required for 'navigate' action")
                
                result = await browser.navigate(url)
                return ToolResult(output=f"Successfully navigated to {url}")

            elif action == "get_content":
                content = await browser.get_page_content()
                return ToolResult(output=content)

            elif action == "extract_data":
                if not selector:
                    return ToolResult(error="Selector is required for 'extract_data' action")
                
                data = await browser.extract_elements(selector)
                return ToolResult(output=json.dumps(data, ensure_ascii=False))

            elif action == "screenshot":
                screenshot_data = await browser.take_screenshot()
                # Return base64 encoded screenshot
                return ToolResult(output=f"Screenshot captured successfully: {screenshot_data[:50]}...")
                
            elif action == "click":
                if not selector:
                    return ToolResult(error="Selector is required for 'click' action")
                
                await browser.click_element(selector)
                return ToolResult(output=f"Successfully clicked element with selector: {selector}")
                
            elif action == "input_text":
                if not selector:
                    return ToolResult(error="Selector is required for 'input_text' action")
                if text is None:
                    return ToolResult(error="Text is required for 'input_text' action")
                
                await browser.input_text(selector, text)
                return ToolResult(output=f"Successfully input text into element with selector: {selector}")
                
            elif action == "execute_js":
                if not script:
                    return ToolResult(error="Script is required for 'execute_js' action")
                
                result = await browser.execute_javascript(script)
                return ToolResult(output=f"Successfully executed JavaScript with result: {result}")
                
            elif action == "scroll":
                amount = scroll_amount or 500  # Default scroll amount
                
                if amount > 0:
                    await browser.execute_javascript(f"window.scrollBy(0, {amount});")
                    return ToolResult(output=f"Successfully scrolled down by {amount} pixels")
                else:
                    await browser.execute_javascript(f"window.scrollBy(0, {amount});")
                    return ToolResult(output=f"Successfully scrolled up by {abs(amount)} pixels")

            else:
                return ToolResult(error=f"Unsupported action: {action}")

        except Exception as e:
            return ToolResult(error=f"Error executing web-ui browser action: {str(e)}")
        finally:
            # Clean up resources
            if 'browser' in locals():
                await browser.close()

    async def cleanup(self) -> None:
        """Clean up resources."""
        # No persistent browser instance to clean up
        pass
