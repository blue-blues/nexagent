"""
Test script for the plan visualization features.

This script demonstrates the use of the EnhancedPlanningTool with visualization capabilities.
"""

import asyncio
import os
from app.planning.enhanced_planning_tool import EnhancedPlanningTool


async def test_plan_visualization():
    """Test the plan visualization features."""
    # Create the enhanced planning tool
    planning_tool = EnhancedPlanningTool()
    
    # Create a test plan
    plan_id = "test_plan"
    result = await planning_tool.execute(
        command="create",
        plan_id=plan_id,
        title="Test Plan for Visualization",
        description="A plan to test the visualization features",
        steps=[
            "Research visualization libraries",
            "Design visualization formats",
            "Implement text visualization",
            "Implement markdown visualization",
            "Implement dependency graph visualization",
            "Implement timeline visualization",
            "Implement branch visualization",
            "Add export functionality",
            "Integrate with PlanningTool",
            "Write documentation",
            "Create tests"
        ],
        step_dependencies=[
            [2, 0],  # Step 3 depends on Step 1
            [2, 1],  # Step 3 depends on Step 2
            [3, 0],  # Step 4 depends on Step 1
            [3, 1],  # Step 4 depends on Step 2
            [4, 0],  # Step 5 depends on Step 1
            [4, 1],  # Step 5 depends on Step 2
            [5, 0],  # Step 6 depends on Step 1
            [5, 1],  # Step 6 depends on Step 2
            [7, 2],  # Step 8 depends on Step 3
            [7, 3],  # Step 8 depends on Step 4
            [7, 4],  # Step 8 depends on Step 5
            [7, 5],  # Step 8 depends on Step 6
            [7, 6],  # Step 8 depends on Step 7
            [8, 7],  # Step 9 depends on Step 8
            [9, 8],  # Step 10 depends on Step 9
            [10, 8]  # Step 11 depends on Step 9
        ]
    )
    
    print("Plan created:", result.output if hasattr(result, "output") else result)
    
    # Update step statuses
    plan = planning_tool.plans[plan_id]
    plan["step_statuses"] = [
        "completed",      # Step 1
        "completed",      # Step 2
        "completed",      # Step 3
        "completed",      # Step 4
        "completed",      # Step 5
        "in_progress",    # Step 6
        "not_started",    # Step 7
        "not_started",    # Step 8
        "not_started",    # Step 9
        "not_started",    # Step 10
        "not_started"     # Step 11
    ]
    
    # Create a version
    result = await planning_tool.execute(
        command="create_version",
        plan_id=plan_id,
        version_id="v1",
        version_description="Initial version"
    )
    
    print("\nVersion created:", result.output if hasattr(result, "output") else result)
    
    # Update the plan
    result = await planning_tool.execute(
        command="update",
        plan_id=plan_id,
        steps=[
            "Research visualization libraries",
            "Design visualization formats",
            "Implement text visualization",
            "Implement markdown visualization",
            "Implement dependency graph visualization",
            "Implement timeline visualization",
            "Implement branch visualization",
            "Add export functionality",
            "Integrate with PlanningTool",
            "Write documentation",
            "Create tests",
            "Deploy visualization features"  # Added step
        ],
        step_dependencies=[
            [2, 0],  # Step 3 depends on Step 1
            [2, 1],  # Step 3 depends on Step 2
            [3, 0],  # Step 4 depends on Step 1
            [3, 1],  # Step 4 depends on Step 2
            [4, 0],  # Step 5 depends on Step 1
            [4, 1],  # Step 5 depends on Step 2
            [5, 0],  # Step 6 depends on Step 1
            [5, 1],  # Step 6 depends on Step 2
            [7, 2],  # Step 8 depends on Step 3
            [7, 3],  # Step 8 depends on Step 4
            [7, 4],  # Step 8 depends on Step 5
            [7, 5],  # Step 8 depends on Step 6
            [7, 6],  # Step 8 depends on Step 7
            [8, 7],  # Step 9 depends on Step 8
            [9, 8],  # Step 10 depends on Step 9
            [10, 8],  # Step 11 depends on Step 9
            [11, 10]  # Step 12 depends on Step 11
        ]
    )
    
    print("\nPlan updated:", result.output if hasattr(result, "output") else result)
    
    # Create another version
    result = await planning_tool.execute(
        command="create_version",
        plan_id=plan_id,
        version_id="v2",
        version_description="Added deployment step"
    )
    
    print("\nVersion created:", result.output if hasattr(result, "output") else result)
    
    # Create a branch
    result = await planning_tool.execute(
        command="branch",
        plan_id=plan_id,
        branch_name="feature-branch"
    )
    
    print("\nBranch created:", result.output if hasattr(result, "output") else result)
    
    # Test plan visualization
    print("\n=== Plan Visualization (Text) ===")
    result = await planning_tool.execute(
        command="visualize_plan",
        plan_id=plan_id,
        format_type="text"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Test dependency graph visualization
    print("\n=== Dependency Graph Visualization (Text) ===")
    result = await planning_tool.execute(
        command="visualize_dependency_graph",
        plan_id=plan_id,
        format_type="text"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Test timeline visualization
    print("\n=== Timeline Visualization (Text) ===")
    result = await planning_tool.execute(
        command="visualize_timeline",
        plan_id=plan_id,
        format_type="text"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Test branch visualization
    print("\n=== Branch Visualization (Text) ===")
    result = await planning_tool.execute(
        command="visualize_branches",
        plan_id=plan_id,
        format_type="text"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Test version comparison visualization
    print("\n=== Version Comparison Visualization (Text) ===")
    result = await planning_tool.execute(
        command="visualize_version_comparison",
        plan_id=plan_id,
        version_id="v1",
        compare_with_version="v2",
        format_type="text"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Test export functionality
    print("\n=== Export Visualizations ===")
    
    # Export plan visualization as markdown
    result = await planning_tool.execute(
        command="visualize_plan",
        plan_id=plan_id,
        format_type="markdown",
        export_path="output/plan.md"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Export dependency graph visualization as markdown
    result = await planning_tool.execute(
        command="visualize_dependency_graph",
        plan_id=plan_id,
        format_type="markdown",
        export_path="output/dependency_graph.md"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Export timeline visualization as markdown
    result = await planning_tool.execute(
        command="visualize_timeline",
        plan_id=plan_id,
        format_type="markdown",
        export_path="output/timeline.md"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Export branch visualization as markdown
    result = await planning_tool.execute(
        command="visualize_branches",
        plan_id=plan_id,
        format_type="markdown",
        export_path="output/branches.md"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Export version comparison visualization as markdown
    result = await planning_tool.execute(
        command="visualize_version_comparison",
        plan_id=plan_id,
        version_id="v1",
        compare_with_version="v2",
        format_type="markdown",
        export_path="output/version_comparison.md"
    )
    print(result.output if hasattr(result, "output") else result)
    
    # Export dependency graph as DOT format
    result = await planning_tool.execute(
        command="visualize_dependency_graph",
        plan_id=plan_id,
        format_type="dot",
        export_path="output/dependency_graph.dot"
    )
    print(result.output if hasattr(result, "output") else result)


if __name__ == "__main__":
    asyncio.run(test_plan_visualization())
