"""
Trend Analyzer for the Adaptive Learning System.

This module contains the TrendAnalyzer class that analyzes performance trends
over time to identify patterns and changes in agent performance.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

from app.adaptive_learning.core.config import AdaptiveLearningConfig
from app.adaptive_learning.core.exceptions import AnalyticsProcessingError

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Analyzes performance trends over time.
    
    This class is responsible for tracking and analyzing performance metrics
    over time to identify trends, patterns, and changes in agent performance.
    
    Attributes:
        config (AdaptiveLearningConfig): Configuration for trend analysis
        metric_history (Dict): Historical metric data for trend analysis
        trend_cache (Dict): Cached trend analysis results
    """
    
    def __init__(self, config: AdaptiveLearningConfig):
        """
        Initialize the TrendAnalyzer.
        
        Args:
            config: Configuration for trend analysis
        """
        self.config = config
        self.metric_history = {}  # Historical metric data
        self.trend_cache = {}  # Cached trend analysis results
        logger.info("TrendAnalyzer initialized")
    
    async def update_trends(self, metrics: Dict[str, Any]) -> None:
        """
        Update trend data with new metrics.
        
        Args:
            metrics: New performance metrics
            
        Raises:
            AnalyticsProcessingError: If update fails
        """
        try:
            timestamp = datetime.now().isoformat()
            
            # Store metrics in history
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, (int, float)):
                    if metric_name not in self.metric_history:
                        self.metric_history[metric_name] = []
                    
                    self.metric_history[metric_name].append({
                        "timestamp": timestamp,
                        "value": metric_value,
                    })
            
            # Invalidate trend cache
            self.trend_cache = {}
            
            logger.debug(f"Updated trend data with {len(metrics)} metrics")
            
        except Exception as e:
            logger.error(f"Error updating trends: {str(e)}")
            raise AnalyticsProcessingError(f"Failed to update trends: {str(e)}")
    
    async def get_trends(self, time_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Get trend analysis for all metrics.
        
        Args:
            time_period: Optional time period for trend analysis
            
        Returns:
            Dict containing trend analysis results
            
        Raises:
            AnalyticsProcessingError: If trend analysis fails
        """
        try:
            # Check if we have cached results
            cache_key = f"trends_{time_period}"
            if cache_key in self.trend_cache:
                return self.trend_cache[cache_key]
            
            logger.debug(f"Analyzing trends for period: {time_period}")
            
            # Filter metrics by time period
            filtered_history = self._filter_by_time_period(time_period)
            
            # Calculate trends for each metric
            metric_trends = {}
            for metric_name, history in filtered_history.items():
                if len(history) >= 3:  # Need at least 3 data points for trend analysis
                    metric_trends[metric_name] = self._analyze_metric_trend(history)
            
            # Calculate overall trend
            overall_trend = self._calculate_overall_trend(metric_trends)
            
            # Prepare result
            result = {
                "time_period": time_period,
                "metric_trends": metric_trends,
                "overall_trend": overall_trend,
            }
            
            # Cache the results
            self.trend_cache[cache_key] = result
            
            logger.debug(f"Completed trend analysis for {len(metric_trends)} metrics")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            raise AnalyticsProcessingError(f"Failed to analyze trends: {str(e)}")
    
    async def get_recent_trends(self) -> Dict[str, Any]:
        """
        Get trend analysis for recent metrics.
        
        Returns:
            Dict containing recent trend analysis results
            
        Raises:
            AnalyticsProcessingError: If trend analysis fails
        """
        # Use the last 24 hours as the default recent period
        return await self.get_trends("day")
    
    def _filter_by_time_period(self, time_period: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter metric history by time period.
        
        Args:
            time_period: Time period to filter by
            
        Returns:
            Filtered metric history
        """
        if not time_period:
            return self.metric_history
        
        now = datetime.now()
        filtered = {}
        
        for metric_name, history in self.metric_history.items():
            filtered_history = []
            
            for entry in history:
                timestamp = entry["timestamp"]
                if isinstance(timestamp, str):
                    entry_time = datetime.fromisoformat(timestamp)
                else:
                    entry_time = timestamp
                
                if time_period == "day" and (now - entry_time) <= timedelta(days=1):
                    filtered_history.append(entry)
                elif time_period == "week" and (now - entry_time) <= timedelta(days=7):
                    filtered_history.append(entry)
                elif time_period == "month" and (now - entry_time) <= timedelta(days=30):
                    filtered_history.append(entry)
            
            if filtered_history:
                filtered[metric_name] = filtered_history
        
        return filtered
    
    def _analyze_metric_trend(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze trend for a specific metric.
        
        Args:
            history: Historical data for the metric
            
        Returns:
            Dict containing trend analysis results
        """
        # Sort history by timestamp
        sorted_history = sorted(history, key=lambda x: x["timestamp"])
        
        # Extract values
        values = [entry["value"] for entry in sorted_history]
        
        # Calculate simple statistics
        avg_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)
        
        # Calculate trend direction and slope
        trend_direction, slope = self._calculate_trend_direction(values)
        
        # Calculate trend significance
        significance = self._calculate_trend_significance(values, slope)
        
        # Calculate volatility
        volatility = self._calculate_volatility(values)
        
        return {
            "direction": trend_direction,
            "slope": slope,
            "significance": significance,
            "volatility": volatility,
            "average": avg_value,
            "min": min_value,
            "max": max_value,
            "data_points": len(values),
        }
    
    def _calculate_trend_direction(self, values: List[float]) -> tuple:
        """
        Calculate the direction and slope of a trend.
        
        Args:
            values: List of metric values
            
        Returns:
            Tuple of (direction, slope)
        """
        n = len(values)
        
        if n <= 1:
            return "stable", 0.0
        
        # Simple linear regression
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_x_squared = sum(xi * xi for xi in x)
        sum_xy = sum(xi * yi for xi, yi in zip(x, values))
        
        # Calculate slope
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
        except ZeroDivisionError:
            slope = 0.0
        
        # Determine direction based on slope
        if abs(slope) < 0.01:  # Threshold for "stable"
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        return direction, slope
    
    def _calculate_trend_significance(self, values: List[float], slope: float) -> float:
        """
        Calculate the significance of a trend.
        
        Args:
            values: List of metric values
            slope: Slope of the trend
            
        Returns:
            Significance score (0-1)
        """
        n = len(values)
        
        if n <= 1 or slope == 0:
            return 0.0
        
        # Calculate mean and standard deviation
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std_dev = math.sqrt(variance) if variance > 0 else 0.001  # Avoid division by zero
        
        # Calculate coefficient of determination (R-squared)
        x = list(range(n))
        y_pred = [mean + slope * xi for xi in x]
        ss_total = sum((yi - mean) ** 2 for yi in values)
        ss_residual = sum((yi - y_pred_i) ** 2 for yi, y_pred_i in zip(values, y_pred))
        
        if ss_total == 0:
            r_squared = 0.0
        else:
            r_squared = 1 - (ss_residual / ss_total)
        
        # Calculate significance based on R-squared and slope
        slope_significance = min(1.0, abs(slope) / (std_dev * 0.5))
        
        # Combine R-squared and slope significance
        significance = (r_squared * 0.7) + (slope_significance * 0.3)
        
        return significance
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """
        Calculate the volatility of a metric.
        
        Args:
            values: List of metric values
            
        Returns:
            Volatility score (0-1)
        """
        n = len(values)
        
        if n <= 1:
            return 0.0
        
        # Calculate mean
        mean = sum(values) / n
        
        # Calculate standard deviation
        variance = sum((v - mean) ** 2 for v in values) / n
        std_dev = math.sqrt(variance)
        
        # Calculate coefficient of variation (normalized standard deviation)
        if mean == 0:
            cv = 0.0
        else:
            cv = std_dev / abs(mean)
        
        # Normalize to 0-1 range
        volatility = min(1.0, cv)
        
        return volatility
    
    def _calculate_overall_trend(self, metric_trends: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate the overall trend across all metrics.
        
        Args:
            metric_trends: Trends for individual metrics
            
        Returns:
            Dict containing overall trend analysis
        """
        if not metric_trends:
            return {
                "direction": "stable",
                "significance": 0.0,
                "volatility": 0.0,
            }
        
        # Count metrics by direction
        direction_counts = {"increasing": 0, "decreasing": 0, "stable": 0}
        
        # Calculate weighted average of significance and volatility
        total_significance = 0.0
        total_volatility = 0.0
        total_weight = 0.0
        
        for metric_name, trend in metric_trends.items():
            direction = trend["direction"]
            significance = trend["significance"]
            volatility = trend["volatility"]
            
            # Get weight for this metric from config
            weight = self.config.analytics.metric_weights.get(metric_name, 0.1)
            
            # Update direction counts
            direction_counts[direction] += weight
            
            # Update weighted averages
            total_significance += significance * weight
            total_volatility += volatility * weight
            total_weight += weight
        
        # Determine overall direction
        if total_weight > 0:
            if direction_counts["stable"] / total_weight > 0.5:
                overall_direction = "stable"
            elif direction_counts["increasing"] > direction_counts["decreasing"]:
                overall_direction = "improving"
            else:
                overall_direction = "declining"
            
            # Calculate weighted averages
            avg_significance = total_significance / total_weight
            avg_volatility = total_volatility / total_weight
        else:
            overall_direction = "stable"
            avg_significance = 0.0
            avg_volatility = 0.0
        
        return {
            "direction": overall_direction,
            "significance": avg_significance,
            "volatility": avg_volatility,
        }
