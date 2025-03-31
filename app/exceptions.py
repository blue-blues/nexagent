class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


class OpenManusError(Exception):
    """Base exception for all OpenManus errors"""


class TokenLimitExceeded(OpenManusError):
    """Exception raised when the token limit is exceeded"""


class DataProcessingError(OpenManusError):
    """Exception raised when data processing operations fail"""
    
    def __init__(self, message):
        self.message = message
        super().__init__(message)
