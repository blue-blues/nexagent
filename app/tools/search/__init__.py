"""Search tools for Nexagent.

This module provides tools for searching the web.
"""

from app.tools.search.base import WebSearchEngine
from app.tools.search.google_search import GoogleSearchEngine
from app.tools.search.duckduckgo_search import DuckDuckGoSearchEngine
from app.tools.search.baidu_search import BaiduSearchEngine

# Import from parent directory if it exists there
try:
    from app.tools.web_search import WebSearch
except ImportError:
    WebSearch = None

__all__ = [
    'WebSearchEngine',
    'GoogleSearchEngine',
    'DuckDuckGoSearchEngine',
    'BaiduSearchEngine',
    'WebSearch'
]