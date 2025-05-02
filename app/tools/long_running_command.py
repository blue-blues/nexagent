"""Utility to handle long-running commands with improved timeout handling."""

import asyncio
import os
import platform
import signal
from typing import Optional, Tuple

from app.exceptions import ToolError
from app.tools.base import BaseTool, CLIResult, ToolResult
from app.logger import logger


class LongRunningCommand(BaseTool):
    """A tool for executing long-running commands with improved timeout handling"""

    name: str = "long_running_command"
    description: str = """Execute a command that may take a long time to complete.
    This tool is designed to handle commands that might exceed the standard timeout.
    For commands that are expected to run for more than a few minutes, use this tool instead of bash.
    The command will be executed in the background and can be monitored for completion.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute. For long-running processes, consider redirecting output to a file.",
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in seconds. Default is 1800 (30 minutes). Set to 0 for no timeout.",
            },
            "background": {
                "type": "boolean",
                "description": "Run in background without waiting for completion. Default is False.",
            },
        },
        "required": ["command"],
    }

    _process: Optional[asyncio.subprocess.Process] = None
    _background_processes: dict = {}

    async def execute(
        self, 
        command: str, 
        timeout: float = 1800.0,  # 30 minutes default
        background: bool = False,
        **kwargs
    ) -> CLIResult:
        """Execute a command with extended timeout handling."""
        
        if background:
            return await self._execute_background(command)
        
        try:
            # Create subprocess
            if platform.system() == "Windows":
                self._process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                # Unix-based systems can use process groups
                self._process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=os.setsid,
                )

            # Wait for process with timeout
            if timeout > 0:
                try:
                    stdout, stderr = await asyncio.wait_for(self._process.communicate(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Command timed out after {timeout} seconds: {command}")
                    self._terminate_process()
                    return CLIResult(
                        output="",
                        error=f"Command timed out after {timeout} seconds. Consider running with background=True."
                    )
            else:
                # No timeout
                stdout, stderr = await self._process.communicate()
                
            return CLIResult(
                output=stdout.decode() if stdout else "",
                error=stderr.decode() if stderr else "",
            )
            
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return CLIResult(output="", error=f"Error: {str(e)}")
        finally:
            self._process = None
    
    async def _execute_background(self, command: str) -> CLIResult:
        """Execute a command in the background without waiting for completion."""
        try:
            # Generate a unique ID for this background process
            process_id = f"bg_{len(self._background_processes) + 1}_{id(command)}"
            
            # Start the process
            if platform.system() == "Windows":
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                # Unix-based systems can use process groups
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=os.setsid,
                )
            
            # Store the process
            self._background_processes[process_id] = {
                "process": process,
                "command": command,
                "started_at": asyncio.get_event_loop().time(),
            }
            
            # Start a task to collect output (but don't wait for it)
            asyncio.create_task(self._collect_background_output(process_id))
            
            return CLIResult(
                output=f"Command started in background with ID: {process_id}\nUse check_background_command tool with this ID to check status.",
                error="",
            )
            
        except Exception as e:
            logger.error(f"Error starting background command: {str(e)}")
            return CLIResult(output="", error=f"Error starting background command: {str(e)}")
    
    async def _collect_background_output(self, process_id: str) -> None:
        """Collect output from a background process."""
        if process_id not in self._background_processes:
            return
            
        process_info = self._background_processes[process_id]
        process = process_info["process"]
        
        try:
            stdout, stderr = await process.communicate()
            process_info["stdout"] = stdout.decode() if stdout else ""
            process_info["stderr"] = stderr.decode() if stderr else ""
            process_info["returncode"] = process.returncode
            process_info["completed"] = True
            process_info["completed_at"] = asyncio.get_event_loop().time()
        except Exception as e:
            process_info["stdout"] = ""
            process_info["stderr"] = f"Error collecting output: {str(e)}"
            process_info["returncode"] = -1
            process_info["completed"] = True
            process_info["completed_at"] = asyncio.get_event_loop().time()
    
    async def check_background_command(self, process_id: str) -> CLIResult:
        """Check the status of a background command."""
        if process_id not in self._background_processes:
            return CLIResult(
                output="",
                error=f"No background process found with ID: {process_id}",
            )
            
        process_info = self._background_processes[process_id]
        process = process_info["process"]
        
        # If process is already completed, return the stored output
        if process_info.get("completed", False):
            duration = process_info.get("completed_at", 0) - process_info.get("started_at", 0)
            return CLIResult(
                output=f"Command completed with exit code: {process_info.get('returncode')}\n"
                       f"Duration: {duration:.2f} seconds\n\n"
                       f"STDOUT:\n{process_info.get('stdout', '')}\n\n"
                       f"STDERR:\n{process_info.get('stderr', '')}",
                error="",
            )
        
        # Check if process is still running
        if process.returncode is None:
            duration = asyncio.get_event_loop().time() - process_info.get("started_at", 0)
            return CLIResult(
                output=f"Command still running (Duration: {duration:.2f} seconds)\nCommand: {process_info['command']}",
                error="",
            )
        else:
            # Process completed but output collection task hasn't updated the info yet
            # Wait a moment for the output collection task to complete
            await asyncio.sleep(0.5)
            
            # If still not marked as completed, do it now
            if not process_info.get("completed", False):
                try:
                    stdout, stderr = b"", b""
                    if hasattr(process, "stdout") and process.stdout:
                        stdout = await process.stdout.read()
                    if hasattr(process, "stderr") and process.stderr:
                        stderr = await process.stderr.read()
                        
                    process_info["stdout"] = stdout.decode() if stdout else ""
                    process_info["stderr"] = stderr.decode() if stderr else ""
                    process_info["returncode"] = process.returncode
                    process_info["completed"] = True
                    process_info["completed_at"] = asyncio.get_event_loop().time()
                except Exception as e:
                    process_info["stderr"] = f"Error collecting output: {str(e)}"
                    process_info["completed"] = True
                    process_info["completed_at"] = asyncio.get_event_loop().time()
            
            duration = process_info.get("completed_at", 0) - process_info.get("started_at", 0)
            return CLIResult(
                output=f"Command completed with exit code: {process_info.get('returncode')}\n"
                       f"Duration: {duration:.2f} seconds\n\n"
                       f"STDOUT:\n{process_info.get('stdout', '')}\n\n"
                       f"STDERR:\n{process_info.get('stderr', '')}",
                error="",
            )
    
    async def terminate_background_command(self, process_id: str) -> CLIResult:
        """Terminate a background command."""
        if process_id not in self._background_processes:
            return CLIResult(
                output="",
                error=f"No background process found with ID: {process_id}",
            )
            
        process_info = self._background_processes[process_id]
        process = process_info["process"]
        
        if process.returncode is not None:
            return CLIResult(
                output=f"Process already completed with exit code: {process.returncode}",
                error="",
            )
        
        # Terminate the process
        self._terminate_process(process)
        
        # Mark as completed
        process_info["completed"] = True
        process_info["completed_at"] = asyncio.get_event_loop().time()
        process_info["returncode"] = -9  # SIGKILL
        process_info["stderr"] = process_info.get("stderr", "") + "\nProcess terminated by user."
        
        return CLIResult(
            output=f"Process {process_id} terminated.",
            error="",
        )
    
    def _terminate_process(self, process=None):
        """Terminate a process with proper signal handling."""
        if process is None:
            process = self._process
            
        if process is None or process.returncode is not None:
            return
            
        try:
            if platform.system() == "Windows":
                # Windows doesn't have SIGTERM, use terminate()
                process.terminate()
            else:
                # On Unix, send SIGTERM to the process group
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)
                
            # Give it a moment to terminate gracefully
            asyncio.create_task(self._force_kill_after_delay(process))
        except Exception as e:
            logger.error(f"Error terminating process: {str(e)}")
    
    async def _force_kill_after_delay(self, process, delay=5.0):
        """Force kill a process after a delay if it hasn't terminated."""
        try:
            # Wait for the process to terminate gracefully
            try:
                await asyncio.wait_for(process.wait(), timeout=delay)
                return  # Process terminated gracefully
            except asyncio.TimeoutError:
                pass  # Process didn't terminate, force kill it
                
            # Force kill
            if platform.system() == "Windows":
                process.kill()
            else:
                try:
                    pgid = os.getpgid(process.pid)
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    # Process already terminated
                    pass
        except Exception as e:
            logger.error(f"Error in force kill: {str(e)}")