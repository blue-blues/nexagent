# tool/planning.py
import copy
import datetime
from typing import Dict, List, Literal, Optional, Any

from app.exceptions import ToolError
from app.tools.base import BaseTool, ToolResult
from app.logger import logger


_PLANNING_TOOL_DESCRIPTION = """
A planning tool that allows the agent to create and manage plans for solving complex tasks.
The tool provides functionality for creating plans, updating plans, and managing plan versions.
Supports versioning and rollback capabilities to track changes and revert to previous plan versions.
Features include intent parsing, step breakdown, validation, and automatic plan optimization.
"""


class PlanningTool(BaseTool):
    """
    A planning tool that allows the agent to create and manage plans for solving complex tasks.
    The tool provides functionality for creating plans, updating plans,
    and managing plan versions with rollback capabilities.

    Enhanced features include:
    - Intent parsing from natural language instructions
    - Automatic step breakdown with dependencies
    - Plan validation and optimization
    - Comprehensive versioning with branching support
    - Detailed plan comparison and conflict resolution
    - Automatic plan healing and adaptation
    """

    name: str = "planning"
    description: str = _PLANNING_TOOL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: create, update, list, get, set_active, delete, create_version, list_versions, get_version, compare_versions, rollback, parse_intent, validate_plan, optimize_plan, branch, merge, analyze_dependencies.",
                "enum": [
                    "create",
                    "update",
                    "list",
                    "get",
                    "set_active",
                    "delete",
                    "create_version",
                    "list_versions",
                    "get_version",
                    "compare_versions",
                    "rollback",
                    "parse_intent",
                    "validate_plan",
                    "optimize_plan",
                    "branch",
                    "merge",
                    "analyze_dependencies"
                ],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan. Required for create, update, set_active, and delete commands. Optional for get and mark_step (uses active plan if not specified).",
                "type": "string",
            },
            "title": {
                "description": "Title for the plan. Required for create command, optional for update command.",
                "type": "string",
            },
            "description": {
                "description": "Detailed description of the plan's purpose and goals.",
                "type": "string",
            },
            "steps": {
                "description": "List of steps for the plan. Each step should be a clear, actionable task.",
                "type": "array",
                "items": {"type": "string"}
            },
            "step_dependencies": {
                "description": "Dependencies between steps, specified as a list of [step_index, dependency_step_index] pairs.",
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2
                }
            },
            "version_id": {
                "description": "Version identifier for version-related commands. Required for get_version, compare_versions, and rollback commands.",
                "type": "string",
            },
            "version_description": {
                "description": "Description of the version being created. Optional for create_version command.",
                "type": "string",
            },
            "compare_with_version": {
                "description": "Second version ID to compare with. Required for compare_versions command.",
                "type": "string",
            },
            "user_input": {
                "description": "Natural language input from the user for intent parsing.",
                "type": "string",
            },
            "branch_name": {
                "description": "Name of the branch to create or merge from.",
                "type": "string",
            },
            "target_branch": {
                "description": "Target branch for merge operations.",
                "type": "string",
            },
            "conflict_resolution": {
                "description": "Strategy for resolving conflicts during merge (auto, manual, theirs, ours).",
                "type": "string",
                "enum": ["auto", "manual", "theirs", "ours"]
            },
            "tag_name": {
                "description": "Name of the tag to apply to a version.",
                "type": "string"
            },
            "fork_name": {
                "description": "Name for the forked version.",
                "type": "string"
            },
            "merge_strategy": {
                "description": "Strategy for merging versions (auto, manual, selective).",
                "type": "string",
                "enum": ["auto", "manual", "selective"]
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    plans: Dict[str, Dict[str, Any]] = {}  # Dictionary to store plans by plan_id
    _current_plan_id: Optional[str] = None  # Track the current active plan
    _plan_versions: Dict[str, Dict[str, Dict[str, Any]]] = {}  # Dictionary to store plan versions by plan_id
    _plan_branches: Dict[str, Dict[str, str]] = {}  # Dictionary to store branches for each plan
    _intent_cache: Dict[str, Dict[str, Any]] = {}  # Cache for parsed intents
    _version_history: Dict[str, List[str]] = {}  # Track version history for each plan
    _version_tags: Dict[str, Dict[str, str]] = {}  # Store tags for versions
    _version_metadata: Dict[str, Dict[str, Dict[str, Any]]] = {}  # Store additional metadata for versions

    async def execute(
        self,
        *,
        command: Literal[
            "create", "update", "list", "get", "set_active", "delete",
            "create_version", "list_versions", "get_version", "compare_versions", "rollback",
            "parse_intent", "validate_plan", "optimize_plan", "branch", "merge", "analyze_dependencies",
            "tag_version", "get_version_history", "fork_version", "merge_versions"
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
    ):
        """
        Execute the planning tool with the given command and parameters.

        Parameters:
        - command: The operation to perform (create, update, list, get, set_active, delete,
                  create_version, list_versions, get_version, compare_versions, rollback,
                  parse_intent, validate_plan, optimize_plan, branch, merge, analyze_dependencies)
        - plan_id: Unique identifier for the plan
        - title: Title for the plan (used with create command)
        - description: Detailed description of the plan's purpose and goals
        - steps: List of steps for the plan
        - step_dependencies: Dependencies between steps as [step_index, dependency_step_index] pairs
        - version_id: Identifier for the version (required for version-related commands)
        - version_description: Description of the version (optional for create_version)
        - compare_with_version: Second version ID to compare with (required for compare_versions)
        - user_input: Natural language input from the user for intent parsing
        - branch_name: Name of the branch to create or merge from
        - target_branch: Target branch for merge operations
        - conflict_resolution: Strategy for resolving conflicts during merge
        - tag_name: Name of the tag to apply to a version
        - fork_name: Name for the forked version
        - merge_strategy: Strategy for merging versions (auto, manual, selective)
        """

        try:
            # Check for required parameters based on command
            if command == "create":
                if not plan_id:
                    # Generate a plan ID if not provided
                    import uuid
                    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
                    logger.info(f"Auto-generated plan ID: {plan_id}")

                if not title:
                    raise ToolError("Parameter `title` is required for command: create")

                return self._create_plan(plan_id, title, description, steps, step_dependencies)
            elif command == "update":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: update")

                return self._update_plan(plan_id, title, description, steps, step_dependencies)
            elif command == "list":
                return self._list_plans()
            elif command == "get":
                # If no plan_id is provided, use the active plan
                if not plan_id and self._current_plan_id:
                    plan_id = self._current_plan_id
                    logger.info(f"Using active plan ID: {plan_id}")

                return self._get_plan(plan_id)
            elif command == "set_active":
                if not plan_id:
                    raise ToolError("Parameter `plan_id` is required for command: set_active")

                return self._set_active_plan(plan_id)
            elif command == "delete":
                if not plan_id:
                    raise ToolError("Parameter `plan_id` is required for command: delete")

                return self._delete_plan(plan_id)
            elif command == "create_version":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: create_version")

                return self._create_version(plan_id, version_id, version_description)
            elif command == "list_versions":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: list_versions")

                return self._list_versions(plan_id)
            elif command == "get_version":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: get_version")

                if not version_id:
                    raise ToolError("Parameter `version_id` is required for command: get_version")

                return self._get_version(plan_id, version_id)
            elif command == "compare_versions":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: compare_versions")

                if not version_id:
                    raise ToolError("Parameter `version_id` is required for command: compare_versions")

                if not compare_with_version:
                    raise ToolError("Parameter `compare_with_version` is required for command: compare_versions")

                return self._compare_versions(plan_id, version_id, compare_with_version)
            elif command == "rollback":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: rollback")

                if not version_id:
                    raise ToolError("Parameter `version_id` is required for command: rollback")

                return self._rollback_to_version(plan_id, version_id)
            elif command == "parse_intent":
                if not user_input:
                    raise ToolError("Parameter `user_input` is required for command: parse_intent")

                return self._parse_intent(user_input)
            elif command == "validate_plan":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: validate_plan")

                return self._validate_plan(plan_id)
            elif command == "optimize_plan":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: optimize_plan")

                return self._optimize_plan(plan_id)
            elif command == "branch":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: branch")

                if not branch_name:
                    raise ToolError("Parameter `branch_name` is required for command: branch")

                return self._create_branch(plan_id, branch_name)
            elif command == "merge":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: merge")

                if not branch_name:
                    raise ToolError("Parameter `branch_name` is required for command: merge")

                if not target_branch:
                    raise ToolError("Parameter `target_branch` is required for command: merge")

                return self._merge_branch(plan_id, branch_name, target_branch, conflict_resolution)
            elif command == "analyze_dependencies":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: analyze_dependencies")

                return self._analyze_dependencies(plan_id)
            elif command == "tag_version":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: tag_version")

                if not version_id:
                    raise ToolError("Parameter `version_id` is required for command: tag_version")

                if not tag_name:
                    raise ToolError("Parameter `tag_name` is required for command: tag_version")

                return self._tag_version(plan_id, version_id, tag_name)
            elif command == "get_version_history":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: get_version_history")

                return self._get_version_history(plan_id)
            elif command == "fork_version":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: fork_version")

                if not version_id:
                    raise ToolError("Parameter `version_id` is required for command: fork_version")

                if not fork_name:
                    raise ToolError("Parameter `fork_name` is required for command: fork_version")

                return self._fork_version(plan_id, version_id, fork_name)
            elif command == "merge_versions":
                if not plan_id:
                    # Try to use the active plan if available
                    if self._current_plan_id:
                        plan_id = self._current_plan_id
                        logger.info(f"Using active plan ID: {plan_id}")
                    else:
                        raise ToolError("Parameter `plan_id` is required for command: merge_versions")

                if not version_id:
                    raise ToolError("Parameter `version_id` is required for command: merge_versions")

                if not compare_with_version:
                    raise ToolError("Parameter `compare_with_version` is required for command: merge_versions")

                return self._merge_versions(plan_id, version_id, compare_with_version, merge_strategy)
            else:
                allowed_commands = "create, update, list, get, set_active, delete, create_version, list_versions, get_version, compare_versions, rollback, parse_intent, validate_plan, optimize_plan, branch, merge, analyze_dependencies, tag_version, get_version_history, fork_version, merge_versions"
                raise ToolError(f"Unrecognized command: {command}. Allowed commands are: {allowed_commands}")
        except Exception as e:
            logger.error(f"Error in PlanningTool.execute: {str(e)}")
            return ToolResult(error=f"Error executing command '{command}': {str(e)}")

    def _create_plan(
        self, plan_id: Optional[str], title: Optional[str], description: Optional[str] = None,
        steps: Optional[List[str]] = None, step_dependencies: Optional[List[List[int]]] = None
    ) -> ToolResult:
        """Create a new plan with the given ID, title, and optional details."""
        # plan_id is now guaranteed to be non-None due to the check in execute()
        assert plan_id is not None, "plan_id should not be None at this point"

        if plan_id in self.plans:
            raise ToolError(
                f"A plan with ID '{plan_id}' already exists. Use 'update' to modify existing plans."
            )

        # title is now guaranteed to be non-None due to the check in execute()
        assert title is not None, "title should not be None at this point"

        # Create a new plan with enhanced structure
        plan = {
            "plan_id": plan_id,
            "title": title,
            "description": description or "",
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "steps": steps or [],
            "step_statuses": ["not_started"] * len(steps) if steps else [],
            "step_notes": [""] * len(steps) if steps else [],
            "step_dependencies": step_dependencies or [],
            "metadata": {
                "version": "1.0",
                "current_branch": "main",
                "tags": []
            }
        }

        self.plans[plan_id] = plan
        self._current_plan_id = plan_id  # Set as active plan

        # Initialize branches for this plan
        self._plan_branches[plan_id] = {"main": "main"}

        # Create initial version
        self._create_version(plan_id, "v1", "Initial version")

        return ToolResult(
            output=f"Plan created successfully with ID: {plan_id}\n\n{self._format_plan(plan)}"
        )

    def _update_plan(
        self, plan_id: Optional[str], title: Optional[str], description: Optional[str] = None,
        steps: Optional[List[str]] = None, step_dependencies: Optional[List[List[int]]] = None
    ) -> ToolResult:
        """Update an existing plan with new details."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: update")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]

        # Track if any changes were made
        changes_made = False

        if title:
            plan["title"] = title
            changes_made = True

        if description is not None:
            plan["description"] = description
            changes_made = True

        if steps is not None:
            # Update steps while preserving status for existing steps
            old_steps = plan.get("steps", [])
            old_statuses = plan.get("step_statuses", [])
            old_notes = plan.get("step_notes", [])

            # Initialize new status and notes lists
            new_statuses = []
            new_notes = []

            # For each new step, try to find matching old step and preserve its status and notes
            for i, step in enumerate(steps):
                if i < len(old_steps) and step == old_steps[i]:
                    # Same step at same position, preserve status and notes
                    status = old_statuses[i] if i < len(old_statuses) else "not_started"
                    note = old_notes[i] if i < len(old_notes) else ""
                else:
                    # New or modified step, set default status and empty notes
                    status = "not_started"
                    note = ""

                new_statuses.append(status)
                new_notes.append(note)

            plan["steps"] = steps
            plan["step_statuses"] = new_statuses
            plan["step_notes"] = new_notes
            changes_made = True

        if step_dependencies is not None:
            plan["step_dependencies"] = step_dependencies
            changes_made = True

        if changes_made:
            # Update the timestamp
            plan["updated_at"] = datetime.datetime.now().isoformat()

            # Create a new version to track the changes
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            self._create_version(plan_id, f"v_update_{timestamp}", "Automatic version after update")

        return ToolResult(
            output=f"Plan updated successfully: {plan_id}\n\n{self._format_detailed_plan(plan)}"
        )

    def _list_plans(self) -> ToolResult:
        """List all available plans."""
        if not self.plans:
            return ToolResult(
                output="No plans available. Create a plan with the 'create' command."
            )

        output = "Available plans:\n"
        for plan_id, plan in self.plans.items():
            current_marker = " (active)" if plan_id == self._current_plan_id else ""
            output += f"• {plan_id}{current_marker}: {plan['title']}\n"

        return ToolResult(output=output)

    def _get_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Get details of a specific plan."""
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self._current_plan_id

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]
        return ToolResult(output=self._format_plan(plan))

    def _set_active_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Set a plan as the active plan."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: set_active")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        self._current_plan_id = plan_id
        return ToolResult(
            output=f"Plan '{plan_id}' is now the active plan.\n\n{self._format_plan(self.plans[plan_id])}"
        )



    def _delete_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Delete a plan."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: delete")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        del self.plans[plan_id]

        # Remove any versions of this plan
        if plan_id in self._plan_versions:
            del self._plan_versions[plan_id]

        # If the deleted plan was the active plan, clear the active plan
        if self._current_plan_id == plan_id:
            self._current_plan_id = None

        return ToolResult(output=f"Plan '{plan_id}' has been deleted.")

    def _create_version(self, plan_id: Optional[str], version_id: Optional[str], version_description: Optional[str]) -> ToolResult:
        """Create a new version of a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for create_version command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        # Generate a version ID if not provided
        if not version_id:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            version_id = f"v{timestamp}"

        # Initialize versions dictionary for this plan if it doesn't exist
        if plan_id not in self._plan_versions:
            self._plan_versions[plan_id] = {}

        # Check if version ID already exists
        if version_id in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{version_id}' already exists for plan '{plan_id}'")

        # Create a deep copy of the current plan
        plan_copy = copy.deepcopy(self.plans[plan_id])

        # Add version metadata
        version_info = {
            "version_id": version_id,
            "created_at": datetime.datetime.now().isoformat(),
            "description": version_description or f"Version {version_id}",
            "plan_data": plan_copy
        }

        # Store the version
        self._plan_versions[plan_id][version_id] = version_info

        # Track version history
        if plan_id not in self._version_history:
            self._version_history[plan_id] = []
        self._version_history[plan_id].append(version_id)

        # Initialize version metadata
        if plan_id not in self._version_metadata:
            self._version_metadata[plan_id] = {}
        if version_id not in self._version_metadata[plan_id]:
            self._version_metadata[plan_id][version_id] = {}

        # Add creation metadata
        self._version_metadata[plan_id][version_id]["created_at"] = datetime.datetime.now().isoformat()
        self._version_metadata[plan_id][version_id]["created_by"] = "user"
        self._version_metadata[plan_id][version_id]["parent_version"] = None  # No parent for initial versions

        return ToolResult(output=f"Created version '{version_id}' for plan '{plan_id}'")

    def _list_versions(self, plan_id: Optional[str]) -> ToolResult:
        """List all versions of a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for list_versions command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        if plan_id not in self._plan_versions or not self._plan_versions[plan_id]:
            return ToolResult(output=f"No versions found for plan '{plan_id}'")

        # Format the versions list
        versions_list = []
        for version_id, version_info in self._plan_versions[plan_id].items():
            versions_list.append({
                "version_id": version_id,
                "created_at": version_info["created_at"],
                "description": version_info["description"]
            })

        # Sort versions by creation time (newest first)
        versions_list.sort(key=lambda x: x["created_at"], reverse=True)

        # Format the output
        output = f"Versions for plan '{plan_id}':\n\n"
        for version in versions_list:
            output += f"- {version['version_id']} ({version['created_at']}): {version['description']}\n"

        return ToolResult(output=output)

    def _get_version(self, plan_id: Optional[str], version_id: Optional[str]) -> ToolResult:
        """Get a specific version of a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for get_version command")

        if not version_id:
            return ToolResult(error="Version ID is required for get_version command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        if plan_id not in self._plan_versions or not self._plan_versions[plan_id]:
            return ToolResult(error=f"No versions found for plan '{plan_id}'")

        if version_id not in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{version_id}' not found for plan '{plan_id}'")

        # Get the version data
        version_info = self._plan_versions[plan_id][version_id]
        plan_data = version_info["plan_data"]

        # Format the output
        output = f"Version '{version_id}' of plan '{plan_id}':\n\n"
        output += f"Title: {plan_data['title']}\n"
        output += f"Created at: {version_info['created_at']}\n"
        output += f"Description: {version_info['description']}\n\n"
        output += "Steps:\n"

        for i, step in enumerate(plan_data["steps"]):
            status = plan_data["step_statuses"][i] if i < len(plan_data["step_statuses"]) else "not_started"
            notes = plan_data["step_notes"][i] if i < len(plan_data["step_notes"]) else ""

            status_icon = "⬜" if status == "not_started" else "🔄" if status == "in_progress" else "✅" if status == "completed" else "⛔"
            output += f"{i+1}. {status_icon} {step}"
            if notes:
                output += f" - Notes: {notes}"
            output += "\n"

        return ToolResult(output=output)

    def _compare_versions(self, plan_id: Optional[str], version_id: Optional[str], compare_with_version: Optional[str]) -> ToolResult:
        """Compare two versions of a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for compare_versions command")

        if not version_id:
            return ToolResult(error="Version ID is required for compare_versions command")

        if not compare_with_version:
            return ToolResult(error="compare_with_version is required for compare_versions command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        if plan_id not in self._plan_versions or not self._plan_versions[plan_id]:
            return ToolResult(error=f"No versions found for plan '{plan_id}'")

        if version_id not in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{version_id}' not found for plan '{plan_id}'")

        if compare_with_version not in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{compare_with_version}' not found for plan '{plan_id}'")

        # Get the version data
        version1_info = self._plan_versions[plan_id][version_id]
        version2_info = self._plan_versions[plan_id][compare_with_version]

        plan1 = version1_info["plan_data"]
        plan2 = version2_info["plan_data"]

        # Compare the plans
        differences = []

        # Compare titles
        if plan1["title"] != plan2["title"]:
            differences.append(f"Title changed from '{plan2['title']}' to '{plan1['title']}'")

        # Compare steps
        steps1 = plan1["steps"]
        steps2 = plan2["steps"]

        # Find added, removed, and modified steps
        # Find added steps
        for i, step in enumerate(steps1):
            if step not in steps2:
                differences.append(f"Added step {i+1}: {step}")

        # Find removed steps
        for i, step in enumerate(steps2):
            if step not in steps1:
                differences.append(f"Removed step {i+1}: {step}")

        # Compare step statuses
        for i, step in enumerate(steps1):
            if i < len(steps1) and i < len(steps2) and steps1[i] == steps2[i]:
                # Compare status if the step exists in both versions
                status1 = plan1["step_statuses"][i] if i < len(plan1["step_statuses"]) else "not_started"
                status2 = plan2["step_statuses"][i] if i < len(plan2["step_statuses"]) else "not_started"

                if status1 != status2:
                    differences.append(f"Step {i+1} status changed from '{status2}' to '{status1}'")

                # Compare notes if the step exists in both versions
                notes1 = plan1["step_notes"][i] if i < len(plan1["step_notes"]) else ""
                notes2 = plan2["step_notes"][i] if i < len(plan2["step_notes"]) else ""

                if notes1 != notes2:
                    differences.append(f"Step {i+1} notes changed from '{notes2}' to '{notes1}'")

        # Format the output
        if not differences:
            output = f"No differences found between versions '{version_id}' and '{compare_with_version}' of plan '{plan_id}'"
        else:
            output = f"Differences between version '{version_id}' and '{compare_with_version}' of plan '{plan_id}':\n\n"
            for diff in differences:
                output += f"- {diff}\n"

        return ToolResult(output=output)

    def _rollback_to_version(self, plan_id: Optional[str], version_id: Optional[str]) -> ToolResult:
        """Roll back a plan to a specific version."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for rollback command")

        if not version_id:
            return ToolResult(error="Version ID is required for rollback command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        if plan_id not in self._plan_versions or not self._plan_versions[plan_id]:
            return ToolResult(error=f"No versions found for plan '{plan_id}'")

        if version_id not in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{version_id}' not found for plan '{plan_id}'")

        # Get the version data
        version_info = self._plan_versions[plan_id][version_id]
        plan_data = version_info["plan_data"]

        # Create a version of the current plan before rolling back
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        auto_version_id = f"pre_rollback_{timestamp}"

        # Store the current plan as a version
        if plan_id not in self._plan_versions:
            self._plan_versions[plan_id] = {}

        self._plan_versions[plan_id][auto_version_id] = {
            "version_id": auto_version_id,
            "created_at": datetime.datetime.now().isoformat(),
            "description": f"Auto-saved before rollback to {version_id}",
            "plan_data": copy.deepcopy(self.plans[plan_id])
        }

        # Roll back the plan to the specified version
        self.plans[plan_id] = copy.deepcopy(plan_data)

        # Track the rollback in version history
        if plan_id not in self._version_history:
            self._version_history[plan_id] = []
        self._version_history[plan_id].append(version_id)  # Add the rolled-back version to history

        # Add rollback metadata
        if plan_id not in self._version_metadata:
            self._version_metadata[plan_id] = {}
        if version_id not in self._version_metadata[plan_id]:
            self._version_metadata[plan_id][version_id] = {}

        # Record rollback information
        self._version_metadata[plan_id][version_id]["rollback_info"] = {
            "rolled_back_at": datetime.datetime.now().isoformat(),
            "previous_version": auto_version_id,
            "reason": "User-initiated rollback"
        }

        return ToolResult(output=f"Plan '{plan_id}' has been rolled back to version '{version_id}'. Current state saved as version '{auto_version_id}'")

    def _format_plan(self, plan: Dict[str, Any]) -> str:
        """Format a plan for basic display."""
        output = f"Plan: {plan['title']} (ID: {plan['plan_id']})\n"
        output += "=" * len(output) + "\n\n"

        if plan.get("description"):
            output += f"Description: {plan['description']}\n\n"

        if plan.get("created_at"):
            output += f"Created: {plan['created_at']}\n"

        if plan.get("updated_at"):
            output += f"Last Updated: {plan['updated_at']}\n"

        # Add branch information if available
        if plan['plan_id'] in self._plan_branches and plan.get("metadata", {}).get("current_branch"):
            current_branch = plan["metadata"]["current_branch"]
            output += f"Current Branch: {current_branch}\n"

        output += "\n"
        return output

    def _format_detailed_plan(self, plan: Dict[str, Any]) -> str:
        """Format a plan with detailed information including steps, dependencies, and version history."""
        output = self._format_plan(plan)

        # Add version information if available
        plan_id = plan.get('plan_id')
        if plan_id and plan_id in self._plan_versions:
            # Get the latest version
            if plan_id in self._version_history and self._version_history[plan_id]:
                latest_version = self._version_history[plan_id][-1]
                output += f"Latest Version: {latest_version}\n"

            # Get version count
            version_count = len(self._plan_versions[plan_id])
            output += f"Total Versions: {version_count}\n"

            # Get tags if any
            if plan_id in self._version_tags and self._version_tags[plan_id]:
                tags = list(self._version_tags[plan_id].keys())
                output += f"Tags: {', '.join(tags)}\n"

            output += "\n"

        # Add steps information
        if plan.get("steps"):
            output += "Steps:\n"
            for i, step in enumerate(plan["steps"]):
                # Get status and notes if available
                status = plan["step_statuses"][i] if i < len(plan.get("step_statuses", [])) else "not_started"
                notes = plan["step_notes"][i] if i < len(plan.get("step_notes", [])) else ""

                # Format status icon
                status_icon = "⬜" if status == "not_started" else "🔄" if status == "in_progress" else "✅" if status == "completed" else "⛔"

                # Check if this step has dependencies
                dependencies = []
                for dep in plan.get("step_dependencies", []):
                    if dep[0] == i:  # This step depends on another step
                        dependencies.append(str(dep[1] + 1))  # +1 for 1-based indexing in display

                # Format the step line
                output += f"{i+1}. {status_icon} {step}"

                # Add dependencies if any
                if dependencies:
                    output += f" (depends on steps: {', '.join(dependencies)})"

                # Add notes if any
                if notes:
                    output += f"\n   Notes: {notes}"

                output += "\n"

        return output


    def _tag_version(self, plan_id: Optional[str], version_id: Optional[str], tag_name: Optional[str]) -> ToolResult:
        """Tag a specific version of a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for tag_version command")

        if not version_id:
            return ToolResult(error="Version ID is required for tag_version command")

        if not tag_name:
            return ToolResult(error="Tag name is required for tag_version command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        if plan_id not in self._plan_versions or not self._plan_versions[plan_id]:
            return ToolResult(error=f"No versions found for plan '{plan_id}'")

        if version_id not in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{version_id}' not found for plan '{plan_id}'")

        # Initialize tags dictionary for this plan if it doesn't exist
        if plan_id not in self._version_tags:
            self._version_tags[plan_id] = {}

        # Store the tag
        self._version_tags[plan_id][tag_name] = version_id

        # Add tag to version metadata
        if plan_id not in self._version_metadata:
            self._version_metadata[plan_id] = {}
        if version_id not in self._version_metadata[plan_id]:
            self._version_metadata[plan_id][version_id] = {}
        if "tags" not in self._version_metadata[plan_id][version_id]:
            self._version_metadata[plan_id][version_id]["tags"] = []

        self._version_metadata[plan_id][version_id]["tags"].append(tag_name)

        return ToolResult(output=f"Tagged version '{version_id}' of plan '{plan_id}' as '{tag_name}'")

    def _get_version_history(self, plan_id: Optional[str]) -> ToolResult:
        """Get the version history of a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for get_version_history command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        if plan_id not in self._plan_versions or not self._plan_versions[plan_id]:
            return ToolResult(output=f"No version history found for plan '{plan_id}'")

        # Get the version history
        if plan_id not in self._version_history:
            # If no explicit history is stored, create one based on creation timestamps
            versions = list(self._plan_versions[plan_id].values())
            versions.sort(key=lambda v: v["created_at"])
            history = [v["version_id"] for v in versions]
        else:
            history = self._version_history[plan_id]

        # Format the output
        output = f"Version history for plan '{plan_id}':\n\n"

        for i, version_id in enumerate(history):
            if version_id in self._plan_versions[plan_id]:
                version_info = self._plan_versions[plan_id][version_id]
                created_at = version_info["created_at"]
                description = version_info["description"]

                # Get tags for this version
                tags = []
                if plan_id in self._version_tags:
                    for tag, ver_id in self._version_tags[plan_id].items():
                        if ver_id == version_id:
                            tags.append(tag)

                # Format tags
                tags_str = f" [tags: {', '.join(tags)}]" if tags else ""

                output += f"{i+1}. {version_id} ({created_at}){tags_str}: {description}\n"

        return ToolResult(output=output)

    def _fork_version(self, plan_id: Optional[str], version_id: Optional[str], fork_name: Optional[str]) -> ToolResult:
        """Fork a specific version of a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for fork_version command")

        if not version_id:
            return ToolResult(error="Version ID is required for fork_version command")

        if not fork_name:
            return ToolResult(error="Fork name is required for fork_version command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        if plan_id not in self._plan_versions or not self._plan_versions[plan_id]:
            return ToolResult(error=f"No versions found for plan '{plan_id}'")

        if version_id not in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{version_id}' not found for plan '{plan_id}'")

        # Create a new plan ID for the fork
        fork_plan_id = f"{plan_id}_{fork_name}"

        # Check if the fork already exists
        if fork_plan_id in self.plans:
            return ToolResult(error=f"A plan with ID '{fork_plan_id}' already exists")

        # Get the version data
        version_info = self._plan_versions[plan_id][version_id]
        plan_data = copy.deepcopy(version_info["plan_data"])

        # Update the plan data for the fork
        plan_data["plan_id"] = fork_plan_id
        plan_data["title"] = f"{plan_data['title']} (forked from {plan_id}:{version_id})"
        plan_data["created_at"] = datetime.datetime.now().isoformat()
        plan_data["updated_at"] = datetime.datetime.now().isoformat()
        plan_data["metadata"]["forked_from"] = {"plan_id": plan_id, "version_id": version_id}

        # Create the new plan
        self.plans[fork_plan_id] = plan_data

        # Initialize branches for the fork
        self._plan_branches[fork_plan_id] = {"main": "main"}

        # Create initial version for the fork
        self._create_version(fork_plan_id, "v1", f"Initial version (forked from {plan_id}:{version_id})")

        return ToolResult(output=f"Forked version '{version_id}' of plan '{plan_id}' to new plan '{fork_plan_id}'\n\n{self._format_plan(plan_data)}")

    def _merge_versions(self, plan_id: Optional[str], version_id: Optional[str], compare_with_version: Optional[str], merge_strategy: Optional[str]) -> ToolResult:
        """Merge two versions of a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for merge_versions command")

        if not version_id:
            return ToolResult(error="Version ID is required for merge_versions command")

        if not compare_with_version:
            return ToolResult(error="compare_with_version is required for merge_versions command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        if plan_id not in self._plan_versions or not self._plan_versions[plan_id]:
            return ToolResult(error=f"No versions found for plan '{plan_id}'")

        if version_id not in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{version_id}' not found for plan '{plan_id}'")

        if compare_with_version not in self._plan_versions[plan_id]:
            return ToolResult(error=f"Version '{compare_with_version}' not found for plan '{plan_id}'")

        # Set default merge strategy if not provided
        if not merge_strategy:
            merge_strategy = "auto"

        if merge_strategy not in ["auto", "manual", "selective"]:
            return ToolResult(error=f"Invalid merge strategy: {merge_strategy}. Supported strategies: auto, manual, selective")

        # Get the version data
        version1_info = self._plan_versions[plan_id][version_id]
        version2_info = self._plan_versions[plan_id][compare_with_version]

        plan1 = version1_info["plan_data"]
        plan2 = version2_info["plan_data"]

        # Create a new plan as the merge result
        merged_plan = copy.deepcopy(plan1)
        merged_plan["updated_at"] = datetime.datetime.now().isoformat()

        # Merge steps based on the strategy
        if merge_strategy == "auto":
            # Automatic merging - take all unique steps from both versions
            all_steps = list(plan1["steps"])
            for step in plan2["steps"]:
                if step not in all_steps:
                    all_steps.append(step)

            # Update the merged plan
            merged_plan["steps"] = all_steps
            merged_plan["step_statuses"] = ["not_started"] * len(all_steps)
            merged_plan["step_notes"] = [""] * len(all_steps)

            # Merge dependencies
            merged_dependencies = list(plan1.get("step_dependencies", []))
            for dep in plan2.get("step_dependencies", []):
                if dep not in merged_dependencies:
                    merged_dependencies.append(dep)

            merged_plan["step_dependencies"] = merged_dependencies

        elif merge_strategy == "selective":
            # Selective merging - take steps from version1 and add non-conflicting steps from version2
            all_steps = list(plan1["steps"])
            added_steps = []

            for i, step in enumerate(plan2["steps"]):
                if step not in all_steps:
                    all_steps.append(step)
                    added_steps.append((len(all_steps) - 1, i))  # (new_index, old_index)

            # Update the merged plan
            merged_plan["steps"] = all_steps

            # Update statuses and notes
            new_statuses = list(plan1["step_statuses"])
            new_notes = list(plan1["step_notes"])

            # Add statuses and notes for new steps
            for new_idx, old_idx in added_steps:
                if new_idx >= len(new_statuses):
                    new_statuses.extend(["not_started"] * (new_idx - len(new_statuses) + 1))
                if new_idx >= len(new_notes):
                    new_notes.extend([""] * (new_idx - len(new_notes) + 1))

                if old_idx < len(plan2.get("step_statuses", [])):
                    new_statuses[new_idx] = plan2["step_statuses"][old_idx]
                if old_idx < len(plan2.get("step_notes", [])):
                    new_notes[new_idx] = plan2["step_notes"][old_idx]

            merged_plan["step_statuses"] = new_statuses
            merged_plan["step_notes"] = new_notes

            # Merge dependencies with mapping for new indices
            merged_dependencies = list(plan1.get("step_dependencies", []))

            # Add dependencies from version2 for the added steps
            for new_idx, old_idx in added_steps:
                for dep in plan2.get("step_dependencies", []):
                    if dep[0] == old_idx:  # This step in version2 has dependencies
                        # Find the new index of the dependency
                        dep_step = plan2["steps"][dep[1]]
                        if dep_step in all_steps:
                            new_dep_idx = all_steps.index(dep_step)
                            new_dep = [new_idx, new_dep_idx]
                            if new_dep not in merged_dependencies:
                                merged_dependencies.append(new_dep)

            merged_plan["step_dependencies"] = merged_dependencies

        # Create a new version for the merged result
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        merge_version_id = f"merge_{timestamp}"

        # Update the current plan
        self.plans[plan_id] = merged_plan

        # Create a version for the merged result
        self._create_version(
            plan_id,
            merge_version_id,
            f"Merged version '{version_id}' with '{compare_with_version}' using {merge_strategy} strategy"
        )

        # Add metadata about the merge
        if plan_id not in self._version_metadata:
            self._version_metadata[plan_id] = {}
        if merge_version_id not in self._version_metadata[plan_id]:
            self._version_metadata[plan_id][merge_version_id] = {}

        self._version_metadata[plan_id][merge_version_id]["merge_info"] = {
            "source_versions": [version_id, compare_with_version],
            "strategy": merge_strategy,
            "timestamp": datetime.datetime.now().isoformat()
        }

        return ToolResult(
            output=f"Merged version '{version_id}' with '{compare_with_version}' using {merge_strategy} strategy.\n\nNew version created: {merge_version_id}\n\n{self._format_detailed_plan(merged_plan)}"
        )

    def _analyze_dependencies(self, plan_id: Optional[str]) -> ToolResult:
        """Analyze dependencies between steps in a plan."""
        if not plan_id:
            return ToolResult(error="Plan ID is required for analyze_dependencies command")

        if plan_id not in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' not found")

        plan = self.plans[plan_id]
        steps = plan.get("steps", [])
        dependencies = plan.get("step_dependencies", [])

        if not steps:
            return ToolResult(output=f"Plan '{plan_id}' has no steps to analyze")

        # Build dependency graph
        graph = {i: [] for i in range(len(steps))}
        reverse_graph = {i: [] for i in range(len(steps))}

        for dep in dependencies:
            if len(dep) == 2 and 0 <= dep[0] < len(steps) and 0 <= dep[1] < len(steps):
                graph[dep[0]].append(dep[1])  # Step dep[0] depends on step dep[1]
                reverse_graph[dep[1]].append(dep[0])  # Step dep[1] is depended on by step dep[0]

        # Find root steps (no dependencies)
        root_steps = [i for i in range(len(steps)) if not graph[i]]

        # Find leaf steps (no dependents)
        leaf_steps = [i for i in range(len(steps)) if not reverse_graph[i]]

        # Check for cycles
        visited = set()
        temp_visited = set()
        has_cycle = False
        cycle_path = []

        def dfs(node, path):
            nonlocal has_cycle, cycle_path
            if node in temp_visited:
                has_cycle = True
                cycle_path = path + [node]
                return
            if node in visited:
                return

            temp_visited.add(node)
            path.append(node)

            for neighbor in graph[node]:
                dfs(neighbor, path)
                if has_cycle:
                    return

            path.pop()
            temp_visited.remove(node)
            visited.add(node)

        for i in range(len(steps)):
            if i not in visited:
                dfs(i, [])
                if has_cycle:
                    break

        # Format the output
        output = f"Dependency analysis for plan '{plan_id}':\n\n"

        # List all steps with their dependencies
        output += "Steps and their dependencies:\n"
        for i, step in enumerate(steps):
            deps = graph[i]
            deps_str = ", ".join([str(d+1) for d in deps]) if deps else "None"
            output += f"{i+1}. {step}\n   Depends on: {deps_str}\n"

        # List root steps
        output += "\nRoot steps (no dependencies):\n"
        if root_steps:
            for i in root_steps:
                output += f"{i+1}. {steps[i]}\n"
        else:
            output += "None\n"

        # List leaf steps
        output += "\nLeaf steps (no dependents):\n"
        if leaf_steps:
            for i in leaf_steps:
                output += f"{i+1}. {steps[i]}\n"
        else:
            output += "None\n"

        # Report cycles if found
        if has_cycle:
            output += "\nWarning: Dependency cycle detected!\n"
            output += "Cycle: " + " -> ".join([f"Step {i+1} ({steps[i]})" for i in cycle_path]) + "\n"
            output += "This may cause issues with plan execution.\n"

        return ToolResult(output=output)


# Add the Planning class as a wrapper around PlanningTool
class Planning(PlanningTool):
    """Wrapper class for PlanningTool to maintain backward compatibility."""
    pass
