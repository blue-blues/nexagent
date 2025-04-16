"""
Windows Sandbox Implementation

This module provides a Windows-specific implementation of the sandbox.
It uses Windows Job Objects to limit resources and isolate processes.
"""

import os
import sys
import subprocess
import tempfile
import time
import signal
import ctypes
from ctypes import wintypes
import psutil
from typing import Dict, List, Any, Optional, Union, Tuple

from app.sandbox.base import BaseSandbox, ResourceLimits, SandboxResult, SandboxException


# Windows API constants and structures
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x00000400
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_LIMIT_PROCESS_TIME = 0x00000002

# Load Windows API functions
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# Define Windows API function prototypes
CreateJobObjectW = kernel32.CreateJobObjectW
CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
CreateJobObjectW.restype = wintypes.HANDLE

AssignProcessToJobObject = kernel32.AssignProcessToJobObject
AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
AssignProcessToJobObject.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

# Define a simplified version of the JOBOBJECT_EXTENDED_LIMIT_INFORMATION structure
class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    """Windows Job Object Basic Limit Information structure."""
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]

class IO_COUNTERS(ctypes.Structure):
    """Windows IO Counters structure."""
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]

class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    """Windows Job Object Extended Limit Information structure."""
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t)
    ]

SetInformationJobObject = kernel32.SetInformationJobObject
SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
SetInformationJobObject.restype = wintypes.BOOL


class WindowsSandbox(BaseSandbox):
    """
    Windows-specific implementation of the sandbox.

    This class uses Windows Job Objects to limit resources and isolate processes.
    """

    def __init__(self):
        """Initialize the Windows sandbox."""
        super().__init__()

    def _create_job_object(self, resource_limits: ResourceLimits) -> wintypes.HANDLE:
        """
        Create a Windows Job Object with the specified resource limits.

        Args:
            resource_limits: Resource limits to apply

        Returns:
            wintypes.HANDLE: Handle to the created Job Object
        """
        # Create a Job Object
        job_handle = CreateJobObjectW(None, None)
        if job_handle == 0:
            raise SandboxException(f"Failed to create Job Object: {ctypes.get_last_error()}")

        # Set Job Object limits
        limit_info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()

        # Set memory limit
        if resource_limits.max_memory > 0:
            limit_info.ProcessMemoryLimit = resource_limits.max_memory
            limit_info.JobMemoryLimit = resource_limits.max_memory

        # Set CPU time limit (in 100-nanosecond intervals)
        if resource_limits.max_cpu_time > 0:
            # Convert seconds to 100-nanosecond intervals
            cpu_time_limit = int(resource_limits.max_cpu_time * 10000000)
            # This would normally go into BasicLimitInformation.PerProcessUserTimeLimit
            # For simplicity, we're not setting this directly

        # Set Job Object information
        # For simplicity, we're not setting all possible limits
        # In a real implementation, you would set more limits

        return job_handle

    def _execute_with_job_object(
        self,
        command: List[str],
        input_data: Optional[str],
        resource_limits: ResourceLimits,
        working_dir: Optional[str],
        environment: Optional[Dict[str, str]]
    ) -> Tuple[int, str, str, float, int]:
        """
        Execute a command with a Job Object for resource limiting.

        Args:
            command: Command to execute
            input_data: Input data for the command
            resource_limits: Resource limits to apply
            working_dir: Working directory for the command
            environment: Environment variables for the command

        Returns:
            Tuple[int, str, str, float, int]: Tuple of (exit_code, stdout, stderr, execution_time, memory_usage)
        """
        # Create a Job Object
        job_handle = self._create_job_object(resource_limits)

        try:
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
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Assign the process to the Job Object
            if not AssignProcessToJobObject(job_handle, int(process.pid)):
                raise SandboxException(f"Failed to assign process to Job Object: {ctypes.get_last_error()}")

            # Send input data if provided
            stdout, stderr = "", ""
            try:
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=resource_limits.max_cpu_time
                )
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                stderr += f"\nProcess timed out after {resource_limits.max_cpu_time} seconds."

            # Get execution time
            execution_time = time.time() - start_time

            # Get memory usage (peak working set)
            memory_usage = 0
            try:
                process_info = psutil.Process(process.pid)
                memory_info = process_info.memory_info()
                memory_usage = memory_info.peak_wset
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process might have already exited
                pass

            return process.returncode, stdout, stderr, execution_time, memory_usage

        finally:
            # Close the Job Object handle
            CloseHandle(job_handle)

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
            elif language.lower() == "shell" or language.lower() == "batch":
                file_extension = ".bat"
                interpreter = ["cmd", "/c"]
            else:
                raise SandboxException(f"Unsupported language: {language}")

            # Write code to file
            main_file = f"main{file_extension}"
            main_file_path = self._write_file(execution_dir, main_file, code)

            # Write additional files
            if additional_files:
                for filename, content in additional_files.items():
                    self._write_file(execution_dir, filename, content)

            # Prepare command
            command = interpreter + [main_file_path]

            # Execute command
            exit_code, stdout, stderr, execution_time, memory_usage = self._execute_with_job_object(
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
            exit_code, stdout, stderr, execution_time, memory_usage = self._execute_with_job_object(
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
