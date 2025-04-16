"""
Exceptions for the Adaptive Learning System.

This module defines custom exceptions used throughout the Adaptive Learning System
to provide clear error handling and reporting.
"""


class AdaptiveLearningError(Exception):
    """Base exception for all Adaptive Learning System errors."""
    pass


class FeedbackProcessingError(AdaptiveLearningError):
    """Exception raised when there's an error processing user feedback."""
    pass


class MemoryStorageError(AdaptiveLearningError):
    """Exception raised when there's an error storing or retrieving memories."""
    pass


class MemoryRetrievalError(AdaptiveLearningError):
    """Exception raised when there's an error retrieving memories."""
    pass


class AnalyticsProcessingError(AdaptiveLearningError):
    """Exception raised when there's an error processing performance analytics."""
    pass


class StrategyAdaptationError(AdaptiveLearningError):
    """Exception raised when there's an error adapting agent strategies."""
    pass


class ConfigurationError(AdaptiveLearningError):
    """Exception raised when there's an error in the system configuration."""
    pass


class DataConsistencyError(AdaptiveLearningError):
    """Exception raised when there's a data consistency issue."""
    pass
