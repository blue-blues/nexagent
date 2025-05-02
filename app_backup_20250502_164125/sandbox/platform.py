"""
Platform Detection Module

This module provides utilities for detecting and handling platform-specific functionality
for the sandbox system.
"""

import os
import sys
import platform
from enum import Enum
from typing import Dict, Any, Optional


class PlatformType(Enum):
    """Enum representing supported platform types."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


def detect_platform() -> PlatformType:
    """
    Detect the current platform.
    
    Returns:
        PlatformType: The detected platform type
    """
    system = platform.system().lower()
    
    if system == "windows":
        return PlatformType.WINDOWS
    elif system == "linux":
        return PlatformType.LINUX
    elif system == "darwin":
        return PlatformType.MACOS
    else:
        return PlatformType.UNKNOWN


def get_platform_info() -> Dict[str, Any]:
    """
    Get detailed information about the current platform.
    
    Returns:
        Dict[str, Any]: Dictionary containing platform information
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "is_64bit": sys.maxsize > 2**32,
        "path_separator": os.path.sep,
        "line_separator": os.linesep,
        "environment_variables": dict(os.environ)
    }


def is_admin() -> bool:
    """
    Check if the current process has administrator/root privileges.
    
    Returns:
        bool: True if the process has admin privileges, False otherwise
    """
    try:
        if detect_platform() == PlatformType.WINDOWS:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            # For Unix-based systems, check if UID is 0 (root)
            return os.geteuid() == 0
    except:
        return False


def get_temp_directory() -> str:
    """
    Get the system's temporary directory path.
    
    Returns:
        str: Path to the temporary directory
    """
    import tempfile
    return tempfile.gettempdir()


def get_sandbox_directory() -> str:
    """
    Get the directory to use for sandbox operations.
    
    Returns:
        str: Path to the sandbox directory
    """
    base_dir = get_temp_directory()
    sandbox_dir = os.path.join(base_dir, "nexagent_sandbox")
    
    # Create the directory if it doesn't exist
    if not os.path.exists(sandbox_dir):
        os.makedirs(sandbox_dir, exist_ok=True)
    
    return sandbox_dir


def get_platform_specific_sandbox():
    """
    Get the appropriate sandbox implementation for the current platform.
    
    Returns:
        BaseSandbox: Platform-specific sandbox implementation
    """
    platform_type = detect_platform()
    
    if platform_type == PlatformType.WINDOWS:
        from app.sandbox.windows import WindowsSandbox
        return WindowsSandbox()
    elif platform_type in (PlatformType.LINUX, PlatformType.MACOS):
        from app.sandbox.unix import UnixSandbox
        return UnixSandbox()
    else:
        from app.sandbox.base import BaseSandbox
        return BaseSandbox()  # Fallback to base implementation
