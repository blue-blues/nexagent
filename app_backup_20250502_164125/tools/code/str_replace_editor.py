from collections import defaultdict
import os
from pathlib import Path
from typing import Literal, get_args

from app.exceptions import ToolError
from app.tools.base import BaseTool, ToolResult
from app.tools.cli_result import CLIResult
from app.tools.run import run


Command = Literal[
    "view",
    "create",
    "str_replace",
    "insert",
    "undo_edit",
]
SNIPPET_LINES: int = 4

MAX_RESPONSE_LEN: int = 16000

TRUNCATED_MESSAGE: str = "<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>"

_STR_REPLACE_EDITOR_DESCRIPTION = """Custom editing tool for viewing, creating and editing files
* State is persistent across command calls and discussions with the user
* Conversation memory tracks all interactions with files for improved context awareness
* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* The `undo_edit` command will revert the last edit made to the file at `path`

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`
"""


def maybe_truncate(content: str, truncate_after: int | None = MAX_RESPONSE_LEN):
    """Truncate content and append a notice if content exceeds the specified length."""
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


class StrReplaceEditor(BaseTool):
    """A tool for executing bash commands"""

    name: str = "str_replace_editor"
    description: str = _STR_REPLACE_EDITOR_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.",
                "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
                "type": "string",
            },
            "path": {
                "description": "Absolute path to file or directory.",
                "type": "string",
            },
            "file_text": {
                "description": "Required parameter of `create` command, with the content of the file to be created.",
                "type": "string",
            },
            "old_str": {
                "description": "Required parameter of `str_replace` command containing the string in `path` to replace.",
                "type": "string",
            },
            "new_str": {
                "description": "Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.",
                "type": "string",
            },
            "insert_line": {
                "description": "Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.",
                "type": "integer",
            },
            "view_range": {
                "description": "Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
                "items": {"type": "integer"},
                "type": "array",
            },
        },
        "required": ["command", "path"],
    }

    _file_history: list = defaultdict(list)
    _conversation_memory: dict = defaultdict(list)

    async def execute(
        self,
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        **kwargs,
    ) -> str:
        _path = Path(path)
        self.validate_path(command, _path)
        if command == "view":
            result = await self.view(_path, view_range)
        elif command == "create":
            if file_text is None:
                raise ToolError("Parameter `file_text` is required for command: create")
            self.write_file(_path, file_text)
            self._file_history[_path].append(file_text)
            result = ToolResult(output=f"File created successfully at: {_path}")
        elif command == "str_replace":
            if old_str is None:
                raise ToolError(
                    "Parameter `old_str` is required for command: str_replace"
                )
            result = self.str_replace(_path, old_str, new_str)
        elif command == "insert":
            if insert_line is None:
                raise ToolError(
                    "Parameter `insert_line` is required for command: insert"
                )
            if new_str is None:
                raise ToolError("Parameter `new_str` is required for command: insert")
            result = self.insert(_path, insert_line, new_str)
        elif command == "undo_edit":
            result = self.undo_edit(_path)
        else:
            raise ToolError(
                f'Unrecognized command {command}. The allowed commands for the {self.name} tool are: {", ".join(get_args(Command))}'
            )
        return str(result)

    def validate_path(self, command: str, path: Path):
        """
        Check that the path/command combination is valid.
        """
        # Check if its an absolute path using os.path.isabs for better cross-platform compatibility
        if not os.path.isabs(str(path)):
            # Convert relative path to absolute using current working directory
            suggested_path = Path(os.getcwd()) / path
            # Provide OS-specific guidance in the error message
            if os.name == 'nt':  # Windows
                raise ToolError(
                    f"The path {path} is not an absolute path. On Windows, absolute paths should include a drive letter (e.g., C:\\path\\to\\file). Maybe you meant {suggested_path}?"
                )
            else:  # Unix/Linux
                raise ToolError(
                    f"The path {path} is not an absolute path, it should start with `/`. Maybe you meant {suggested_path}?"
                )

        # For create command, we only need to check if the file already exists
        if command == "create":
            if path.exists():
                raise ToolError(
                    f"File already exists at: {path}. Cannot overwrite files using command `create`."
                )
            return

        # Check if path exists for other commands
        if not path.exists():
            raise ToolError(
                f"The path {path} does not exist. Please provide a valid path."
            )

        # Check if the path points to a directory
        if path.is_dir():
            if command != "view":
                raise ToolError(
                    f"The path {path} is a directory and only the `view` command can be used on directories"
                )

    async def view(self, path: Path, view_range: list[int] | None = None):
        """Implement the view command"""
        if path.is_dir():
            if view_range:
                raise ToolError(
                    "The `view_range` parameter is not allowed when `path` points to a directory."
                )

            # Use a more efficient approach for directory listing with timeout handling
            try:
                if os.name == 'nt':  # Windows
                    # Use dir command on Windows with a 30-second timeout
                    _, stdout, stderr = await run(
                        rf"dir /B /S \"{path}\" | findstr /V /B /C:\".\\\"")
                else:  # Unix/Linux
                    # Use find command on Unix with a 30-second timeout
                    _, stdout, stderr = await run(
                        f"find \"{path}\" -type f -not -path \"*/\\.*\" | sort")

                return CLIResult(output=maybe_truncate(stdout))
            except Exception as e:
                raise ToolError(f"Failed to list directory {path}: {str(e)}")

        # If it's a file, read its content
        try:
            file_content = self.read_file(path)
        except Exception as e:
            raise ToolError(f"Failed to read file {path}: {str(e)}")
        init_line = 1
        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError(
                    "Invalid `view_range`. It should be a list of two integers."
                )
            file_lines = file_content.split("\n")
            n_lines_file = len(file_lines)
            init_line, final_line = view_range
            if init_line < 1 or init_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its first element `{init_line}` should be within the range of lines of the file: {[1, n_lines_file]}"
                )
            if final_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its second element `{final_line}` should be smaller than the number of lines in the file: `{n_lines_file}`"
                )
            if final_line != -1 and final_line < init_line:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its second element `{final_line}` should be larger or equal than its first `{init_line}`"
                )

            if final_line == -1:
                file_content = "\n".join(file_lines[init_line - 1 :])
            else:
                file_content = "\n".join(file_lines[init_line - 1 : final_line])

        return CLIResult(
            output=self._make_output(file_content, str(path), init_line=init_line)
        )

    def str_replace(self, path: Path, old_str: str, new_str: str | None):
        """Implement the str_replace command, which replaces old_str with new_str in the file content"""
        # Read the file content
        file_content = self.read_file(path).expandtabs()
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ""

        # Check if old_str is empty
        if not old_str:
            raise ToolError(
                "The `old_str` parameter cannot be empty. Please provide a non-empty string to replace."
            )

        # Check if old_str is unique in the file
        occurrences = file_content.count(old_str)
        if occurrences == 0:
            raise ToolError(
                f"No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}."
            )
        elif occurrences > 1:
            file_content_lines = file_content.split("\n")
            lines = [
                idx + 1
                for idx, line in enumerate(file_content_lines)
                if old_str in line
            ]
            raise ToolError(
                f"No replacement was performed. Multiple occurrences of old_str `{old_str}` in lines {lines}. Please ensure it is unique"
            )

        # Replace old_str with new_str
        new_file_content = file_content.replace(old_str, new_str)

        # Write the new content to the file
        self.write_file(path, new_file_content)

        # Save the content to history
        self._file_history[path].append(file_content)

        # Create a snippet of the edited section - safely handle the split operation
        try:
            replacement_line = file_content.split(old_str)[0].count("\n")
            start_line = max(0, replacement_line - SNIPPET_LINES)
            end_line = replacement_line + SNIPPET_LINES + new_str.count("\n")
            snippet = "\n".join(new_file_content.split("\n")[start_line : end_line + 1])
        except ValueError:
            # Fallback if there's an issue with splitting - just show the first few lines
            start_line = 0
            end_line = min(SNIPPET_LINES * 2, len(new_file_content.split("\n")))
            snippet = "\n".join(new_file_content.split("\n")[start_line:end_line])

        # Prepare the success message
        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet, f"a snippet of {path}", start_line + 1
        )
        success_msg += "Review the changes and make sure they are as expected. Edit the file again if necessary."

        return CLIResult(output=success_msg)

    def insert(self, path: Path, insert_line: int, new_str: str):
        """Implement the insert command, which inserts new_str at the specified line in the file content."""
        file_text = self.read_file(path).expandtabs()
        new_str = new_str.expandtabs()
        file_text_lines = file_text.split("\n")
        n_lines_file = len(file_text_lines)

        if insert_line < 0 or insert_line > n_lines_file:
            raise ToolError(
                f"Invalid `insert_line` parameter: {insert_line}. It should be within the range of lines of the file: {[0, n_lines_file]}"
            )

        new_str_lines = new_str.split("\n")
        new_file_text_lines = (
            file_text_lines[:insert_line]
            + new_str_lines
            + file_text_lines[insert_line:]
        )
        snippet_lines = (
            file_text_lines[max(0, insert_line - SNIPPET_LINES) : insert_line]
            + new_str_lines
            + file_text_lines[insert_line : insert_line + SNIPPET_LINES]
        )

        new_file_text = "\n".join(new_file_text_lines)
        snippet = "\n".join(snippet_lines)

        self.write_file(path, new_file_text)
        self._file_history[path].append(file_text)

        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet,
            "a snippet of the edited file",
            max(1, insert_line - SNIPPET_LINES + 1),
        )
        success_msg += "Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary."
        return CLIResult(output=success_msg)

    def undo_edit(self, path: Path):
        """Implement the undo_edit command."""
        if not self._file_history[path]:
            raise ToolError(f"No edit history found for {path}.")

        old_text = self._file_history[path].pop()
        self.write_file(path, old_text)

        return CLIResult(
            output=f"Last edit to {path} undone successfully. {self._make_output(old_text, str(path))}"
        )

    def read_file(self, path: Path):
        """Read the content of a file from a given path; raise a ToolError if an error occurs."""
        try:
            return path.read_text()
        except Exception as e:
            raise ToolError(f"Ran into {e} while trying to read {path}") from None

    def write_file(self, path: Path, file: str):
        """Write the content of a file to a given path; raise a ToolError if an error occurs.
        Creates parent directories if they don't exist.
        """
        try:
            # Ensure the directory exists before writing the file
            directory = path.parent
            if directory and not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
            path.write_text(file)
        except Exception as e:
            raise ToolError(f"Ran into {e} while trying to write to {path}") from None

    def _make_output(
        self,
        file_content: str,
        file_descriptor: str,
        init_line: int = 1,
        expand_tabs: bool = True,
    ):
        """Generate output for the CLI based on the content of a file."""
        file_content = maybe_truncate(file_content)
        if expand_tabs:
            file_content = file_content.expandtabs()
        file_content = "\n".join(
            [
                f"{i + init_line:6}\t{line}"
                for i, line in enumerate(file_content.split("\n"))
            ]
        )
        return (
            f"Here's the result of running `cat -n` on {file_descriptor}:\n"
            + file_content
            + "\n"
        )

    def get_conversation_memory(self, path: Path, limit: int = 10):
        """Retrieve conversation memory for a specific path.

        Args:
            path: The path to retrieve conversation memory for
            limit: Maximum number of entries to return (most recent first)

        Returns:
            A list of conversation memory entries
        """
        if path not in self._conversation_memory:
            return []

        # Return the most recent entries first, limited by the limit parameter
        return list(reversed(self._conversation_memory[path][-limit:]))

    def clear_conversation_memory(self, path: Path = None):
        """Clear conversation memory.

        Args:
            path: The path to clear conversation memory for. If None, clear all conversation memory.
        """
        if path is None:
            self._conversation_memory.clear()
        elif path in self._conversation_memory:
            del self._conversation_memory[path]

    def get_conversation_summary(self, path: Path = None):
        """Generate a summary of conversation memory.

        Args:
            path: The path to generate a summary for. If None, generate a summary for all paths.

        Returns:
            A dictionary with summary information
        """
        summary = {}

        if path is not None:
            if path in self._conversation_memory:
                entries = self._conversation_memory[path]
                summary[str(path)] = {
                    "total_interactions": len(entries),
                    "commands": {cmd: sum(1 for e in entries if e["command"] == cmd) for cmd in get_args(Command)},
                }
        else:
            for path, entries in self._conversation_memory.items():
                summary[str(path)] = {
                    "total_interactions": len(entries),
                    "commands": {cmd: sum(1 for e in entries if e["command"] == cmd) for cmd in get_args(Command)},
                }

        return summary
