import asyncio
import os
import shlex
from typing import Optional, Dict, Any
from colorama import init, Fore, Back, Style
from tqdm import tqdm
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import FormattedText

from app.tool.base import BaseTool, CLIResult

# Initialize colorama for Windows support
init()

class EnhancedTerminal(BaseTool):
    name: str = "execute_command"
    description: str = """
    Enhanced terminal interface with colorful output, progress indicators, and interactive suggestions.
    Features:
    - Colorful output formatting for better readability
    - Interactive command suggestions
    - Progress indicators for long-running operations
    - Enhanced error messages with descriptive formatting
    - Command history support
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "(required) The CLI command to execute. This should be valid for the current operating system.",
            }
        },
        "required": ["command"],
    }
    
    # Define class attributes for Pydantic
    process: Optional[asyncio.subprocess.Process] = None
    current_path: str = ""
    lock: asyncio.Lock = None
    command_history: list = []
    session: Any = None
    command_completer: Any = None
    
    def __init__(self):
        super().__init__()
        self.process: Optional[asyncio.subprocess.Process] = None
        self.current_path: str = os.getcwd()
        self.lock: asyncio.Lock = asyncio.Lock()
        self.command_history: list = []
        self.session = PromptSession()
        
        # Common command suggestions
        self.command_completer = WordCompleter([
            'cd', 'dir', 'ls', 'copy', 'move', 'del', 'mkdir', 'rmdir',
            'echo', 'type', 'more', 'find', 'where', 'help'
        ])
    
    def _format_success(self, message: str) -> str:
        return f"{Fore.GREEN}{message}{Style.RESET_ALL}"
    
    def _format_error(self, message: str) -> str:
        return f"{Fore.RED}{Back.WHITE}{message}{Style.RESET_ALL}"
    
    def _format_info(self, message: str) -> str:
        return f"{Fore.CYAN}{message}{Style.RESET_ALL}"
    
    def _format_warning(self, message: str) -> str:
        return f"{Fore.YELLOW}{message}{Style.RESET_ALL}"
    
    def _format_path(self, path: str) -> str:
        return f"{Fore.BLUE}{Style.BRIGHT}{path}{Style.RESET_ALL}"
    
    async def execute(self, command: str) -> CLIResult:
        """Execute a terminal command with enhanced output formatting."""
        commands = [cmd.strip() for cmd in command.split("&") if cmd.strip()]
        final_output = CLIResult(output="", error="")
        
        for cmd in commands:
            sanitized_command = self._sanitize_command(cmd)
            self.command_history.append(sanitized_command)
            
            if sanitized_command.lstrip().startswith("cd "):
                result = await self._handle_cd_command(sanitized_command)
            else:
                async with self.lock:
                    try:
                        # Show progress for long-running commands
                        with tqdm(total=100, desc=self._format_info("Executing command")) as pbar:
                            self.process = await asyncio.create_subprocess_shell(
                                sanitized_command,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                                cwd=self.current_path,
                            )
                            stdout, stderr = await self.process.communicate()
                            pbar.update(100)
                        
                        result = CLIResult(
                            output=self._format_success(stdout.decode().strip()),
                            error=self._format_error(stderr.decode().strip()) if stderr else "",
                        )
                    except Exception as e:
                        result = CLIResult(
                            output="",
                            error=self._format_error(f"Error executing command: {str(e)}")
                        )
                    finally:
                        self.process = None
            
            # Combine outputs with formatting
            if result.output:
                final_output.output += (
                    (result.output + "\n") if final_output.output else result.output
                )
            if result.error:
                final_output.error += (
                    (result.error + "\n") if final_output.error else result.error
                )
        
        # Remove trailing newlines while preserving formatting
        final_output.output = final_output.output.rstrip()
        final_output.error = final_output.error.rstrip()
        return final_output
    
    async def _handle_cd_command(self, command: str) -> CLIResult:
        """Handle 'cd' commands with enhanced path display."""
        try:
            parts = shlex.split(command)
            if len(parts) < 2:
                new_path = os.path.expanduser("~")
            else:
                new_path = os.path.expanduser(parts[1])
            
            if not os.path.isabs(new_path):
                new_path = os.path.join(self.current_path, new_path)
            
            new_path = os.path.abspath(new_path)
            
            if os.path.isdir(new_path):
                self.current_path = new_path
                return CLIResult(
                    output=self._format_success(
                        f"Changed directory to {self._format_path(self.current_path)}"
                    ),
                    error=""
                )
            else:
                return CLIResult(
                    output="",
                    error=self._format_error(f"No such directory: {self._format_path(new_path)}")
                )
        except Exception as e:
            return CLIResult(
                output="",
                error=self._format_error(f"Error changing directory: {str(e)}")
            )
    
    @staticmethod
    def _sanitize_command(command: str) -> str:
        """Sanitize the command with enhanced security checks."""
        dangerous_commands = ["rm", "sudo", "shutdown", "reboot", "format"]
        try:
            parts = shlex.split(command)
            if any(cmd in dangerous_commands for cmd in parts):
                raise ValueError(
                    "Security Warning: Use of potentially dangerous commands is restricted."
                )
        except Exception:
            if any(cmd in command for cmd in dangerous_commands):
                raise ValueError(
                    "Security Warning: Use of potentially dangerous commands is restricted."
                )
        return command
    
    async def close(self):
        """Close the terminal session with cleanup."""
        async with self.lock:
            if self.process:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
                finally:
                    self.process = None
                    print(self._format_info("Terminal session closed successfully."))
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()