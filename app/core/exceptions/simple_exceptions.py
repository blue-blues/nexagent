"""
Simplified exceptions implementation to avoid import issues.
"""

class ToolError(Exception):
    """Base class for tool errors."""
    pass


class TokenLimitExceeded(Exception):
    """Exception raised when token limit is exceeded."""
    pass
