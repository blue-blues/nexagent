"""
Browser Factory for Nexagent.

This module provides a factory for creating and managing browser instances.
It supports different browser types and configurations.
"""

import asyncio
from typing import Dict, Optional, Any, List
import logging

from app.tools.enhanced_browser_tool import EnhancedBrowserTool
from app.tools.fallback_browser_tool import FallbackBrowserTool
from app.tools.web_ui_browser_tool import WebUIBrowserTool
from app.config import config
from app.logger import logger

class BrowserFactory:
    """
    Factory for creating and managing browser instances.
    
    This class provides methods for creating, managing, and cleaning up browser instances.
    It supports different browser types and configurations.
    """
    
    # Singleton instance
    _instance = None
    
    # Browser instances
    _browsers: Dict[str, Any] = {}
    
    # Lock for thread safety
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls):
        """Get the singleton instance of the browser factory."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance
    
    async def _initialize(self):
        """Initialize the browser factory."""
        logger.info("Initializing browser factory")
        
        # Load configuration
        self.browser_config = getattr(config, "browser_config", None)
        
        # Initialize browser pool settings
        self.max_browsers = getattr(self.browser_config, "max_browsers", 3) if self.browser_config else 3
        self.browser_timeout = getattr(self.browser_config, "browser_timeout", 300) if self.browser_config else 300
        
        logger.info(f"Browser factory initialized with max_browsers={self.max_browsers}, browser_timeout={self.browser_timeout}")
    
    async def get_browser(self, browser_type: str = "enhanced", new_instance: bool = False) -> Any:
        """
        Get a browser instance of the specified type.
        
        Args:
            browser_type: The type of browser to get ("enhanced", "fallback", "webui")
            new_instance: Whether to create a new instance or reuse an existing one
            
        Returns:
            A browser instance of the specified type
        """
        async with self._lock:
            browser_key = f"{browser_type}_{len(self._browsers)}" if new_instance else browser_type
            
            # Check if we already have this browser type
            if not new_instance and browser_key in self._browsers:
                logger.info(f"Reusing existing {browser_type} browser instance")
                return self._browsers[browser_key]
            
            # Check if we've reached the maximum number of browsers
            if len(self._browsers) >= self.max_browsers and new_instance:
                logger.warning(f"Maximum number of browsers ({self.max_browsers}) reached, cleaning up oldest browser")
                await self._cleanup_oldest_browser()
            
            # Create a new browser instance
            logger.info(f"Creating new {browser_type} browser instance")
            browser = await self._create_browser(browser_type)
            
            if browser:
                self._browsers[browser_key] = {
                    "instance": browser,
                    "created_at": asyncio.get_event_loop().time(),
                    "last_used": asyncio.get_event_loop().time(),
                    "type": browser_type
                }
                return browser
            
            logger.error(f"Failed to create {browser_type} browser instance")
            return None
    
    async def _create_browser(self, browser_type: str) -> Any:
        """
        Create a new browser instance of the specified type.
        
        Args:
            browser_type: The type of browser to create
            
        Returns:
            A new browser instance of the specified type
        """
        try:
            if browser_type == "enhanced":
                return EnhancedBrowserTool()
            elif browser_type == "fallback":
                return FallbackBrowserTool()
            elif browser_type == "webui":
                return WebUIBrowserTool()
            else:
                logger.error(f"Unknown browser type: {browser_type}")
                return None
        except Exception as e:
            logger.error(f"Error creating {browser_type} browser: {str(e)}", exc_info=True)
            return None
    
    async def _cleanup_oldest_browser(self):
        """Clean up the oldest browser instance."""
        if not self._browsers:
            return
        
        # Find the oldest browser
        oldest_key = None
        oldest_time = float('inf')
        
        for key, data in self._browsers.items():
            if data["last_used"] < oldest_time:
                oldest_time = data["last_used"]
                oldest_key = key
        
        if oldest_key:
            logger.info(f"Cleaning up oldest browser: {oldest_key}")
            await self.close_browser(oldest_key)
    
    async def close_browser(self, browser_key: str):
        """
        Close a specific browser instance.
        
        Args:
            browser_key: The key of the browser to close
        """
        if browser_key in self._browsers:
            browser_data = self._browsers[browser_key]
            browser = browser_data["instance"]
            
            try:
                logger.info(f"Closing browser: {browser_key}")
                
                # Check if the browser has a close method
                if hasattr(browser, "close") and callable(getattr(browser, "close")):
                    await browser.close()
                
                # Remove from the dictionary
                del self._browsers[browser_key]
                
                # Force garbage collection
                import gc
                gc.collect()
                
                logger.info(f"Browser {browser_key} closed successfully")
            
            except Exception as e:
                logger.error(f"Error closing browser {browser_key}: {str(e)}", exc_info=True)
    
    async def close_all_browsers(self):
        """Close all browser instances."""
        logger.info(f"Closing all browsers ({len(self._browsers)} instances)")
        
        for browser_key in list(self._browsers.keys()):
            await self.close_browser(browser_key)
        
        logger.info("All browsers closed")
    
    def update_last_used(self, browser_key: str):
        """
        Update the last used timestamp for a browser.
        
        Args:
            browser_key: The key of the browser to update
        """
        if browser_key in self._browsers:
            self._browsers[browser_key]["last_used"] = asyncio.get_event_loop().time()
    
    async def cleanup_idle_browsers(self, max_idle_time: float = 300):
        """
        Clean up browser instances that have been idle for too long.
        
        Args:
            max_idle_time: The maximum idle time in seconds before a browser is cleaned up
        """
        current_time = asyncio.get_event_loop().time()
        
        for browser_key in list(self._browsers.keys()):
            browser_data = self._browsers[browser_key]
            idle_time = current_time - browser_data["last_used"]
            
            if idle_time > max_idle_time:
                logger.info(f"Cleaning up idle browser {browser_key} (idle for {idle_time:.2f} seconds)")
                await self.close_browser(browser_key)
