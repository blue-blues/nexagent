from typing import List, Optional, Dict, Any
import asyncio
import platform
from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.tools import ToolCollection
from app.tools.terminal import Bash
from app.tools.code import StrReplaceEditor, PythonExecute, CodeAnalyzer
from app.tools.terminate import Terminate
from app.tools.enhanced_browser_tool import EnhancedBrowserTool
from app.tools.browser import WebSearch
from app.tools.long_running_command import LongRunningCommand
from app.schema import Message
from app.logger import logger

SYSTEM_PROMPT = """
You are CodeAssist, an advanced AI software development assistant capable of writing, debugging, optimizing, and executing code across multiple programming languages.

Your capabilities include:
1. Intelligent Code Generation & Optimization
2. Autonomous Debugging & Error Resolution
3. Execution & Environment Management
4. Software Architecture & Design
5. API Integration & External Tool Usage
6. Automated Testing & CI/CD Integration
7. Real-Time Collaboration

You have access to various tools to accomplish these tasks, including file editing, command execution, web search, and more.

Always approach problems systematically:
1. Understand the requirements thoroughly
2. Plan your approach before implementation
3. Execute the plan step by step
4. Verify and test your solution
5. Suggest improvements or next steps
"""

NEXT_STEP_TEMPLATE = """
{{observation}}

Current working directory: {{working_dir}}
Open files: {{open_files}}

What would you like me to do next?
"""

class SoftwareDevAgent(ToolCallAgent):
    """
    An advanced AI-powered software development assistant capable of writing, debugging,
    optimizing, and executing code across multiple programming languages.
    """

    name: str = "software_dev"
    description: str = "An advanced AI-powered software development assistant"
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_TEMPLATE
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            Bash(),
            StrReplaceEditor(),
            PythonExecute(),
            EnhancedBrowserTool(),
            WebSearch(),
            CodeAnalyzer(),
            LongRunningCommand(),
            Terminate()
        )
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
    max_steps: int = 50
    max_observe: int = 5000
    bash: Bash = Field(default_factory=Bash)
    working_dir: str = "."
    open_files: List[str] = Field(default_factory=list)
    language_context: Optional[str] = None
    project_structure: Dict[str, Any] = Field(default_factory=dict)
    error_history: List[Dict[str, Any]] = Field(default_factory=list)
    # Add websocket attribute with default None to prevent attribute errors
    websocket: Optional[Any] = None

    async def think(self) -> bool:
        """Process current state and decide next actions for software development tasks"""
        try:
            # Use platform-appropriate command to get current working directory
            # 'pwd' for Unix-like systems, 'cd' for Windows
            cwd_command = "cd" if platform.system() == "Windows" else "pwd"

            # Add timeout and error handling for working directory command
            self.working_dir = await asyncio.wait_for(
                self.execute_command(cwd_command),
                timeout=10  # 10 seconds timeout for pwd command
            )
        except asyncio.TimeoutError as e:
            logger.warning(f"Timeout while getting working directory: {str(e)}")
            self.working_dir = "<unknown>"  # Fallback value if pwd times out
        except Exception as e:
            logger.warning(f"Failed to get working directory: {str(e)}")
            # Store error details for better debugging
            error_info = {"command": cwd_command, "error": str(e), "context": "getting working directory"}
            self.error_history.append(error_info)
            self.working_dir = "<unknown>"  # Fallback value if pwd fails

        formatted_prompt = self.next_step_prompt.format(
            working_dir=self.working_dir,
            open_files=", ".join(self.open_files) if self.open_files else "None"
        )
        user_msg = Message.user_message(formatted_prompt)
        self.messages.append(user_msg)
        return await super().think()

    async def detect_programming_language(self, code_snippet: str) -> str:
        """Detect the programming language of a code snippet"""
        if "def " in code_snippet and (":" in code_snippet or "import " in code_snippet):
            return "python"
        elif "{" in code_snippet and (";" in code_snippet or "function" in code_snippet):
            if "<" in code_snippet and ">" in code_snippet and ("component" in code_snippet or "render" in code_snippet):
                return "jsx/tsx"
            elif "console.log" in code_snippet or "const " in code_snippet or "let " in code_snippet:
                return "javascript"
            elif "public class" in code_snippet or "private" in code_snippet:
                return "java"
            else:
                return "c/c++"
        elif "<" in code_snippet and ">" in code_snippet and ("<div" in code_snippet or "<p" in code_snippet):
            return "html"
        elif "@" in code_snippet and ("margin" in code_snippet or "padding" in code_snippet):
            return "css"
        return "unknown"

    async def analyze_error(self, error_message: str) -> Dict[str, Any]:
        """Analyze an error message and suggest potential fixes"""
        error_info = {"message": error_message, "type": "unknown", "suggestions": []}
        if "ModuleNotFoundError" in error_message or "ImportError" in error_message:
            error_info["type"] = "dependency"
            module_name = error_message.split("'")
            if len(module_name) > 1:
                module = module_name[1]
                error_info["suggestions"].append(f"Install missing module: pip install {module}")
        elif "SyntaxError" in error_message:
            error_info["type"] = "syntax"
            error_info["suggestions"].extend([
                "Check for missing parentheses, brackets, or quotes",
                "Verify proper indentation in the code"
            ])
        elif "TypeError" in error_message:
            error_info["type"] = "type"
            error_info["suggestions"].extend([
                "Check the data types of variables being used",
                "Ensure function arguments match expected types"
            ])
        elif "IndexError" in error_message or "KeyError" in error_message:
            error_info["type"] = "access"
            error_info["suggestions"].extend([
                "Verify that the index or key exists before accessing it",
                "Add proper error handling for missing indices or keys"
            ])
        self.error_history.append(error_info)
        return error_info

    async def run(self, prompt: str) -> str:
        """Run the software development agent with the given prompt"""
        if any(term in prompt.lower() for term in [
            "code", "program", "script", "function", "class", "bug", "error",
            "debug", "fix", "implement", "develop", "build", "create", "write"
        ]):
            for lang in ["python", "javascript", "java", "c++", "html", "css", "typescript"]:
                if lang in prompt.lower():
                    self.language_context = lang
                    break

        # Reset error history for new run
        self.error_history = []

        # Check if this is a book-related task
        if any(term in prompt.lower() for term in ["book", "table", "list", "catalog", "library"]):
            logger.info(f"📚 Detected book-related task, will use optimized data processing")

        logger.info(f"🚀 Starting software development task: {prompt[:50]}...")

        # Set a global timeout for the entire task
        try:
            return await asyncio.wait_for(
                super().run(prompt),
                timeout=1800  # 30 minutes max for any task
            )
        except asyncio.TimeoutError:
            logger.error(f"Task timed out after 30 minutes: {prompt[:50]}...")
            return "The task timed out after 30 minutes. Please try breaking it down into smaller steps or provide more specific instructions."

    async def execute_command(self, command: str) -> str:
        """Execute a command, automatically choosing between bash and long_running_command based on the nature of the command"""
        # Check if this is likely a long-running command
        is_long_running = self._is_long_running_command(command)

        # Add progress tracking
        start_time = asyncio.get_event_loop().time()
        progress_marker = 0

        async def log_progress():
            nonlocal progress_marker
            while True:
                await asyncio.sleep(5)  # Log progress every 5 seconds
                elapsed = asyncio.get_event_loop().time() - start_time
                progress_marker += 1
                logger.info(f"Command still running ({elapsed:.1f}s): {command[:50]}... [progress marker: {progress_marker}]")

        # Initialize progress_task outside the try block
        progress_task = None

        try:
            # Start progress tracking task
            progress_task = asyncio.create_task(log_progress())

            if is_long_running:
                logger.info(f"Using long_running_command for potentially long-running operation: {command[:50]}...")
                try:
                    result = await self.available_tools.execute(
                        name="long_running_command",
                        tool_input={"command": command, "timeout": 1800}  # 30 minutes timeout
                    )
                except Exception as e:
                    error_info = {
                        "command": command,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "context": "long_running_command execution"
                    }
                    self.error_history.append(error_info)
                    logger.error(f"Error in long_running_command '{command[:50]}...': {type(e).__name__}: {str(e)}")
                    raise  # Re-raise to be caught by outer try block
            else:
                logger.info(f"Using bash for command: {command[:50]}...")
                # Set a timeout for bash commands to prevent hanging
                try:
                    # Use asyncio.wait_for to add an additional timeout safety net
                    result = await asyncio.wait_for(
                        self.bash.execute(command),
                        timeout=60  # 60 seconds timeout for regular bash commands
                    )
                except asyncio.TimeoutError as e:
                    logger.warning(f"Bash command timed out, falling back to long_running_command: {command[:50]}...")
                    error_info = {
                        "command": command,
                        "error": "Bash command timed out",
                        "error_type": "TimeoutError",
                        "context": "bash execution timeout"
                    }
                    self.error_history.append(error_info)

                    # If bash times out, fall back to long_running_command
                    try:
                        result = await self.available_tools.execute(
                            name="long_running_command",
                            tool_input={"command": command, "timeout": 300}  # 5 minutes timeout
                        )
                    except Exception as fallback_error:
                        error_info = {
                            "command": command,
                            "error": str(fallback_error),
                            "error_type": type(fallback_error).__name__,
                            "context": "fallback to long_running_command"
                        }
                        self.error_history.append(error_info)
                        logger.error(f"Fallback to long_running_command failed: {type(fallback_error).__name__}: {str(fallback_error)}")
                        raise  # Re-raise to be caught by outer try block
                except Exception as e:
                    error_info = {
                        "command": command,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "context": "bash execution"
                    }
                    self.error_history.append(error_info)
                    logger.error(f"Error in bash execution '{command[:50]}...': {type(e).__name__}: {str(e)}")
                    raise  # Re-raise to be caught by outer try block

            # Check if the result indicates a timeout or error
            result_str = str(result)
            if "timed out" in result_str.lower() or "timeout" in result_str.lower():
                logger.warning(f"Command execution timed out: {command[:50]}...")
                # Store error details for better debugging
                error_info = {"command": command, "error": "Command timed out", "context": "execution timeout"}
                self.error_history.append(error_info)
                return f"Command timed out: {command}. Please try a different approach or break down the task."

            return result.output if hasattr(result, "output") else str(result)

        except Exception as e:
            # Store detailed error information for debugging
            error_info = {
                "command": command,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": "command execution"
            }
            self.error_history.append(error_info)

            # Log the error with more context
            logger.error(f"Error executing command '{command[:50]}...': {type(e).__name__}: {str(e)}")
            return f"Error executing command: {str(e)}. Please try a different approach."

        finally:
            # Cancel progress tracking if it exists and is still running
            if progress_task and not progress_task.done():
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

    def _is_long_running_command(self, command: str) -> bool:
        """Determine if a command is likely to be long-running"""
        if not command:
            return False

        command_lower = command.lower()

        # Book-related commands that might involve large data processing
        if any(term in command_lower for term in ["book", "table", "list", "catalog", "library", "database", "csv", "excel", "spreadsheet"]):
            logger.info(f"Detected book-related command that might be long-running: {command[:50]}...")
            return True

        # Data processing commands
        data_processing_commands = ["cat ", "grep ", "awk ", "sed ", "sort ", "uniq ", "wc ", "head ", "tail ",
                                  "cut ", "paste ", "join ", "split ", "csvsql", "jq ", "xsv ", "find "]
        if any(cmd in command_lower for cmd in data_processing_commands):
            return True

        # Data file extensions
        data_file_extensions = [".csv", ".json", ".txt", ".xml", ".yaml", ".log", ".dat", ".tsv"]
        if any(ext in command_lower for ext in data_file_extensions):
            return True

        # Build and installation commands
        build_commands = ["npm install", "pip install", "yarn", "gradle", "maven", "make", "cmake",
                         "build", "compile", "install", "setup.py", "configure"]
        if any(cmd in command_lower for cmd in build_commands):
            return True

        # Download and network commands
        network_commands = ["wget", "curl", "download", "clone", "fetch", "pull", "push"]
        if any(cmd in command_lower for cmd in network_commands):
            return True

        # Test and analysis commands
        test_commands = ["test", "pytest", "unittest", "jest", "mocha", "cypress", "selenium",
                        "analyze", "benchmark", "profile"]
        if any(cmd in command_lower for cmd in test_commands):
            return True

        return False