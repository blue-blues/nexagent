import multiprocessing
import sys
import re
import time
from io import StringIO
from typing import Dict, List, Optional, Tuple, Union, ClassVar, Any

from app.tool.base import BaseTool
from app.logger import logger
from app.sandbox.code_sandbox import default_code_sandbox
from app.timeline.timeline import Timeline
from app.timeline import events as timeline_events


class PythonExecute(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions."""

    name: str = "python_execute"
    description: str = "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results. Shell commands will not be executed."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Execution timeout in seconds. Default is 5 seconds.",
                "default": 5
            },
        },
        "required": ["code"],
    }

    # Timeline for tracking execution events
    timeline: Optional[Timeline] = None

    # List of approved models that can be used
    APPROVED_MODELS: ClassVar[List[str]] = [
        "deepseek-ai/DeepSeek-R1",
        "meta-llama/Llama-2",
        "mistralai/Mistral",
        "anthropic/claude",
        "openai/gpt-4",
        "openai/gpt-3.5-turbo",
        "google/gemini",
        "google/palm"
    ]

    # Shell command patterns to detect
    SHELL_COMMAND_PATTERNS: ClassVar[List[str]] = [
        r"^\s*pip\s+install",
        r"^\s*apt\s+get",
        r"^\s*apt-get",
        r"^\s*yum\s+install",
        r"^\s*brew\s+install",
        r"^\s*npm\s+install",
        r"^\s*conda\s+install",
        r"^\s*docker\s+",
        r"^\s*wget\s+",
        r"^\s*curl\s+",
        r"^\s*git\s+",
        r"^\s*cd\s+",
        r"^\s*mkdir\s+",
        r"^\s*rm\s+",
        r"^\s*mv\s+",
        r"^\s*cp\s+"
    ]

    def _is_shell_command(self, code: str) -> bool:
        """Check if the code contains shell commands."""
        # Check each line for shell command patterns
        for line in code.split('\n'):
            for pattern in self.SHELL_COMMAND_PATTERNS:
                if re.match(pattern, line):
                    return True
        return False

    def _validate_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate Python code syntax."""
        try:
            compile(code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def _check_for_unapproved_models(self, code: str) -> Tuple[bool, Optional[str]]:
        """Check if code references models not in the approved list."""
        # Common model loading patterns
        model_patterns = [
            r'from\s+transformers\s+import.*AutoModel.*\s+model\s*=\s*AutoModel\w*\.from_pretrained\(\s*["\'](.*?)["\']',
            r'AutoModel\w*\.from_pretrained\(\s*["\'](.*?)["\']',
            r'from_pretrained\(\s*["\'](.*?)["\']',
            r'model\s*=\s*["\'](.*?)["\']',
            r'model_name\s*=\s*["\'](.*?)["\']',
            r'model_id\s*=\s*["\'](.*?)["\']'
        ]

        for pattern in model_patterns:
            matches = re.findall(pattern, code)
            for match in matches:
                # Check if the matched model name is in the approved list
                if match and not any(approved in match for approved in self.APPROVED_MODELS):
                    return False, match

        return True, None

    def _run_code(self, code: str, result_dict: dict, safe_globals: dict) -> None:
        original_stdout = sys.stdout
        try:
            output_buffer = StringIO()
            sys.stdout = output_buffer
            exec(code, safe_globals, safe_globals)
            result_dict["observation"] = output_buffer.getvalue()
            result_dict["success"] = True
            result_dict["error_type"] = None
        except Exception as e:
            result_dict["observation"] = str(e)
            result_dict["success"] = False

            # Categorize the error type
            error_type = type(e).__name__
            result_dict["error_type"] = error_type

            # Check for specific error types
            if "rate limit" in str(e).lower() or "resource exhausted" in str(e).lower():
                result_dict["error_type"] = "RateLimitError"
            elif "timeout" in str(e).lower() or "timed out" in str(e).lower():
                result_dict["error_type"] = "TimeoutError"
        finally:
            sys.stdout = original_stdout

    def __init__(self):
        super().__init__()
        # Get timeout from config if available
        from app.config import config
        self._default_timeout = 5  # Default timeout in seconds
        if hasattr(config, "llm") and hasattr(config.llm, "python_execute_timeout"):
            self._default_timeout = int(config.llm.python_execute_timeout)
        elif hasattr(config, "llm") and isinstance(config.llm, dict) and "python_execute_timeout" in config.llm:
            self._default_timeout = int(config.llm["python_execute_timeout"])
        logger.info(f"Python execute timeout set to {self._default_timeout} seconds")

        # Initialize timeline for tracking execution events
        self.timeline = Timeline()

    async def execute(
        self,
        code: str,
        timeout: int = None,
        retry_count: int = 0,
        max_retries: int = 2,
        timeline: Optional[Timeline] = None
    ) -> Dict:
        """
        Executes the provided Python code with a timeout and safety checks.

        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds. If None, uses the configured default timeout.
            retry_count (int): Current retry attempt (internal use).
            max_retries (int): Maximum number of retry attempts for certain errors.

        Returns:
            Dict: Contains 'output' with execution output or error message and 'success' status.
        """
        # Use default timeout if none provided
        if timeout is None:
            timeout = self._default_timeout

        # Use the provided timeline or the instance timeline
        active_timeline = timeline or self.timeline

        # Create a code execution event in the timeline
        execution_event = timeline_events.create_code_execution_event(
            active_timeline,
            code,
            language="python"
        )

        try:
            # Check if the code contains shell commands
            if self._is_shell_command(code):
                logger.warning("Shell command detected in Python execution")
                error_msg = "⚠️ Shell command detected. Please execute shell commands externally or use the appropriate shell execution tool. Python execution tool only accepts valid Python code."
                execution_event.mark_error(error_msg)
                return {
                    "observation": error_msg,
                    "success": False,
                    "error_type": "ShellCommandError"
                }

            # Validate Python syntax
            is_valid, syntax_error = self._validate_syntax(code)
            if not is_valid:
                logger.warning(f"Python syntax error: {syntax_error}")
                error_msg = f"⚠️ Python syntax error: {syntax_error}\nPlease fix the syntax before execution."
                execution_event.mark_error(error_msg)
                return {
                    "observation": error_msg,
                    "success": False,
                    "error_type": "SyntaxError"
                }

            # Check for unapproved models
            is_approved, unapproved_model = self._check_for_unapproved_models(code)
            if not is_approved:
                warning_msg = f"⚠️ Warning: The code references an unapproved model: '{unapproved_model}'. "
                warning_msg += f"Please use one of the approved models: {', '.join(self.APPROVED_MODELS)}"
                logger.warning(f"Unapproved model detected: {unapproved_model}")
                execution_event.mark_error(warning_msg)
                return {
                    "observation": warning_msg,
                    "success": False,
                    "error_type": "UnapprovedModelError"
                }

            # Adjust timeout for model loading operations
            if "from_pretrained" in code or "download" in code or "load_model" in code:
                original_timeout = timeout
                # Increase timeout for model operations if it's too low
                if timeout < 30:
                    timeout = max(30, timeout * 2)
                    logger.info(f"Increased timeout from {original_timeout}s to {timeout}s for model operations")

            # Execute the code in the sandbox
            logger.info(f"Executing Python code in sandbox with timeout {timeout}s")
            result_dict = await default_code_sandbox.execute(code, timeout=timeout)

            # Handle specific error types and implement retry logic
            if not result_dict["success"] and retry_count < max_retries:
                error_type = result_dict.get("error_type")

                # Handle rate limit errors with exponential backoff
                if error_type == "RateLimitError":
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Rate limit encountered. Waiting {wait_time}s before retry {retry_count+1}/{max_retries}")
                    time.sleep(wait_time)
                    return await self.execute(code, timeout, retry_count + 1, max_retries, active_timeline)

                # Handle timeout errors by increasing timeout
                elif error_type == "TimeoutError":
                    new_timeout = timeout * 2
                    logger.info(f"Timeout error. Increasing timeout to {new_timeout}s for retry {retry_count+1}/{max_retries}")
                    return await self.execute(code, new_timeout, retry_count + 1, max_retries, active_timeline)

            # Add helpful context to error messages
            if not result_dict["success"] and result_dict.get("error_type"):
                error_msg = result_dict.get("error", result_dict.get("stderr", ""))
                error_type = result_dict.get("error_type")

                if error_type == "RateLimitError":
                    result_dict["observation"] = f"⚠️ API rate limit exceeded: {error_msg}\nPlease wait a few minutes before trying again or adjust your quota settings."
                elif "ModuleNotFoundError" in error_msg:
                    module_match = re.search(r"No module named '(.*?)'", error_msg)
                    if module_match:
                        module_name = module_match.group(1)
                        result_dict["observation"] = f"⚠️ Module not found: {error_msg}\nPlease install the required module '{module_name}' using your terminal with 'pip install {module_name}' before running this code."
                elif "ImportError" in error_msg:
                    result_dict["observation"] = f"⚠️ Import error: {error_msg}\nPlease ensure all required dependencies are installed correctly."
                elif "MemoryError" in error_msg:
                    result_dict["observation"] = f"⚠️ Memory error: {error_msg}\nThe code is trying to use more memory than available. Consider reducing the size of data being processed."
                elif "PermissionError" in error_msg:
                    result_dict["observation"] = f"⚠️ Permission error: {error_msg}\nThe code is trying to access resources without proper permissions."
                elif "FileNotFoundError" in error_msg:
                    result_dict["observation"] = f"⚠️ File not found: {error_msg}\nPlease check that the file path is correct and the file exists."
                elif "ZeroDivisionError" in error_msg:
                    result_dict["observation"] = f"⚠️ Zero division error: {error_msg}\nThe code is attempting to divide by zero. Please check your calculations."
                elif "KeyError" in error_msg or "IndexError" in error_msg:
                    result_dict["observation"] = f"⚠️ Access error: {error_msg}\nThe code is trying to access a key or index that doesn't exist. Please check your data structures."
                elif "ValueError" in error_msg:
                    result_dict["observation"] = f"⚠️ Value error: {error_msg}\nThe code is using an inappropriate value. Please check your inputs."
                elif "TypeError" in error_msg:
                    result_dict["observation"] = f"⚠️ Type error: {error_msg}\nThe code is using incompatible types. Please check your variable types."
                elif "SecurityError" in error_msg:
                    result_dict["observation"] = f"⚠️ Security error: {error_msg}\nThe code contains potentially unsafe operations that are not allowed in the sandbox."

            # Combine stdout and stderr for the final observation if not already set
            if "observation" not in result_dict:
                stdout = result_dict.get("stdout", "")
                stderr = result_dict.get("stderr", "")
                result_dict["observation"] = stdout
                if stderr:
                    if stdout:
                        result_dict["observation"] += "\n\nErrors/Warnings:\n" + stderr
                    else:
                        result_dict["observation"] = stderr

            # Update the timeline event with the result
            if result_dict["success"]:
                execution_event.mark_success(result_dict["observation"])
            else:
                execution_event.mark_error(result_dict.get("error", result_dict.get("observation", "Unknown error")))

            return result_dict
        except Exception as e:
            # Handle any unexpected exceptions
            logger.error(f"Unexpected error in Python execution: {str(e)}")
            execution_event.mark_error(str(e))
            return {
                "observation": f"⚠️ Unexpected error during execution: {str(e)}",
                "success": False,
                "error_type": type(e).__name__
            }
