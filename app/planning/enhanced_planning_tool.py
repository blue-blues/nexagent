"""
Enhanced Planning Tool Module

This module extends the PlanningTool with visualization capabilities.
"""

from typing import Dict, List, Literal, Optional, Any, Union

from app.tools.planning import PlanningTool
from app.tools.base import ToolResult
from app.exceptions import ToolError
from app.logger import logger
from app.planning.visualization import PlanVisualizer


class EnhancedPlanningTool(PlanningTool):
    """
    Enhanced Planning Tool with visualization capabilities.
    
    This class extends the PlanningTool with additional commands for
    visualizing plans, dependencies, timelines, and branches.
    """
    
    async def execute(
        self,
        *,
        command: Literal[
            "create", "update", "list", "get", "set_active", "delete",
            "create_version", "list_versions", "get_version", "compare_versions", "rollback",
            "parse_intent", "validate_plan", "optimize_plan", "branch", "merge", "analyze_dependencies",
            "tag_version", "get_version_history", "fork_version", "merge_versions",
            # New visualization commands
            "visualize_plan", "visualize_dependency_graph", "visualize_timeline", 
            "visualize_branches", "visualize_version_comparison", "export_visualization"
        ],
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_dependencies: Optional[List[List[int]]] = None,
        version_id: Optional[str] = None,
        version_description: Optional[str] = None,
        compare_with_version: Optional[str] = None,
        user_input: Optional[str] = None,
        branch_name: Optional[str] = None,
        target_branch: Optional[str] = None,
        conflict_resolution: Optional[str] = None,
        tag_name: Optional[str] = None,
        fork_name: Optional[str] = None,
        merge_strategy: Optional[str] = None,
        # New visualization parameters
        format_type: Optional[str] = "text",
        export_path: Optional[str] = None,
    ):
        """
        Execute the planning tool with the given command and parameters.
        
        Parameters:
        - command: The operation to perform
        - plan_id: Unique identifier for the plan
        - title: Title for the plan (used with create command)
        - description: Detailed description of the plan's purpose and goals
        - steps: List of steps for the plan
        - step_dependencies: Dependencies between steps as [step_index, dependency_step_index] pairs
        - version_id: Identifier for the version (required for version-related commands)
        - version_description: Description of the version (optional for create_version)
        - compare_with_version: Version to compare with (for compare_versions command)
        - user_input: Natural language input for intent parsing
        - branch_name: Name of the branch to create or operate on
        - target_branch: Target branch for merge operations
        - conflict_resolution: Strategy for resolving conflicts during merge
        - tag_name: Name of the tag to apply to a version
        - fork_name: Name of the fork to create
        - merge_strategy: Strategy for merging versions
        - format_type: Format type for visualization (text, markdown, html, json, dot)
        - export_path: Path to export visualization to
        """
        # Handle visualization commands
        try:
            if command == "visualize_plan":
                return self._visualize_plan(plan_id, format_type, export_path)
            elif command == "visualize_dependency_graph":
                return self._visualize_dependency_graph(plan_id, format_type, export_path)
            elif command == "visualize_timeline":
                return self._visualize_timeline(plan_id, format_type, export_path)
            elif command == "visualize_branches":
                return self._visualize_branches(plan_id, format_type, export_path)
            elif command == "visualize_version_comparison":
                return self._visualize_version_comparison(plan_id, version_id, compare_with_version, format_type, export_path)
            elif command == "export_visualization":
                return self._export_visualization(user_input, format_type, export_path)
            else:
                # Call the parent class execute method for non-visualization commands
                return await super().execute(
                    command=command,
                    plan_id=plan_id,
                    title=title,
                    description=description,
                    steps=steps,
                    step_dependencies=step_dependencies,
                    version_id=version_id,
                    version_description=version_description,
                    compare_with_version=compare_with_version,
                    user_input=user_input,
                    branch_name=branch_name,
                    target_branch=target_branch,
                    conflict_resolution=conflict_resolution,
                    tag_name=tag_name,
                    fork_name=fork_name,
                    merge_strategy=merge_strategy,
                )
        except Exception as e:
            logger.error(f"Error in EnhancedPlanningTool.execute: {str(e)}")
            return ToolResult(error=f"Error executing command '{command}': {str(e)}")
    
    def _visualize_plan(
        self, 
        plan_id: Optional[str], 
        format_type: Optional[str] = "text",
        export_path: Optional[str] = None
    ) -> ToolResult:
        """
        Visualize a plan in the specified format.
        
        Args:
            plan_id: ID of the plan to visualize
            format_type: Format type (text, markdown)
            export_path: Path to export visualization to
            
        Returns:
            ToolResult containing the visualization
        """
        if not plan_id:
            return ToolResult(error="Plan ID is required for visualize_plan command")
        
        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")
        
        plan = self.plans[plan_id]
        
        # Generate visualization based on format type
        if format_type == "markdown":
            visualization = PlanVisualizer.format_plan_as_markdown(plan)
        else:
            visualization = PlanVisualizer.format_plan_as_text(plan)
        
        # Export if path provided
        if export_path:
            result = PlanVisualizer.export_visualization(visualization, format_type, export_path)
            if result:
                return ToolResult(output=f"Plan visualization exported to {result}")
            else:
                return ToolResult(error=f"Failed to export plan visualization to {export_path}")
        
        return ToolResult(output=visualization)
    
    def _visualize_dependency_graph(
        self, 
        plan_id: Optional[str], 
        format_type: Optional[str] = "text",
        export_path: Optional[str] = None
    ) -> ToolResult:
        """
        Visualize the dependency graph for a plan.
        
        Args:
            plan_id: ID of the plan
            format_type: Format type (text, markdown, dot)
            export_path: Path to export visualization to
            
        Returns:
            ToolResult containing the visualization
        """
        if not plan_id:
            return ToolResult(error="Plan ID is required for visualize_dependency_graph command")
        
        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")
        
        plan = self.plans[plan_id]
        
        # Generate visualization based on format type
        if format_type == "markdown":
            visualization = PlanVisualizer.format_dependency_graph_as_markdown(plan)
        elif format_type == "dot":
            visualization = PlanVisualizer.export_dependency_graph_as_dot(plan)
            if not visualization:
                return ToolResult(error="Failed to generate DOT format. NetworkX may not be available.")
        else:
            visualization = PlanVisualizer.format_dependency_graph_as_text(plan)
        
        # Export if path provided
        if export_path:
            result = PlanVisualizer.export_visualization(visualization, format_type, export_path)
            if result:
                return ToolResult(output=f"Dependency graph visualization exported to {result}")
            else:
                return ToolResult(error=f"Failed to export dependency graph visualization to {export_path}")
        
        return ToolResult(output=visualization)
    
    def _visualize_timeline(
        self, 
        plan_id: Optional[str], 
        format_type: Optional[str] = "text",
        export_path: Optional[str] = None
    ) -> ToolResult:
        """
        Visualize the timeline for a plan.
        
        Args:
            plan_id: ID of the plan
            format_type: Format type (text, markdown)
            export_path: Path to export visualization to
            
        Returns:
            ToolResult containing the visualization
        """
        if not plan_id:
            return ToolResult(error="Plan ID is required for visualize_timeline command")
        
        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")
        
        plan = self.plans[plan_id]
        
        # Generate visualization based on format type
        if format_type == "markdown":
            visualization = PlanVisualizer.format_timeline_as_markdown(plan)
        else:
            visualization = PlanVisualizer.format_timeline_as_text(plan)
        
        # Export if path provided
        if export_path:
            result = PlanVisualizer.export_visualization(visualization, format_type, export_path)
            if result:
                return ToolResult(output=f"Timeline visualization exported to {result}")
            else:
                return ToolResult(error=f"Failed to export timeline visualization to {export_path}")
        
        return ToolResult(output=visualization)
    
    def _visualize_branches(
        self, 
        plan_id: Optional[str], 
        format_type: Optional[str] = "text",
        export_path: Optional[str] = None
    ) -> ToolResult:
        """
        Visualize the branch structure for a plan.
        
        Args:
            plan_id: ID of the plan
            format_type: Format type (text, markdown)
            export_path: Path to export visualization to
            
        Returns:
            ToolResult containing the visualization
        """
        if not plan_id:
            return ToolResult(error="Plan ID is required for visualize_branches command")
        
        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")
        
        # Get branch information
        if plan_id not in self._plan_branches:
            self._plan_branches[plan_id] = {}
        
        branches = self._plan_branches[plan_id]
        current_branch = self.plans[plan_id]['metadata'].get('current_branch', 'main')
        
        # Generate visualization based on format type
        if format_type == "markdown":
            visualization = PlanVisualizer.format_branch_visualization_as_markdown(
                plan_id, branches, current_branch
            )
        else:
            visualization = PlanVisualizer.format_branch_visualization_as_text(
                plan_id, branches, current_branch
            )
        
        # Export if path provided
        if export_path:
            result = PlanVisualizer.export_visualization(visualization, format_type, export_path)
            if result:
                return ToolResult(output=f"Branch visualization exported to {result}")
            else:
                return ToolResult(error=f"Failed to export branch visualization to {export_path}")
        
        return ToolResult(output=visualization)
    
    def _visualize_version_comparison(
        self, 
        plan_id: Optional[str], 
        version_id: Optional[str],
        compare_with_version: Optional[str],
        format_type: Optional[str] = "text",
        export_path: Optional[str] = None
    ) -> ToolResult:
        """
        Visualize a comparison between two plan versions.
        
        Args:
            plan_id: ID of the plan
            version_id: ID of the first version
            compare_with_version: ID of the second version
            format_type: Format type (text, markdown)
            export_path: Path to export visualization to
            
        Returns:
            ToolResult containing the visualization
        """
        if not plan_id:
            return ToolResult(error="Plan ID is required for visualize_version_comparison command")
        
        if not version_id:
            return ToolResult(error="Version ID is required for visualize_version_comparison command")
        
        if not compare_with_version:
            return ToolResult(error="Compare with version ID is required for visualize_version_comparison command")
        
        if plan_id not in self._plan_versions:
            return ToolResult(error=f"No versions found for plan '{plan_id}'")
        
        versions = self._plan_versions[plan_id]
        
        if version_id not in versions:
            return ToolResult(error=f"Version '{version_id}' not found for plan '{plan_id}'")
        
        if compare_with_version not in versions:
            return ToolResult(error=f"Version '{compare_with_version}' not found for plan '{plan_id}'")
        
        version1 = versions[version_id]
        version2 = versions[compare_with_version]
        
        # Generate visualization based on format type
        if format_type == "markdown":
            visualization = PlanVisualizer.format_version_comparison_as_markdown(
                plan_id, version1, version2
            )
        else:
            visualization = PlanVisualizer.format_version_comparison_as_text(
                plan_id, version1, version2
            )
        
        # Export if path provided
        if export_path:
            result = PlanVisualizer.export_visualization(visualization, format_type, export_path)
            if result:
                return ToolResult(output=f"Version comparison visualization exported to {result}")
            else:
                return ToolResult(error=f"Failed to export version comparison visualization to {export_path}")
        
        return ToolResult(output=visualization)
    
    def _export_visualization(
        self, 
        visualization: Optional[str],
        format_type: Optional[str] = "text",
        export_path: Optional[str] = None
    ) -> ToolResult:
        """
        Export a visualization to a file.
        
        Args:
            visualization: The visualization content to export
            format_type: Format type (text, markdown, html, json, dot)
            export_path: Path to export visualization to
            
        Returns:
            ToolResult containing the result
        """
        if not visualization:
            return ToolResult(error="Visualization content is required for export_visualization command")
        
        if not export_path:
            return ToolResult(error="Export path is required for export_visualization command")
        
        result = PlanVisualizer.export_visualization(visualization, format_type, export_path)
        
        if result:
            return ToolResult(output=f"Visualization exported to {result}")
        else:
            return ToolResult(error=f"Failed to export visualization to {export_path}")
