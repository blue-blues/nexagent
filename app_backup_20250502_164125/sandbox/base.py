"""
Base Sandbox Module

This module provides the base class for sandbox implementations.
All platform-specific sandbox implementations should inherit from this class.
"""

import os
import sys
import subprocess
import tempfile
import uuid
import json
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from abc import ABC, abstractmethod

from app.sandbox.platform import get_sandbox_directory


class SandboxException(Exception):
    """Exception raised for sandbox-related errors."""
    pass


class ResourceLimits:
    """Class representing resource limits for sandbox execution."""
    
    def __init__(
        self,
        max_cpu_time: float = 30.0,  # seconds
        max_memory: int = 512 * 1024 * 1024,  # 512 MB in bytes
        max_processes: int = 10,
        max_file_size: int = 10 * 1024 * 1024,  # 10 MB in bytes
        max_open_files: int = 20,
        network_access: bool = False,
        allow_file_write: bool = False
    ):
        """
        Initialize resource limits.
        
        Args:
            max_cpu_time: Maximum CPU time in seconds
            max_memory: Maximum memory usage in bytes
            max_processes: Maximum number of processes
            max_file_size: Maximum file size in bytes
            max_open_files: Maximum number of open files
            network_access: Whether to allow network access
            allow_file_write: Whether to allow file writing
        """
        self.max_cpu_time = max_cpu_time
        self.max_memory = max_memory
        self.max_processes = max_processes
        self.max_file_size = max_file_size
        self.max_open_files = max_open_files
        self.network_access = network_access
        self.allow_file_write = allow_file_write
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resource limits to a dictionary."""
        return {
            "max_cpu_time": self.max_cpu_time,
            "max_memory": self.max_memory,
            "max_processes": self.max_processes,
            "max_file_size": self.max_file_size,
            "max_open_files": self.max_open_files,
            "network_access": self.network_access,
            "allow_file_write": self.allow_file_write
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceLimits':
        """Create resource limits from a dictionary."""
        return cls(
            max_cpu_time=data.get("max_cpu_time", 30.0),
            max_memory=data.get("max_memory", 512 * 1024 * 1024),
            max_processes=data.get("max_processes", 10),
            max_file_size=data.get("max_file_size", 10 * 1024 * 1024),
            max_open_files=data.get("max_open_files", 20),
            network_access=data.get("network_access", False),
            allow_file_write=data.get("allow_file_write", False)
        )


class SandboxResult:
    """Class representing the result of a sandbox execution."""
    
    def __init__(
        self,
        success: bool,
        stdout: str,
        stderr: str,
        exit_code: int,
        execution_time: float,
        memory_usage: int,
        error_message: Optional[str] = None,
        output_files: Optional[Dict[str, str]] = None
    ):
        """
        Initialize sandbox result.
        
        Args:
            success: Whether the execution was successful
            stdout: Standard output from the execution
            stderr: Standard error from the execution
            exit_code: Exit code from the execution
            execution_time: Execution time in seconds
            memory_usage: Memory usage in bytes
            error_message: Error message if execution failed
            output_files: Dictionary mapping file names to file contents
        """
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.execution_time = execution_time
        self.memory_usage = memory_usage
        self.error_message = error_message
        self.output_files = output_files or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sandbox result to a dictionary."""
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "memory_usage": self.memory_usage,
            "error_message": self.error_message,
            "output_files": self.output_files
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SandboxResult':
        """Create sandbox result from a dictionary."""
        return cls(
            success=data.get("success", False),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            exit_code=data.get("exit_code", -1),
            execution_time=data.get("execution_time", 0.0),
            memory_usage=data.get("memory_usage", 0),
            error_message=data.get("error_message"),
            output_files=data.get("output_files", {})
        )
    
    def __str__(self) -> str:
        """String representation of the sandbox result."""
        if self.success:
            return f"Success (exit code: {self.exit_code}, time: {self.execution_time:.2f}s)"
        else:
            return f"Failure (exit code: {self.exit_code}, error: {self.error_message})"


class BaseSandbox(ABC):
    """
    Base class for sandbox implementations.
    
    This class defines the interface that all sandbox implementations must follow.
    Platform-specific implementations should inherit from this class and override
    the abstract methods.
    """
    
    def __init__(self):
        """Initialize the sandbox."""
        self.sandbox_dir = get_sandbox_directory()
        self._ensure_sandbox_directory()
    
    def _ensure_sandbox_directory(self):
        """Ensure that the sandbox directory exists."""
        if not os.path.exists(self.sandbox_dir):
            os.makedirs(self.sandbox_dir, exist_ok=True)
    
    def _create_execution_directory(self) -> str:
        """
        Create a unique directory for execution.
        
        Returns:
            str: Path to the execution directory
        """
        execution_id = str(uuid.uuid4())
        execution_dir = os.path.join(self.sandbox_dir, execution_id)
        os.makedirs(execution_dir, exist_ok=True)
        return execution_dir
    
    def _cleanup_execution_directory(self, execution_dir: str):
        """
        Clean up the execution directory.
        
        Args:
            execution_dir: Path to the execution directory
        """
        import shutil
        if os.path.exists(execution_dir):
            try:
                shutil.rmtree(execution_dir)
            except Exception as e:
                print(f"Error cleaning up execution directory: {e}")
    
    def _write_file(self, execution_dir: str, filename: str, content: str) -> str:
        """
        Write content to a file in the execution directory.
        
        Args:
            execution_dir: Path to the execution directory
            filename: Name of the file
            content: Content to write
            
        Returns:
            str: Path to the created file
        """
        file_path = os.path.join(execution_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def _read_file(self, file_path: str) -> str:
        """
        Read content from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Content of the file
        """
        if not os.path.exists(file_path):
            return ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _collect_output_files(self, execution_dir: str, output_patterns: List[str]) -> Dict[str, str]:
        """
        Collect output files matching the given patterns.
        
        Args:
            execution_dir: Path to the execution directory
            output_patterns: List of file patterns to collect
            
        Returns:
            Dict[str, str]: Dictionary mapping file names to file contents
        """
        import glob
        
        output_files = {}
        
        for pattern in output_patterns:
            pattern_path = os.path.join(execution_dir, pattern)
            for file_path in glob.glob(pattern_path):
                if os.path.isfile(file_path):
                    relative_path = os.path.relpath(file_path, execution_dir)
                    output_files[relative_path] = self._read_file(file_path)
        
        return output_files
    
    @abstractmethod
    def execute_code(
        self,
        code: str,
        language: str,
        input_data: Optional[str] = None,
        resource_limits: Optional[ResourceLimits] = None,
        additional_files: Optional[Dict[str, str]] = None,
        output_patterns: Optional[List[str]] = None
    ) -> SandboxResult:
        """
        Execute code in the sandbox.
        
        Args:
            code: Code to execute
            language: Programming language of the code
            input_data: Input data to provide to the code
            resource_limits: Resource limits for execution
            additional_files: Additional files to include
            output_patterns: Patterns of output files to collect
            
        Returns:
            SandboxResult: Result of the execution
        """
        pass
    
    @abstractmethod
    def execute_command(
        self,
        command: List[str],
        input_data: Optional[str] = None,
        resource_limits: Optional[ResourceLimits] = None,
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        output_patterns: Optional[List[str]] = None
    ) -> SandboxResult:
        """
        Execute a command in the sandbox.
        
        Args:
            command: Command to execute as a list of arguments
            input_data: Input data to provide to the command
            resource_limits: Resource limits for execution
            working_dir: Working directory for the command
            environment: Environment variables for the command
            output_patterns: Patterns of output files to collect
            
        Returns:
            SandboxResult: Result of the execution
        """
        pass
    
    def execute_python(
        self,
        code: str,
        input_data: Optional[str] = None,
        resource_limits: Optional[ResourceLimits] = None,
        additional_files: Optional[Dict[str, str]] = None,
        output_patterns: Optional[List[str]] = None
    ) -> SandboxResult:
        """
        Execute Python code in the sandbox.
        
        Args:
            code: Python code to execute
            input_data: Input data to provide to the code
            resource_limits: Resource limits for execution
            additional_files: Additional files to include
            output_patterns: Patterns of output files to collect
            
        Returns:
            SandboxResult: Result of the execution
        """
        return self.execute_code(
            code=code,
            language="python",
            input_data=input_data,
            resource_limits=resource_limits,
            additional_files=additional_files,
            output_patterns=output_patterns
        )
    
    def execute_javascript(
        self,
        code: str,
        input_data: Optional[str] = None,
        resource_limits: Optional[ResourceLimits] = None,
        additional_files: Optional[Dict[str, str]] = None,
        output_patterns: Optional[List[str]] = None
    ) -> SandboxResult:
        """
        Execute JavaScript code in the sandbox.
        
        Args:
            code: JavaScript code to execute
            input_data: Input data to provide to the code
            resource_limits: Resource limits for execution
            additional_files: Additional files to include
            output_patterns: Patterns of output files to collect
            
        Returns:
            SandboxResult: Result of the execution
        """
        return self.execute_code(
            code=code,
            language="javascript",
            input_data=input_data,
            resource_limits=resource_limits,
            additional_files=additional_files,
            output_patterns=output_patterns
        )
    
    def execute_shell(
        self,
        script: str,
        input_data: Optional[str] = None,
        resource_limits: Optional[ResourceLimits] = None,
        additional_files: Optional[Dict[str, str]] = None,
        output_patterns: Optional[List[str]] = None
    ) -> SandboxResult:
        """
        Execute a shell script in the sandbox.
        
        Args:
            script: Shell script to execute
            input_data: Input data to provide to the script
            resource_limits: Resource limits for execution
            additional_files: Additional files to include
            output_patterns: Patterns of output files to collect
            
        Returns:
            SandboxResult: Result of the execution
        """
        return self.execute_code(
            code=script,
            language="shell",
            input_data=input_data,
            resource_limits=resource_limits,
            additional_files=additional_files,
            output_patterns=output_patterns
        )
