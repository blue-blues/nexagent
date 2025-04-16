# Task-Based Execution in Nexagent

This document describes the task-based execution system that replaces the step-based execution model in Nexagent.

## Overview

The task-based execution system automatically converts the planner's to-do list into executable tasks, eliminating the need for a fixed number of steps. This approach provides several benefits:

1. **More natural execution flow**: Tasks are executed based on their dependencies, not a fixed step count.
2. **Better handling of complex tasks**: Complex tasks can be broken down into subtasks with dependencies.
3. **Improved progress tracking**: Each task has a clear status (pending, in_progress, completed, failed).
4. **Automatic task generation**: Tasks are automatically generated from the planner's to-do list.

## Components

The task-based execution system consists of the following components:

### 1. TaskBasedAgent

The `TaskBasedAgent` class is the base class for all task-based agents. It provides the core functionality for managing and executing tasks.

Key features:
- Task creation and management
- Dependency tracking
- Task execution with proper status updates
- Automatic task selection based on dependencies

### 2. TaskBasedToolCallAgent

The `TaskBasedToolCallAgent` class extends the `TaskBasedAgent` class to provide tool call functionality. It allows tasks to be executed using tool calls.

Key features:
- Tool call execution
- Thinking and acting loop
- Tool result handling
- Special tool handling (e.g., terminate)

### 3. TaskBasedPlanningAgent

The `TaskBasedPlanningAgent` class extends the `TaskBasedToolCallAgent` class to provide planning functionality. It automatically converts plan steps into executable tasks.

Key features:
- Plan creation
- Plan step to task conversion
- Plan step status updates
- Plan versioning

### 4. TaskBasedNexagent

The `TaskBasedNexagent` class extends the `TaskBasedToolCallAgent` class to provide the full Nexagent functionality. It automatically breaks down complex tasks into manageable steps.

Key features:
- Task complexity analysis
- Automatic subtask generation
- Thinking process tracking
- Task history tracking

### 5. TaskBasedIntegratedFlow

The `TaskBasedIntegratedFlow` class integrates the task-based approach with the existing flow system. It provides a unified interface for executing tasks.

Key features:
- Simple prompt handling
- Agent selection based on task type
- Timeline integration
- Output organization

## Usage

To use the task-based execution system, simply initialize the `TaskBasedIntegratedFlow` class and call its `execute` method with the input text:

```python
from app.flow.task_based_integrated_flow import TaskBasedIntegratedFlow

# Initialize the task-based integrated flow
flow = TaskBasedIntegratedFlow()

# Execute the flow with input text
result = await flow.execute("Your task here")
```

The flow will automatically analyze the input, break it down into tasks, and execute them using the appropriate tools.

## Benefits

The task-based execution system provides several benefits over the step-based execution model:

1. **More flexible**: Tasks can be executed in any order based on their dependencies.
2. **More efficient**: No need to waste steps on simple tasks.
3. **Better progress tracking**: Each task has a clear status and result.
4. **More natural**: Tasks are a more natural way to think about execution than steps.
5. **Better handling of complex tasks**: Complex tasks can be broken down into subtasks with dependencies.

## Future Improvements

Future improvements to the task-based execution system could include:

1. **Task prioritization**: Allow tasks to be prioritized based on importance or urgency.
2. **Task parallelization**: Allow independent tasks to be executed in parallel.
3. **Task retry**: Automatically retry failed tasks with exponential backoff.
4. **Task timeout**: Set timeouts for tasks to prevent them from running indefinitely.
5. **Task cancellation**: Allow tasks to be cancelled by the user or other tasks.
6. **Task visualization**: Provide a visual representation of the task graph.
7. **Task templates**: Create reusable task templates for common operations.
8. **Task history**: Keep a history of executed tasks for analysis and debugging.
9. **Task metrics**: Collect metrics on task execution for performance analysis.
10. **Task notifications**: Send notifications when tasks are completed or failed.
