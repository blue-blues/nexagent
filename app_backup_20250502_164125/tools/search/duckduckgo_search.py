from duckduckgo_search import DDGS

from app.tools.search.base import WebSearchEngine


class DuckDuckGoSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=50, *args, **kwargs):
        """DuckDuckGo search engine."""
        try:
            ddgs = DDGS()
            return ddgs.text(keywords=query, max_results=num_results)
        except Exception as e:
            # Log the error but don't raise it to allow fallback to other engines
            print(f"DuckDuckGo search failed: {e}")
            return []
