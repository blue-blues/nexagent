"""
Git tool for Nexagent.

This tool provides Git functionality for the Nexagent agent, allowing it to
interact with Git repositories.
"""

from typing import Dict, Any, List, Optional
import os
import json

from app.tools.base import BaseTool, ToolResult
from app.util.git_utils import (
    is_git_repository,
    init_repository,
    get_status,
    add_files,
    commit,
    push,
    create_branch,
    checkout_branch,
    get_current_branch,
    clone_repository,
    auto_commit_and_push
)
from app.logger import logger

class GitTool(BaseTool):
    """
    Tool for interacting with Git repositories.
    """
    name: str = "git"
    description: str = "Interact with Git repositories"
    
    async def execute(
        self,
        command: str,
        repository_path: str = ".",
        **kwargs
    ) -> ToolResult:
        """
        Execute a Git command.
        
        Args:
            command: The Git command to execute (status, init, add, commit, push, etc.)
            repository_path: Path to the Git repository
            **kwargs: Additional arguments specific to each command
            
        Returns:
            ToolResult with the command output
        """
        try:
            # Normalize the repository path
            repository_path = os.path.abspath(repository_path)
            
            # Execute the appropriate command
            if command == "status":
                return await self._get_status(repository_path)
            elif command == "init":
                return await self._init_repository(repository_path)
            elif command == "add":
                files = kwargs.get("files", [])
                return await self._add_files(repository_path, files)
            elif command == "commit":
                message = kwargs.get("message", "Commit changes")
                return await self._commit(repository_path, message)
            elif command == "push":
                remote = kwargs.get("remote", "origin")
                branch = kwargs.get("branch")
                return await self._push(repository_path, remote, branch)
            elif command == "create_branch":
                branch_name = kwargs.get("branch_name")
                if not branch_name:
                    return ToolResult(error=True, output="Branch name is required")
                return await self._create_branch(repository_path, branch_name)
            elif command == "checkout":
                branch_name = kwargs.get("branch_name")
                if not branch_name:
                    return ToolResult(error=True, output="Branch name is required")
                return await self._checkout_branch(repository_path, branch_name)
            elif command == "current_branch":
                return await self._get_current_branch(repository_path)
            elif command == "clone":
                url = kwargs.get("url")
                if not url:
                    return ToolResult(error=True, output="Repository URL is required")
                target_path = kwargs.get("target_path")
                branch = kwargs.get("branch")
                return await self._clone_repository(url, target_path, branch)
            elif command == "auto_commit_push":
                message = kwargs.get("message", "Auto-commit changes")
                return await self._auto_commit_and_push(repository_path, message)
            else:
                return ToolResult(
                    error=True,
                    output=f"Unknown command: {command}. Available commands: status, init, add, commit, push, create_branch, checkout, current_branch, clone, auto_commit_push"
                )
        except Exception as e:
            logger.error(f"Error executing Git command: {e}")
            return ToolResult(error=True, output=f"Error executing Git command: {str(e)}")
    
    async def _get_status(self, repository_path: str) -> ToolResult:
        """Get the status of the Git repository."""
        success, status = get_status(repository_path)
        if success:
            return ToolResult(error=False, output=json.dumps(status, indent=2))
        else:
            return ToolResult(error=True, output=f"Failed to get repository status: {status.get('error', ['Unknown error'])}")
    
    async def _init_repository(self, repository_path: str) -> ToolResult:
        """Initialize a Git repository."""
        success = init_repository(repository_path)
        if success:
            return ToolResult(error=False, output=f"Initialized Git repository at {repository_path}")
        else:
            return ToolResult(error=True, output=f"Failed to initialize Git repository at {repository_path}")
    
    async def _add_files(self, repository_path: str, files: List[str]) -> ToolResult:
        """Add files to the Git staging area."""
        if not files:
            return ToolResult(error=True, output="No files specified to add")
            
        success = add_files(files, repository_path)
        if success:
            return ToolResult(error=False, output=f"Added {len(files)} files to staging area")
        else:
            return ToolResult(error=True, output="Failed to add files to staging area")
    
    async def _commit(self, repository_path: str, message: str) -> ToolResult:
        """Commit changes to the Git repository."""
        success = commit(message, repository_path)
        if success:
            return ToolResult(error=False, output=f"Committed changes with message: {message}")
        else:
            return ToolResult(error=True, output="Failed to commit changes")
    
    async def _push(self, repository_path: str, remote: str, branch: Optional[str]) -> ToolResult:
        """Push changes to a remote repository."""
        success = push(remote, branch, repository_path)
        if success:
            branch_info = f" to branch {branch}" if branch else ""
            return ToolResult(error=False, output=f"Pushed changes to {remote}{branch_info}")
        else:
            return ToolResult(error=True, output="Failed to push changes")
    
    async def _create_branch(self, repository_path: str, branch_name: str) -> ToolResult:
        """Create a new Git branch."""
        success = create_branch(branch_name, repository_path)
        if success:
            return ToolResult(error=False, output=f"Created and switched to branch: {branch_name}")
        else:
            return ToolResult(error=True, output=f"Failed to create branch: {branch_name}")
    
    async def _checkout_branch(self, repository_path: str, branch_name: str) -> ToolResult:
        """Checkout a Git branch."""
        success = checkout_branch(branch_name, repository_path)
        if success:
            return ToolResult(error=False, output=f"Switched to branch: {branch_name}")
        else:
            return ToolResult(error=True, output=f"Failed to checkout branch: {branch_name}")
    
    async def _get_current_branch(self, repository_path: str) -> ToolResult:
        """Get the current Git branch."""
        branch = get_current_branch(repository_path)
        if branch:
            return ToolResult(error=False, output=branch)
        else:
            return ToolResult(error=True, output="Failed to get current branch")
    
    async def _clone_repository(self, url: str, target_path: Optional[str], branch: Optional[str]) -> ToolResult:
        """Clone a Git repository."""
        success = clone_repository(url, target_path, branch)
        if success:
            target_info = f" to {target_path}" if target_path else ""
            branch_info = f" (branch: {branch})" if branch else ""
            return ToolResult(error=False, output=f"Cloned repository {url}{target_info}{branch_info}")
        else:
            return ToolResult(error=True, output=f"Failed to clone repository: {url}")
    
    async def _auto_commit_and_push(self, repository_path: str, message: str) -> ToolResult:
        """Automatically commit and push changes based on configuration."""
        success = auto_commit_and_push(message, repository_path)
        if success:
            return ToolResult(error=False, output=f"Auto-committed and pushed changes with message: {message}")
        else:
            return ToolResult(error=True, output="Failed to auto-commit and push changes")
