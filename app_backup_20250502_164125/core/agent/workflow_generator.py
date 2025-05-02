from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import json

from app.agent.base import BaseAgent
from app.schema import Message
from app.tool.base import ToolResult

class WorkflowStep(BaseModel):
    """Represents a single step in a workflow with validation and dependencies."""
    step_id: str
    description: str
    tool_name: str
    tool_params: Dict[str, Any]
    dependencies: List[str] = Field(default_factory=list)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    fallback_strategy: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="pending")
    retry_count: int = Field(default=0)
    last_error: Optional[str] = None
    execution_time: Optional[float] = None

class WorkflowGenerator:
    """Handles dynamic workflow generation and optimization based on natural language inputs."""

    def __init__(self):
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}

    async def analyze_prompt(self, prompt: str, agent: BaseAgent) -> Dict[str, Any]:
        """Analyze prompt to extract intent, requirements, constraints and cognitive complexity."""
        analysis_prompt = {
            "role": "user",
            "content": f"Analyze this task request and extract key components with cognitive complexity assessment:\n{prompt}"
        }
        
        # Get initial analysis from LLM
        analysis_result = await agent.llm.create_chat_completion(
            messages=[analysis_prompt],
            functions=[
                {
                    "name": "task_analysis",
                    "description": "Extract key components from task request",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "primary_intent": {"type": "string"},
                            "required_capabilities": {"type": "array", "items": {"type": "string"}},
                            "implicit_dependencies": {"type": "array", "items": {"type": "string"}},
                            "constraints": {"type": "array", "items": {"type": "string"}},
                            "edge_cases": {"type": "array", "items": {"type": "string"}},
                            "cognitive_complexity": {"type": "object", "properties": {
                                "task_complexity": {"type": "number"},
                                "context_depth": {"type": "number"},
                                "decision_points": {"type": "number"},
                                "required_expertise": {"type": "string"}
                            }}
                        }
                    }
                }
            ]
        )
        
        return json.loads(analysis_result.function_call.arguments)

    async def generate_workflow(self, analysis: Dict[str, Any], agent: BaseAgent) -> str:
        """Generate an optimized workflow based on prompt analysis."""
        workflow_id = f"wf_{len(self.workflows) + 1}"
        
        # Generate workflow steps using LLM
        workflow_prompt = {
            "role": "user",
            "content": f"Generate an optimized workflow for:\n{json.dumps(analysis, indent=2)}"
        }
        
        steps_result = await agent.llm.create_chat_completion(
            messages=[workflow_prompt],
            functions=[
                {
                    "name": "create_workflow",
                    "description": "Create workflow steps with validation and fallbacks",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": WorkflowStep.model_json_schema()["properties"]
                                }
                            }
                        }
                    }
                }
            ]
        )
        
        workflow_steps = json.loads(steps_result.function_call.arguments)["steps"]
        self.workflows[workflow_id] = [WorkflowStep(**step) for step in workflow_steps]
        
        return workflow_id

    async def optimize_workflow(self, workflow_id: str, metrics: Dict[str, Any]) -> None:
        """Optimize workflow based on execution metrics and feedback."""
        if workflow_id not in self.workflows:
            return
            
        workflow = self.workflows[workflow_id]
        history = self.execution_history.get(workflow_id, [])
        
        for step in workflow:
            # Update step metrics with performance data
            step.metrics.update({
                "error_rate": metrics.get("error_rate", 0),
                "avg_execution_time": metrics.get("avg_execution_time", 0),
                "success_rate": metrics.get("success_rate", 1.0),
                "resource_usage": metrics.get("resource_usage", {}),
                "throughput": metrics.get("throughput", 0)
            })
            
            # Enhanced performance analysis
            if step.metrics["error_rate"] > 0.2 or step.metrics["success_rate"] < 0.8:
                step.fallback_strategy = await self._generate_fallback(step)
                
            if step.metrics["avg_execution_time"] > step.metrics.get("expected_duration", 0):
                step.tool_params = await self._optimize_params(step)
                
            # Update validation rules based on observed patterns
            step.validation_rules.update({
                "input_constraints": self._generate_input_constraints(step),
                "output_validation": self._generate_output_validation(step),
                "resource_limits": self._generate_resource_limits(step.metrics)
            })

    async def _generate_fallback(self, step: WorkflowStep) -> Dict[str, Any]:
        """Generate sophisticated fallback strategy for failing steps."""
        error_patterns = self._analyze_error_patterns(step)
        resource_usage = step.metrics.get("resource_usage", {})
        
        strategy = {
            "retry_strategy": "adaptive_backoff",
            "max_retries": min(5, 10 - step.retry_count),
            "backoff_factor": 1.5,
            "alternative_tools": self._get_compatible_tools(step.tool_name),
            "circuit_breaker": {
                "error_threshold": 0.3,
                "reset_timeout": 300
            },
            "resource_allocation": {
                "cpu_limit": resource_usage.get("cpu", 100) * 1.5,
                "memory_limit": resource_usage.get("memory", 256) * 1.5
            }
        }
        
        if error_patterns.get("timeout_frequency", 0) > 0.5:
            strategy["timeout_ms"] = int(step.metrics.get("avg_execution_time", 1000) * 2)
        
        return strategy

    async def _optimize_params(self, step: WorkflowStep) -> Dict[str, Any]:
        """Optimize tool parameters based on comprehensive performance analysis."""
        optimized_params = step.tool_params.copy()
        metrics = step.metrics
        
        # Dynamic batch size optimization
        if "batch_size" in optimized_params:
            optimal_batch = self._calculate_optimal_batch_size(
                current_size=optimized_params["batch_size"],
                execution_time=metrics.get("avg_execution_time", 0),
                error_rate=metrics.get("error_rate", 0),
                throughput=metrics.get("throughput", 0)
            )
            optimized_params["batch_size"] = optimal_batch
        
        # Resource allocation optimization
        resource_usage = metrics.get("resource_usage", {})
        if resource_usage:
            optimized_params["resource_config"] = {
                "cpu_allocation": self._optimize_cpu_allocation(resource_usage),
                "memory_allocation": self._optimize_memory_allocation(resource_usage),
                "timeout": self._calculate_optimal_timeout(metrics)
            }
        
        # Concurrency optimization
        if "concurrency" in optimized_params:
            optimized_params["concurrency"] = self._optimize_concurrency_level(metrics)
        
        return optimized_params