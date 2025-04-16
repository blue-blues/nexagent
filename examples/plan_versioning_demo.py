#!/usr/bin/env python
"""
Demo script for the plan versioning and rollback capabilities.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tool.planning import PlanningTool


async def main():
    """Run the demo."""
    print("=== Plan Versioning and Rollback Demo ===\n")

    # Create a planning tool
    planning_tool = PlanningTool()

    # Create a new plan
    print("Creating a new plan...")
    result = await planning_tool.execute(
        command="create",
        plan_id="project-x",
        title="Project X Implementation Plan"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")


    # Create a version of the plan
    print("Creating a version of the plan...")
    result = await planning_tool.execute(
        command="create_version",
        plan_id="project-x",
        version_id="v1",
        version_description="Initial version with requirements completed"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")


    # Create another version
    print("Creating another version...")
    result = await planning_tool.execute(
        command="create_version",
        plan_id="project-x",
        version_id="v2",
        version_description="Architecture design in progress"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # List all versions
    print("Listing all versions...")
    result = await planning_tool.execute(
        command="list_versions",
        plan_id="project-x"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # Get a specific version
    print("Getting version v1...")
    result = await planning_tool.execute(
        command="get_version",
        plan_id="project-x",
        version_id="v1"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # Compare versions
    print("Comparing versions v1 and v2...")
    result = await planning_tool.execute(
        command="compare_versions",
        plan_id="project-x",
        version_id="v2",
        compare_with_version="v1"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # Update the plan title
    print("Updating the plan title...")
    result = await planning_tool.execute(
        command="update",
        plan_id="project-x",
        title="Project X Implementation Plan - Updated"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # Create another version
    print("Creating version v3...")
    result = await planning_tool.execute(
        command="create_version",
        plan_id="project-x",
        version_id="v3",
        version_description="Added security audit step"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # Compare versions
    print("Comparing versions v3 and v2...")
    result = await planning_tool.execute(
        command="compare_versions",
        plan_id="project-x",
        version_id="v3",
        compare_with_version="v2"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # Roll back to version v1
    print("Rolling back to version v1...")
    result = await planning_tool.execute(
        command="rollback",
        plan_id="project-x",
        version_id="v1"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # Get the current plan after rollback
    print("Getting the current plan after rollback...")
    result = await planning_tool.execute(
        command="get",
        plan_id="project-x"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    # List all versions after rollback
    print("Listing all versions after rollback...")
    result = await planning_tool.execute(
        command="list_versions",
        plan_id="project-x"
    )
    print(result.output)
    print("\n" + "-" * 50 + "\n")

    print("Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
