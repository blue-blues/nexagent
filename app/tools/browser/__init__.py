"""Browser tools for Nexagent.

This module provides tools for interacting with web browsers.
"""

from app.tools.browser.browser_use_tool import BrowserUseTool
from app.tools.browser.enhanced_browser_tool import EnhancedBrowserTool
from app.tools.browser.web_ui_browser_tool import WebUIBrowserTool
try:
    from app.tools.browser.web_search import WebSearch
except ImportError:
    WebSearch = None

# Import these from the parent directory if they exist there
try:
    from app.tools.enhanced_web_browser import EnhancedWebBrowser
except ImportError:
    EnhancedWebBrowser = None

try:
    from app.tools.fallback_browser_tool import FallbackBrowserTool
except ImportError:
    FallbackBrowserTool = None

__all__ = [
    'BrowserUseTool',
    'EnhancedBrowserTool',
    'WebUIBrowserTool',
    'WebSearch',
    'EnhancedWebBrowser',
    'FallbackBrowserTool'
]