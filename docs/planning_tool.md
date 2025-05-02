# Planning Tool

The Planning Tool allows the agent to create and manage plans for solving complex tasks. It provides functionality for creating plans, updating plans, and managing plan versions with rollback capabilities.

## Features

- Create and manage plans with steps and dependencies
- Track plan versions and rollback to previous versions
- Analyze dependencies between steps
- Optimize plans for better execution
- Branch and merge plans for complex workflows

## Usage

### Basic Usage

```python
from app.tools.planning import PlanningTool

# Create a planning tool instance
planning_tool = PlanningTool()

# Create a new plan
result = await planning_tool.execute(
    command="create",
    title="My Plan",
    description="This is my plan",
    steps=[
        "Step 1",
        "Step 2",
        "Step 3"
    ]
)

# List all plans
result = await planning_tool.execute(command="list")

# Get the active plan
result = await planning_tool.execute(command="get")

# Update the active plan
result = await planning_tool.execute(
    command="update",
    steps=[
        "Step 1",
        "Step 2",
        "Step 3",
        "Step 4"
    ]
)
```

### Using the Planning Helper

For convenience, you can use the planning helper functions:

```python
from app.tools.planning import PlanningTool
from app.util.planning_helper import create_plan, update_plan, get_active_plan, list_plans

# Create a planning tool instance
planning_tool = PlanningTool()

# Create a new plan
result = await create_plan(
    planning_tool=planning_tool,
    title="My Plan",
    description="This is my plan",
    steps=[
        "Step 1",
        "Step 2",
        "Step 3"
    ]
)

# List all plans
result = await list_plans(planning_tool)

# Get the active plan
result = await get_active_plan(planning_tool)

# Update a plan
result = await update_plan(
    planning_tool=planning_tool,
    plan_id="plan_1",
    steps=[
        "Step 1",
        "Step 2",
        "Step 3",
        "Step 4"
    ]
)
```

## Commands

The Planning Tool supports the following commands:

- `create`: Create a new plan
- `update`: Update an existing plan
- `list`: List all available plans
- `get`: Get details of a specific plan
- `set_active`: Set a plan as the active plan
- `delete`: Delete a plan
- `create_version`: Create a new version of a plan
- `list_versions`: List all versions of a plan
- `get_version`: Get a specific version of a plan
- `compare_versions`: Compare two versions of a plan
- `rollback`: Roll back a plan to a specific version
- `parse_intent`: Parse natural language input into a plan
- `validate_plan`: Validate a plan for consistency
- `optimize_plan`: Optimize a plan for better execution
- `branch`: Create a branch of a plan
- `merge`: Merge branches of a plan
- `analyze_dependencies`: Analyze dependencies between steps
- `tag_version`: Tag a specific version of a plan
- `get_version_history`: Get the version history of a plan
- `fork_version`: Fork a specific version of a plan
- `merge_versions`: Merge two versions of a plan

## Examples

See the `examples` directory for example scripts:

- `planning_simple.py`: Simple example of using the Planning Tool directly
- `planning_example.py`: Example of using the Planning Tool with the planning helper

## Notes

- The Planning Tool automatically generates a plan ID if one is not provided
- The Planning Tool keeps track of the active plan, which is used as the default if no plan ID is provided
- The Planning Tool automatically creates versions when plans are updated
- The Planning Tool supports dependencies between steps, which can be analyzed and optimized
