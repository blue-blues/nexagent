"""
Enhanced browser sandbox for secure web browsing.

This module provides a secure environment for web browsing operations
with proper resource management and security restrictions.
"""

import asyncio
import os
import tempfile
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.logger import logger


class BrowserSandbox:
    """
    A sandbox for browser operations with security restrictions.
    
    This class provides methods for safely performing web browsing operations
    with proper resource management and security restrictions.
    """
    
    def __init__(
        self,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        timeout: int = 30000,
        max_pages: int = 5,
        allowed_domains: Optional[List[str]] = None
    ):
        """
        Initialize the browser sandbox.
        
        Args:
            headless: Whether to run the browser in headless mode
            user_data_dir: Directory to store browser data
            timeout: Default timeout for browser operations in milliseconds
            max_pages: Maximum number of pages allowed
            allowed_domains: List of allowed domains (None for all domains)
        """
        self.headless = headless
        self.user_data_dir = user_data_dir or tempfile.mkdtemp(prefix="nexagent_browser_")
        self.timeout = timeout
        self.max_pages = max_pages
        self.allowed_domains = allowed_domains
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.pages = {}
        self.page_count = 0
        
        logger.info(f"Initialized browser sandbox with user data dir: {self.user_data_dir}")
    
    async def _initialize(self) -> BrowserContext:
        """
        Initialize the browser and context.
        
        Returns:
            The browser context
        """
        if self.playwright is None:
            self.playwright = await async_playwright().start()
        
        if self.browser is None:
            # Launch the browser with enhanced security settings
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                    "--disable-web-security",
                    "--disable-popup-blocking",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ]
            )
        
        if self.context is None:
            # Create a browser context with enhanced privacy settings
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
                java_script_enabled=True,
                user_data_dir=self.user_data_dir,
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation", "notifications"],
            )
            
            # Set default timeout
            self.context.set_default_timeout(self.timeout)
        
        return self.context
    
    def _is_allowed_url(self, url: str) -> bool:
        """
        Check if a URL is allowed based on domain restrictions.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL is allowed, False otherwise
        """
        if not self.allowed_domains:
            return True
        
        try:
            domain = urlparse(url).netloc
            return any(domain.endswith(allowed_domain) for allowed_domain in self.allowed_domains)
        except Exception:
            return False
    
    async def create_page(self, page_id: Optional[str] = None) -> str:
        """
        Create a new browser page.
        
        Args:
            page_id: Optional page ID
            
        Returns:
            The page ID
        """
        # Initialize browser if needed
        await self._initialize()
        
        # Check page limit
        if self.page_count >= self.max_pages:
            raise ValueError(f"Maximum number of pages ({self.max_pages}) reached")
        
        # Generate page ID if not provided
        if page_id is None:
            page_id = f"page_{self.page_count + 1}"
        
        # Create a new page
        page = await self.context.new_page()
        self.pages[page_id] = page
        self.page_count += 1
        
        logger.info(f"Created new browser page with ID: {page_id}")
        
        return page_id
    
    async def close_page(self, page_id: str) -> bool:
        """
        Close a browser page.
        
        Args:
            page_id: The page ID
            
        Returns:
            True if the page was closed, False otherwise
        """
        if page_id not in self.pages:
            return False
        
        page = self.pages[page_id]
        await page.close()
        del self.pages[page_id]
        self.page_count -= 1
        
        logger.info(f"Closed browser page with ID: {page_id}")
        
        return True
    
    async def navigate(self, page_id: str, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL in a browser page.
        
        Args:
            page_id: The page ID
            url: The URL to navigate to
            
        Returns:
            A dictionary with navigation results
        """
        if page_id not in self.pages:
            raise ValueError(f"Page with ID {page_id} does not exist")
        
        # Check if URL is allowed
        if not self._is_allowed_url(url):
            raise ValueError(f"URL {url} is not allowed")
        
        page = self.pages[page_id]
        
        try:
            # Navigate to the URL
            response = await page.goto(url, wait_until="domcontentloaded")
            
            # Get page information
            title = await page.title()
            content = await page.content()
            
            return {
                'url': page.url,
                'title': title,
                'status': response.status if response else None,
                'content_length': len(content),
                'success': True,
            }
        except Exception as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            return {
                'url': url,
                'error': str(e),
                'success': False,
            }
    
    async def get_content(self, page_id: str) -> str:
        """
        Get the HTML content of a page.
        
        Args:
            page_id: The page ID
            
        Returns:
            The HTML content
        """
        if page_id not in self.pages:
            raise ValueError(f"Page with ID {page_id} does not exist")
        
        page = self.pages[page_id]
        return await page.content()
    
    async def get_text(self, page_id: str) -> str:
        """
        Get the text content of a page.
        
        Args:
            page_id: The page ID
            
        Returns:
            The text content
        """
        if page_id not in self.pages:
            raise ValueError(f"Page with ID {page_id} does not exist")
        
        page = self.pages[page_id]
        return await page.evaluate("() => document.body.innerText")
    
    async def screenshot(self, page_id: str, path: Optional[str] = None) -> bytes:
        """
        Take a screenshot of a page.
        
        Args:
            page_id: The page ID
            path: Optional path to save the screenshot
            
        Returns:
            The screenshot as bytes
        """
        if page_id not in self.pages:
            raise ValueError(f"Page with ID {page_id} does not exist")
        
        page = self.pages[page_id]
        
        if path:
            return await page.screenshot(path=path)
        else:
            return await page.screenshot()
    
    async def click(self, page_id: str, selector: str) -> bool:
        """
        Click an element on a page.
        
        Args:
            page_id: The page ID
            selector: The CSS selector for the element
            
        Returns:
            True if the click was successful, False otherwise
        """
        if page_id not in self.pages:
            raise ValueError(f"Page with ID {page_id} does not exist")
        
        page = self.pages[page_id]
        
        try:
            await page.click(selector)
            return True
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {str(e)}")
            return False
    
    async def type(self, page_id: str, selector: str, text: str) -> bool:
        """
        Type text into an element on a page.
        
        Args:
            page_id: The page ID
            selector: The CSS selector for the element
            text: The text to type
            
        Returns:
            True if typing was successful, False otherwise
        """
        if page_id not in self.pages:
            raise ValueError(f"Page with ID {page_id} does not exist")
        
        page = self.pages[page_id]
        
        try:
            await page.fill(selector, text)
            return True
        except Exception as e:
            logger.error(f"Error typing into element {selector}: {str(e)}")
            return False
    
    async def extract_links(self, page_id: str) -> List[Dict[str, str]]:
        """
        Extract links from a page.
        
        Args:
            page_id: The page ID
            
        Returns:
            A list of dictionaries with link information
        """
        if page_id not in self.pages:
            raise ValueError(f"Page with ID {page_id} does not exist")
        
        page = self.pages[page_id]
        
        links = await page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll('a')).map(a => {
                    return {
                        href: a.href,
                        text: a.innerText.trim(),
                        title: a.title || null
                    };
                });
            }
        """)
        
        return links
    
    async def extract_text_content(self, page_id: str, selector: str) -> str:
        """
        Extract text content from elements matching a selector.
        
        Args:
            page_id: The page ID
            selector: The CSS selector
            
        Returns:
            The extracted text content
        """
        if page_id not in self.pages:
            raise ValueError(f"Page with ID {page_id} does not exist")
        
        page = self.pages[page_id]
        
        try:
            elements = await page.query_selector_all(selector)
            texts = []
            
            for element in elements:
                text = await element.inner_text()
                texts.append(text)
            
            return "\n".join(texts)
        except Exception as e:
            logger.error(f"Error extracting text from {selector}: {str(e)}")
            return ""
    
    async def close(self):
        """Close the browser and clean up resources."""
        # Close all pages
        for page_id in list(self.pages.keys()):
            await self.close_page(page_id)
        
        # Close browser and context
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        logger.info("Closed browser sandbox and cleaned up resources")


# Create a global instance with default settings
default_browser_sandbox = BrowserSandbox()
