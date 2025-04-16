import asyncio
from typing import List

from app.config import config
from app.tools.base import BaseTool
from app.logger import logger
from app.tools.search import (
    WebSearchEngine,
    GoogleSearchEngine,
    DuckDuckGoSearchEngine,
    BaiduSearchEngine
)

# Import BraveSearchEngine if available
try:
    from app.tools.search.brave_search import BraveSearchEngine
except ImportError:
    BraveSearchEngine = None

class WebSearch(BaseTool):
    name: str = "web_search"
    description: str = """Perform a web search and return a list of relevant links.
    This function attempts to use the primary search engine API to get up-to-date results.
    If an error occurs, it falls back to an alternative search engine."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to the search engine.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 100,
            },
        },
        "required": ["query"],
    }
    def __init__(self):
        """Initialize the WebSearch tool with available search engines."""
        super().__init__()
        # Initialize search engines
        self._search_engine = {
            "google": GoogleSearchEngine(),
            "baidu": BaiduSearchEngine(),
            "duckduckgo": DuckDuckGoSearchEngine(),
        }

        # Add Brave search engine if available
        if BraveSearchEngine is not None:
            try:
                self._search_engine["brave"] = BraveSearchEngine()
                logger.info("Brave search engine added to WebSearch tool")
            except Exception as e:
                logger.error(f"Error initializing Brave search engine: {str(e)}")

    async def execute(self, query: str, num_results: int = 100) -> List[str]:
        """
        Execute a Web search and return a list of URLs.

        Args:
            query (str): The search query to submit to the search engine.
            num_results (int, optional): The number of search results to return. Default is 10.

        Returns:
            List[str]: A list of URLs matching the search query.
        """
        from loguru import logger

        engine_order = self._get_engine_order()
        all_errors = {}

        for engine_name in engine_order:
            engine = self._search_engine[engine_name]
            try:
                logger.info(f"Attempting search with {engine_name} engine for query: {query}")
                links = await self._perform_search_with_engine(engine, query, num_results)
                if links:
                    logger.success(f"Search successful with {engine_name} engine")
                    return links
                else:
                    logger.warning(f"Search with {engine_name} engine returned no results")
            except Exception as e:
                error_msg = f"Search engine '{engine_name}' failed with error: {e}"
                logger.error(error_msg)
                all_errors[engine_name] = str(e)

        # If we get here, all engines failed
        logger.error(f"All search engines failed. Errors: {all_errors}")
        return []

    def _get_engine_order(self) -> List[str]:
        """
        Determines the order in which to try search engines.
        Preferred engine is first (based on configuration), followed by the remaining engines.

        Returns:
            List[str]: Ordered list of search engine names.
        """
        preferred = "google"
        if config.search_config and config.search_config.engine:
            preferred = config.search_config.engine.lower()

        engine_order = []
        if preferred in self._search_engine:
            engine_order.append(preferred)
        for key in self._search_engine:
            if key not in engine_order:
                engine_order.append(key)
        return engine_order

    async def _perform_search_with_engine(
        self,
        engine: WebSearchEngine,
        query: str,
        num_results: int,
    ) -> List[str]:
        from loguru import logger

        try:
            loop = asyncio.get_event_loop()
            # Remove the retry decorator and handle retries manually
            max_attempts = 3
            attempt = 0
            last_error = None

            while attempt < max_attempts:
                try:
                    attempt += 1
                    logger.debug(f"Search attempt {attempt}/{max_attempts}")
                    result = await loop.run_in_executor(
                        None, lambda: list(engine.perform_search(query, num_results=num_results))
                    )
                    return [str(url) for url in result]
                except Exception as e:
                    last_error = e
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff with max of 10 seconds
                    logger.warning(f"Search attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

            # If we get here, all attempts failed
            raise last_error or Exception("All search attempts failed")
        except Exception as e:
            logger.error(f"Search engine failed after {max_attempts} attempts: {e}")
            return []