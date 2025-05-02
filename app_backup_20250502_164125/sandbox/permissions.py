"""
Sandbox Permissions Module

This module provides a permission system for controlling access to resources
and operations within the sandbox.
"""

from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union, Set


class Permission(Enum):
    """Enum representing different permissions."""
    # File system permissions
    READ_FILES = auto()
    WRITE_FILES = auto()
    EXECUTE_FILES = auto()
    
    # Network permissions
    NETWORK_ACCESS = auto()
    OUTBOUND_CONNECTIONS = auto()
    INBOUND_CONNECTIONS = auto()
    
    # Process permissions
    CREATE_PROCESSES = auto()
    KILL_PROCESSES = auto()
    
    # System permissions
    READ_ENVIRONMENT = auto()
    MODIFY_ENVIRONMENT = auto()
    
    # Tool permissions
    USE_TOOLS = auto()
    MODIFY_TOOLS = auto()
    
    # Sandbox permissions
    BYPASS_SANDBOX = auto()
    MODIFY_SANDBOX = auto()


class PermissionSet:
    """Class representing a set of permissions."""
    
    def __init__(self, permissions: Optional[List[Permission]] = None):
        """
        Initialize a permission set.
        
        Args:
            permissions: List of permissions to include
        """
        self.permissions: Set[Permission] = set(permissions or [])
    
    def add(self, permission: Permission):
        """
        Add a permission to the set.
        
        Args:
            permission: Permission to add
        """
        self.permissions.add(permission)
    
    def remove(self, permission: Permission):
        """
        Remove a permission from the set.
        
        Args:
            permission: Permission to remove
        """
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    def has(self, permission: Permission) -> bool:
        """
        Check if the set has a permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            bool: True if the set has the permission, False otherwise
        """
        return permission in self.permissions
    
    def clear(self):
        """Clear all permissions."""
        self.permissions.clear()
    
    def to_list(self) -> List[str]:
        """
        Convert permissions to a list of strings.
        
        Returns:
            List[str]: List of permission names
        """
        return [p.name for p in self.permissions]
    
    @classmethod
    def from_list(cls, permission_names: List[str]) -> 'PermissionSet':
        """
        Create a permission set from a list of permission names.
        
        Args:
            permission_names: List of permission names
            
        Returns:
            PermissionSet: Created permission set
        """
        permissions = []
        for name in permission_names:
            try:
                permissions.append(Permission[name])
            except KeyError:
                # Ignore invalid permission names
                pass
        
        return cls(permissions)
    
    def __str__(self) -> str:
        """String representation of the permission set."""
        return f"PermissionSet({', '.join(self.to_list())})"


class PermissionManager:
    """
    Class for managing permissions.
    
    This class provides utilities for checking and enforcing permissions
    for different operations within the sandbox.
    """
    
    def __init__(self, default_permissions: Optional[PermissionSet] = None):
        """
        Initialize a permission manager.
        
        Args:
            default_permissions: Default permissions to use
        """
        self.default_permissions = default_permissions or PermissionSet()
        self.tool_permissions: Dict[str, PermissionSet] = {}
    
    def set_tool_permissions(self, tool_name: str, permissions: PermissionSet):
        """
        Set permissions for a specific tool.
        
        Args:
            tool_name: Name of the tool
            permissions: Permissions to set
        """
        self.tool_permissions[tool_name] = permissions
    
    def get_tool_permissions(self, tool_name: str) -> PermissionSet:
        """
        Get permissions for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            PermissionSet: Permissions for the tool
        """
        return self.tool_permissions.get(tool_name, self.default_permissions)
    
    def check_permission(self, permission: Permission, tool_name: Optional[str] = None) -> bool:
        """
        Check if a permission is granted.
        
        Args:
            permission: Permission to check
            tool_name: Name of the tool to check for
            
        Returns:
            bool: True if the permission is granted, False otherwise
        """
        if tool_name and tool_name in self.tool_permissions:
            return self.tool_permissions[tool_name].has(permission)
        
        return self.default_permissions.has(permission)
    
    def require_permission(self, permission: Permission, tool_name: Optional[str] = None):
        """
        Require a permission, raising an exception if not granted.
        
        Args:
            permission: Permission to require
            tool_name: Name of the tool to check for
            
        Raises:
            PermissionError: If the permission is not granted
        """
        if not self.check_permission(permission, tool_name):
            tool_str = f" for tool '{tool_name}'" if tool_name else ""
            raise PermissionError(f"Permission '{permission.name}' required{tool_str}")
    
    def create_restricted_set(self) -> PermissionSet:
        """
        Create a restricted permission set with minimal permissions.
        
        Returns:
            PermissionSet: Restricted permission set
        """
        return PermissionSet([
            Permission.READ_FILES,
            Permission.READ_ENVIRONMENT
        ])
    
    def create_standard_set(self) -> PermissionSet:
        """
        Create a standard permission set with common permissions.
        
        Returns:
            PermissionSet: Standard permission set
        """
        return PermissionSet([
            Permission.READ_FILES,
            Permission.WRITE_FILES,
            Permission.EXECUTE_FILES,
            Permission.READ_ENVIRONMENT,
            Permission.CREATE_PROCESSES,
            Permission.USE_TOOLS
        ])
    
    def create_elevated_set(self) -> PermissionSet:
        """
        Create an elevated permission set with most permissions.
        
        Returns:
            PermissionSet: Elevated permission set
        """
        return PermissionSet([
            Permission.READ_FILES,
            Permission.WRITE_FILES,
            Permission.EXECUTE_FILES,
            Permission.NETWORK_ACCESS,
            Permission.OUTBOUND_CONNECTIONS,
            Permission.CREATE_PROCESSES,
            Permission.KILL_PROCESSES,
            Permission.READ_ENVIRONMENT,
            Permission.MODIFY_ENVIRONMENT,
            Permission.USE_TOOLS,
            Permission.MODIFY_TOOLS
        ])
    
    def create_admin_set(self) -> PermissionSet:
        """
        Create an admin permission set with all permissions.
        
        Returns:
            PermissionSet: Admin permission set
        """
        return PermissionSet(list(Permission))


# Create a global permission manager instance
global_permission_manager = PermissionManager()

# Set default permissions to restricted
global_permission_manager.default_permissions = global_permission_manager.create_restricted_set()
