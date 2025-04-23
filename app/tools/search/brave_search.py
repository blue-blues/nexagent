"""
Brave Search Engine implementation for Nexagent.

This module provides a BraveSearchEngine class that implements the WebSearchEngine interface
for the Brave Search API.
"""

import requests
from typing import List, Dict, Any, Optional
import os
import time

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
        self.max_retries = 3
        self.timeout = 10  # seconds
        self.retry_delay = 2  # seconds

        if not self.api_key:
            logger.warning("Brave Search API key not found. Brave search will not be available.")

    def _get_api_key(self) -> Optional[str]:
        """
        Get the Brave Search API key from environment variables or config.

        Returns:
            The API key if available, None otherwise
        """
        # Try to get from environment variable first
        api_key = os.environ.get("BRAVE_SEARCH_API_KEY")

        # If not in environment, try to get from config
        if not api_key and config.search_config and hasattr(config.search_config, "brave_api_key"):
            api_key = config.search_config.brave_api_key

        return api_key

    def perform_search(self, query: str, num_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Perform a search using the Brave Search API.

        Args:
            query: The search query
            num_results: Maximum number of results to return
            **kwargs: Additional parameters to pass to the API

        Returns:
            A list of search results with title, url, and snippet

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

        # Add optional parameters if provided
        if "offset" in kwargs:
            params["offset"] = kwargs["offset"]

        if "freshness" in kwargs:
            params["freshness"] = kwargs["freshness"]

        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Brave Search attempt {attempt+1}/{self.max_retries} for query: {query}")
                response = requests.get(
                    self.base_url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()

                # Extract results from the response
                results = []
                if "web" in data and "results" in data["web"]:
                    for result in data["web"]["results"]:
                        results.append({
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("description", "")
                        })

                logger.info(f"Brave Search returned {len(results)} results for query: {query}")
                return results

            except requests.exceptions.RequestException as e:
                logger.warning(f"Brave Search API request failed (attempt {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    # Wait before retrying with exponential backoff
                    retry_wait = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {retry_wait} seconds...")
                    time.sleep(retry_wait)
                else:
                    logger.error(f"All Brave Search API requests failed: {str(e)}")
                    # Don't raise exception to allow fallback to other engines
                    return []

            except Exception as e:
                logger.error(f"Error processing Brave Search results: {str(e)}")
                return []

        return []  # Fallback empty result if all attempts fail
