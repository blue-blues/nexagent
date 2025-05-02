"""
Core Exception Definitions

This module defines the custom exceptions used throughout the application.
"""

class NexagentException(Exception):
    """Base exception for all Nexagent exceptions"""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class ToolError(NexagentException):
    """Raised when a tool encounters an error."""
    pass


class TokenLimitExceeded(NexagentException):
    """Exception raised when the token limit is exceeded"""
    pass


class DataProcessingError(NexagentException):
    """Exception raised when data processing operations fail"""
    pass


class ConfigurationError(NexagentException):
    """Raised when there's an error in the configuration"""
    pass


class LLMError(NexagentException):
    """Base exception for LLM-related errors"""
    pass


class ToolExecutionError(NexagentException):
    """Raised when a tool execution fails"""
    pass


class AgentExecutionError(NexagentException):
    """Raised when an agent execution fails"""
    pass


class ContextError(NexagentException):
    """Raised when there's an error with the context"""
    pass
