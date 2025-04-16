"""
Brave Search Engine implementation for Nexagent.

This module provides a BraveSearchEngine class that implements the WebSearchEngine interface
for the Brave Search API.
"""

import requests
from typing import List, Optional
import os

from app.config import config
from app.tools.search.base import WebSearchEngine
from app.logger import logger

class BraveSearchEngine(WebSearchEngine):
    """
    Brave Search Engine implementation.
    
    This class uses the Brave Search API to perform web searches.
    """
    
    def __init__(self):
        """Initialize the Brave Search Engine."""
        self.api_key = self._get_api_key()
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        
    def _get_api_key(self) -> Optional[str]:
        """
        Get the Brave Search API key from environment variables or config.
        
        Returns:
            The API key if available, None otherwise
        """
        # Try to get from environment variable first
        api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
        
        # If not in environment, try to get from config
        if not api_key and hasattr(config, "search") and hasattr(config.search, "brave_api_key"):
            api_key = config.search.brave_api_key
            
        return api_key
    
    def perform_search(self, query: str, num_results: int = 10, **kwargs) -> List[str]:
        """
        Perform a search using the Brave Search API.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            A list of URLs from the search results
            
        Raises:
            Exception: If the API request fails
        """
        if not self.api_key:
            logger.warning("Brave Search API key not found. Skipping Brave search.")
            return []
            
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": min(num_results, 50),  # Brave API has a max of 50 results per request
            "search_lang": kwargs.get("language", "en"),
            "country": kwargs.get("country", "US"),
            "safesearch": kwargs.get("safe_search", "moderate")
        }
        
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract URLs from the results
            urls = []
            if "web" in data and "results" in data["web"]:
                for result in data["web"]["results"]:
                    if "url" in result:
                        urls.append(result["url"])
            
            return urls
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Brave Search API request failed: {str(e)}")
            raise Exception(f"Brave Search API request failed: {str(e)}")
        except ValueError as e:
            logger.error(f"Failed to parse Brave Search API response: {str(e)}")
            raise Exception(f"Failed to parse Brave Search API response: {str(e)}")
