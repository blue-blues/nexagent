"""
Git utility functions for Nexagent.

This module provides utility functions for interacting with Git repositories.
It uses the configuration from config.toml to set up Git operations.
"""

import os
import subprocess
from typing import List, Optional, Dict, Any, Tuple
import logging

from app.config import get_config

# Set up logging
logger = logging.getLogger(__name__)

def get_git_config() -> Dict[str, Any]:
    """
    Get Git configuration from config.toml.
    
    Returns:
        Dict containing Git configuration
    """
    config = get_config()
    git_config = config.get("git", {})
    return git_config

def run_git_command(command: List[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    """
    Run a Git command and return the result.
    
    Args:
        command: List of command parts (e.g. ["git", "status"])
        cwd: Working directory for the command
        
    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False  # Don't raise an exception on non-zero exit
        )
        
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            logger.error(f"Git command failed: {' '.join(command)}")
            logger.error(f"Error: {result.stderr.strip()}")
            return False, result.stderr.strip()
    except Exception as e:
        logger.error(f"Exception running Git command: {e}")
        return False, str(e)

def is_git_repository(path: str = ".") -> bool:
    """
    Check if the given path is a Git repository.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is a Git repository, False otherwise
    """
    success, _ = run_git_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=path)
    return success

def init_repository(path: str = ".") -> bool:
    """
    Initialize a Git repository.
    
    Args:
        path: Path to initialize
        
    Returns:
        True if successful, False otherwise
    """
    if is_git_repository(path):
        logger.info(f"Repository already initialized at {path}")
        return True
        
    success, output = run_git_command(["git", "init"], cwd=path)
    if success:
        logger.info(f"Initialized Git repository at {path}")
        
        # Configure user name and email
        git_config = get_git_config()
        user_name = git_config.get("user_name")
        user_email = git_config.get("user_email")
        
        if user_name:
            run_git_command(["git", "config", "user.name", user_name], cwd=path)
        if user_email:
            run_git_command(["git", "config", "user.email", user_email], cwd=path)
            
        return True
    else:
        logger.error(f"Failed to initialize Git repository at {path}: {output}")
        return False

def get_status(path: str = ".") -> Tuple[bool, Dict[str, List[str]]]:
    """
    Get the status of the Git repository.
    
    Args:
        path: Repository path
        
    Returns:
        Tuple of (success, status_dict)
    """
    if not is_git_repository(path):
        return False, {"error": ["Not a Git repository"]}
        
    success, output = run_git_command(["git", "status", "--porcelain"], cwd=path)
    if not success:
        return False, {"error": [output]}
        
    status = {
        "modified": [],
        "added": [],
        "deleted": [],
        "renamed": [],
        "untracked": []
    }
    
    for line in output.splitlines():
        if not line.strip():
            continue
            
        status_code = line[:2]
        file_path = line[3:]
        
        if status_code == "M " or status_code == " M":
            status["modified"].append(file_path)
        elif status_code == "A " or status_code == "AM":
            status["added"].append(file_path)
        elif status_code == "D " or status_code == " D":
            status["deleted"].append(file_path)
        elif status_code.startswith("R"):
            status["renamed"].append(file_path)
        elif status_code == "??":
            status["untracked"].append(file_path)
            
    return True, status

def add_files(files: List[str], path: str = ".") -> bool:
    """
    Add files to the Git staging area.
    
    Args:
        files: List of files to add
        path: Repository path
        
    Returns:
        True if successful, False otherwise
    """
    if not is_git_repository(path):
        logger.error(f"Not a Git repository: {path}")
        return False
        
    if not files:
        logger.warning("No files specified to add")
        return True
        
    command = ["git", "add"] + files
    success, output = run_git_command(command, cwd=path)
    
    if success:
        logger.info(f"Added {len(files)} files to staging area")
        return True
    else:
        logger.error(f"Failed to add files: {output}")
        return False

def commit(message: str, path: str = ".") -> bool:
    """
    Commit changes to the Git repository.
    
    Args:
        message: Commit message
        path: Repository path
        
    Returns:
        True if successful, False otherwise
    """
    if not is_git_repository(path):
        logger.error(f"Not a Git repository: {path}")
        return False
        
    # Format the commit message using the template
    git_config = get_git_config()
    template = git_config.get("commit_message_template", "{message}")
    formatted_message = template.format(message=message)
    
    command = ["git", "commit", "-m", formatted_message]
    success, output = run_git_command(command, cwd=path)
    
    if success:
        logger.info(f"Committed changes: {formatted_message}")
        return True
    else:
        logger.error(f"Failed to commit changes: {output}")
        return False

def push(remote: str = "origin", branch: Optional[str] = None, path: str = ".") -> bool:
    """
    Push changes to a remote repository.
    
    Args:
        remote: Remote name
        branch: Branch name (if None, uses the current branch)
        path: Repository path
        
    Returns:
        True if successful, False otherwise
    """
    if not is_git_repository(path):
        logger.error(f"Not a Git repository: {path}")
        return False
        
    # If branch is not specified, use the current branch
    if branch is None:
        success, current_branch = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
        if not success:
            logger.error(f"Failed to determine current branch: {current_branch}")
            return False
        branch = current_branch
        
    command = ["git", "push", remote, branch]
    success, output = run_git_command(command, cwd=path)
    
    if success:
        logger.info(f"Pushed changes to {remote}/{branch}")
        return True
    else:
        logger.error(f"Failed to push changes: {output}")
        return False

def create_branch(branch_name: str, path: str = ".") -> bool:
    """
    Create a new Git branch.
    
    Args:
        branch_name: Name of the branch to create
        path: Repository path
        
    Returns:
        True if successful, False otherwise
    """
    if not is_git_repository(path):
        logger.error(f"Not a Git repository: {path}")
        return False
        
    command = ["git", "checkout", "-b", branch_name]
    success, output = run_git_command(command, cwd=path)
    
    if success:
        logger.info(f"Created and switched to branch: {branch_name}")
        return True
    else:
        logger.error(f"Failed to create branch: {output}")
        return False

def checkout_branch(branch_name: str, path: str = ".") -> bool:
    """
    Checkout a Git branch.
    
    Args:
        branch_name: Name of the branch to checkout
        path: Repository path
        
    Returns:
        True if successful, False otherwise
    """
    if not is_git_repository(path):
        logger.error(f"Not a Git repository: {path}")
        return False
        
    command = ["git", "checkout", branch_name]
    success, output = run_git_command(command, cwd=path)
    
    if success:
        logger.info(f"Switched to branch: {branch_name}")
        return True
    else:
        logger.error(f"Failed to checkout branch: {output}")
        return False

def get_current_branch(path: str = ".") -> Optional[str]:
    """
    Get the current Git branch.
    
    Args:
        path: Repository path
        
    Returns:
        Current branch name or None if not in a Git repository
    """
    if not is_git_repository(path):
        logger.error(f"Not a Git repository: {path}")
        return None
        
    success, output = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    
    if success:
        return output
    else:
        logger.error(f"Failed to get current branch: {output}")
        return None

def clone_repository(url: str, target_path: Optional[str] = None, branch: Optional[str] = None) -> bool:
    """
    Clone a Git repository.
    
    Args:
        url: Repository URL
        target_path: Target path (if None, uses the repository name)
        branch: Branch to clone (if None, clones the default branch)
        
    Returns:
        True if successful, False otherwise
    """
    command = ["git", "clone"]
    
    if branch:
        command.extend(["-b", branch])
        
    command.append(url)
    
    if target_path:
        command.append(target_path)
        
    success, output = run_git_command(command)
    
    if success:
        logger.info(f"Cloned repository: {url}")
        return True
    else:
        logger.error(f"Failed to clone repository: {output}")
        return False

def auto_commit_and_push(message: str, path: str = ".") -> bool:
    """
    Automatically commit and push changes based on configuration.
    
    Args:
        message: Commit message
        path: Repository path
        
    Returns:
        True if successful, False otherwise
    """
    git_config = get_git_config()
    auto_commit = git_config.get("auto_commit", False)
    auto_push = git_config.get("auto_push", False)
    
    if not auto_commit:
        logger.info("Auto-commit is disabled in configuration")
        return False
        
    # Get status to see if there are changes to commit
    success, status = get_status(path)
    if not success:
        logger.error(f"Failed to get repository status: {status.get('error', ['Unknown error'])}")
        return False
        
    # Check if there are any changes
    has_changes = any(len(files) > 0 for files in status.values())
    if not has_changes:
        logger.info("No changes to commit")
        return True
        
    # Add all changes
    files_to_add = []
    for category in ["modified", "added", "deleted", "renamed", "untracked"]:
        files_to_add.extend(status.get(category, []))
        
    if not add_files(files_to_add, path):
        return False
        
    # Commit changes
    if not commit(message, path):
        return False
        
    # Push changes if auto-push is enabled
    if auto_push:
        default_branch = git_config.get("default_branch", "main")
        current_branch = get_current_branch(path) or default_branch
        return push("origin", current_branch, path)
        
    return True
