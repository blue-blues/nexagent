"""
Performance Analyzer for the Adaptive Learning System.

This module contains the PerformanceAnalyzer class that analyzes agent performance
metrics to identify trends, strengths, weaknesses, and opportunities for improvement.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from app.adaptive_learning.core.config import AdaptiveLearningConfig
from app.adaptive_learning.core.exceptions import AnalyticsProcessingError
from app.adaptive_learning.analytics.metrics_collector import MetricsCollector
from app.adaptive_learning.analytics.trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Analyzes agent performance metrics to drive improvements.
    
    This class is responsible for collecting, analyzing, and reporting on
    performance metrics to identify trends and opportunities for improvement.
    
    Attributes:
        config (AdaptiveLearningConfig): Configuration for performance analytics
        metrics_collector (MetricsCollector): Collector for performance metrics
        trend_analyzer (TrendAnalyzer): Analyzer for performance trends
        metrics_store (Dict): In-memory store for metrics (would use a database in production)
    """
    
    def __init__(self, config: AdaptiveLearningConfig):
        """
        Initialize the PerformanceAnalyzer.
        
        Args:
            config: Configuration for performance analytics
        """
        self.config = config
        self.metrics_collector = MetricsCollector(config)
        self.trend_analyzer = TrendAnalyzer(config)
        self.metrics_store = {}  # In-memory store (would use a database in production)
        logger.info("PerformanceAnalyzer initialized")
    
    async def analyze_interaction(self, interaction_id: str, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze performance metrics for an interaction.
        
        Args:
            interaction_id: Unique identifier for the interaction
            interaction_data: Data from the interaction
            
        Returns:
            Dict containing performance metrics and analysis
            
        Raises:
            AnalyticsProcessingError: If analysis fails
        """
        try:
            logger.debug(f"Analyzing performance for interaction {interaction_id}")
            
            # Collect metrics from the interaction
            metrics = await self.metrics_collector.collect_metrics(interaction_data)
            
            # Calculate overall performance score
            overall_score = self._calculate_overall_score(metrics)
            
            # Identify strengths and weaknesses
            strengths, weaknesses = self._identify_strengths_and_weaknesses(metrics)
            
            # Generate insights
            insights = self._generate_insights(metrics, interaction_data)
            
            # Store the metrics
            self.metrics_store[interaction_id] = {
                "interaction_id": interaction_id,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "overall_score": overall_score,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "insights": insights,
            }
            
            # Update trend analysis
            await self.trend_analyzer.update_trends(metrics)
            
            # Prepare result
            result = {
                "interaction_id": interaction_id,
                "overall_score": overall_score,
                "metrics": metrics,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "insights": insights,
                "trends": await self.trend_analyzer.get_recent_trends(),
            }
            
            logger.info(f"Completed performance analysis for interaction {interaction_id} with score {overall_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {str(e)}")
            raise AnalyticsProcessingError(f"Failed to analyze performance: {str(e)}")
    
    async def get_performance_metrics(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve performance metrics based on query parameters.
        
        Args:
            query_params: Parameters to filter and customize metrics retrieval
            
        Returns:
            Dict containing retrieved metrics and analysis
            
        Raises:
            AnalyticsProcessingError: If retrieval fails
        """
        try:
            logger.debug(f"Retrieving performance metrics with params: {query_params}")
            
            # Extract query parameters
            interaction_id = query_params.get("interaction_id")
            time_period = query_params.get("time_period")
            metric_names = query_params.get("metrics")
            
            # Retrieve metrics based on parameters
            if interaction_id:
                # Get metrics for a specific interaction
                if interaction_id not in self.metrics_store:
                    return {"error": f"No metrics found for interaction {interaction_id}"}
                
                metrics_data = self.metrics_store[interaction_id]
                
                # Filter metrics if specific ones are requested
                if metric_names:
                    filtered_metrics = {k: v for k, v in metrics_data["metrics"].items() if k in metric_names}
                    metrics_data = {**metrics_data, "metrics": filtered_metrics}
                
                return metrics_data
            else:
                # Get aggregated metrics across multiple interactions
                aggregated_metrics = await self._aggregate_metrics(time_period, metric_names)
                trends = await self.trend_analyzer.get_trends(time_period)
                
                return {
                    "time_period": time_period,
                    "aggregated_metrics": aggregated_metrics,
                    "trends": trends,
                }
            
        except Exception as e:
            logger.error(f"Error retrieving performance metrics: {str(e)}")
            raise AnalyticsProcessingError(f"Failed to retrieve performance metrics: {str(e)}")
    
    async def generate_report(self, time_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.
        
        Args:
            time_period: Optional time period to cover in the report
            
        Returns:
            Dict containing the performance report data
        """
        try:
            logger.info(f"Generating performance report for period: {time_period}")
            
            # Get aggregated metrics
            aggregated_metrics = await self._aggregate_metrics(time_period)
            
            # Get trends
            trends = await self.trend_analyzer.get_trends(time_period)
            
            # Calculate key performance indicators
            kpis = self._calculate_kpis(aggregated_metrics)
            
            # Generate insights
            insights = self._generate_report_insights(aggregated_metrics, trends)
            
            # Prepare report
            report = {
                "time_period": time_period,
                "generated_at": datetime.now().isoformat(),
                "key_metrics": kpis,
                "aggregated_metrics": aggregated_metrics,
                "trends": trends,
                "insights": insights,
                "recommendations": self._generate_recommendations(insights, trends),
            }
            
            logger.info(f"Completed performance report generation")
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            raise AnalyticsProcessingError(f"Failed to generate performance report: {str(e)}")
    
    def _calculate_overall_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate an overall performance score from metrics.
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Overall performance score (0-1)
        """
        score = 0.0
        total_weight = 0.0
        
        # Calculate weighted score based on configured weights
        for metric_name, weight in self.config.analytics.metric_weights.items():
            if metric_name in metrics:
                metric_value = metrics[metric_name]
                
                # Normalize metric value to 0-1 range if needed
                if isinstance(metric_value, (int, float)):
                    # For response_time, lower is better, so invert the score
                    if metric_name == "response_time":
                        # Assuming response_time is in seconds, normalize to 0-1 range
                        # where 0 seconds -> 1.0 score, 10+ seconds -> 0.0 score
                        normalized_value = max(0, 1 - (metric_value / 10))
                    else:
                        # For other metrics, assume they're already in 0-1 range
                        normalized_value = metric_value
                    
                    score += normalized_value * weight
                    total_weight += weight
        
        # Return normalized score
        if total_weight > 0:
            return score / total_weight
        else:
            return 0.0
    
    def _identify_strengths_and_weaknesses(self, metrics: Dict[str, Any]) -> tuple:
        """
        Identify strengths and weaknesses from metrics.
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Tuple of (strengths, weaknesses) lists
        """
        strengths = []
        weaknesses = []
        
        # Define thresholds for strengths and weaknesses
        strength_threshold = 0.8
        weakness_threshold = 0.6
        
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                # For response_time, lower is better
                if metric_name == "response_time":
                    # Normalize to 0-1 range where lower is better
                    normalized_value = max(0, 1 - (metric_value / 10))
                    
                    if normalized_value >= strength_threshold:
                        strengths.append({
                            "metric": metric_name,
                            "value": metric_value,
                            "score": normalized_value,
                        })
                    elif normalized_value <= weakness_threshold:
                        weaknesses.append({
                            "metric": metric_name,
                            "value": metric_value,
                            "score": normalized_value,
                        })
                else:
                    # For other metrics, higher is better
                    if metric_value >= strength_threshold:
                        strengths.append({
                            "metric": metric_name,
                            "value": metric_value,
                            "score": metric_value,
                        })
                    elif metric_value <= weakness_threshold:
                        weaknesses.append({
                            "metric": metric_name,
                            "value": metric_value,
                            "score": metric_value,
                        })
        
        # Sort strengths and weaknesses by score
        strengths.sort(key=lambda x: x["score"], reverse=True)
        weaknesses.sort(key=lambda x: x["score"])
        
        return strengths, weaknesses
    
    def _generate_insights(self, metrics: Dict[str, Any], interaction_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate insights from metrics and interaction data.
        
        Args:
            metrics: Performance metrics
            interaction_data: Data from the interaction
            
        Returns:
            List of insights
        """
        insights = []
        
        # Check response time
        if "response_time" in metrics:
            response_time = metrics["response_time"]
            if response_time > 5:
                insights.append({
                    "type": "performance_issue",
                    "metric": "response_time",
                    "description": f"Response time ({response_time:.2f}s) is above the recommended threshold (5s)",
                    "severity": "medium",
                    "suggested_action": "Optimize tool usage and reduce unnecessary processing",
                })
        
        # Check completion rate
        if "completion_rate" in metrics:
            completion_rate = metrics["completion_rate"]
            if completion_rate < 0.7:
                insights.append({
                    "type": "performance_issue",
                    "metric": "completion_rate",
                    "description": f"Completion rate ({completion_rate:.2f}) is below the recommended threshold (0.7)",
                    "severity": "high",
                    "suggested_action": "Improve task planning and error handling",
                })
        
        # Check accuracy
        if "accuracy" in metrics:
            accuracy = metrics["accuracy"]
            if accuracy < 0.8:
                insights.append({
                    "type": "performance_issue",
                    "metric": "accuracy",
                    "description": f"Accuracy ({accuracy:.2f}) is below the recommended threshold (0.8)",
                    "severity": "high",
                    "suggested_action": "Enhance validation and verification steps",
                })
        
        # Check tool usage efficiency
        if "tool_usage_efficiency" in metrics:
            efficiency = metrics["tool_usage_efficiency"]
            if efficiency < 0.6:
                insights.append({
                    "type": "performance_issue",
                    "metric": "tool_usage_efficiency",
                    "description": f"Tool usage efficiency ({efficiency:.2f}) is below the recommended threshold (0.6)",
                    "severity": "medium",
                    "suggested_action": "Optimize tool selection and reduce redundant tool calls",
                })
        
        # Check for positive patterns
        if "accuracy" in metrics and metrics["accuracy"] > 0.9:
            # Look for patterns in high-accuracy interactions
            task_type = interaction_data.get("task_type")
            if task_type:
                insights.append({
                    "type": "positive_pattern",
                    "metric": "accuracy",
                    "description": f"High accuracy ({metrics['accuracy']:.2f}) achieved for {task_type} task",
                    "severity": "low",
                    "suggested_action": f"Apply similar approach to other task types",
                })
        
        return insights
    
    async def _aggregate_metrics(
        self, time_period: Optional[str] = None, metric_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate metrics across multiple interactions.
        
        Args:
            time_period: Optional time period to filter metrics
            metric_names: Optional list of specific metrics to aggregate
            
        Returns:
            Dict containing aggregated metrics
        """
        # Get all metrics
        all_metrics = list(self.metrics_store.values())
        
        # Filter by time period if specified
        if time_period:
            now = datetime.now()
            filtered_metrics = []
            
            for metrics_data in all_metrics:
                timestamp = datetime.fromisoformat(metrics_data["timestamp"])
                
                if time_period == "day" and (now - timestamp).days <= 1:
                    filtered_metrics.append(metrics_data)
                elif time_period == "week" and (now - timestamp).days <= 7:
                    filtered_metrics.append(metrics_data)
                elif time_period == "month" and (now - timestamp).days <= 30:
                    filtered_metrics.append(metrics_data)
            
            all_metrics = filtered_metrics
        
        # Initialize aggregated metrics
        aggregated = {
            "count": len(all_metrics),
            "average": {},
            "min": {},
            "max": {},
            "median": {},
        }
        
        # If no metrics, return empty aggregation
        if not all_metrics:
            return aggregated
        
        # Get all metric names if not specified
        if not metric_names:
            metric_names = set()
            for metrics_data in all_metrics:
                metric_names.update(metrics_data["metrics"].keys())
            metric_names = list(metric_names)
        
        # Aggregate metrics
        for metric_name in metric_names:
            # Collect all values for this metric
            values = [
                metrics_data["metrics"].get(metric_name)
                for metrics_data in all_metrics
                if metric_name in metrics_data["metrics"] and isinstance(metrics_data["metrics"][metric_name], (int, float))
            ]
            
            if values:
                # Calculate statistics
                aggregated["average"][metric_name] = sum(values) / len(values)
                aggregated["min"][metric_name] = min(values)
                aggregated["max"][metric_name] = max(values)
                
                # Calculate median
                sorted_values = sorted(values)
                mid = len(sorted_values) // 2
                if len(sorted_values) % 2 == 0:
                    aggregated["median"][metric_name] = (sorted_values[mid - 1] + sorted_values[mid]) / 2
                else:
                    aggregated["median"][metric_name] = sorted_values[mid]
        
        # Calculate overall score statistics
        overall_scores = [metrics_data["overall_score"] for metrics_data in all_metrics]
        aggregated["average"]["overall_score"] = sum(overall_scores) / len(overall_scores)
        aggregated["min"]["overall_score"] = min(overall_scores)
        aggregated["max"]["overall_score"] = max(overall_scores)
        
        # Calculate median overall score
        sorted_scores = sorted(overall_scores)
        mid = len(sorted_scores) // 2
        if len(sorted_scores) % 2 == 0:
            aggregated["median"]["overall_score"] = (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
        else:
            aggregated["median"]["overall_score"] = sorted_scores[mid]
        
        return aggregated
    
    def _calculate_kpis(self, aggregated_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate key performance indicators from aggregated metrics.
        
        Args:
            aggregated_metrics: Aggregated metrics data
            
        Returns:
            Dict containing KPIs
        """
        kpis = {}
        
        # Extract average metrics
        avg_metrics = aggregated_metrics.get("average", {})
        
        # Calculate overall performance score
        if "overall_score" in avg_metrics:
            kpis["overall_performance"] = avg_metrics["overall_score"]
        
        # Calculate task success rate
        if "completion_rate" in avg_metrics and "accuracy" in avg_metrics:
            kpis["task_success_rate"] = avg_metrics["completion_rate"] * avg_metrics["accuracy"]
        
        # Calculate user satisfaction index
        if "user_satisfaction" in avg_metrics:
            kpis["user_satisfaction_index"] = avg_metrics["user_satisfaction"]
        
        # Calculate efficiency index
        if "response_time" in avg_metrics and "tool_usage_efficiency" in avg_metrics:
            # Normalize response time (lower is better)
            normalized_response_time = max(0, 1 - (avg_metrics["response_time"] / 10))
            kpis["efficiency_index"] = (normalized_response_time + avg_metrics["tool_usage_efficiency"]) / 2
        
        # Calculate quality index
        if "accuracy" in avg_metrics and "reasoning_quality" in avg_metrics:
            kpis["quality_index"] = (avg_metrics["accuracy"] + avg_metrics["reasoning_quality"]) / 2
        
        return kpis
    
    def _generate_report_insights(
        self, aggregated_metrics: Dict[str, Any], trends: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate insights for a performance report.
        
        Args:
            aggregated_metrics: Aggregated metrics data
            trends: Performance trends data
            
        Returns:
            List of insights
        """
        insights = []
        
        # Extract average metrics
        avg_metrics = aggregated_metrics.get("average", {})
        
        # Check overall performance
        if "overall_score" in avg_metrics:
            overall_score = avg_metrics["overall_score"]
            if overall_score < 0.6:
                insights.append({
                    "type": "performance_concern",
                    "metric": "overall_performance",
                    "description": f"Overall performance ({overall_score:.2f}) is below target (0.7)",
                    "severity": "high",
                })
            elif overall_score > 0.8:
                insights.append({
                    "type": "performance_strength",
                    "metric": "overall_performance",
                    "description": f"Overall performance ({overall_score:.2f}) exceeds target (0.8)",
                    "severity": "low",
                })
        
        # Check metric trends
        for metric_name, trend in trends.get("metric_trends", {}).items():
            if trend.get("direction") == "increasing" and trend.get("significance", 0) > 0.7:
                if metric_name == "response_time":
                    # For response_time, increasing is bad
                    insights.append({
                        "type": "negative_trend",
                        "metric": metric_name,
                        "description": f"{metric_name} is showing a significant increasing trend",
                        "severity": "high",
                    })
                else:
                    # For other metrics, increasing is good
                    insights.append({
                        "type": "positive_trend",
                        "metric": metric_name,
                        "description": f"{metric_name} is showing a significant improving trend",
                        "severity": "low",
                    })
            elif trend.get("direction") == "decreasing" and trend.get("significance", 0) > 0.7:
                if metric_name == "response_time":
                    # For response_time, decreasing is good
                    insights.append({
                        "type": "positive_trend",
                        "metric": metric_name,
                        "description": f"{metric_name} is showing a significant improving trend",
                        "severity": "low",
                    })
                else:
                    # For other metrics, decreasing is bad
                    insights.append({
                        "type": "negative_trend",
                        "metric": metric_name,
                        "description": f"{metric_name} is showing a significant declining trend",
                        "severity": "high",
                    })
        
        # Check for performance gaps
        if "accuracy" in avg_metrics and "completion_rate" in avg_metrics:
            if avg_metrics["accuracy"] > 0.8 and avg_metrics["completion_rate"] < 0.7:
                insights.append({
                    "type": "performance_gap",
                    "metrics": ["accuracy", "completion_rate"],
                    "description": "High accuracy but low completion rate suggests issues with task completion",
                    "severity": "medium",
                })
        
        if "user_satisfaction" in avg_metrics and "accuracy" in avg_metrics:
            if avg_metrics["user_satisfaction"] < 0.7 and avg_metrics["accuracy"] > 0.8:
                insights.append({
                    "type": "performance_gap",
                    "metrics": ["user_satisfaction", "accuracy"],
                    "description": "High accuracy but low user satisfaction suggests issues with user experience",
                    "severity": "medium",
                })
        
        return insights
    
    def _generate_recommendations(
        self, insights: List[Dict[str, Any]], trends: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on insights and trends.
        
        Args:
            insights: Performance insights
            trends: Performance trends
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Generate recommendations based on insights
        for insight in insights:
            if insight["type"] == "performance_concern" and insight["metric"] == "overall_performance":
                recommendations.append({
                    "priority": "high",
                    "area": "overall_performance",
                    "description": "Conduct a comprehensive review of agent performance",
                    "actions": [
                        "Review all metrics to identify specific areas for improvement",
                        "Analyze recent interactions with low performance scores",
                        "Implement targeted improvements for the weakest metrics",
                    ],
                })
            
            elif insight["type"] == "negative_trend":
                metric = insight["metric"]
                recommendations.append({
                    "priority": "high",
                    "area": metric,
                    "description": f"Address declining {metric} performance",
                    "actions": [
                        f"Analyze recent interactions with poor {metric} performance",
                        f"Identify patterns or changes that may have affected {metric}",
                        f"Implement specific improvements targeting {metric}",
                    ],
                })
            
            elif insight["type"] == "performance_gap" and "accuracy" in insight["metrics"] and "completion_rate" in insight["metrics"]:
                recommendations.append({
                    "priority": "medium",
                    "area": "task_completion",
                    "description": "Improve task completion while maintaining accuracy",
                    "actions": [
                        "Enhance error handling and recovery mechanisms",
                        "Implement better progress tracking for complex tasks",
                        "Add validation steps to ensure task requirements are met",
                    ],
                })
            
            elif insight["type"] == "performance_gap" and "user_satisfaction" in insight["metrics"] and "accuracy" in insight["metrics"]:
                recommendations.append({
                    "priority": "medium",
                    "area": "user_experience",
                    "description": "Improve user experience while maintaining accuracy",
                    "actions": [
                        "Enhance explanation clarity and transparency",
                        "Improve response formatting and presentation",
                        "Add more interactive and engaging elements to responses",
                    ],
                })
        
        # Add general recommendations based on trends
        if "overall_trend" in trends and trends["overall_trend"]["direction"] == "stable":
            recommendations.append({
                "priority": "low",
                "area": "innovation",
                "description": "Explore new capabilities to drive performance improvements",
                "actions": [
                    "Experiment with new prompt strategies",
                    "Test enhanced reasoning approaches",
                    "Implement more advanced tool usage patterns",
                ],
            })
        
        return recommendations
