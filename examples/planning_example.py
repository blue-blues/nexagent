"""
Planning Tool Example

This script demonstrates how to use the PlanningTool with the planning_helper module.
"""

import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.planning import PlanningTool
from app.util.planning_helper import create_plan, update_plan, get_active_plan, list_plans


async def main():
    """Run the planning tool example."""
    print("Planning Tool Example")
    print("====================")
    
    # Create a planning tool instance
    planning_tool = PlanningTool()
    
    # Create a new plan
    print("\nCreating a new plan...")
    result = await create_plan(
        planning_tool=planning_tool,
        title="My Example Plan",
        description="This is an example plan created using the planning helper.",
        steps=[
            "Research the topic",
            "Create an outline",
            "Write the first draft",
            "Review and revise",
            "Finalize and submit"
        ],
        step_dependencies=[
            [1, 0],  # Step 2 depends on Step 1
            [2, 1],  # Step 3 depends on Step 2
            [3, 2],  # Step 4 depends on Step 3
            [4, 3]   # Step 5 depends on Step 4
        ]
    )
    print(result.output)
    
    # List all plans
    print("\nListing all plans...")
    result = await list_plans(planning_tool)
    print(result.output)
    
    # Get the active plan
    print("\nGetting the active plan...")
    result = await get_active_plan(planning_tool)
    print(result.output)
    
    # Update the plan
    print("\nUpdating the plan...")
    result = await update_plan(
        planning_tool=planning_tool,
        plan_id="plan_1",  # Use the plan ID from the create_plan result
        title="My Updated Plan",
        steps=[
            "Research the topic",
            "Create an outline",
            "Write the first draft",
            "Get feedback from peers",
            "Review and revise",
            "Finalize and submit"
        ]
    )
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
