"""
Metrics Collector for the Adaptive Learning System.

This module contains the MetricsCollector class that extracts and calculates
performance metrics from interaction data.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union

from app.adaptive_learning.core.config import AdaptiveLearningConfig
from app.adaptive_learning.core.exceptions import AnalyticsProcessingError

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and calculates performance metrics from interaction data.
    
    This class is responsible for extracting raw metrics from interaction data
    and calculating derived metrics to provide a comprehensive view of agent
    performance.
    
    Attributes:
        config (AdaptiveLearningConfig): Configuration for metrics collection
    """
    
    def __init__(self, config: AdaptiveLearningConfig):
        """
        Initialize the MetricsCollector.
        
        Args:
            config: Configuration for metrics collection
        """
        self.config = config
        logger.info("MetricsCollector initialized")
    
    async def collect_metrics(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect and calculate metrics from interaction data.
        
        Args:
            interaction_data: Data from the interaction
            
        Returns:
            Dict containing collected metrics
            
        Raises:
            AnalyticsProcessingError: If metrics collection fails
        """
        try:
            logger.debug("Collecting metrics from interaction data")
            
            metrics = {}
            
            # Extract basic metrics
            metrics.update(self._extract_basic_metrics(interaction_data))
            
            # Calculate derived metrics
            metrics.update(self._calculate_derived_metrics(interaction_data, metrics))
            
            logger.debug(f"Collected {len(metrics)} metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
            raise AnalyticsProcessingError(f"Failed to collect metrics: {str(e)}")
    
    def _extract_basic_metrics(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract basic metrics directly from interaction data.
        
        Args:
            interaction_data: Data from the interaction
            
        Returns:
            Dict containing basic metrics
        """
        metrics = {}
        
        # Response time
        if "start_time" in interaction_data and "end_time" in interaction_data:
            start_time = interaction_data["start_time"]
            end_time = interaction_data["end_time"]
            
            # Convert to timestamps if they're strings
            if isinstance(start_time, str):
                start_time = time.mktime(time.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%f"))
            if isinstance(end_time, str):
                end_time = time.mktime(time.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%f"))
            
            metrics["response_time"] = end_time - start_time
        
        # Completion status
        if "status" in interaction_data:
            metrics["completion_rate"] = 1.0 if interaction_data["status"] == "completed" else 0.0
        
        # User satisfaction (if available)
        if "user_feedback" in interaction_data:
            feedback = interaction_data["user_feedback"]
            if "rating" in feedback and isinstance(feedback["rating"], (int, float)):
                # Normalize rating to 0-1 range (assuming 1-5 scale)
                metrics["user_satisfaction"] = (feedback["rating"] - 1) / 4
        
        # Tool usage
        if "tools_used" in interaction_data:
            tools_used = interaction_data["tools_used"]
            metrics["tool_count"] = len(tools_used)
        
        # Error count
        if "errors" in interaction_data:
            errors = interaction_data["errors"]
            metrics["error_count"] = len(errors)
        
        return metrics
    
    def _calculate_derived_metrics(
        self, interaction_data: Dict[str, Any], basic_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate derived metrics from interaction data and basic metrics.
        
        Args:
            interaction_data: Data from the interaction
            basic_metrics: Basic metrics extracted from the interaction
            
        Returns:
            Dict containing derived metrics
        """
        derived_metrics = {}
        
        # Accuracy (if available)
        if "expected_result" in interaction_data and "actual_result" in interaction_data:
            expected = interaction_data["expected_result"]
            actual = interaction_data["actual_result"]
            
            # Simple exact match accuracy
            derived_metrics["accuracy"] = 1.0 if expected == actual else 0.0
        
        # Tool usage efficiency
        if "tool_count" in basic_metrics and "tools_used" in interaction_data:
            tools_used = interaction_data["tools_used"]
            task_complexity = interaction_data.get("task_complexity", 1.0)
            
            # Calculate efficiency based on task complexity and tool count
            # More complex tasks may require more tools
            expected_tool_count = max(1, int(task_complexity * 3))  # Simple heuristic
            
            if basic_metrics["tool_count"] <= expected_tool_count:
                derived_metrics["tool_usage_efficiency"] = 1.0
            else:
                # Efficiency decreases as tool count exceeds expected count
                excess_tools = basic_metrics["tool_count"] - expected_tool_count
                derived_metrics["tool_usage_efficiency"] = max(0.0, 1.0 - (excess_tools / expected_tool_count) * 0.5)
        
        # Error rate
        if "error_count" in basic_metrics and "steps" in interaction_data:
            steps = interaction_data["steps"]
            step_count = len(steps)
            
            if step_count > 0:
                derived_metrics["error_rate"] = basic_metrics["error_count"] / step_count
            else:
                derived_metrics["error_rate"] = 0.0
        
        # Reasoning quality (if available)
        if "reasoning_steps" in interaction_data:
            reasoning_steps = interaction_data["reasoning_steps"]
            
            # Simple heuristic based on number of reasoning steps
            if len(reasoning_steps) >= 3:
                derived_metrics["reasoning_quality"] = 0.8
            elif len(reasoning_steps) >= 1:
                derived_metrics["reasoning_quality"] = 0.5
            else:
                derived_metrics["reasoning_quality"] = 0.2
        
        return derived_metrics
