"""CLI Result module for Nexagent."""

from typing import Optional


class CLIResult:
    """Result of a CLI command execution."""

    def __init__(
        self,
        output: str,
        error: Optional[str] = None,
        exit_code: Optional[int] = None,
    ):
        """Initialize a CLI result.
        
        Args:
            output: The standard output of the command
            error: The standard error of the command
            exit_code: The exit code of the command
        """
        self.output = output
        self.error = error
        self.exit_code = exit_code

    def __str__(self) -> str:
        """Return a string representation of the CLI result."""
        return self.output
