"""
Plan Visualization Module

This module provides utilities for visualizing plans in various formats.
It supports text, markdown, graph, and timeline visualizations for plans,
as well as version comparison and branch visualization.
"""

import json
import io
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from app.logger import logger


class PlanVisualizer:
    """
    Class for visualizing plans in various formats.

    This class provides utilities for converting plans to formats
    suitable for visualization in different contexts, including
    text, markdown, dependency graphs, and timelines.
    """

    @staticmethod
    def format_plan_as_text(plan: Dict[str, Any]) -> str:
        """
        Format a plan as plain text.

        Args:
            plan: Plan data to format

        Returns:
            str: Text representation of the plan
        """
        output = []

        # Add header
        output.append(f"Plan: {plan['title']}")
        output.append("=" * (len(plan['title']) + 6))
        output.append("")

        # Add metadata
        output.append(f"ID: {plan['plan_id']}")
        output.append(f"Description: {plan['description']}")
        output.append(f"Created: {plan['created_at']}")
        output.append(f"Updated: {plan['updated_at']}")
        output.append("")

        # Add steps
        output.append("Steps:")
        output.append("------")
        for i, step in enumerate(plan['steps']):
            status = plan['step_statuses'][i] if i < len(plan['step_statuses']) else "unknown"
            status_symbol = PlanVisualizer._get_status_symbol(status)
            output.append(f"{i+1}. {status_symbol} {step}")

            # Add step notes if available
            if i < len(plan['step_notes']) and plan['step_notes'][i]:
                output.append(f"   Note: {plan['step_notes'][i]}")

        output.append("")

        # Add dependencies
        if plan['step_dependencies']:
            output.append("Dependencies:")
            output.append("-------------")
            for dep in plan['step_dependencies']:
                if len(dep) == 2:
                    output.append(f"Step {dep[0]+1} depends on Step {dep[1]+1}")
            output.append("")

        # Add metadata
        if 'metadata' in plan:
            output.append("Metadata:")
            output.append("---------")
            for key, value in plan['metadata'].items():
                output.append(f"{key}: {value}")

        return "\n".join(output)

    @staticmethod
    def format_plan_as_markdown(plan: Dict[str, Any]) -> str:
        """
        Format a plan as markdown.

        Args:
            plan: Plan data to format

        Returns:
            str: Markdown representation of the plan
        """
        output = []

        # Add header
        output.append(f"# Plan: {plan['title']}")
        output.append("")

        # Add metadata
        output.append(f"**ID:** `{plan['plan_id']}`")
        output.append(f"**Description:** {plan['description']}")
        output.append(f"**Created:** {plan['created_at']}")
        output.append(f"**Updated:** {plan['updated_at']}")
        output.append("")

        # Add steps
        output.append("## Steps")
        output.append("")
        for i, step in enumerate(plan['steps']):
            status = plan['step_statuses'][i] if i < len(plan['step_statuses']) else "unknown"
            status_symbol = PlanVisualizer._get_status_symbol(status)
            output.append(f"{i+1}. {status_symbol} {step}")

            # Add step notes if available
            if i < len(plan['step_notes']) and plan['step_notes'][i]:
                output.append(f"   > *Note: {plan['step_notes'][i]}*")

        output.append("")

        # Add dependencies
        if plan['step_dependencies']:
            output.append("## Dependencies")
            output.append("")
            for dep in plan['step_dependencies']:
                if len(dep) == 2:
                    output.append(f"* Step {dep[0]+1} depends on Step {dep[1]+1}")
            output.append("")

        # Add metadata
        if 'metadata' in plan:
            output.append("## Metadata")
            output.append("")
            output.append("| Key | Value |")
            output.append("| --- | ----- |")
            for key, value in plan['metadata'].items():
                if isinstance(value, (list, dict)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                output.append(f"| {key} | {value_str} |")

        return "\n".join(output)

    @staticmethod
    def format_version_comparison_as_text(
        plan_id: str,
        version1: Dict[str, Any],
        version2: Dict[str, Any]
    ) -> str:
        """
        Format a comparison between two plan versions as text.

        Args:
            plan_id: ID of the plan
            version1: First version data
            version2: Second version data

        Returns:
            str: Text representation of the version comparison
        """
        output = []

        # Add header
        output.append(f"Plan Version Comparison: {plan_id}")
        output.append("=" * (len(plan_id) + 24))
        output.append("")

        # Add version info
        v1_id = version1['version_id']
        v2_id = version2['version_id']
        output.append(f"Comparing Version {v1_id} with Version {v2_id}")
        output.append(f"Version {v1_id}: {version1['description']}")
        output.append(f"Version {v2_id}: {version2['description']}")
        output.append(f"Created: {version1['created_at']} vs {version2['created_at']}")
        output.append("")

        # Get plan data
        plan1 = version1['plan_data']
        plan2 = version2['plan_data']

        # Compare steps
        steps1 = plan1['steps']
        steps2 = plan2['steps']

        output.append("Step Changes:")
        output.append("-------------")

        # Find added, removed, and modified steps
        common_length = min(len(steps1), len(steps2))

        # Check modified steps
        for i in range(common_length):
            if steps1[i] != steps2[i]:
                output.append(f"Step {i+1} modified:")
                output.append(f"  - {steps1[i]}")
                output.append(f"  + {steps2[i]}")

        # Check added steps
        if len(steps2) > len(steps1):
            for i in range(len(steps1), len(steps2)):
                output.append(f"Step {i+1} added: {steps2[i]}")

        # Check removed steps
        if len(steps1) > len(steps2):
            for i in range(len(steps2), len(steps1)):
                output.append(f"Step {i+1} removed: {steps1[i]}")

        output.append("")

        # Compare dependencies
        deps1 = plan1['step_dependencies']
        deps2 = plan2['step_dependencies']

        output.append("Dependency Changes:")
        output.append("-------------------")

        # Find added and removed dependencies
        deps1_set = {(d[0], d[1]) for d in deps1}
        deps2_set = {(d[0], d[1]) for d in deps2}

        added_deps = deps2_set - deps1_set
        removed_deps = deps1_set - deps2_set

        for dep in added_deps:
            output.append(f"Dependency added: Step {dep[0]+1} depends on Step {dep[1]+1}")

        for dep in removed_deps:
            output.append(f"Dependency removed: Step {dep[0]+1} no longer depends on Step {dep[1]+1}")

        return "\n".join(output)

    @staticmethod
    def format_version_comparison_as_markdown(
        plan_id: str,
        version1: Dict[str, Any],
        version2: Dict[str, Any]
    ) -> str:
        """
        Format a comparison between two plan versions as markdown.

        Args:
            plan_id: ID of the plan
            version1: First version data
            version2: Second version data

        Returns:
            str: Markdown representation of the version comparison
        """
        output = []

        # Add header
        output.append(f"# Plan Version Comparison: {plan_id}")
        output.append("")

        # Add version info
        v1_id = version1['version_id']
        v2_id = version2['version_id']
        output.append(f"Comparing **Version {v1_id}** with **Version {v2_id}**")
        output.append("")
        output.append(f"**Version {v1_id}:** {version1['description']}")
        output.append(f"**Version {v2_id}:** {version2['description']}")
        output.append(f"**Created:** {version1['created_at']} vs {version2['created_at']}")
        output.append("")

        # Get plan data
        plan1 = version1['plan_data']
        plan2 = version2['plan_data']

        # Compare steps
        steps1 = plan1['steps']
        steps2 = plan2['steps']

        output.append("## Step Changes")
        output.append("")

        # Find added, removed, and modified steps
        common_length = min(len(steps1), len(steps2))

        # Check modified steps
        modified = False
        for i in range(common_length):
            if steps1[i] != steps2[i]:
                if not modified:
                    output.append("### Modified Steps")
                    output.append("")
                    modified = True
                output.append(f"**Step {i+1}:**")
                output.append(f"- 🔴 ~~{steps1[i]}~~")
                output.append(f"- 🟢 **{steps2[i]}**")
                output.append("")

        # Check added steps
        if len(steps2) > len(steps1):
            output.append("### Added Steps")
            output.append("")
            for i in range(len(steps1), len(steps2)):
                output.append(f"- ✅ Step {i+1}: **{steps2[i]}**")
            output.append("")

        # Check removed steps
        if len(steps1) > len(steps2):
            output.append("### Removed Steps")
            output.append("")
            for i in range(len(steps2), len(steps1)):
                output.append(f"- ❌ Step {i+1}: ~~{steps1[i]}~~")
            output.append("")

        # Compare dependencies
        deps1 = plan1['step_dependencies']
        deps2 = plan2['step_dependencies']

        output.append("## Dependency Changes")
        output.append("")

        # Find added and removed dependencies
        deps1_set = {(d[0], d[1]) for d in deps1}
        deps2_set = {(d[0], d[1]) for d in deps2}

        added_deps = deps2_set - deps1_set
        removed_deps = deps1_set - deps2_set

        if added_deps:
            output.append("### Added Dependencies")
            output.append("")
            for dep in added_deps:
                output.append(f"- ✅ Step {dep[0]+1} depends on Step {dep[1]+1}")
            output.append("")

        if removed_deps:
            output.append("### Removed Dependencies")
            output.append("")
            for dep in removed_deps:
                output.append(f"- ❌ Step {dep[0]+1} no longer depends on Step {dep[1]+1}")
            output.append("")

        return "\n".join(output)

    @staticmethod
    def _get_status_symbol(status: str) -> str:
        """Get a symbol representing the step status."""
        status_map = {
            "not_started": "⬜",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌",
            "blocked": "⛔",
            "skipped": "⏭️",
            "unknown": "❓"
        }
        return status_map.get(status.lower(), "❓")

    @staticmethod
    def create_dependency_graph(plan: Dict[str, Any]) -> Optional[nx.DiGraph]:
        """
        Create a directed graph representing the dependencies between steps.

        Args:
            plan: Plan data

        Returns:
            Optional[nx.DiGraph]: Directed graph of dependencies, or None if NetworkX is not available
        """
        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX is not available. Cannot create dependency graph.")
            return None

        # Create a directed graph
        G = nx.DiGraph()

        # Add nodes for each step
        for i, step in enumerate(plan['steps']):
            status = plan['step_statuses'][i] if i < len(plan['step_statuses']) else "unknown"
            G.add_node(i, label=step, status=status, step_number=i+1)

        # Add edges for dependencies
        for dep in plan['step_dependencies']:
            if len(dep) == 2:
                # Edge from dependent step to dependency
                G.add_edge(dep[0], dep[1])

        return G

    @staticmethod
    def format_dependency_graph_as_text(plan: Dict[str, Any]) -> str:
        """
        Format the dependency graph as ASCII text.

        Args:
            plan: Plan data

        Returns:
            str: ASCII representation of the dependency graph
        """
        if not NETWORKX_AVAILABLE:
            return "NetworkX is not available. Cannot create dependency graph visualization."

        G = PlanVisualizer.create_dependency_graph(plan)
        if not G:
            return "Failed to create dependency graph."

        output = []
        output.append(f"Dependency Graph for Plan: {plan['title']}")
        output.append("=" * (len(plan['title']) + 24))
        output.append("")

        # Find root nodes (no incoming edges)
        root_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]

        # Find leaf nodes (no outgoing edges)
        leaf_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]

        # Format the output
        output.append("Steps and their dependencies:")
        for i, step in enumerate(plan['steps']):
            deps = list(G.successors(i))
            deps_str = ", ".join([str(d+1) for d in deps]) if deps else "None"
            status = plan['step_statuses'][i] if i < len(plan['step_statuses']) else "unknown"
            status_symbol = PlanVisualizer._get_status_symbol(status)
            output.append(f"{i+1}. {status_symbol} {step}")
            output.append(f"   Depends on: {deps_str}")

        output.append("")

        # List root steps
        output.append("Root steps (no dependencies):")
        if root_nodes:
            for i in root_nodes:
                output.append(f"{i+1}. {plan['steps'][i]}")
        else:
            output.append("None")

        output.append("")

        # List leaf steps
        output.append("Leaf steps (no dependents):")
        if leaf_nodes:
            for i in leaf_nodes:
                output.append(f"{i+1}. {plan['steps'][i]}")
        else:
            output.append("None")

        # Try to create a simple ASCII representation of the graph
        output.append("")
        output.append("ASCII Graph Representation:")
        output.append("")

        # Sort nodes by topological order if possible
        try:
            sorted_nodes = list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible:
            # Graph has cycles
            sorted_nodes = list(G.nodes())

        # Create a simple ASCII representation
        visited = set()

        def print_node(node, depth=0, prefix=""):
            if node in visited:
                output.append(f"{prefix}{'  ' * depth}Step {node+1} (see above)")
                return

            visited.add(node)
            status = G.nodes[node].get('status', 'unknown')
            status_symbol = PlanVisualizer._get_status_symbol(status)
            step_text = plan['steps'][node]
            output.append(f"{prefix}{'  ' * depth}Step {node+1}: {status_symbol} {step_text}")

            # Print children
            children = list(G.predecessors(node))
            for i, child in enumerate(children):
                if i == len(children) - 1:
                    # Last child
                    print_node(child, depth + 1, prefix="└─ ")
                else:
                    print_node(child, depth + 1, prefix="├─ ")

        # Start with root nodes
        for root in root_nodes:
            print_node(root)
            visited = set()  # Reset visited for each root

        return "\n".join(output)

    @staticmethod
    def format_dependency_graph_as_markdown(plan: Dict[str, Any]) -> str:
        """
        Format the dependency graph as markdown.

        Args:
            plan: Plan data

        Returns:
            str: Markdown representation of the dependency graph
        """
        if not NETWORKX_AVAILABLE:
            return "NetworkX is not available. Cannot create dependency graph visualization."

        G = PlanVisualizer.create_dependency_graph(plan)
        if not G:
            return "Failed to create dependency graph."

        output = []
        output.append(f"# Dependency Graph for Plan: {plan['title']}")
        output.append("")

        # Find root nodes (no incoming edges)
        root_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]

        # Find leaf nodes (no outgoing edges)
        leaf_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]

        # Format the output
        output.append("## Steps and Dependencies")
        output.append("")
        output.append("| Step | Description | Dependencies | Status |")
        output.append("| ---- | ----------- | ------------ | ------ |")

        for i, step in enumerate(plan['steps']):
            deps = list(G.successors(i))
            deps_str = ", ".join([f"Step {d+1}" for d in deps]) if deps else "None"
            status = plan['step_statuses'][i] if i < len(plan['step_statuses']) else "unknown"
            status_symbol = PlanVisualizer._get_status_symbol(status)
            output.append(f"| {i+1} | {step} | {deps_str} | {status_symbol} {status} |")

        output.append("")

        # List root steps
        output.append("## Root Steps (No Dependencies)")
        output.append("")
        if root_nodes:
            for i in root_nodes:
                status = G.nodes[i].get('status', 'unknown')
                status_symbol = PlanVisualizer._get_status_symbol(status)
                output.append(f"- Step {i+1}: {status_symbol} {plan['steps'][i]}")
        else:
            output.append("*None*")

        output.append("")

        # List leaf steps
        output.append("## Leaf Steps (No Dependents)")
        output.append("")
        if leaf_nodes:
            for i in leaf_nodes:
                status = G.nodes[i].get('status', 'unknown')
                status_symbol = PlanVisualizer._get_status_symbol(status)
                output.append(f"- Step {i+1}: {status_symbol} {plan['steps'][i]}")
        else:
            output.append("*None*")

        # Add a mermaid graph if possible
        output.append("")
        output.append("## Dependency Graph Visualization")
        output.append("")
        output.append("```mermaid")
        output.append("graph TD")

        # Add nodes
        for i in G.nodes():
            status = G.nodes[i].get('status', 'unknown')
            status_class = status.replace("_", "")
            output.append(f"    {i+1}[\"{i+1}: {plan['steps'][i]}\"]:::status{status_class}")

        # Add edges
        for edge in G.edges():
            output.append(f"    {edge[0]+1} --> {edge[1]+1}")

        # Add style classes
        output.append("    classDef statusnotstarted fill:#f9f9f9,stroke:#ccc")
        output.append("    classDef statusinprogress fill:#e1f5fe,stroke:#03a9f4")
        output.append("    classDef statuscompleted fill:#e8f5e9,stroke:#4caf50")
        output.append("    classDef statusfailed fill:#ffebee,stroke:#f44336")
        output.append("    classDef statusblocked fill:#ffecb3,stroke:#ffc107")
        output.append("    classDef statusskipped fill:#e0e0e0,stroke:#9e9e9e")
        output.append("    classDef statusunknown fill:#f5f5f5,stroke:#9e9e9e")

        output.append("```")

        return "\n".join(output)

    @staticmethod
    def export_dependency_graph_as_dot(plan: Dict[str, Any]) -> Optional[str]:
        """
        Export the dependency graph in DOT format for use with Graphviz.

        Args:
            plan: Plan data

        Returns:
            Optional[str]: DOT representation of the graph, or None if NetworkX is not available
        """
        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX is not available. Cannot export dependency graph as DOT.")
            return None

        G = PlanVisualizer.create_dependency_graph(plan)
        if not G:
            return None

        # Add attributes for visualization
        for i, step in enumerate(plan['steps']):
            status = plan['step_statuses'][i] if i < len(plan['step_statuses']) else "unknown"

            # Map status to color
            color_map = {
                "not_started": "gray",
                "in_progress": "blue",
                "completed": "green",
                "failed": "red",
                "blocked": "orange",
                "skipped": "lightgray",
                "unknown": "black"
            }

            color = color_map.get(status.lower(), "black")

            # Update node attributes
            G.nodes[i]['label'] = f"Step {i+1}: {step}"
            G.nodes[i]['color'] = color
            G.nodes[i]['style'] = 'filled'
            G.nodes[i]['fillcolor'] = color if status == 'completed' else 'white'
            G.nodes[i]['fontcolor'] = 'white' if status == 'completed' else 'black'

        # Export as DOT format
        try:
            dot_data = nx.drawing.nx_pydot.to_pydot(G).to_string()
            return dot_data
        except Exception as e:
            logger.error(f"Error exporting graph as DOT: {str(e)}")
            return None

    @staticmethod
    def format_timeline_as_text(plan: Dict[str, Any]) -> str:
        """
        Format a plan as a timeline in text format.

        Args:
            plan: Plan data

        Returns:
            str: Text representation of the plan timeline
        """
        output = []

        # Add header
        output.append(f"Timeline for Plan: {plan['title']}")
        output.append("=" * (len(plan['title']) + 16))
        output.append("")

        # Add metadata
        output.append(f"ID: {plan['plan_id']}")
        output.append(f"Created: {plan['created_at']}")
        output.append(f"Updated: {plan['updated_at']}")
        output.append("")

        # Create a dependency graph if NetworkX is available
        dependency_order = list(range(len(plan['steps'])))
        if NETWORKX_AVAILABLE:
            G = PlanVisualizer.create_dependency_graph(plan)
            if G:
                try:
                    # Try to get a topological sort
                    dependency_order = list(nx.topological_sort(G))
                except nx.NetworkXUnfeasible:
                    # Graph has cycles, use original order
                    pass

        # Add timeline
        output.append("Timeline:")
        output.append("---------")

        for i, step_idx in enumerate(dependency_order):
            if step_idx < len(plan['steps']):
                step = plan['steps'][step_idx]
                status = plan['step_statuses'][step_idx] if step_idx < len(plan['step_statuses']) else "unknown"
                status_symbol = PlanVisualizer._get_status_symbol(status)

                # Find dependencies
                deps = []
                for dep in plan['step_dependencies']:
                    if len(dep) == 2 and dep[0] == step_idx:
                        deps.append(dep[1])

                deps_str = ", ".join([str(d+1) for d in deps]) if deps else "None"

                output.append(f"{i+1}. Step {step_idx+1}: {status_symbol} {step}")
                output.append(f"   Dependencies: {deps_str}")

                # Add step notes if available
                if step_idx < len(plan['step_notes']) and plan['step_notes'][step_idx]:
                    output.append(f"   Note: {plan['step_notes'][step_idx]}")

                output.append("")

        return "\n".join(output)

    @staticmethod
    def format_timeline_as_markdown(plan: Dict[str, Any]) -> str:
        """
        Format a plan as a timeline in markdown format.

        Args:
            plan: Plan data

        Returns:
            str: Markdown representation of the plan timeline
        """
        output = []

        # Add header
        output.append(f"# Timeline for Plan: {plan['title']}")
        output.append("")

        # Add metadata
        output.append(f"**ID:** `{plan['plan_id']}`")
        output.append(f"**Created:** {plan['created_at']}")
        output.append(f"**Updated:** {plan['updated_at']}")
        output.append("")

        # Create a dependency graph if NetworkX is available
        dependency_order = list(range(len(plan['steps'])))
        if NETWORKX_AVAILABLE:
            G = PlanVisualizer.create_dependency_graph(plan)
            if G:
                try:
                    # Try to get a topological sort
                    dependency_order = list(nx.topological_sort(G))
                except nx.NetworkXUnfeasible:
                    # Graph has cycles, use original order
                    pass

        # Add timeline
        output.append("## Timeline")
        output.append("")

        for i, step_idx in enumerate(dependency_order):
            if step_idx < len(plan['steps']):
                step = plan['steps'][step_idx]
                status = plan['step_statuses'][step_idx] if step_idx < len(plan['step_statuses']) else "unknown"
                status_symbol = PlanVisualizer._get_status_symbol(status)

                # Find dependencies
                deps = []
                for dep in plan['step_dependencies']:
                    if len(dep) == 2 and dep[0] == step_idx:
                        deps.append(dep[1])

                deps_str = ", ".join([f"Step {d+1}" for d in deps]) if deps else "None"

                output.append(f"### {i+1}. Step {step_idx+1}: {status_symbol} {step}")
                output.append("")
                output.append(f"**Dependencies:** {deps_str}")

                # Add step notes if available
                if step_idx < len(plan['step_notes']) and plan['step_notes'][step_idx]:
                    output.append(f"**Note:** {plan['step_notes'][step_idx]}")

                output.append("")

        # Add a mermaid timeline if possible
        output.append("## Timeline Visualization")
        output.append("")
        output.append("```mermaid")
        output.append("gantt")
        output.append("    title Plan Timeline")
        output.append("    dateFormat  YYYY-MM-DD")
        output.append("    axisFormat %d")
        output.append("    todayMarker off")

        # Add sections for each step
        current_date = datetime.now().strftime("%Y-%m-%d")
        for i, step_idx in enumerate(dependency_order):
            if step_idx < len(plan['steps']):
                step = plan['steps'][step_idx]
                status = plan['step_statuses'][step_idx] if step_idx < len(plan['step_statuses']) else "unknown"

                # Determine duration based on status
                if status == "completed":
                    duration = "1d"
                elif status == "in_progress":
                    duration = "2d"
                else:
                    duration = "3d"

                # Escape special characters in step text
                step_text = step.replace(":", "&#58;")

                output.append(f"    section Step {step_idx+1}")
                output.append(f"    {step_text} :{status}, {current_date}, {duration}")

        output.append("```")

        return "\n".join(output)

    @staticmethod
    def format_branch_visualization_as_text(
        plan_id: str,
        branches: Dict[str, str],
        current_branch: str
    ) -> str:
        """
        Format branch information as text.

        Args:
            plan_id: ID of the plan
            branches: Dictionary mapping branch names to parent branches
            current_branch: Name of the current active branch

        Returns:
            str: Text representation of the branch structure
        """
        output = []

        # Add header
        output.append(f"Branch Structure for Plan: {plan_id}")
        output.append("=" * (len(plan_id) + 24))
        output.append("")

        # Add current branch
        output.append(f"Current Branch: {current_branch}")
        output.append("")

        # Add branch list
        output.append("Branches:")
        output.append("---------")

        # Build branch tree
        branch_tree = {}
        root_branches = []

        for branch, parent in branches.items():
            if parent:
                if parent not in branch_tree:
                    branch_tree[parent] = []
                branch_tree[parent].append(branch)
            else:
                root_branches.append(branch)

        # Print branch tree
        def print_branch(branch, depth=0, prefix=""):
            is_current = branch == current_branch
            marker = "* " if is_current else "  "
            output.append(f"{prefix}{'  ' * depth}{marker}{branch}")

            if branch in branch_tree:
                children = sorted(branch_tree[branch])
                for i, child in enumerate(children):
                    if i == len(children) - 1:
                        # Last child
                        print_branch(child, depth + 1, prefix="└─ ")
                    else:
                        print_branch(child, depth + 1, prefix="├─ ")

        for root in sorted(root_branches):
            print_branch(root)

        return "\n".join(output)

    @staticmethod
    def format_branch_visualization_as_markdown(
        plan_id: str,
        branches: Dict[str, str],
        current_branch: str
    ) -> str:
        """
        Format branch information as markdown.

        Args:
            plan_id: ID of the plan
            branches: Dictionary mapping branch names to parent branches
            current_branch: Name of the current active branch

        Returns:
            str: Markdown representation of the branch structure
        """
        output = []

        # Add header
        output.append(f"# Branch Structure for Plan: {plan_id}")
        output.append("")

        # Add current branch
        output.append(f"**Current Branch:** `{current_branch}`")
        output.append("")

        # Add branch list
        output.append("## Branches")
        output.append("")

        # Build branch tree
        branch_tree = {}
        root_branches = []

        for branch, parent in branches.items():
            if parent:
                if parent not in branch_tree:
                    branch_tree[parent] = []
                branch_tree[parent].append(branch)
            else:
                root_branches.append(branch)

        # Print branch tree
        def print_branch(branch, depth=0):
            is_current = branch == current_branch
            marker = "**" if is_current else ""
            output.append(f"{'  ' * depth}- {marker}{branch}{marker}")

            if branch in branch_tree:
                children = sorted(branch_tree[branch])
                for child in children:
                    print_branch(child, depth + 1)

        for root in sorted(root_branches):
            print_branch(root)

        # Add a mermaid diagram
        output.append("")
        output.append("## Branch Visualization")
        output.append("")
        output.append("```mermaid")
        output.append("graph TD")

        # Add nodes
        for branch in branches:
            if branch == current_branch:
                output.append(f"    {branch}[\"{branch}\"]:::current")
            else:
                output.append(f"    {branch}[\"{branch}\"]")

        # Add edges
        for branch, parent in branches.items():
            if parent:
                output.append(f"    {parent} --> {branch}")

        # Add style for current branch
        output.append("    classDef current fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px")

        output.append("```")

        return "\n".join(output)

    @staticmethod
    def export_visualization(
        visualization: str,
        format_type: str,
        file_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Export a visualization to a file.

        Args:
            visualization: The visualization content to export
            format_type: The format type (text, markdown, html, json, dot)
            file_path: Optional file path to save to. If None, returns the content.

        Returns:
            Optional[str]: The file path if saved, or None if an error occurred
        """
        if not file_path:
            return visualization

        try:
            # Determine file extension based on format
            if not file_path.endswith(f".{format_type}"):
                if format_type == "text":
                    file_path += ".txt"
                elif format_type == "markdown":
                    file_path += ".md"
                elif format_type == "html":
                    file_path += ".html"
                elif format_type == "json":
                    file_path += ".json"
                elif format_type == "dot":
                    file_path += ".dot"

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(visualization)

            return file_path
        except Exception as e:
            logger.error(f"Error exporting visualization: {str(e)}")
            return None