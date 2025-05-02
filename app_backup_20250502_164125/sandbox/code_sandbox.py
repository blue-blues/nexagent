"""
Sandboxed code execution environment.

This module provides a secure environment for executing untrusted code
with resource limits and security restrictions.
"""

import ast
import builtins
import contextlib
import io
import multiprocessing
import os
import platform
import signal
import sys
import time
from typing import Dict, List, Optional, Tuple, Any, Set

from app.logger import logger

# Check if we're on Windows
IS_WINDOWS = platform.system() == "Windows"

# Import resource module only on Unix systems
if not IS_WINDOWS:
    import resource


# List of allowed built-in functions
ALLOWED_BUILTINS = {
    # Basic functions
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
    'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter', 'float',
    'format', 'frozenset', 'hash', 'hex', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'oct', 'ord',
    'pow', 'print', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
    'sorted', 'str', 'sum', 'tuple', 'type', 'zip',

    # Type conversion
    'bool', 'int', 'float', 'complex', 'str', 'list', 'tuple', 'dict', 'set',
    'frozenset', 'bytes', 'bytearray',

    # Constants
    'True', 'False', 'None',

    # Exception handling
    'Exception', 'TypeError', 'ValueError', 'RuntimeError', 'KeyError',
    'IndexError', 'AttributeError', 'ZeroDivisionError',
}

# List of allowed modules
ALLOWED_MODULES = {
    # Standard library modules
    'math', 'random', 'datetime', 'collections', 'itertools', 'functools',
    'operator', 'string', 're', 'json', 'csv', 'io', 'typing',

    # Data processing modules
    'numpy', 'pandas',

    # Visualization modules
    'matplotlib', 'seaborn', 'plotly',
}

# Default resource limits
DEFAULT_RESOURCE_LIMITS = {
    'cpu_time': 5,  # seconds
    'memory': 100 * 1024 * 1024,  # 100 MB
    'file_size': 1024 * 1024,  # 1 MB
    'processes': 1,
}


class CodeSandbox:
    """
    A sandbox for executing untrusted code with security restrictions.

    This class provides methods for safely executing Python code with
    resource limits and security restrictions.
    """

    def __init__(
        self,
        allowed_builtins: Optional[Set[str]] = None,
        allowed_modules: Optional[Set[str]] = None,
        resource_limits: Optional[Dict[str, int]] = None
    ):
        """
        Initialize the code sandbox with security settings.

        Args:
            allowed_builtins: Set of allowed built-in functions
            allowed_modules: Set of allowed modules
            resource_limits: Resource limits for code execution
        """
        self.allowed_builtins = allowed_builtins or ALLOWED_BUILTINS
        self.allowed_modules = allowed_modules or ALLOWED_MODULES
        self.resource_limits = resource_limits or DEFAULT_RESOURCE_LIMITS

    def _is_safe_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Check if the code is safe to execute.

        Args:
            code: The Python code to check

        Returns:
            A tuple of (is_safe, reason) where reason is None if the code is safe
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"

        # Check for potentially dangerous operations
        for node in ast.walk(tree):
            # Check for imports
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name.split('.')[0] not in self.allowed_modules:
                        return False, f"Import of disallowed module: {name.name}"

            # Check for from ... import ...
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] not in self.allowed_modules:
                    return False, f"Import from disallowed module: {node.module}"

            # Check for exec or eval
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ('exec', 'eval', 'compile', '__import__'):
                    return False, f"Use of {node.func.id}() is not allowed"

            # Check for attribute access on disallowed modules
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == 'os' and node.attr in ('system', 'popen', 'spawn', 'exec'):
                    return False, f"Use of os.{node.attr} is not allowed"
                if node.value.id == 'subprocess':
                    return False, "Use of subprocess module is not allowed"

        return True, None

    def _create_safe_globals(self) -> Dict[str, Any]:
        """
        Create a safe globals dictionary for code execution.

        Returns:
            A dictionary of safe global variables
        """
        # Start with a clean globals dictionary
        safe_globals = {}

        # Add allowed builtins
        safe_builtins = {}
        for name in self.allowed_builtins:
            if hasattr(builtins, name):
                safe_builtins[name] = getattr(builtins, name)

        safe_globals['__builtins__'] = safe_builtins

        # Add allowed modules
        for module_name in self.allowed_modules:
            try:
                module = __import__(module_name)
                safe_globals[module_name] = module
            except ImportError:
                # Skip modules that aren't available
                pass

        return safe_globals

    def _set_resource_limits(self):
        """Set resource limits for the current process."""
        # Skip resource limits on Windows
        if IS_WINDOWS:
            logger.warning("Resource limits not supported on Windows. Running without limits.")
            return

        # Set CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (self.resource_limits['cpu_time'], self.resource_limits['cpu_time']))

        # Set memory limit
        resource.setrlimit(resource.RLIMIT_AS, (self.resource_limits['memory'], self.resource_limits['memory']))

        # Set file size limit
        resource.setrlimit(resource.RLIMIT_FSIZE, (self.resource_limits['file_size'], self.resource_limits['file_size']))

        # Set process limit
        if hasattr(resource, 'RLIMIT_NPROC'):
            resource.setrlimit(resource.RLIMIT_NPROC, (self.resource_limits['processes'], self.resource_limits['processes']))

    def _execute_in_subprocess(self, code: str, result_dict: Dict[str, Any]):
        """
        Execute code in a subprocess with resource limits.

        Args:
            code: The Python code to execute
            result_dict: A shared dictionary to store the result
        """
        try:
            # Set resource limits (only works on Unix systems)
            self._set_resource_limits()

            # Set a timeout using signal (not reliable on Windows, but we'll use process join timeout as backup)
            if not IS_WINDOWS and self.resource_limits['cpu_time'] > 0:
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Code execution timed out after {self.resource_limits['cpu_time']} seconds")

                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.resource_limits['cpu_time'])

            # Redirect stdout and stderr
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                # Create safe globals
                safe_globals = self._create_safe_globals()

                # Execute the code
                exec(code, safe_globals)

            # Cancel the alarm if set
            if not IS_WINDOWS and self.resource_limits['cpu_time'] > 0:
                signal.alarm(0)

            # Store the results
            result_dict['stdout'] = stdout_buffer.getvalue()
            result_dict['stderr'] = stderr_buffer.getvalue()
            result_dict['success'] = True
            result_dict['error'] = None

        except Exception as e:
            # Capture any exceptions
            result_dict['stdout'] = stdout_buffer.getvalue() if 'stdout_buffer' in locals() else ""
            result_dict['stderr'] = stderr_buffer.getvalue() if 'stderr_buffer' in locals() else ""
            result_dict['success'] = False
            result_dict['error'] = str(e)
            result_dict['error_type'] = type(e).__name__

    async def execute(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Execute Python code in a sandbox with resource limits.

        Args:
            code: The Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            A dictionary containing execution results
        """
        # Check if the code is safe
        is_safe, reason = self._is_safe_code(code)
        if not is_safe:
            logger.warning(f"Unsafe code detected: {reason}")
            return {
                'stdout': '',
                'stderr': f"Security error: {reason}",
                'success': False,
                'error': reason,
                'error_type': 'SecurityError'
            }

        # Execute the code in a subprocess with resource limits
        with multiprocessing.Manager() as manager:
            result_dict = manager.dict({
                'stdout': '',
                'stderr': '',
                'success': False,
                'error': None,
                'error_type': None
            })

            # Create and start the subprocess
            process = multiprocessing.Process(
                target=self._execute_in_subprocess,
                args=(code, result_dict)
            )

            start_time = time.time()
            process.start()

            # Wait for the process to complete or timeout
            process.join(timeout)

            # If the process is still running after the timeout, terminate it
            if process.is_alive():
                process.terminate()
                process.join()

                return {
                    'stdout': result_dict.get('stdout', ''),
                    'stderr': result_dict.get('stderr', '') + "\nExecution timed out",
                    'success': False,
                    'error': f"Execution timed out after {timeout} seconds",
                    'error_type': 'TimeoutError',
                    'execution_time': time.time() - start_time
                }

            # Return the results
            return {
                'stdout': result_dict.get('stdout', ''),
                'stderr': result_dict.get('stderr', ''),
                'success': result_dict.get('success', False),
                'error': result_dict.get('error', None),
                'error_type': result_dict.get('error_type', None),
                'execution_time': time.time() - start_time
            }


# Create a global instance with default settings
default_code_sandbox = CodeSandbox()
