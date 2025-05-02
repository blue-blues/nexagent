import asyncio
import logging
import random
from typing import Optional, Dict, Any, List, Tuple

from browser_use import Browser as BrowserUseBrowser
from browser_use.browser.browser import ProxySettings
from browser_use.browser.context import BrowserContext, BrowserContextConfig

from app.config import config
from app.tools.proxy_manager import proxy_manager, Proxy
from app.tools.captcha_handler import captcha_handler

logger = logging.getLogger(__name__)


class HeadlessBrowserManager:
    """
    Manages headless browser instances with enhanced stealth capabilities,
    proxy rotation, and captcha handling.
    """
    
    def __init__(self):
        self.browser: Optional[BrowserUseBrowser] = None
        self.context: Optional[BrowserContext] = None
        self.current_proxy: Optional[Proxy] = None
        self.stealth_mode_enabled: bool = True
        self.random_delay_enabled: bool = True
        self.random_delay_config: Dict[str, int] = {"min": 500, "max": 2000}
        self.captcha_handling_enabled: bool = True
        self.user_agent_rotation_enabled: bool = True
        self.current_user_agent: Optional[str] = None
        self.initialized: bool = False
        self._lock = asyncio.Lock()
        
        # Common user agents for rotation
        self.user_agents: List[str] = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 OPR/82.0.4227.50",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0"
        ]
    
    async def initialize(self):
        """Initialize the headless browser manager"""
        async with self._lock:
            if self.initialized:
                return
            
            # Initialize proxy manager
            await proxy_manager.initialize()
            
            # Initialize browser with headless mode
            await self._initialize_browser(headless=True)
            
            self.initialized = True
            logger.info("Headless browser manager initialized")
    
    async def _initialize_browser(self, headless: bool = True, proxy: Optional[Proxy] = None):
        """Initialize the browser with the specified settings"""
        try:
            # Close existing browser if any
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    logger.warning(f"Error closing existing browser: {e}")
            
            # Prepare browser configuration
            browser_config_kwargs = {
                "headless": headless,
                "disable_security": True,
                "viewport_width": 1920,
                "viewport_height": 1080
            }
            
            # Add proxy if provided
            if proxy:
                self.current_proxy = proxy
                browser_config_kwargs["proxy"] = ProxySettings(
                    server=proxy.server,
                    username=proxy.username,
                    password=proxy.password
                )
            elif config.browser_config and config.browser_config.proxy and config.browser_config.proxy.server:
                browser_config_kwargs["proxy"] = ProxySettings(
                    server=config.browser_config.proxy.server,
                    username=config.browser_config.proxy.username,
                    password=config.browser_config.proxy.password
                )
            
            # Create browser instance
            self.browser = await BrowserUseBrowser.create(
                **browser_config_kwargs
            )
            
            # Create browser context
            context_config = BrowserContextConfig()
            self.context = await self.browser.new_context(context_config)
            
            # Apply stealth mode if enabled
            if self.stealth_mode_enabled:
                await self._apply_stealth_mode()
            
            # Apply user agent if rotation is enabled
            if self.user_agent_rotation_enabled:
                await self._rotate_user_agent()
            
            logger.info(f"Browser initialized with headless={headless}")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing browser: {e}")
            return False
    
    async def _apply_stealth_mode(self):
        """Apply stealth mode to avoid detection"""
        if not self.context:
            logger.warning("Cannot apply stealth mode: browser context not initialized")
            return False
        
        try:
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
            """
            
            await self.context.execute_javascript(stealth_script)
            logger.info("Stealth mode applied successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error applying stealth mode: {e}")
            return False
    
    async def _rotate_user_agent(self, specific_agent: Optional[str] = None):
        """Rotate or set a specific user agent"""
        if not self.context:
            logger.warning("Cannot rotate user agent: browser context not initialized")
            return False
        
        try:
            if specific_agent:
                self.current_user_agent = specific_agent
            else:
                self.current_user_agent = random.choice(self.user_agents)
            
            # Apply the user agent
            await self.context.execute_javascript(f"""
            Object.defineProperty(navigator, 'userAgent', {{
                get: () => '{self.current_user_agent}'
            }});
            """)
            
            logger.info(f"User agent set to: {self.current_user_agent}")
            return True
        
        except Exception as e:
            logger.error(f"Error rotating user agent: {e}")
            return False
    
    async def _rotate_proxy(self):
        """Rotate to a new proxy server"""
        try:
            # Get next available proxy
            new_proxy = await proxy_manager.get_next_proxy()
            if not new_proxy:
                logger.warning("No available proxies for rotation")
                return False
            
            # Reinitialize browser with new proxy
            success = await self._initialize_browser(headless=True, proxy=new_proxy)
            if success:
                logger.info(f"Rotated to new proxy: {new_proxy.server}")
                return True
            else:
                logger.error(f"Failed to rotate to new proxy: {new_proxy.server}")
                await proxy_manager.report_result(new_proxy, False)
                return False
        
        except Exception as e:
            logger.error(f"Error rotating proxy: {e}")
            return False
    
    async def navigate(self, url: str, timeout: int = 30000) -> Tuple[bool, str]:
        """Navigate to a URL with enhanced capabilities"""
        if not self.initialized:
            await self.initialize()
        
        if not self.context:
            logger.error("Browser context not initialized")
            return False, "Browser context not initialized"
        
        try:
            # Apply random delay if enabled
            if self.random_delay_enabled:
                delay_ms = random.randint(
                    self.random_delay_config["min"],
                    self.random_delay_config["max"]
                )
                await asyncio.sleep(delay_ms / 1000)  # Convert to seconds
            
            # Navigate to the URL
            await asyncio.wait_for(
                self.context.navigate_to(url),
                timeout=timeout / 1000  # Convert to seconds
            )
            
            # Wait for page to load more completely
            await asyncio.sleep(2)
            
            # Check for captcha if enabled
            if self.captcha_handling_enabled:
                captcha_detected, captcha_type, captcha_details = await captcha_handler.detect_captcha(self.context)
                
                if captcha_detected:
                    logger.info(f"Detected {captcha_type} captcha, attempting to solve")
                    solution = await captcha_handler.solve_captcha(self.context, captcha_type, captcha_details)
                    
                    if solution and solution.success:
                        success = await captcha_handler.apply_solution(self.context, solution)
                        if success:
                            logger.info(f"Successfully solved {captcha_type} captcha")
                            captcha_handler.store_solution(solution)
                        else:
                            logger.warning(f"Failed to apply {captcha_type} captcha solution")
                    else:
                        logger.warning(f"Failed to solve {captcha_type} captcha")
                        
                        # If captcha solving failed, try rotating proxy
                        if self.current_proxy:
                            await proxy_manager.report_result(self.current_proxy, False)
                            await self._rotate_proxy()
                            # Try navigating again with new proxy
                            return await self.navigate(url, timeout)
            
            # Report successful proxy usage if applicable
            if self.current_proxy:
                await proxy_manager.report_result(self.current_proxy, True)
            
            return True, "Navigation successful"
        
        except asyncio.TimeoutError:
            logger.error(f"Navigation to {url} timed out after {timeout}ms")
            
            # Report proxy failure if applicable
            if self.current_proxy:
                await proxy_manager.report_result(self.current_proxy, False)
            
            return False, f"Navigation timed out after {timeout}ms"
        
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            
            # Report proxy failure if applicable
            if self.current_proxy:
                await proxy_manager.report_result(self.current_proxy, False)
            
            return False, f"Navigation error: {str(e)}"
    
    async def handle_anti_scraping_error(self, error_message: str) -> bool:
        """Handle anti-scraping errors by rotating proxies and applying stealth techniques"""
        try:
            logger.info(f"Handling anti-scraping error: {error_message}")
            
            # First, ensure stealth mode is enabled
            if not self.stealth_mode_enabled:
                self.stealth_mode_enabled = True
                await self._apply_stealth_mode()
            
            # Rotate user agent
            await self._rotate_user_agent()
            
            # Rotate proxy if available
            proxy_rotated = await self._rotate_proxy()
            
            # If proxy rotation failed or no proxies available, try other techniques
            if not proxy_rotated:
                # Increase random delays
                self.random_delay_config = {"min": 1000, "max": 5000}
                self.random_delay_enabled = True
            
            return True
        
        except Exception as e:
            logger.error(f"Error handling anti-scraping measures: {e}")
            return False
    
    async def close(self):
        """Close the browser and clean up resources"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.context = None
                self.initialized = False
                logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")


# Singleton instance
headless_browser_manager = HeadlessBrowserManager()