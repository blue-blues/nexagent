"""
Test script for the Plan Versioning System.

This script tests the basic functionality of the Plan Versioning System
without requiring the full CLI interface.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.planning import PlanningTool


async def test_plan_versioning():
    """Test the Plan Versioning System."""
    print("Testing Plan Versioning System...")
    
    # Create a planning tool
    planning_tool = PlanningTool()
    
    # Create a plan
    plan_id = "test_plan"
    title = "Test Plan"
    
    print(f"\nCreating plan '{plan_id}' with title '{title}'...")
    result = await planning_tool.execute(
        command="create",
        plan_id=plan_id,
        title=title
    )
    print(result.output)
    
    # Update the plan
    print(f"\nUpdating plan '{plan_id}'...")
    result = await planning_tool.execute(
        command="update",
        plan_id=plan_id,
        title="Updated Test Plan",
        steps=["Step 1", "Step 2", "Step 3"]
    )
    print(result.output)
    
    # Create a version
    version_id = "v1"
    print(f"\nCreating version '{version_id}' for plan '{plan_id}'...")
    result = await planning_tool.execute(
        command="create_version",
        plan_id=plan_id,
        version_id=version_id,
        version_description="Initial version"
    )
    print(result.output)
    
    # Update the plan again
    print(f"\nUpdating plan '{plan_id}' again...")
    result = await planning_tool.execute(
        command="update",
        plan_id=plan_id,
        title="Updated Test Plan",
        steps=["Step 1", "Step 2", "Step 3", "Step 4"]
    )
    print(result.output)
    
    # Create another version
    version_id2 = "v2"
    print(f"\nCreating version '{version_id2}' for plan '{plan_id}'...")
    result = await planning_tool.execute(
        command="create_version",
        plan_id=plan_id,
        version_id=version_id2,
        version_description="Updated version"
    )
    print(result.output)
    
    # List versions
    print(f"\nListing versions for plan '{plan_id}'...")
    result = await planning_tool.execute(
        command="list_versions",
        plan_id=plan_id
    )
    print(result.output)
    
    # Compare versions
    print(f"\nComparing versions '{version_id}' and '{version_id2}' for plan '{plan_id}'...")
    result = await planning_tool.execute(
        command="compare_versions",
        plan_id=plan_id,
        version_id=version_id2,
        compare_with_version=version_id
    )
    print(result.output)
    
    # Get version history
    print(f"\nGetting version history for plan '{plan_id}'...")
    result = await planning_tool.execute(
        command="get_version_history",
        plan_id=plan_id
    )
    print(result.output)
    
    # Rollback to a version
    print(f"\nRolling back to version '{version_id}' for plan '{plan_id}'...")
    result = await planning_tool.execute(
        command="rollback",
        plan_id=plan_id,
        version_id=version_id
    )
    print(result.output)
    
    # Get the plan after rollback
    print(f"\nGetting plan '{plan_id}' after rollback...")
    result = await planning_tool.execute(
        command="get",
        plan_id=plan_id
    )
    print(result.output)
    
    print("\nPlan Versioning System test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_plan_versioning())
