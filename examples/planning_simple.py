"""
Simple Planning Tool Example

This script demonstrates how to use the PlanningTool directly with the updated implementation.
"""

import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.planning import PlanningTool


async def main():
    """Run the simple planning tool example."""
    print("Simple Planning Tool Example")
    print("===========================")
    
    # Create a planning tool instance
    planning_tool = PlanningTool()
    
    # Create a new plan without specifying a plan_id (it will be auto-generated)
    print("\nCreating a new plan...")
    result = await planning_tool.execute(
        command="create",
        title="My Example Plan",
        description="This is an example plan created using the planning tool.",
        steps=[
            "Research the topic",
            "Create an outline",
            "Write the first draft",
            "Review and revise",
            "Finalize and submit"
        ]
    )
    print(result.output)
    
    # List all plans
    print("\nListing all plans...")
    result = await planning_tool.execute(command="list")
    print(result.output)
    
    # Get the active plan
    print("\nGetting the active plan...")
    result = await planning_tool.execute(command="get")
    print(result.output)
    
    # Update the plan without specifying a plan_id (it will use the active plan)
    print("\nUpdating the active plan...")
    result = await planning_tool.execute(
        command="update",
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
