import asyncio
import json
import re
from typing import Optional, List, Dict, Any

from pydantic import Field

from app.config import config
from app.tools.base import BaseTool, ToolResult
from app.tools.enhanced_browser_tool import EnhancedBrowserTool
from app.tools.web_ui_browser_tool import WebUIBrowserTool


class FallbackBrowserTool(BaseTool):
    """
    A browser tool that combines EnhancedBrowserTool with WebUIBrowserTool as a fallback.
    This tool first attempts to use the regular browser automation, and if that fails,
    it automatically falls back to using the browser-use/web-ui approach.
    """

    name: str = "fallback_browser"
    description: str = """
    Advanced browser tool with automatic fallback capabilities for handling websites with strong anti-scraping measures.
    This tool first attempts to use regular browser automation, and if that fails due to anti-scraping measures,
    it automatically falls back to using the browser-use/web-ui approach.
    Supports all standard browser actions with enhanced reliability.
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
                    "stealth_mode",
                    "random_delay",
                    "rotate_user_agent",
                    "extract_structured",
                    "navigate_and_extract",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'navigate' actions",
            },
            "selector": {
                "type": "string",
                "description": "CSS selector for element interactions or extraction",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in milliseconds (default: 30000)",
            },
            # Additional parameters from EnhancedBrowserTool
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
            "extraction_type": {
                "type": "string",
                "description": "Type of data to extract (table, list, etc.) for 'extract_structured' action",
            },
            "extract_type": {
                "type": "string",
                "description": "Type of content to extract for 'navigate_and_extract' action (text, links, tables)",
            },
        },
        "required": ["action"],
    }

    # Primary and fallback browser tools
    primary_browser: EnhancedBrowserTool = Field(default_factory=EnhancedBrowserTool)
    fallback_browser: WebUIBrowserTool = Field(default_factory=WebUIBrowserTool)
    
    # Fallback configuration
    auto_fallback: bool = Field(default=True)  # Whether to automatically try fallback
    fallback_attempts: int = Field(default=0)  # Counter for fallback attempts
    max_fallback_attempts: int = Field(default=3)  # Maximum fallback attempts
    
    def __init__(self, **data):
        super().__init__(**data)
        # Apply configuration from config.toml if available
        if config.browser_config:
            if hasattr(config.browser_config, "enable_fallback"):
                self.auto_fallback = config.browser_config.enable_fallback
            if hasattr(config.browser_config, "max_fallback_attempts"):
                self.max_fallback_attempts = config.browser_config.max_fallback_attempts
            if hasattr(config.browser_config, "web_ui_url") and hasattr(self.fallback_browser, "web_ui_url"):
                self.fallback_browser.web_ui_url = config.browser_config.web_ui_url

    # Anti-scraping detection patterns
    anti_scraping_patterns: List[str] = Field(default_factory=lambda: [
        "captcha", "cloudflare", "access denied", "forbidden", "blocked", 
        "403", "bot detection", "automated access", "too many requests", 
        "rate limited", "429", "security check", "challenge", "verify"
    ])

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a browser action with automatic fallback if the primary method fails.
        """
        # Reset fallback attempts counter for new actions
        if action in ["navigate", "navigate_and_extract"]:
            self.fallback_attempts = 0

        # First try with the primary browser (EnhancedBrowserTool)
        try:
            result = await self.primary_browser.execute(action=action, url=url, selector=selector, timeout=timeout, **kwargs)
            
            # Check if the result indicates an anti-scraping measure or other failure
            if self._should_fallback(result):
                return await self._try_fallback(action, url, selector, timeout, **kwargs)
            
            return result
        
        except Exception as e:
            # If primary browser throws an exception, try fallback
            error_message = str(e)
            if self.auto_fallback and self._is_anti_scraping_error(error_message):
                return await self._try_fallback(action, url, selector, timeout, **kwargs)
            
            # Re-raise the exception if we shouldn't fallback
            return ToolResult(error=f"Primary browser error: {error_message}")

    async def _try_fallback(self, action: str, url: Optional[str] = None, selector: Optional[str] = None, 
                          timeout: Optional[int] = None, **kwargs) -> ToolResult:
        """
        Try the fallback browser (WebUIBrowserTool) when primary browser fails.
        """
        self.fallback_attempts += 1
        if self.fallback_attempts > self.max_fallback_attempts:
            return ToolResult(error=f"Exceeded maximum fallback attempts ({self.max_fallback_attempts}). Unable to access content.")

        # Map the action from EnhancedBrowserTool to WebUIBrowserTool
        fallback_action = self._map_action_to_fallback(action)
        if not fallback_action:
            return ToolResult(error=f"Action '{action}' cannot be mapped to fallback browser")

        try:
            # Extract relevant parameters from kwargs for the fallback browser
            text = kwargs.get('text')
            script = kwargs.get('script')
            scroll_amount = kwargs.get('scroll_amount')
            
            # Execute with the fallback browser
            result = await self.fallback_browser.execute(
                action=fallback_action, 
                url=url, 
                selector=selector, 
                timeout=timeout,
                text=text,
                script=script,
                scroll_amount=scroll_amount
            )
            
            if not result.error:
                result.output = f"[FALLBACK BROWSER] {result.output}"
            
            return result
        
        except Exception as e:
            return ToolResult(error=f"Fallback browser error: {str(e)}")

    def _should_fallback(self, result: ToolResult) -> bool:
        """
        Determine if we should try the fallback browser based on the result.
        """
        if not self.auto_fallback:
            return False
            
        if not result or not isinstance(result, ToolResult):
            return True
            
        if result.error and self._is_anti_scraping_error(result.error):
            return True
            
        # Check for empty or very limited content that might indicate blocking
        if not result.error and result.output and len(result.output.strip()) < 100:
            # Check if the limited content contains indicators of blocking
            return any(pattern.lower() in result.output.lower() for pattern in self.anti_scraping_patterns)
            
        return False

    def _is_anti_scraping_error(self, error_message: str) -> bool:
        """
        Check if an error message indicates anti-scraping measures.
        """
        error_message = error_message.lower()
        return any(pattern.lower() in error_message for pattern in self.anti_scraping_patterns)

    def _map_action_to_fallback(self, action: str) -> Optional[str]:
        """
        Map actions from EnhancedBrowserTool to equivalent WebUIBrowserTool actions.
        """
        action_mapping = {
            "navigate": "navigate",
            "get_text": "get_content",
            "get_html": "get_content",
            "screenshot": "screenshot",
            "extract_structured": "extract_data",
            "navigate_and_extract": "navigate",  # Will need to follow up with get_content
            "click": "click",
            "input_text": "input_text",
            "execute_js": "execute_js",
            "scroll": "scroll"
        }
        
        return action_mapping.get(action)

    async def cleanup(self) -> None:
        """
        Clean up resources for both browser tools.
        """
        await self.primary_browser.cleanup()
        await self.fallback_browser.cleanup()