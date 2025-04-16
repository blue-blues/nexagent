"""
Strategy Adaptation Module for Nexagent.

This module provides functionality for dynamically adjusting the bot's approach
based on past performance data.
"""

import json
import time
import random
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from collections import defaultdict

from app.logger import logger
from app.learning.memory_store import MemoryStore, InteractionRecord, default_memory_store
from app.learning.analytics import PerformanceAnalytics, default_performance_analytics


class Strategy:
    """
    Represents a strategy for solving a particular type of task.
    
    A strategy consists of:
    1. A set of parameters that control the bot's behavior
    2. Performance metrics for evaluating the strategy
    3. Conditions under which the strategy should be applied
    """
    
    def __init__(
        self,
        strategy_id: str,
        task_type: str,
        parameters: Dict[str, Any],
        description: str = "",
        created_at: float = None
    ):
        """
        Initialize a strategy.
        
        Args:
            strategy_id: Unique identifier for the strategy
            task_type: Type of task this strategy is for
            parameters: Parameters that control the bot's behavior
            description: Description of the strategy
            created_at: Timestamp when the strategy was created
        """
        self.strategy_id = strategy_id
        self.task_type = task_type
        self.parameters = parameters
        self.description = description
        self.created_at = created_at or time.time()
        self.performance_metrics = {
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "usage_count": 0,
            "last_used": 0.0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the strategy to a dictionary.
        
        Returns:
            Dictionary representation of the strategy
        """
        return {
            "strategy_id": self.strategy_id,
            "task_type": self.task_type,
            "parameters": self.parameters,
            "description": self.description,
            "created_at": self.created_at,
            "performance_metrics": self.performance_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Strategy":
        """
        Create a strategy from a dictionary.
        
        Args:
            data: Dictionary representation of the strategy
            
        Returns:
            Strategy object
        """
        strategy = cls(
            strategy_id=data["strategy_id"],
            task_type=data["task_type"],
            parameters=data["parameters"],
            description=data.get("description", ""),
            created_at=data.get("created_at")
        )
        
        if "performance_metrics" in data:
            strategy.performance_metrics = data["performance_metrics"]
        
        return strategy


class StrategyAdaptation:
    """
    Dynamically adjusts the bot's approach based on past performance data.
    
    This class provides functionality for:
    1. Selecting the best strategy for a given task
    2. Adapting strategies based on performance feedback
    3. Exploring new strategies through controlled experimentation
    4. Tracking strategy performance over time
    """
    
    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        analytics: Optional[PerformanceAnalytics] = None
    ):
        """
        Initialize the strategy adaptation module.
        
        Args:
            memory_store: Optional memory store to use. If None, the default is used.
            analytics: Optional performance analytics to use. If None, the default is used.
        """
        self.memory_store = memory_store or default_memory_store
        self.analytics = analytics or default_performance_analytics
        
        # Dictionary to store strategies by task type
        self.strategies: Dict[str, List[Strategy]] = defaultdict(list)
        
        # Dictionary to track active A/B tests
        self.ab_tests: Dict[str, Dict[str, Any]] = {}
        
        # Exploration rate (probability of trying a non-optimal strategy)
        self.exploration_rate = 0.1
    
    def select_strategy(
        self,
        task_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Strategy:
        """
        Select the best strategy for a given task type.
        
        Args:
            task_type: Type of task to select a strategy for
            context: Optional context information about the task
            
        Returns:
            The selected strategy
        """
        # Get strategies for the task type
        strategies = self.strategies.get(task_type, [])
        
        # If no strategies exist, create a default one
        if not strategies:
            default_strategy = self._create_default_strategy(task_type)
            strategies = [default_strategy]
            self.strategies[task_type] = strategies
        
        # Check if there's an active A/B test for this task type
        if task_type in self.ab_tests:
            return self._select_ab_test_strategy(task_type, context)
        
        # Decide whether to explore or exploit
        if random.random() < self.exploration_rate:
            # Exploration: select a random strategy
            return random.choice(strategies)
        else:
            # Exploitation: select the best strategy
            return self._select_best_strategy(strategies, context)
    
    def _select_best_strategy(
        self,
        strategies: List[Strategy],
        context: Optional[Dict[str, Any]] = None
    ) -> Strategy:
        """
        Select the best strategy from a list of strategies.
        
        Args:
            strategies: List of strategies to choose from
            context: Optional context information about the task
            
        Returns:
            The best strategy
        """
        # If there's only one strategy, return it
        if len(strategies) == 1:
            return strategies[0]
        
        # Sort strategies by success rate (descending)
        sorted_strategies = sorted(
            strategies,
            key=lambda s: s.performance_metrics["success_rate"],
            reverse=True
        )
        
        # Return the strategy with the highest success rate
        return sorted_strategies[0]
    
    def _select_ab_test_strategy(
        self,
        task_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Strategy:
        """
        Select a strategy for an active A/B test.
        
        Args:
            task_type: Type of task to select a strategy for
            context: Optional context information about the task
            
        Returns:
            The selected strategy
        """
        ab_test = self.ab_tests[task_type]
        strategies = self.strategies[task_type]
        
        # Get the strategies being tested
        strategy_a_id = ab_test["strategy_a_id"]
        strategy_b_id = ab_test["strategy_b_id"]
        
        strategy_a = next((s for s in strategies if s.strategy_id == strategy_a_id), None)
        strategy_b = next((s for s in strategies if s.strategy_id == strategy_b_id), None)
        
        if not strategy_a or not strategy_b:
            # If one of the strategies is missing, fall back to the best strategy
            return self._select_best_strategy(strategies, context)
        
        # Randomly select between the two strategies based on the test weights
        weight_a = ab_test.get("weight_a", 0.5)
        weight_b = ab_test.get("weight_b", 0.5)
        
        if random.random() < weight_a / (weight_a + weight_b):
            return strategy_a
        else:
            return strategy_b
    
    def _create_default_strategy(self, task_type: str) -> Strategy:
        """
        Create a default strategy for a task type.
        
        Args:
            task_type: Type of task to create a strategy for
            
        Returns:
            The created strategy
        """
        strategy_id = f"{task_type}_default_{int(time.time())}"
        
        # Create default parameters based on task type
        parameters = {}
        
        if task_type == "code_generation":
            parameters = {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "tools": ["code_generation", "code_analyzer"]
            }
        elif task_type == "web_search":
            parameters = {
                "model": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 1000,
                "tools": ["web_search", "enhanced_browser"]
            }
        elif task_type == "planning":
            parameters = {
                "model": "gpt-4",
                "temperature": 0.5,
                "max_tokens": 1500,
                "tools": ["planning", "keyword_extraction"]
            }
        else:
            # Generic default parameters
            parameters = {
                "model": "gpt-4",
                "temperature": 0.5,
                "max_tokens": 1000,
                "tools": []
            }
        
        # Create the strategy
        strategy = Strategy(
            strategy_id=strategy_id,
            task_type=task_type,
            parameters=parameters,
            description=f"Default strategy for {task_type} tasks"
        )
        
        return strategy
    
    def update_strategy_performance(
        self,
        strategy: Strategy,
        success: bool,
        execution_time: float
    ) -> None:
        """
        Update a strategy's performance metrics.
        
        Args:
            strategy: The strategy to update
            success: Whether the strategy was successful
            execution_time: The execution time of the strategy
        """
        # Update usage count
        strategy.performance_metrics["usage_count"] += 1
        
        # Update last used timestamp
        strategy.performance_metrics["last_used"] = time.time()
        
        # Update success rate using exponential moving average
        alpha = 0.1  # Weight for the new observation
        old_success_rate = strategy.performance_metrics["success_rate"]
        new_success_rate = (1 - alpha) * old_success_rate + alpha * (1.0 if success else 0.0)
        strategy.performance_metrics["success_rate"] = new_success_rate
        
        # Update average execution time using exponential moving average
        old_avg_time = strategy.performance_metrics["avg_execution_time"]
        new_avg_time = (1 - alpha) * old_avg_time + alpha * execution_time
        strategy.performance_metrics["avg_execution_time"] = new_avg_time
    
    def create_strategy_variant(
        self,
        base_strategy: Strategy,
        parameter_changes: Dict[str, Any],
        description: str = ""
    ) -> Strategy:
        """
        Create a variant of an existing strategy.
        
        Args:
            base_strategy: The base strategy to create a variant of
            parameter_changes: Changes to make to the base strategy's parameters
            description: Description of the variant
            
        Returns:
            The created strategy variant
        """
        # Create a new strategy ID
        strategy_id = f"{base_strategy.task_type}_variant_{int(time.time())}"
        
        # Create new parameters by updating the base strategy's parameters
        parameters = base_strategy.parameters.copy()
        parameters.update(parameter_changes)
        
        # Create the variant strategy
        variant = Strategy(
            strategy_id=strategy_id,
            task_type=base_strategy.task_type,
            parameters=parameters,
            description=description or f"Variant of {base_strategy.strategy_id}"
        )
        
        # Add the variant to the strategies for this task type
        self.strategies[base_strategy.task_type].append(variant)
        
        return variant
    
    def start_ab_test(
        self,
        task_type: str,
        strategy_a_id: str,
        strategy_b_id: str,
        weight_a: float = 0.5,
        weight_b: float = 0.5,
        duration_days: int = 7
    ) -> Dict[str, Any]:
        """
        Start an A/B test between two strategies.
        
        Args:
            task_type: Type of task to test strategies for
            strategy_a_id: ID of the first strategy
            strategy_b_id: ID of the second strategy
            weight_a: Weight for the first strategy
            weight_b: Weight for the second strategy
            duration_days: Duration of the test in days
            
        Returns:
            Dictionary with A/B test information
        """
        # Check if the strategies exist
        strategies = self.strategies.get(task_type, [])
        strategy_a = next((s for s in strategies if s.strategy_id == strategy_a_id), None)
        strategy_b = next((s for s in strategies if s.strategy_id == strategy_b_id), None)
        
        if not strategy_a:
            raise ValueError(f"Strategy {strategy_a_id} not found")
        
        if not strategy_b:
            raise ValueError(f"Strategy {strategy_b_id} not found")
        
        # Create the A/B test
        ab_test = {
            "task_type": task_type,
            "strategy_a_id": strategy_a_id,
            "strategy_b_id": strategy_b_id,
            "weight_a": weight_a,
            "weight_b": weight_b,
            "start_time": time.time(),
            "end_time": time.time() + (duration_days * 24 * 60 * 60),
            "results": {
                "strategy_a": {
                    "usage_count": 0,
                    "success_count": 0,
                    "total_execution_time": 0.0
                },
                "strategy_b": {
                    "usage_count": 0,
                    "success_count": 0,
                    "total_execution_time": 0.0
                }
            }
        }
        
        # Store the A/B test
        self.ab_tests[task_type] = ab_test
        
        return ab_test
    
    def update_ab_test_results(
        self,
        task_type: str,
        strategy_id: str,
        success: bool,
        execution_time: float
    ) -> None:
        """
        Update the results of an A/B test.
        
        Args:
            task_type: Type of task the test is for
            strategy_id: ID of the strategy used
            success: Whether the strategy was successful
            execution_time: The execution time of the strategy
        """
        if task_type not in self.ab_tests:
            return
        
        ab_test = self.ab_tests[task_type]
        
        # Determine which strategy was used
        if strategy_id == ab_test["strategy_a_id"]:
            strategy_key = "strategy_a"
        elif strategy_id == ab_test["strategy_b_id"]:
            strategy_key = "strategy_b"
        else:
            return
        
        # Update the results
        results = ab_test["results"][strategy_key]
        results["usage_count"] += 1
        if success:
            results["success_count"] += 1
        results["total_execution_time"] += execution_time
    
    def check_ab_test_completion(self) -> List[Dict[str, Any]]:
        """
        Check if any A/B tests have completed and process their results.
        
        Returns:
            List of completed A/B tests with their results
        """
        current_time = time.time()
        completed_tests = []
        
        # Check each A/B test
        for task_type, ab_test in list(self.ab_tests.items()):
            if current_time >= ab_test["end_time"]:
                # Process the test results
                completed_test = self._process_ab_test_results(task_type, ab_test)
                completed_tests.append(completed_test)
                
                # Remove the completed test
                del self.ab_tests[task_type]
        
        return completed_tests
    
    def _process_ab_test_results(
        self,
        task_type: str,
        ab_test: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process the results of a completed A/B test.
        
        Args:
            task_type: Type of task the test was for
            ab_test: The A/B test data
            
        Returns:
            Dictionary with processed test results
        """
        # Get the strategies
        strategies = self.strategies.get(task_type, [])
        strategy_a = next((s for s in strategies if s.strategy_id == ab_test["strategy_a_id"]), None)
        strategy_b = next((s for s in strategies if s.strategy_id == ab_test["strategy_b_id"]), None)
        
        if not strategy_a or not strategy_b:
            return {
                "task_type": task_type,
                "error": "One or both strategies not found",
                "ab_test": ab_test
            }
        
        # Calculate success rates
        results_a = ab_test["results"]["strategy_a"]
        results_b = ab_test["results"]["strategy_b"]
        
        success_rate_a = results_a["success_count"] / results_a["usage_count"] if results_a["usage_count"] > 0 else 0
        success_rate_b = results_b["success_count"] / results_b["usage_count"] if results_b["usage_count"] > 0 else 0
        
        # Calculate average execution times
        avg_time_a = results_a["total_execution_time"] / results_a["usage_count"] if results_a["usage_count"] > 0 else 0
        avg_time_b = results_b["total_execution_time"] / results_b["usage_count"] if results_b["usage_count"] > 0 else 0
        
        # Determine the winner
        if success_rate_a > success_rate_b:
            winner = "strategy_a"
            winner_id = ab_test["strategy_a_id"]
        elif success_rate_b > success_rate_a:
            winner = "strategy_b"
            winner_id = ab_test["strategy_b_id"]
        else:
            # If success rates are equal, choose the one with lower execution time
            if avg_time_a < avg_time_b:
                winner = "strategy_a"
                winner_id = ab_test["strategy_a_id"]
            else:
                winner = "strategy_b"
                winner_id = ab_test["strategy_b_id"]
        
        # Update the strategies with the test results
        strategy_a.performance_metrics["success_rate"] = success_rate_a
        strategy_a.performance_metrics["avg_execution_time"] = avg_time_a
        
        strategy_b.performance_metrics["success_rate"] = success_rate_b
        strategy_b.performance_metrics["avg_execution_time"] = avg_time_b
        
        # Return the processed results
        return {
            "task_type": task_type,
            "start_time": ab_test["start_time"],
            "end_time": ab_test["end_time"],
            "strategy_a": {
                "id": ab_test["strategy_a_id"],
                "usage_count": results_a["usage_count"],
                "success_rate": success_rate_a,
                "avg_execution_time": avg_time_a
            },
            "strategy_b": {
                "id": ab_test["strategy_b_id"],
                "usage_count": results_b["usage_count"],
                "success_rate": success_rate_b,
                "avg_execution_time": avg_time_b
            },
            "winner": winner,
            "winner_id": winner_id
        }
    
    def adapt_strategies_based_on_performance(self) -> List[Dict[str, Any]]:
        """
        Adapt strategies based on performance data.
        
        This method:
        1. Analyzes performance data for each task type
        2. Identifies underperforming strategies
        3. Creates new strategy variants to improve performance
        
        Returns:
            List of adaptations made
        """
        adaptations = []
        
        # Check each task type
        for task_type, strategies in self.strategies.items():
            # Skip if there are no strategies
            if not strategies:
                continue
            
            # Get performance data for this task type
            task_analysis = self.analytics.analyze(task_type=task_type)
            
            # Skip if there's no performance data
            if "success_rate" not in task_analysis:
                continue
            
            # Get the overall success rate for this task type
            overall_success_rate = task_analysis["success_rate"]["success_rate"]
            
            # Identify underperforming strategies
            underperforming = []
            for strategy in strategies:
                if strategy.performance_metrics["usage_count"] >= 10:  # Only consider strategies with enough data
                    if strategy.performance_metrics["success_rate"] < overall_success_rate - 0.1:  # 10% below average
                        underperforming.append(strategy)
            
            # Create variants for underperforming strategies
            for strategy in underperforming:
                # Create a variant with adjusted parameters
                parameter_changes = self._generate_parameter_changes(strategy, task_analysis)
                
                variant = self.create_strategy_variant(
                    base_strategy=strategy,
                    parameter_changes=parameter_changes,
                    description=f"Adaptive variant of {strategy.strategy_id} to improve performance"
                )
                
                # Start an A/B test between the original and the variant
                ab_test = self.start_ab_test(
                    task_type=task_type,
                    strategy_a_id=strategy.strategy_id,
                    strategy_b_id=variant.strategy_id,
                    weight_a=0.3,  # Favor the new variant
                    weight_b=0.7,
                    duration_days=3  # Short test period
                )
                
                adaptations.append({
                    "task_type": task_type,
                    "original_strategy_id": strategy.strategy_id,
                    "variant_strategy_id": variant.strategy_id,
                    "parameter_changes": parameter_changes,
                    "ab_test": ab_test
                })
        
        return adaptations
    
    def _generate_parameter_changes(
        self,
        strategy: Strategy,
        task_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate parameter changes to improve a strategy.
        
        Args:
            strategy: The strategy to improve
            task_analysis: Performance analysis for the task type
            
        Returns:
            Dictionary with parameter changes
        """
        parameters = strategy.parameters.copy()
        changes = {}
        
        # Adjust temperature based on success rate
        if "temperature" in parameters:
            current_temp = parameters["temperature"]
            success_rate = strategy.performance_metrics["success_rate"]
            
            if success_rate < 0.5:
                # If success rate is low, reduce temperature for more conservative outputs
                new_temp = max(0.1, current_temp - 0.2)
                changes["temperature"] = new_temp
            elif success_rate > 0.9:
                # If success rate is very high, we can try increasing temperature for more creativity
                new_temp = min(1.0, current_temp + 0.1)
                changes["temperature"] = new_temp
        
        # Adjust max_tokens based on execution time
        if "max_tokens" in parameters:
            current_max = parameters["max_tokens"]
            avg_time = strategy.performance_metrics["avg_execution_time"]
            
            if avg_time > 10.0:  # If execution is slow
                # Reduce max_tokens to speed up execution
                new_max = max(500, int(current_max * 0.8))
                changes["max_tokens"] = new_max
        
        # Adjust model based on task complexity
        if "model" in parameters:
            current_model = parameters["model"]
            
            if strategy.performance_metrics["success_rate"] < 0.4:
                # If success rate is very low, try a more powerful model
                if current_model == "gpt-3.5-turbo":
                    changes["model"] = "gpt-4"
        
        # Adjust tools based on task type
        if "tools" in parameters:
            current_tools = parameters["tools"]
            
            # Get tool usage from the task analysis
            if "tool_usage" in task_analysis:
                tool_usage = task_analysis["tool_usage"]
                
                # Find tools with high success rates
                successful_tools = []
                for tool, tool_data in tool_usage.get("tool_success_rates", {}).items():
                    if tool_data > 0.8:  # 80% success rate
                        successful_tools.append(tool)
                
                # Add successful tools that aren't already in the strategy
                for tool in successful_tools:
                    if tool not in current_tools:
                        changes["tools"] = current_tools + [tool]
                        break
        
        return changes
    
    def save_strategies(self, file_path: str) -> None:
        """
        Save strategies to a file.
        
        Args:
            file_path: Path to save the strategies to
        """
        try:
            # Convert strategies to dictionaries
            strategies_dict = {}
            for task_type, strategies in self.strategies.items():
                strategies_dict[task_type] = [s.to_dict() for s in strategies]
            
            # Save to file
            with open(file_path, "w") as f:
                json.dump(strategies_dict, f, indent=2)
            
            logger.info(f"Saved strategies to {file_path}")
        
        except Exception as e:
            logger.error(f"Error saving strategies: {str(e)}")
    
    def load_strategies(self, file_path: str) -> None:
        """
        Load strategies from a file.
        
        Args:
            file_path: Path to load the strategies from
        """
        try:
            # Load from file
            with open(file_path, "r") as f:
                strategies_dict = json.load(f)
            
            # Convert dictionaries to Strategy objects
            for task_type, strategies_data in strategies_dict.items():
                self.strategies[task_type] = [
                    Strategy.from_dict(s) for s in strategies_data
                ]
            
            logger.info(f"Loaded strategies from {file_path}")
        
        except Exception as e:
            logger.error(f"Error loading strategies: {str(e)}")


# Create a default strategy adaptation instance
default_strategy_adaptation = StrategyAdaptation()
