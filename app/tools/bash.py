import asyncio
import os
import platform
from typing import Optional

from app.exceptions import ToolError
from app.tool.base import BaseTool, CLIResult, ToolResult
from app.config import config


_BASH_DESCRIPTION = """Execute a bash command in the terminal.
* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.
* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.
* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.
"""


class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "powershell" if platform.system() == "Windows" else "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 300.0  # seconds (default, will be overridden by config)
    _sentinel: str = "<<exit>>"
    _data_file_extensions = [".csv", ".json", ".txt", ".xml", ".yaml", ".log", ".dat", ".tsv"]
    _data_processing_commands = ["cat", "grep", "awk", "sed", "sort", "uniq", "wc", "head", "tail", 
                               "cut", "paste", "join", "split", "csvsql", "jq", "xsv", "find"]

    def __init__(self):
        self._started = False
        self._timed_out = False
        # Get timeout from config if available
        try:
            # Access the bash_timeout from the config dictionary
            llm_config = config.llm.get("default", {})
            if hasattr(llm_config, "bash_timeout"):
                self._timeout = float(llm_config.bash_timeout)
            elif isinstance(llm_config, dict) and "bash_timeout" in llm_config:
                self._timeout = float(llm_config["bash_timeout"])
        except (AttributeError, ValueError, KeyError):
            # Fallback to default timeout if config not available
            pass
            
    def _is_data_processing(self, command: str) -> bool:
        """Determine if a command is likely processing data files"""
        if not command:
            return False
            
        command_lower = command.lower()
        
        # Check for data file extensions
        if any(ext in command_lower for ext in self._data_file_extensions):
            return True
            
        # Check for data processing commands
        if any(cmd + " " in command_lower for cmd in self._data_processing_commands):
            return True
            
        # Check for other data-related keywords
        data_keywords = ["process", "data", "parse", "extract", "transform", "analyze"]
        if any(keyword in command_lower for keyword in data_keywords):
            return True
            
        return False

    async def start(self):
        if self._started:
            return

        # Create subprocess with platform-specific options
        # os.setsid is only available on Unix-based systems
        if platform.system() == "Windows":
            self._process = await asyncio.create_subprocess_shell(
                self.command,
                shell=True,
                bufsize=0,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            # Unix-based systems can use os.setsid
            self._process = await asyncio.create_subprocess_shell(
                self.command,
                preexec_fn=os.setsid,
                shell=True,
                bufsize=0,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        self._started = True

    def stop(self):
        """Terminate the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """Execute a command in the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"bash has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            )

        # we know these are not None because we created the process with PIPEs
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr
        
        # Check if this is a data processing command that might take longer
        is_data_processing = self._is_data_processing(command)

        # send command to the process
        self._process.stdin.write(
            command.encode() + f"; echo '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # read output from the process, until the sentinel is found
        try:
            # Adjust timeout for data processing commands
            timeout_value = self._timeout * 2 if is_data_processing else self._timeout
            
            async with asyncio.timeout(timeout_value):
                while True:
                    await asyncio.sleep(self._output_delay)
                    # if we read directly from stdout/stderr, it will wait forever for
                    # EOF. use the StreamReader buffer directly instead.
                    output = (
                        self._process.stdout._buffer.decode()
                    )  # pyright: ignore[reportAttributeAccessIssue]
                    if self._sentinel in output:
                        # strip the sentinel and break
                        output = output[: output.index(self._sentinel)]
                        break
                    
                    # For data processing commands, check for progress indicators and reset timeout
                    if is_data_processing and any(indicator in output for indicator in [
                        "progress", "processing", "loading", "reading", "writing", "%", "bytes", "records", "lines", "files"
                    ]):
                        # Continue processing for data tasks showing progress
                        continue
                        
                    # Check if we're processing a large data file
                    if is_data_processing and len(output) > 1000:
                        # Large output likely means data processing is happening
                        # Continue to allow more time for completion
                        continue
        except asyncio.TimeoutError:
            # For data processing commands, try to gracefully handle timeout
            if is_data_processing:
                # Try to get partial output before timing out
                try:
                    output = self._process.stdout._buffer.decode()  # pyright: ignore[reportAttributeAccessIssue]
                    if output:
                        # For data processing commands, provide more helpful information
                        return CLIResult(
                            output=f"Command is still running (processing data). Partial output:\n{output}\n\nFor processing large data files, use the long_running_command tool instead of bash.",
                            error="Data processing timeout. The command is taking longer than expected. Consider using the long_running_command tool which has better support for data processing tasks."
                        )
                except Exception:
                    pass
                    
                # Even if we couldn't get output, provide a helpful message
                return CLIResult(
                    output="The data processing command timed out without producing output.",
                    error="For reliable data file processing, use the long_running_command tool instead of bash."
                )
                
            self._timed_out = True
            raise ToolError(
                f"timed out: bash has not returned in {timeout_value} seconds and must be restarted",
            ) from None

        if output.endswith("\n"):
            output = output[:-1]

        error = (
            self._process.stderr._buffer.decode()
        )  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # clear the buffers so that the next output can be read correctly
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


class Bash(BaseTool):
    """A tool for executing bash commands"""

    name: str = "bash"
    description: str = _BASH_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute. Can be empty to view additional logs when previous exit code is `-1`. Can be `ctrl+c` to interrupt the currently running process.",
            },
        },
        "required": ["command"],
    }

    _session: Optional[_BashSession] = None

    async def execute(
        self, command: str | None = None, restart: bool = False, **kwargs
    ) -> CLIResult:
        if restart:
            if self._session:
                self._session.stop()
            self._session = _BashSession()
            await self._session.start()

            return ToolResult(system="tool has been restarted.")

        if self._session is None:
            self._session = _BashSession()
            await self._session.start()
            
        # Check if this is a data file processing command
        if command and any(term in command.lower() for term in [
            "cat ", "grep ", "awk ", "sed ", "sort ", "uniq ", "wc ", "head ", "tail ", 
            "cut ", "paste ", "join ", "split ", "csvsql", "jq ", "xsv ", "find ", 
            ".csv", ".json", ".txt", ".xml", ".log", ".dat"
        ]):
            # For data processing commands, suggest using long_running_command for better reliability
            logger.info(f"Data file processing command detected: {command[:50]}...")
            # We'll still execute it, but with a warning in case it times out

        if command is not None:
            # If this is a data file processing command, add a warning to the result
            is_data_processing = command and any(term in command.lower() for term in [
                "cat ", "grep ", "awk ", "sed ", "sort ", "uniq ", "wc ", "head ", "tail ", 
                "cut ", "paste ", "join ", "split ", "csvsql", "jq ", "xsv ", "find ", 
                ".csv", ".json", ".txt", ".xml", ".log", ".dat"
            ])
            
            result = await self._session.run(command)
            
            # Add a helpful warning for data processing commands
            if is_data_processing and not result.error:
                result.output = result.output + "\n\nNote: For more reliable processing of data files, consider using the long_running_command tool instead of bash."
                
            return result

        raise ToolError("no command provided.")


if __name__ == "__main__":
    bash = Bash()
    rst = asyncio.run(bash.execute("ls -l"))
    print(rst)
