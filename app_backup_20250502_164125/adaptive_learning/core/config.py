"""
Configuration for the Adaptive Learning System.

This module defines the configuration structure for the Adaptive Learning System,
including settings for all components such as feedback collection, memory management,
performance analytics, and strategy adaptation.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field


@dataclass
class FeedbackConfig:
    """Configuration for the feedback collection and processing component."""
    
    # Minimum feedback quality threshold (0-1)
    quality_threshold: float = 0.6
    
    # Maximum number of feedback items to store per interaction
    max_feedback_per_interaction: int = 10
    
    # Types of feedback to collect
    feedback_types: List[str] = field(default_factory=lambda: [
        "rating", "text_comment", "specific_aspect", "improvement_suggestion"
    ])
    
    # Weights for different feedback types in impact calculation
    feedback_type_weights: Dict[str, float] = field(default_factory=lambda: {
        "rating": 0.3,
        "text_comment": 0.2,
        "specific_aspect": 0.3,
        "improvement_suggestion": 0.2,
    })


@dataclass
class MemoryConfig:
    """Configuration for the memory management component."""
    
    # Maximum number of memories to store
    max_memories: int = 10000
    
    # Threshold for memory importance to be stored (0-1)
    importance_threshold: float = 0.4
    
    # Decay rate for memory importance over time (0-1)
    importance_decay_rate: float = 0.05
    
    # Embedding model to use for memory vectorization
    embedding_model: str = "text-embedding-3-small"
    
    # Vector dimension for memory embeddings
    embedding_dimension: int = 1536
    
    # Memory types to track
    memory_types: List[str] = field(default_factory=lambda: [
        "interaction", "feedback", "performance", "strategy"
    ])


@dataclass
class AnalyticsConfig:
    """Configuration for the performance analytics component."""
    
    # Metrics to track for performance analysis
    tracked_metrics: List[str] = field(default_factory=lambda: [
        "response_time", "completion_rate", "accuracy", "user_satisfaction",
        "tool_usage_efficiency", "reasoning_quality"
    ])
    
    # Weights for different metrics in overall performance calculation
    metric_weights: Dict[str, float] = field(default_factory=lambda: {
        "response_time": 0.15,
        "completion_rate": 0.2,
        "accuracy": 0.25,
        "user_satisfaction": 0.25,
        "tool_usage_efficiency": 0.1,
        "reasoning_quality": 0.05,
    })
    
    # Time periods for trend analysis
    trend_periods: List[str] = field(default_factory=lambda: [
        "day", "week", "month"
    ])


@dataclass
class StrategyConfig:
    """Configuration for the strategy adaptation component."""
    
    # Minimum performance change to trigger strategy adaptation (0-1)
    adaptation_threshold: float = 0.1
    
    # Maximum number of strategy adaptations per day
    max_adaptations_per_day: int = 5
    
    # Cooldown period between adaptations (in hours)
    adaptation_cooldown_hours: int = 4
    
    # Strategy aspects that can be adapted
    adaptable_aspects: List[str] = field(default_factory=lambda: [
        "prompt_structure", "tool_selection", "reasoning_approach",
        "error_handling", "planning_detail"
    ])
    
    # Weights for different factors in adaptation decisions
    adaptation_factor_weights: Dict[str, float] = field(default_factory=lambda: {
        "performance_metrics": 0.4,
        "user_feedback": 0.3,
        "task_complexity": 0.2,
        "historical_success": 0.1,
    })


@dataclass
class AdaptiveLearningConfig:
    """Main configuration for the Adaptive Learning System."""
    
    # Enable/disable the adaptive learning system
    enabled: bool = True
    
    # Log level for the adaptive learning system
    log_level: str = "INFO"
    
    # Component configurations
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    
    # Data storage configuration
    storage_path: str = "data/adaptive_learning"
    
    # Backup configuration
    backup_enabled: bool = True
    backup_frequency_hours: int = 24
    max_backups: int = 7
