import random
import time
import logging
import aiohttp
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field

from app.config import config

logger = logging.getLogger(__name__)


class Proxy(BaseModel):
    """Model for a proxy server configuration"""
    server: str
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    last_used: float = Field(default_factory=time.time)
    success_count: int = 0
    failure_count: int = 0
    banned_until: Optional[float] = None
    
    @property
    def is_banned(self) -> bool:
        """Check if the proxy is currently banned"""
        if self.banned_until is None:
            return False
        return time.time() < self.banned_until
    
    @property
    def success_ratio(self) -> float:
        """Calculate the success ratio of this proxy"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0  # No data yet, assume good
        return self.success_count / total
    
    @property
    def formatted_url(self) -> str:
        """Return the proxy URL in the format expected by browser-use"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.server}"
        return f"{self.protocol}://{self.server}"
    
    def to_browser_use_format(self) -> Dict[str, str]:
        """Convert to the format expected by browser-use ProxySettings"""
        result = {"server": f"{self.protocol}://{self.server}"}
        if self.username:
            result["username"] = self.username
        if self.password:
            result["password"] = self.password
        return result


class ProxyManager:
    """Manages a pool of proxies with rotation and health checking capabilities"""
    
    def __init__(self):
        self.proxies: List[Proxy] = []
        self.current_index: int = 0
        self.rotation_strategy: str = "round_robin"  # round_robin, random, performance
        self.ban_threshold: int = 3  # Number of failures before temporary ban
        self.ban_duration: int = 300  # Ban duration in seconds (5 minutes)
        self.initialized: bool = False
        self.test_url: str = "https://httpbin.org/ip"
        self._lock = asyncio.Lock()
    
    async def initialize(self, proxies: Optional[List[Dict[str, Any]]] = None):
        """Initialize the proxy manager with a list of proxies"""
        async with self._lock:
            if self.initialized:
                return
            
            # If proxies are provided, use them
            if proxies:
                for proxy_data in proxies:
                    self.proxies.append(Proxy(**proxy_data))
            
            # If no proxies provided but config has a proxy, use it
            elif config.browser_config and config.browser_config.proxy:
                proxy = config.browser_config.proxy
                if proxy.server:
                    self.proxies.append(Proxy(
                        server=proxy.server,
                        username=proxy.username,
                        password=proxy.password
                    ))
            
            # If still no proxies, try to load from a proxy provider service
            if not self.proxies:
                try:
                    await self._load_from_provider()
                except Exception as e:
                    logger.warning(f"Failed to load proxies from provider: {e}")
            
            self.initialized = True
            logger.info(f"Proxy manager initialized with {len(self.proxies)} proxies")
    
    async def _load_from_provider(self, provider: str = "default"):
        """Load proxies from a provider service"""
        # This is a placeholder. In a real implementation, you would
        # connect to a proxy provider API and load proxies.
        # For now, we'll just add some example proxies for testing
        if provider == "default":
            # These are just examples and won't work in production
            # In a real implementation, you would fetch from a proxy service
            example_proxies = [
                # Add your actual proxies here or connect to a proxy service
            ]
            
            for proxy_data in example_proxies:
                self.proxies.append(Proxy(**proxy_data))
    
    async def get_next_proxy(self) -> Optional[Proxy]:
        """Get the next available proxy based on the rotation strategy"""
        if not self.initialized:
            await self.initialize()
        
        if not self.proxies:
            return None
        
        async with self._lock:
            available_proxies = [p for p in self.proxies if not p.is_banned]
            if not available_proxies:
                logger.warning("No available proxies! All are banned or none configured.")
                return None
            
            if self.rotation_strategy == "round_robin":
                self.current_index = (self.current_index + 1) % len(available_proxies)
                proxy = available_proxies[self.current_index]
            
            elif self.rotation_strategy == "random":
                proxy = random.choice(available_proxies)
            
            elif self.rotation_strategy == "performance":
                # Sort by success ratio and pick the best one
                available_proxies.sort(key=lambda p: p.success_ratio, reverse=True)
                proxy = available_proxies[0]
            
            else:  # Default to round robin
                self.current_index = (self.current_index + 1) % len(available_proxies)
                proxy = available_proxies[self.current_index]
            
            proxy.last_used = time.time()
            return proxy
    
    async def report_result(self, proxy: Proxy, success: bool):
        """Report the result of using a proxy"""
        async with self._lock:
            if proxy not in self.proxies:
                return
            
            if success:
                proxy.success_count += 1
            else:
                proxy.failure_count += 1
                if proxy.failure_count >= self.ban_threshold:
                    proxy.banned_until = time.time() + self.ban_duration
                    logger.warning(f"Proxy {proxy.server} banned for {self.ban_duration} seconds")
    
    async def test_proxies(self):
        """Test all proxies and update their status"""
        if not self.initialized:
            await self.initialize()
        
        for proxy in self.proxies:
            success = await self._test_proxy(proxy)
            await self.report_result(proxy, success)
    
    async def _test_proxy(self, proxy: Proxy) -> bool:
        """Test if a proxy is working"""
        try:
            proxy_url = proxy.formatted_url
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.test_url, proxy=proxy_url) as response:
                    if response.status == 200:
                        return True
            return False
        except Exception as e:
            logger.debug(f"Proxy test failed for {proxy.server}: {e}")
            return False
    
    def set_rotation_strategy(self, strategy: str):
        """Set the proxy rotation strategy"""
        valid_strategies = ["round_robin", "random", "performance"]
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid rotation strategy. Must be one of: {valid_strategies}")
        self.rotation_strategy = strategy
    
    async def add_proxy(self, proxy_data: Dict[str, Any]):
        """Add a new proxy to the pool"""
        async with self._lock:
            proxy = Proxy(**proxy_data)
            self.proxies.append(proxy)
            return proxy
    
    async def remove_proxy(self, server: str):
        """Remove a proxy from the pool"""
        async with self._lock:
            self.proxies = [p for p in self.proxies if p.server != server]
    
    async def clear_bans(self):
        """Clear all proxy bans"""
        async with self._lock:
            for proxy in self.proxies:
                proxy.banned_until = None
                proxy.failure_count = 0


# Singleton instance
proxy_manager = ProxyManager()