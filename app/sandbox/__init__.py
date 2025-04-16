"""
Sandbox Module

This module provides a secure sandbox for executing code and commands.
It includes platform-specific implementations for Windows and Unix-based systems,
resource monitoring, and permission management.
"""

from app.sandbox.base import BaseSandbox, ResourceLimits, SandboxResult, SandboxException
from app.sandbox.platform import (
    PlatformType,
    detect_platform,
    get_platform_info,
    is_admin,
    get_temp_directory,
    get_sandbox_directory,
    get_platform_specific_sandbox
)
from app.sandbox.monitor import ResourceUsage, ResourceMonitor
from app.sandbox.permissions import (
    Permission,
    PermissionSet,
    PermissionManager,
    global_permission_manager
)

# Import platform-specific implementations
platform_type = detect_platform()
if platform_type == PlatformType.WINDOWS:
    from app.sandbox.windows import WindowsSandbox
elif platform_type in (PlatformType.LINUX, PlatformType.MACOS):
    from app.sandbox.unix import UnixSandbox

# Create a global sandbox instance
sandbox = get_platform_specific_sandbox()

__all__ = [
    'BaseSandbox',
    'ResourceLimits',
    'SandboxResult',
    'SandboxException',
    'PlatformType',
    'detect_platform',
    'get_platform_info',
    'is_admin',
    'get_temp_directory',
    'get_sandbox_directory',
    'get_platform_specific_sandbox',
    'ResourceUsage',
    'ResourceMonitor',
    'Permission',
    'PermissionSet',
    'PermissionManager',
    'global_permission_manager',
    'sandbox'
]