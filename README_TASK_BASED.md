# Nexagent Task-Based Execution System

**Version:** 1.0.0
**Last Updated:** 2023-11-15
**Status:** Production

## Table of Contents

- [Introduction](#introduction)
- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
  - [TaskBasedAgent](#1-taskbasedagent)
  - [TaskBasedToolCallAgent](#2-taskbasedtoolcallagent)
  - [TaskBasedPlanningAgent](#3-taskbasedplanningagent)
  - [TaskBasedNexagent](#4-taskbasednexagent)
  - [TaskBasedIntegratedFlow](#5-taskbasedintegratedflow)
- [Implementation Details](#implementation-details)
  - [Task Model](#task-model)
  - [Dependency Resolution](#dependency-resolution)
  - [Task Execution Flow](#task-execution-flow)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Performance Considerations](#performance-considerations)
- [Troubleshooting](#troubleshooting)
- [Contribution Guidelines](#contribution-guidelines)
- [Version History](#version-history)
- [Future Roadmap](#future-roadmap)

## Introduction

The Nexagent Task-Based Execution System is a sophisticated framework that replaces the previous step-based execution model. This system dynamically converts high-level plans into executable tasks with proper dependency management, enabling more flexible, efficient, and natural execution flows for complex AI agent operations.

This document provides comprehensive technical documentation for developers implementing or extending the task-based execution system within Nexagent.

## Architecture Overview

The task-based execution system follows a hierarchical architecture with specialized components that build upon each other to provide increasingly sophisticated functionality:

```
┌─────────────────────────────┐
│ TaskBasedIntegratedFlow     │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ TaskBasedNexagent       │ │
│ ├─────────────────────────┤ │
│ │ ┌─────────────────────┐ │ │
│ │ │ TaskBasedPlanning   │ │ │
│ │ │ Agent               │ │ │
│ │ ├─────────────────────┤ │ │
│ │ │ ┌─────────────────┐ │ │ │
│ │ │ │ TaskBasedTool   │ │ │ │
│ │ │ │ CallAgent       │ │ │ │
│ │ │ ├─────────────────┤ │ │ │
│ │ │ │ ┌─────────────┐ │ │ │ │
│ │ │ │ │ TaskBased   │ │ │ │ │
│ │ │ │ │ Agent       │ │ │ │ │
│ │ │ │ └─────────────┘ │ │ │ │
│ │ │ └─────────────────┘ │ │ │
│ │ └─────────────────────┘ │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

The system automatically converts planner's to-do lists into executable tasks, eliminating the need for a fixed number of steps. Key advantages include:

1. **Dependency-based execution flow**: Tasks are executed based on their dependencies, not a predetermined sequence.
2. **Dynamic task decomposition**: Complex tasks are automatically broken down into manageable subtasks with proper dependency relationships.
3. **Comprehensive status tracking**: Each task maintains a clear status (pending, in_progress, completed, failed) throughout its lifecycle.
4. **Automated task generation**: Tasks are dynamically generated from high-level plans and user inputs.

## Core Components

The task-based execution system consists of five primary components, each building upon the capabilities of its predecessors.

### 1. TaskBasedAgent

The `TaskBasedAgent` class serves as the foundation for all task-based agents, providing core functionality for task management and execution.

**Key Features:**
- Task creation, validation, and lifecycle management
- Dependency tracking and resolution
- Task execution with proper status transitions
- Automatic task selection based on dependency satisfaction

**Implementation Example:**

```python
from app.agents.task_based.base import TaskBasedAgent
from app.models.task import Task, TaskStatus

# Create a basic task-based agent
agent = TaskBasedAgent()

# Create tasks with dependencies
task1 = Task(id="task1", description="Fetch data")
task2 = Task(id="task2", description="Process data", dependencies=["task1"])
task3 = Task(id="task3", description="Generate report", dependencies=["task2"])

# Add tasks to the agent
agent.add_task(task1)
agent.add_task(task2)
agent.add_task(task3)

# Execute tasks in dependency order
await agent.execute_all_tasks()
```

### 2. TaskBasedToolCallAgent

The `TaskBasedToolCallAgent` extends `TaskBasedAgent` to enable task execution through tool calls, implementing the thinking-acting loop pattern.

**Key Features:**
- Tool call execution framework
- Thinking and acting loop implementation
- Tool result handling and processing
- Special tool handling (e.g., terminate, user_input)

**Implementation Example:**

```python
from app.agents.task_based.tool_call import TaskBasedToolCallAgent
from app.models.task import Task
from app.tools.registry import ToolRegistry

# Initialize tool registry
tool_registry = ToolRegistry()
tool_registry.register_tool(WebSearchTool())
tool_registry.register_tool(FileOperationTool())

# Create a tool call agent
agent = TaskBasedToolCallAgent(tool_registry=tool_registry)

# Create a task that requires tool calls
task = Task(
    id="research_task",
    description="Research quantum computing advances",
    requires_tools=True
)

# Add task to the agent
agent.add_task(task)

# Execute the task
await agent.execute_task(task.id)
```

### 3. TaskBasedPlanningAgent

The `TaskBasedPlanningAgent` extends `TaskBasedToolCallAgent` to provide planning capabilities, automatically converting plan steps into executable tasks.

**Key Features:**
- Plan creation and management
- Plan step to task conversion with dependency mapping
- Plan step status synchronization
- Plan versioning and rollback capabilities

**Implementation Example:**

```python
from app.agents.task_based.planning import TaskBasedPlanningAgent
from app.models.plan import Plan, PlanStep

# Create a planning agent
agent = TaskBasedPlanningAgent()

# Create a plan with steps
plan = Plan(
    id="research_plan",
    description="Research and summarize quantum computing advances",
    steps=[
        PlanStep(id="step1", description="Search for recent quantum computing papers"),
        PlanStep(id="step2", description="Analyze key findings", dependencies=["step1"]),
        PlanStep(id="step3", description="Prepare summary report", dependencies=["step2"])
    ]
)

# Execute the plan
await agent.execute_plan(plan)
```

### 4. TaskBasedNexagent

The `TaskBasedNexagent` extends `TaskBasedToolCallAgent` to provide comprehensive Nexagent functionality, with advanced task management capabilities.

**Key Features:**
- Task complexity analysis and estimation
- Automatic subtask generation for complex tasks
- Thinking process tracking and explanation
- Comprehensive task history and state management

**Implementation Example:**

```python
from app.agents.task_based.nexagent import TaskBasedNexagent
from app.models.task import Task

# Create a Nexagent instance
agent = TaskBasedNexagent()

# Create a complex task
complex_task = Task(
    id="build_web_app",
    description="Build a web application for data visualization",
    complexity=8  # High complexity (1-10 scale)
)

# Add task to the agent
agent.add_task(complex_task)

# Execute the task (will automatically break it down)
await agent.execute_task(complex_task.id)
```

### 5. TaskBasedIntegratedFlow

The `TaskBasedIntegratedFlow` integrates the task-based approach with Nexagent's flow system, providing a unified interface for task execution.

**Key Features:**
- Intelligent prompt analysis and routing
- Agent selection based on task complexity and requirements
- Timeline integration for progress tracking
- Structured output organization and formatting

**Implementation Example:**

```python
from app.flow.task_based_integrated_flow import TaskBasedIntegratedFlow

# Initialize the task-based integrated flow
flow = TaskBasedIntegratedFlow()

# Execute the flow with input text
result = await flow.execute("Research quantum computing advances and create a summary report")

# Access the structured result
print(f"Final output: {result.final_output}")
print(f"Timeline events: {len(result.timeline_events)}")
print(f"Completed tasks: {len(result.completed_tasks)}")
```

## Implementation Details

### Task Model

Tasks in the system are represented by the `Task` class, which includes the following key attributes:

```python
class Task(BaseModel):
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = Field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requires_tools: bool = False
    complexity: int = 1  # 1-10 scale
    subtasks: List["Task"] = Field(default_factory=list)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### Dependency Resolution

The system uses a topological sorting algorithm to determine the execution order of tasks based on their dependencies:

1. Tasks with no dependencies are executed first
2. As tasks complete, their dependent tasks become eligible for execution
3. Circular dependencies are detected and reported as errors

### Task Execution Flow

The standard task execution flow follows these steps:

1. **Task Selection**: Choose the next eligible task based on dependencies
2. **Status Update**: Mark the task as in_progress
3. **Execution**:
   - For simple tasks: Execute directly
   - For tool-requiring tasks: Use the thinking-acting loop
   - For complex tasks: Break down into subtasks
4. **Result Processing**: Store the task result
5. **Status Update**: Mark the task as completed or failed
6. **Dependency Notification**: Notify dependent tasks that a dependency is complete

## API Reference

### TaskBasedAgent

```python
class TaskBasedAgent:
    def add_task(self, task: Task) -> None
    def get_task(self, task_id: str) -> Optional[Task]
    def get_all_tasks(self) -> List[Task]
    def get_eligible_tasks(self) -> List[Task]
    async def execute_task(self, task_id: str) -> Task
    async def execute_all_tasks(self) -> List[Task]
    def update_task_status(self, task_id: str, status: TaskStatus) -> None
    def set_task_result(self, task_id: str, result: Any) -> None
    def set_task_error(self, task_id: str, error: str) -> None
```

### TaskBasedToolCallAgent

```python
class TaskBasedToolCallAgent(TaskBasedAgent):
    def __init__(self, tool_registry: ToolRegistry)
    async def execute_tool_call(self, tool_name: str, **kwargs) -> Any
    async def thinking_acting_loop(self, task: Task) -> Any
    def handle_special_tool(self, tool_name: str, **kwargs) -> bool
```

### TaskBasedPlanningAgent

```python
class TaskBasedPlanningAgent(TaskBasedToolCallAgent):
    async def create_plan(self, description: str) -> Plan
    async def execute_plan(self, plan: Plan) -> List[Task]
    def convert_plan_to_tasks(self, plan: Plan) -> List[Task]
    async def update_plan_status(self, plan_id: str) -> None
    async def rollback_plan(self, plan_id: str, version: int) -> Plan
```

### TaskBasedNexagent

```python
class TaskBasedNexagent(TaskBasedToolCallAgent):
    async def analyze_task_complexity(self, task: Task) -> int
    async def break_down_task(self, task: Task) -> List[Task]
    async def get_thinking_summary(self, task_id: str) -> str
    def get_task_history(self) -> List[Task]
```

### TaskBasedIntegratedFlow

```python
class TaskBasedIntegratedFlow:
    async def execute(self, input_text: str) -> FlowResult
    async def analyze_input(self, input_text: str) -> InputAnalysisResult
    async def select_agent(self, analysis: InputAnalysisResult) -> BaseAgent
    async def process_timeline_events(self, events: List[TimelineEvent]) -> None
    async def format_output(self, result: Any) -> str
```

## Usage Examples

### Basic Task Execution

```python
from app.flow.task_based_integrated_flow import TaskBasedIntegratedFlow

async def process_user_request(request_text: str):
    flow = TaskBasedIntegratedFlow()
    result = await flow.execute(request_text)
    return result.final_output
```

### Custom Task Creation

```python
from app.agents.task_based.nexagent import TaskBasedNexagent
from app.models.task import Task, TaskStatus

async def custom_workflow():
    agent = TaskBasedNexagent()

    # Create custom tasks
    data_task = Task(id="fetch_data", description="Fetch data from API")
    process_task = Task(id="process_data", description="Process the data", dependencies=["fetch_data"])
    report_task = Task(id="generate_report", description="Generate final report", dependencies=["process_data"])

    # Add tasks to agent
    agent.add_task(data_task)
    agent.add_task(process_task)
    agent.add_task(report_task)

    # Execute all tasks
    completed_tasks = await agent.execute_all_tasks()

    # Get the final report result
    final_report = agent.get_task("generate_report").result
    return final_report
```

## Performance Considerations

- **Task Granularity**: Overly fine-grained tasks can create overhead, while overly coarse tasks may not provide enough flexibility
- **Dependency Management**: Complex dependency graphs can slow down execution due to increased resolution time
- **Memory Usage**: Large task histories can consume significant memory; consider implementing cleanup strategies
- **Tool Call Overhead**: Tool calls introduce latency; batch related operations when possible

## Troubleshooting

### Common Issues

1. **Circular Dependencies**
   - **Symptom**: Tasks remain in pending state indefinitely
   - **Solution**: Check for circular dependencies in task definitions

2. **Task Execution Failures**
   - **Symptom**: Tasks fail with error messages
   - **Solution**: Check task implementation and tool availability

3. **Memory Consumption**
   - **Symptom**: System slows down with many tasks
   - **Solution**: Implement task cleanup or archiving for completed tasks

### Debugging

The system provides several debugging mechanisms:

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed task execution history
agent = TaskBasedNexagent()
history = agent.get_task_history()
for task in history:
    print(f"{task.id}: {task.status} - {task.result or task.error}")

# Inspect task dependencies
for task in agent.get_all_tasks():
    deps = [agent.get_task(dep_id).description for dep_id in task.dependencies]
    print(f"{task.description} depends on: {', '.join(deps)}")
```

## Contribution Guidelines

When contributing to the task-based execution system:

1. Follow the existing architecture and inheritance patterns
2. Maintain backward compatibility with existing APIs
3. Add comprehensive unit tests for new functionality
4. Document all public methods and classes
5. Update this documentation when making significant changes

## Version History

| Version | Date       | Changes                                           |
|---------|------------|---------------------------------------------------|
| 1.0.0   | 2023-11-15 | Initial production release                        |
| 0.9.0   | 2023-10-30 | Beta release with complete feature set            |
| 0.8.0   | 2023-10-15 | Added TaskBasedIntegratedFlow                     |
| 0.7.0   | 2023-10-01 | Added TaskBasedNexagent                           |
| 0.6.0   | 2023-09-15 | Added TaskBasedPlanningAgent                      |
| 0.5.0   | 2023-09-01 | Added TaskBasedToolCallAgent                      |
| 0.4.0   | 2023-08-15 | Initial TaskBasedAgent implementation             |

## Future Roadmap

The task-based execution system roadmap includes:

1. **Task Prioritization**: Implement priority queues for task execution
2. **Parallel Execution**: Enable concurrent execution of independent tasks
3. **Automatic Retry**: Add configurable retry policies with exponential backoff
4. **Task Timeouts**: Implement configurable timeouts to prevent indefinite execution
5. **User Cancellation**: Add API for user-initiated task cancellation
6. **Task Visualization**: Develop interactive visualization of task dependency graphs
7. **Task Templates**: Create a library of reusable task templates
8. **Enhanced History**: Implement comprehensive task execution history with filtering
9. **Performance Metrics**: Add detailed metrics collection for optimization
10. **Notification System**: Implement configurable notifications for task status changes
