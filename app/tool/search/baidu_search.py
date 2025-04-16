from baidusearch.baidusearch import search

from app.tool.search.base import WebSearchEngine


class BaiduSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=50, *args, **kwargs):
        """Baidu search engine."""
        try:
            return search(query, num_results=num_results)
        except Exception as e:
            # Log the error but don't raise it to allow fallback to other engines
            print(f"Baidu search failed: {e}")
            return []
