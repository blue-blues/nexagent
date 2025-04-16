"""
Unix Sandbox Implementation

This module provides a Unix-specific implementation of the sandbox.
It uses resource limits and process isolation to secure execution.
"""

import os
import sys
import subprocess
import tempfile
import time
import signal
import resource
import psutil
from typing import Dict, List, Any, Optional, Union, Tuple

from app.sandbox.base import BaseSandbox, ResourceLimits, SandboxResult, SandboxException


class UnixSandbox(BaseSandbox):
    """
    Unix-specific implementation of the sandbox.
    
    This class uses resource limits and process isolation to secure execution.
    """
    
    def __init__(self):
        """Initialize the Unix sandbox."""
        super().__init__()
    
    def _set_resource_limits(self, resource_limits: ResourceLimits):
        """
        Set resource limits for the current process.
        
        Args:
            resource_limits: Resource limits to apply
        """
        # Set CPU time limit
        if resource_limits.max_cpu_time > 0:
            resource.setrlimit(resource.RLIMIT_CPU, (int(resource_limits.max_cpu_time), int(resource_limits.max_cpu_time)))
        
        # Set memory limit
        if resource_limits.max_memory > 0:
            # Convert bytes to kilobytes for RLIMIT_AS (address space)
            memory_kb = resource_limits.max_memory // 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_kb, memory_kb))
        
        # Set process limit
        if resource_limits.max_processes > 0:
            # RLIMIT_NPROC might not be available on all systems
            try:
                resource.setrlimit(resource.RLIMIT_NPROC, (resource_limits.max_processes, resource_limits.max_processes))
            except (AttributeError, ValueError):
                pass
        
        # Set file size limit
        if resource_limits.max_file_size > 0:
            # Convert bytes to bytes for RLIMIT_FSIZE
            resource.setrlimit(resource.RLIMIT_FSIZE, (resource_limits.max_file_size, resource_limits.max_file_size))
        
        # Set open files limit
        if resource_limits.max_open_files > 0:
            resource.setrlimit(resource.RLIMIT_NOFILE, (resource_limits.max_open_files, resource_limits.max_open_files))
    
    def _preexec_fn(self, resource_limits: ResourceLimits):
        """
        Function to call before exec in the child process.
        
        Args:
            resource_limits: Resource limits to apply
        """
        # Set resource limits
        self._set_resource_limits(resource_limits)
        
        # Create a new process group
        os.setpgrp()
        
        # Disable network access if required
        if not resource_limits.network_access:
            # This is a simplified approach and might not work on all systems
            # A more robust approach would use seccomp or network namespaces
            pass
    
    def _execute_with_resource_limits(
        self,
        command: List[str],
        input_data: Optional[str],
        resource_limits: ResourceLimits,
        working_dir: Optional[str],
        environment: Optional[Dict[str, str]]
    ) -> Tuple[int, str, str, float, int]:
        """
        Execute a command with resource limits.
        
        Args:
            command: Command to execute
            input_data: Input data for the command
            resource_limits: Resource limits to apply
            working_dir: Working directory for the command
            environment: Environment variables for the command
            
        Returns:
            Tuple[int, str, str, float, int]: Tuple of (exit_code, stdout, stderr, execution_time, memory_usage)
        """
        # Start the process
        start_time = time.time()
        
        # Create process with specific options
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir,
            env=environment,
            text=True,
            preexec_fn=lambda: self._preexec_fn(resource_limits)
        )
        
        # Send input data if provided
        stdout, stderr = "", ""
        try:
            stdout, stderr = process.communicate(
                input=input_data,
                timeout=resource_limits.max_cpu_time
            )
        except subprocess.TimeoutExpired:
            # Kill the process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                # Process might have already exited
                pass
            
            process.kill()
            stdout, stderr = process.communicate()
            stderr += f"\nProcess timed out after {resource_limits.max_cpu_time} seconds."
        
        # Get execution time
        execution_time = time.time() - start_time
        
        # Get memory usage (peak resident set size)
        memory_usage = 0
        try:
            process_info = psutil.Process(process.pid)
            memory_info = process_info.memory_info()
            memory_usage = memory_info.rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process might have already exited
            pass
        
        return process.returncode, stdout, stderr, execution_time, memory_usage
    
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
        # Use default resource limits if not provided
        if resource_limits is None:
            resource_limits = ResourceLimits()
        
        # Create execution directory
        execution_dir = self._create_execution_directory()
        
        try:
            # Determine file extension and interpreter based on language
            if language.lower() == "python":
                file_extension = ".py"
                interpreter = [sys.executable]
            elif language.lower() == "javascript":
                file_extension = ".js"
                interpreter = ["node"]
            elif language.lower() == "shell":
                file_extension = ".sh"
                interpreter = ["bash"]
            else:
                raise SandboxException(f"Unsupported language: {language}")
            
            # Write code to file
            main_file = f"main{file_extension}"
            main_file_path = self._write_file(execution_dir, main_file, code)
            
            # Make shell scripts executable
            if language.lower() == "shell":
                os.chmod(main_file_path, 0o755)
            
            # Write additional files
            if additional_files:
                for filename, content in additional_files.items():
                    file_path = self._write_file(execution_dir, filename, content)
                    # Make shell scripts executable
                    if filename.endswith(".sh"):
                        os.chmod(file_path, 0o755)
            
            # Prepare command
            command = interpreter + [main_file_path]
            
            # Execute command
            exit_code, stdout, stderr, execution_time, memory_usage = self._execute_with_resource_limits(
                command=command,
                input_data=input_data,
                resource_limits=resource_limits,
                working_dir=execution_dir,
                environment=None  # Use default environment
            )
            
            # Collect output files
            output_files = {}
            if output_patterns:
                output_files = self._collect_output_files(execution_dir, output_patterns)
            
            # Create result
            success = exit_code == 0
            error_message = None if success else f"Execution failed with exit code {exit_code}"
            
            return SandboxResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=execution_time,
                memory_usage=memory_usage,
                error_message=error_message,
                output_files=output_files
            )
        
        finally:
            # Clean up execution directory
            self._cleanup_execution_directory(execution_dir)
    
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
        # Use default resource limits if not provided
        if resource_limits is None:
            resource_limits = ResourceLimits()
        
        # Create execution directory if working_dir is not provided
        temp_dir_created = False
        if working_dir is None:
            working_dir = self._create_execution_directory()
            temp_dir_created = True
        
        try:
            # Execute command
            exit_code, stdout, stderr, execution_time, memory_usage = self._execute_with_resource_limits(
                command=command,
                input_data=input_data,
                resource_limits=resource_limits,
                working_dir=working_dir,
                environment=environment
            )
            
            # Collect output files
            output_files = {}
            if output_patterns:
                output_files = self._collect_output_files(working_dir, output_patterns)
            
            # Create result
            success = exit_code == 0
            error_message = None if success else f"Execution failed with exit code {exit_code}"
            
            return SandboxResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=execution_time,
                memory_usage=memory_usage,
                error_message=error_message,
                output_files=output_files
            )
        
        finally:
            # Clean up execution directory if we created it
            if temp_dir_created:
                self._cleanup_execution_directory(working_dir)
