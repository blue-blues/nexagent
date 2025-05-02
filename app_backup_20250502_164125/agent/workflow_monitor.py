from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
import json

from app.agent.base import BaseAgent
from app.agent.workflow_generator import WorkflowStep
from app.tool.base import ToolResult
from app.logger import logger

class ExecutionMetrics(BaseModel):
    """Tracks performance metrics for workflow execution."""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error_count: int = 0
    retry_count: int = 0
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    success_rate: float = 1.0
    cognitive_load: float = 0.0  # Measures complexity of current task
    context_switches: int = 0  # Number of times execution switched context
    decision_confidence: float = 1.0  # Confidence level in decisions made
    resource_efficiency: float = 1.0  # Ratio of output quality to resource usage

class StepExecution(BaseModel):
    """Records execution details for a single workflow step."""
    step: WorkflowStep
    metrics: ExecutionMetrics
    status: str  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    rollback_status: Optional[str] = None

class WorkflowMonitor:
    """Monitors and optimizes workflow execution in real-time."""

    def __init__(self, agent: BaseAgent):
        self.agent = agent
        self.executions: Dict[str, List[StepExecution]] = {}
        self.active_workflows: Dict[str, asyncio.Task] = {}
        self.telemetry_buffer: List[Dict[str, Any]] = []
        self.transports: List[asyncio.BaseTransport] = []
        self.performance_thresholds = {
            "error_rate": 0.2,
            "success_rate": 0.8,
            "max_retries": 5,
            "memory_threshold": 0.9,
            "cpu_threshold": 0.8,
            "cognitive_load_threshold": 0.7,
            "context_switch_limit": 10,
            "min_decision_confidence": 0.6,
            "resource_efficiency_target": 0.8
        }
        self.resource_pool = {
            "memory": [],
            "cpu": [],
            "io": []
        }

    async def start_monitoring(self, workflow_id: str, steps: List[WorkflowStep]) -> None:
        """Initialize monitoring for a new workflow execution."""
        self.executions[workflow_id] = [
            StepExecution(
                step=step,
                metrics=ExecutionMetrics(start_time=datetime.now()),
                status="pending"
            ) for step in steps
        ]
        
        # Start telemetry collection with proper cleanup
        task = asyncio.create_task(self._collect_telemetry(workflow_id))
        task.add_done_callback(lambda t: self._cleanup_workflow(workflow_id))
        self.active_workflows[workflow_id] = task

    async def record_step_execution(self, workflow_id: str, step_id: str,
                                  result: Optional[ToolResult] = None,
                                  error: Optional[Exception] = None) -> None:
        """Record execution results and update metrics for a workflow step."""
        if workflow_id not in self.executions:
            return

        for execution in self.executions[workflow_id]:
            if execution.step.step_id == step_id:
                execution.metrics.end_time = datetime.now()
                execution.metrics.duration_ms = (
                    execution.metrics.end_time - execution.metrics.start_time
                ).total_seconds() * 1000

                if error:
                    execution.status = "failed"
                    execution.error = str(error)
                    execution.metrics.error_count += 1
                    execution.metrics.success_rate = max(
                        0, execution.metrics.success_rate - 0.1
                    )
                    await self._handle_failure(workflow_id, execution)
                else:
                    execution.status = "completed"
                    execution.result = result
                break

    async def _handle_failure(self, workflow_id: str, execution: StepExecution) -> None:
        """Handle step failures with automated recovery strategies."""
        if not execution.step.fallback_strategy:
            return

        strategy = execution.step.fallback_strategy
        if strategy.get("retry_strategy") == "exponential_backoff":
            await self._retry_with_backoff(workflow_id, execution)
        elif strategy.get("alternative_tool"):
            await self._try_alternative_tool(workflow_id, execution)

    async def _retry_with_backoff(self, workflow_id: str, execution: StepExecution) -> None:
        """Implement exponential backoff retry strategy."""
        max_retries = execution.step.fallback_strategy.get("max_retries", 3)
        base_delay = 1.0

        for attempt in range(max_retries):
            execution.metrics.retry_count += 1
            delay = base_delay * (2 ** attempt)
            
            logger.info(
                f"Retrying step {execution.step.step_id} in workflow {workflow_id} "
                f"after {delay} seconds (attempt {attempt + 1}/{max_retries})"
            )
            
            await asyncio.sleep(delay)
            
            try:
                result = await self.agent.available_tools.execute(
                    name=execution.step.tool_name,
                    **execution.step.tool_params
                )
                if not isinstance(result, ToolResult) or not result.error:
                    execution.status = "completed"
                    execution.result = result
                    execution.metrics.success_rate = max(
                        0.5, execution.metrics.success_rate
                    )
                    break
            except Exception as e:
                logger.error(f"Retry attempt {attempt + 1} failed: {e}")

    async def _try_alternative_tool(self, workflow_id: str, execution: StepExecution) -> None:
        """Attempt execution with an alternative tool."""
        alt_tool = execution.step.fallback_strategy.get("alternative_tool")
        if not alt_tool or alt_tool not in self.agent.available_tools.tool_map:
            return

        try:
            result = await self.agent.available_tools.execute(
                name=alt_tool,
                **execution.step.tool_params
            )
            if not isinstance(result, ToolResult) or not result.error:
                execution.status = "completed"
                execution.result = result
                execution.metrics.success_rate = 0.7  # Partial success with alternative
        except Exception as e:
            logger.error(f"Alternative tool execution failed: {e}")

    async def _collect_telemetry(self, workflow_id: str) -> None:
        """Continuously collect performance telemetry for the workflow."""
        while workflow_id in self.executions:
            try:
                # Collect enhanced metrics with cognitive load tracking
                for execution in self.executions[workflow_id]:
                    if execution.status == "running":
                        current_metrics = self._calculate_step_metrics(execution)
                        cognitive_metrics = self._assess_cognitive_load(execution)
                        resource_metrics = self._get_resource_usage()
                        
                        # Update execution metrics with cognitive assessment
                        execution.metrics.cognitive_load = cognitive_metrics["cognitive_load"]
                        execution.metrics.context_switches = cognitive_metrics["context_switches"]
                        execution.metrics.decision_confidence = cognitive_metrics["decision_confidence"]
                        execution.metrics.resource_efficiency = self._calculate_resource_efficiency(
                            cognitive_metrics, resource_metrics
                        )
                        
                        self.telemetry_buffer.append({
                            "workflow_id": workflow_id,
                            "step_id": execution.step.step_id,
                            "timestamp": datetime.now().isoformat(),
                            "metrics": current_metrics,
                            "cognitive_metrics": cognitive_metrics,
                            "resource_usage": resource_metrics,
                            "performance_indicators": self._calculate_performance_indicators(execution)
                        })

                        # Dynamic resource allocation based on cognitive load
                        await self._optimize_resource_allocation(execution, cognitive_metrics)
                        
                        # Proactive performance optimization
                        if execution.metrics.cognitive_load > self.performance_thresholds["cognitive_load_threshold"]:
                            await self._optimize_step_performance(execution, current_metrics)

                # Intelligent buffer flushing with adaptive intervals
                if self._should_flush_telemetry():
                    await self._flush_telemetry()

                # Adaptive sleep based on cognitive load
                await asyncio.sleep(self._calculate_adaptive_interval())
            except Exception as e:
                logger.error(f"Error collecting telemetry: {e}")
                await self._retry_failed_flush()

    async def _cleanup_workflow(self, workflow_id: str) -> None:
        """Clean up resources when a workflow completes."""
        if workflow_id in self.executions:
            del self.executions[workflow_id]
        if workflow_id in self.active_workflows:
            task = self.active_workflows.pop(workflow_id)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Clean up transports
        for transport in self.transports:
            if not transport.is_closing():
                transport.close()
        self.transports.clear()

    async def _flush_telemetry(self) -> None:
        """Flush collected telemetry data with intelligent aggregation and cognitive analysis."""
        if not self.telemetry_buffer:
            return

        try:
            # Aggregate telemetry data with cognitive metrics
            aggregated_data = self._aggregate_telemetry_data()
            cognitive_patterns = self._analyze_cognitive_patterns(aggregated_data)
            
            # Analyze performance trends and resource efficiency
            performance_trends = self._analyze_performance_trends(aggregated_data)
            resource_efficiency = self._analyze_resource_efficiency(aggregated_data)
            
            # Generate optimization recommendations
            recommendations = self._generate_optimization_recommendations(
                cognitive_patterns,
                performance_trends,
                resource_efficiency
            )
            
            # Log enhanced telemetry data with cognitive insights
            logger.info(
                f"Flushing {len(self.telemetry_buffer)} telemetry records\n"
                f"Performance Summary: {json.dumps(performance_trends, indent=2)}\n"
                f"Cognitive Patterns: {json.dumps(cognitive_patterns, indent=2)}\n"
                f"Resource Efficiency: {json.dumps(resource_efficiency, indent=2)}\n"
                f"Optimization Recommendations: {json.dumps(recommendations, indent=2)}"
            )
            
            # Store historical data for trend analysis
            self._update_historical_metrics(aggregated_data)
            
            # Update resource allocation based on cognitive patterns
            await self._update_resource_pool(cognitive_patterns, resource_efficiency)
            
            self.telemetry_buffer.clear()
        except Exception as e:
            logger.error(f"Error flushing telemetry: {e}")
            # Implement retry mechanism for failed flushes
            await self._retry_failed_flush()