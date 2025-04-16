"""
Test script for the Git tool.

This script tests the basic functionality of the Git tool.
"""

import asyncio
import os
import sys
import shutil
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.git_tool import GitTool
from app.logger import logger

async def test_git_tool():
    """Test the Git tool functionality."""
    # Create a test directory
    test_dir = Path("./test_git_repo")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()
    
    try:
        # Create a Git tool instance
        git_tool = GitTool()
        
        # Initialize a Git repository
        logger.info("Testing repository initialization...")
        result = await git_tool.execute("init", repository_path=str(test_dir))
        print(f"Init result: {result.output}")
        
        # Create a test file
        test_file = test_dir / "test.txt"
        with open(test_file, "w") as f:
            f.write("This is a test file.")
        
        # Get repository status
        logger.info("Testing repository status...")
        result = await git_tool.execute("status", repository_path=str(test_dir))
        print(f"Status result: {result.output}")
        
        # Add the test file
        logger.info("Testing adding files...")
        result = await git_tool.execute("add", repository_path=str(test_dir), files=["test.txt"])
        print(f"Add result: {result.output}")
        
        # Commit the changes
        logger.info("Testing committing changes...")
        result = await git_tool.execute("commit", repository_path=str(test_dir), message="Add test file")
        print(f"Commit result: {result.output}")
        
        # Get the current branch
        logger.info("Testing getting current branch...")
        result = await git_tool.execute("current_branch", repository_path=str(test_dir))
        print(f"Current branch: {result.output}")
        
        # Create a new branch
        logger.info("Testing creating a new branch...")
        result = await git_tool.execute("create_branch", repository_path=str(test_dir), branch_name="test-branch")
        print(f"Create branch result: {result.output}")
        
        # Modify the test file
        with open(test_file, "a") as f:
            f.write("\nThis is an update to the test file.")
        
        # Get repository status again
        logger.info("Testing repository status after modification...")
        result = await git_tool.execute("status", repository_path=str(test_dir))
        print(f"Status result after modification: {result.output}")
        
        # Test auto-commit functionality
        logger.info("Testing auto-commit functionality...")
        result = await git_tool.execute("auto_commit_push", repository_path=str(test_dir), message="Auto-commit test")
        print(f"Auto-commit result: {result.output}")
        
        logger.info("All Git tool tests completed successfully!")
        
    finally:
        # Clean up the test directory
        if test_dir.exists():
            shutil.rmtree(test_dir)
            logger.info(f"Cleaned up test directory: {test_dir}")

if __name__ == "__main__":
    asyncio.run(test_git_tool())
