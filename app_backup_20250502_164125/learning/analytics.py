"""
Performance Analytics Engine for Nexagent.

This module provides functionality for analyzing the bot's performance
across different tasks and domains to identify strengths and weaknesses.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
import statistics
from collections import defaultdict

from app.logger import logger
from app.learning.memory_store import MemoryStore, InteractionRecord, default_memory_store


class PerformanceMetric:
    """Base class for performance metrics."""
    
    name: str = "base_metric"
    description: str = "Base performance metric"
    
    def calculate(self, records: List[InteractionRecord]) -> Dict[str, Any]:
        """
        Calculate the metric value from a list of interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Dictionary with metric values
        """
        raise NotImplementedError("Subclasses must implement calculate()")


class SuccessRateMetric(PerformanceMetric):
    """Metric for measuring success rate."""
    
    name: str = "success_rate"
    description: str = "Percentage of successful interactions"
    
    def calculate(self, records: List[InteractionRecord]) -> Dict[str, Any]:
        """
        Calculate the success rate from a list of interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Dictionary with success rate metrics
        """
        if not records:
            return {
                "success_rate": 0,
                "success_count": 0,
                "total_count": 0
            }
        
        success_count = sum(1 for record in records if record.success)
        total_count = len(records)
        success_rate = success_count / total_count
        
        return {
            "success_rate": success_rate,
            "success_count": success_count,
            "total_count": total_count
        }


class ExecutionTimeMetric(PerformanceMetric):
    """Metric for measuring execution time."""
    
    name: str = "execution_time"
    description: str = "Statistics about execution time"
    
    def calculate(self, records: List[InteractionRecord]) -> Dict[str, Any]:
        """
        Calculate execution time statistics from a list of interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Dictionary with execution time metrics
        """
        if not records:
            return {
                "avg_execution_time": 0,
                "min_execution_time": 0,
                "max_execution_time": 0,
                "median_execution_time": 0
            }
        
        execution_times = [record.execution_time for record in records]
        
        return {
            "avg_execution_time": statistics.mean(execution_times),
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "median_execution_time": statistics.median(execution_times)
        }


class ToolUsageMetric(PerformanceMetric):
    """Metric for analyzing tool usage."""
    
    name: str = "tool_usage"
    description: str = "Statistics about tool usage"
    
    def calculate(self, records: List[InteractionRecord]) -> Dict[str, Any]:
        """
        Calculate tool usage statistics from a list of interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Dictionary with tool usage metrics
        """
        if not records:
            return {
                "tool_counts": {},
                "tool_success_rates": {}
            }
        
        # Count tool usage
        tool_counts = defaultdict(int)
        tool_success_counts = defaultdict(int)
        
        for record in records:
            for tool in record.tools_used:
                tool_counts[tool] += 1
                if record.success:
                    tool_success_counts[tool] += 1
        
        # Calculate success rates
        tool_success_rates = {}
        for tool, count in tool_counts.items():
            success_count = tool_success_counts[tool]
            tool_success_rates[tool] = success_count / count
        
        return {
            "tool_counts": dict(tool_counts),
            "tool_success_rates": tool_success_rates
        }


class TaskTypeMetric(PerformanceMetric):
    """Metric for analyzing performance by task type."""
    
    name: str = "task_type"
    description: str = "Performance metrics broken down by task type"
    
    def calculate(self, records: List[InteractionRecord]) -> Dict[str, Any]:
        """
        Calculate task type statistics from a list of interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Dictionary with task type metrics
        """
        if not records:
            return {
                "task_type_counts": {},
                "task_type_success_rates": {}
            }
        
        # Group records by task type
        task_type_records = defaultdict(list)
        for record in records:
            if record.task_type:
                task_type_records[record.task_type].append(record)
        
        # Calculate metrics for each task type
        task_type_counts = {}
        task_type_success_rates = {}
        task_type_avg_execution_times = {}
        
        for task_type, task_records in task_type_records.items():
            # Count
            task_type_counts[task_type] = len(task_records)
            
            # Success rate
            success_count = sum(1 for record in task_records if record.success)
            task_type_success_rates[task_type] = success_count / len(task_records)
            
            # Average execution time
            execution_times = [record.execution_time for record in task_records]
            task_type_avg_execution_times[task_type] = statistics.mean(execution_times)
        
        return {
            "task_type_counts": task_type_counts,
            "task_type_success_rates": task_type_success_rates,
            "task_type_avg_execution_times": task_type_avg_execution_times
        }


class TimeSeriesMetric(PerformanceMetric):
    """Metric for analyzing performance over time."""
    
    name: str = "time_series"
    description: str = "Performance metrics over time"
    
    def calculate(self, records: List[InteractionRecord]) -> Dict[str, Any]:
        """
        Calculate time series statistics from a list of interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Dictionary with time series metrics
        """
        if not records:
            return {
                "daily_counts": {},
                "daily_success_rates": {}
            }
        
        # Sort records by timestamp
        sorted_records = sorted(records, key=lambda r: r.timestamp)
        
        # Group records by day
        daily_records = defaultdict(list)
        for record in sorted_records:
            day = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d")
            daily_records[day].append(record)
        
        # Calculate metrics for each day
        daily_counts = {}
        daily_success_rates = {}
        daily_avg_execution_times = {}
        
        for day, day_records in daily_records.items():
            # Count
            daily_counts[day] = len(day_records)
            
            # Success rate
            success_count = sum(1 for record in day_records if record.success)
            daily_success_rates[day] = success_count / len(day_records)
            
            # Average execution time
            execution_times = [record.execution_time for record in day_records]
            daily_avg_execution_times[day] = statistics.mean(execution_times)
        
        return {
            "daily_counts": daily_counts,
            "daily_success_rates": daily_success_rates,
            "daily_avg_execution_times": daily_avg_execution_times
        }


class PerformanceAnalytics:
    """
    Analyzes the bot's performance across different tasks and domains.
    
    This class provides functionality for:
    1. Calculating various performance metrics
    2. Identifying strengths and weaknesses
    3. Tracking performance trends over time
    4. Generating performance reports
    """
    
    def __init__(self, memory_store: Optional[MemoryStore] = None):
        """
        Initialize the performance analytics engine.
        
        Args:
            memory_store: Optional memory store to use. If None, the default is used.
        """
        self.memory_store = memory_store or default_memory_store
        self.metrics = [
            SuccessRateMetric(),
            ExecutionTimeMetric(),
            ToolUsageMetric(),
            TaskTypeMetric(),
            TimeSeriesMetric()
        ]
    
    def analyze(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        task_type: Optional[str] = None,
        tool_used: Optional[str] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Analyze performance based on various criteria.
        
        Args:
            start_time: Optional start timestamp to filter by
            end_time: Optional end timestamp to filter by
            task_type: Optional task type to filter by
            tool_used: Optional tool name to filter by
            limit: Maximum number of records to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Get records from the memory store
        records = self.memory_store.search_interactions(
            task_type=task_type,
            tool_used=tool_used,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        if not records:
            return {
                "error": "No records found matching the criteria",
                "record_count": 0
            }
        
        # Calculate metrics
        results = {
            "record_count": len(records),
            "time_range": {
                "start": min(record.timestamp for record in records),
                "end": max(record.timestamp for record in records)
            }
        }
        
        for metric in self.metrics:
            results[metric.name] = metric.calculate(records)
        
        return results
    
    def analyze_by_period(
        self,
        period: str = "day",
        days: int = 30,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze performance by time period.
        
        Args:
            period: Time period to group by (day, week, month)
            days: Number of days to analyze
            task_type: Optional task type to filter by
            
        Returns:
            Dictionary with analysis results by period
        """
        # Calculate start time
        end_time = time.time()
        start_time = end_time - (days * 24 * 60 * 60)
        
        # Get records from the memory store
        records = self.memory_store.search_interactions(
            task_type=task_type,
            start_time=start_time,
            end_time=end_time,
            limit=10000  # Large limit to get all records
        )
        
        if not records:
            return {
                "error": "No records found matching the criteria",
                "record_count": 0
            }
        
        # Group records by period
        period_records = defaultdict(list)
        
        for record in records:
            record_date = datetime.fromtimestamp(record.timestamp)
            
            if period == "day":
                period_key = record_date.strftime("%Y-%m-%d")
            elif period == "week":
                # Get the start of the week (Monday)
                start_of_week = record_date - timedelta(days=record_date.weekday())
                period_key = start_of_week.strftime("%Y-%m-%d")
            elif period == "month":
                period_key = record_date.strftime("%Y-%m")
            else:
                raise ValueError(f"Invalid period: {period}")
            
            period_records[period_key].append(record)
        
        # Calculate metrics for each period
        results = {
            "record_count": len(records),
            "period": period,
            "periods": {}
        }
        
        for period_key, period_records_list in period_records.items():
            period_results = {}
            
            for metric in self.metrics:
                period_results[metric.name] = metric.calculate(period_records_list)
            
            results["periods"][period_key] = period_results
        
        return results
    
    def identify_strengths_and_weaknesses(self) -> Dict[str, Any]:
        """
        Identify the bot's strengths and weaknesses.
        
        Returns:
            Dictionary with strengths and weaknesses
        """
        # Get overall statistics
        stats = self.memory_store.get_statistics()
        
        # Analyze task types
        task_type_analysis = self.analyze_by_task_type()
        
        # Identify strengths (high success rate)
        strengths = []
        weaknesses = []
        
        # Overall success rate
        overall_success_rate = stats.get("success_rate", 0)
        
        # Analyze task types
        task_type_success_rates = {}
        if "task_type_distribution" in stats:
            for task_type in stats["task_type_distribution"]:
                task_analysis = self.analyze(task_type=task_type)
                if "success_rate" in task_analysis:
                    success_rate = task_analysis["success_rate"]["success_rate"]
                    task_type_success_rates[task_type] = success_rate
        
        # Identify strengths and weaknesses
        for task_type, success_rate in task_type_success_rates.items():
            if success_rate > 0.8:  # 80% success rate threshold for strengths
                strengths.append({
                    "task_type": task_type,
                    "success_rate": success_rate,
                    "count": stats["task_type_distribution"].get(task_type, 0)
                })
            elif success_rate < 0.5:  # 50% success rate threshold for weaknesses
                weaknesses.append({
                    "task_type": task_type,
                    "success_rate": success_rate,
                    "count": stats["task_type_distribution"].get(task_type, 0)
                })
        
        # Analyze tool usage
        tool_success_rates = {}
        if "tool_usage" in stats:
            for tool in stats["tool_usage"]:
                tool_analysis = self.analyze(tool_used=tool)
                if "success_rate" in tool_analysis:
                    success_rate = tool_analysis["success_rate"]["success_rate"]
                    tool_success_rates[tool] = success_rate
        
        # Identify tool strengths and weaknesses
        tool_strengths = []
        tool_weaknesses = []
        
        for tool, success_rate in tool_success_rates.items():
            if success_rate > 0.8:  # 80% success rate threshold for strengths
                tool_strengths.append({
                    "tool": tool,
                    "success_rate": success_rate,
                    "count": stats["tool_usage"].get(tool, 0)
                })
            elif success_rate < 0.5:  # 50% success rate threshold for weaknesses
                tool_weaknesses.append({
                    "tool": tool,
                    "success_rate": success_rate,
                    "count": stats["tool_usage"].get(tool, 0)
                })
        
        return {
            "overall_success_rate": overall_success_rate,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "tool_strengths": tool_strengths,
            "tool_weaknesses": tool_weaknesses
        }
    
    def analyze_by_task_type(self) -> Dict[str, Any]:
        """
        Analyze performance by task type.
        
        Returns:
            Dictionary with analysis results by task type
        """
        # Get statistics from the memory store
        stats = self.memory_store.get_statistics()
        
        if "task_type_distribution" not in stats:
            return {
                "error": "No task type distribution available",
                "task_types": {}
            }
        
        # Analyze each task type
        results = {
            "task_types": {}
        }
        
        for task_type in stats["task_type_distribution"]:
            task_analysis = self.analyze(task_type=task_type)
            results["task_types"][task_type] = task_analysis
        
        return results
    
    def analyze_by_tool(self) -> Dict[str, Any]:
        """
        Analyze performance by tool.
        
        Returns:
            Dictionary with analysis results by tool
        """
        # Get statistics from the memory store
        stats = self.memory_store.get_statistics()
        
        if "tool_usage" not in stats:
            return {
                "error": "No tool usage available",
                "tools": {}
            }
        
        # Analyze each tool
        results = {
            "tools": {}
        }
        
        for tool in stats["tool_usage"]:
            tool_analysis = self.analyze(tool_used=tool)
            results["tools"][tool] = tool_analysis
        
        return results
    
    def generate_report(self) -> str:
        """
        Generate a comprehensive performance report.
        
        Returns:
            Formatted report as a string
        """
        # Get overall statistics
        stats = self.memory_store.get_statistics()
        
        # Identify strengths and weaknesses
        strengths_and_weaknesses = self.identify_strengths_and_weaknesses()
        
        # Analyze performance over time
        time_analysis = self.analyze_by_period(period="day", days=30)
        
        # Format the report
        report = "# Nexagent Performance Report\n\n"
        
        # Overall statistics
        report += "## Overall Statistics\n\n"
        report += f"- Total interactions: {stats.get('total_count', 0)}\n"
        report += f"- Success rate: {stats.get('success_rate', 0) * 100:.1f}%\n"
        report += f"- Average execution time: {stats.get('avg_execution_time', 0):.2f} seconds\n\n"
        
        # Strengths and weaknesses
        report += "## Strengths and Weaknesses\n\n"
        
        report += "### Strengths\n\n"
        for strength in strengths_and_weaknesses.get("strengths", []):
            report += f"- {strength['task_type']}: {strength['success_rate'] * 100:.1f}% success rate ({strength['count']} interactions)\n"
        
        report += "\n### Weaknesses\n\n"
        for weakness in strengths_and_weaknesses.get("weaknesses", []):
            report += f"- {weakness['task_type']}: {weakness['success_rate'] * 100:.1f}% success rate ({weakness['count']} interactions)\n"
        
        report += "\n### Tool Performance\n\n"
        
        report += "#### Strong Tools\n\n"
        for tool in strengths_and_weaknesses.get("tool_strengths", []):
            report += f"- {tool['tool']}: {tool['success_rate'] * 100:.1f}% success rate ({tool['count']} uses)\n"
        
        report += "\n#### Weak Tools\n\n"
        for tool in strengths_and_weaknesses.get("tool_weaknesses", []):
            report += f"- {tool['tool']}: {tool['success_rate'] * 100:.1f}% success rate ({tool['count']} uses)\n"
        
        # Performance over time
        report += "\n## Performance Trends\n\n"
        
        if "periods" in time_analysis:
            report += "### Daily Success Rate\n\n"
            for period, period_data in time_analysis["periods"].items():
                if "success_rate" in period_data:
                    success_rate = period_data["success_rate"]["success_rate"] * 100
                    report += f"- {period}: {success_rate:.1f}%\n"
        
        return report


# Create a default performance analytics instance
default_performance_analytics = PerformanceAnalytics()
