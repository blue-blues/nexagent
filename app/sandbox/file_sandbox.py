"""
Virtual file system for sandboxed file operations.

This module provides a secure virtual file system for agent operations
with proper permission checks and access restrictions.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO, TextIO, Any

from app.logger import logger


class FileSandbox:
    """
    A sandbox for file operations with security restrictions.

    This class provides methods for safely performing file operations
    within a restricted virtual file system.
    """

    def __init__(self, root_dir: Optional[str] = None, max_size: int = 10 * 1024 * 1024):
        """
        Initialize the file sandbox with a root directory.

        Args:
            root_dir: The root directory for the sandbox. If None, a temporary directory will be created.
            max_size: Maximum total size of files in the sandbox (default: 10 MB)
        """
        if root_dir:
            self.root_dir = Path(root_dir)
            os.makedirs(self.root_dir, exist_ok=True)
            self._created_temp_dir = False
        else:
            self.root_dir = Path(tempfile.mkdtemp(prefix="nexagent_sandbox_"))
            self._created_temp_dir = True

        self.max_size = max_size
        self._current_size = 0

        logger.info(f"Initialized file sandbox at {self.root_dir}")

    def __del__(self):
        """Clean up temporary directory if created."""
        if hasattr(self, '_created_temp_dir') and self._created_temp_dir:
            try:
                shutil.rmtree(self.root_dir)
                logger.info(f"Cleaned up temporary sandbox directory {self.root_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up sandbox directory: {e}")

    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """
        Resolve a path relative to the sandbox root.

        Args:
            path: The path to resolve

        Returns:
            The absolute path within the sandbox

        Raises:
            ValueError: If the path tries to escape the sandbox
        """
        # Convert to Path object
        if isinstance(path, str):
            path = Path(path)

        # Make absolute within sandbox
        if not path.is_absolute():
            path = self.root_dir / path

        # Check for sandbox escape
        try:
            path.relative_to(self.root_dir)
        except ValueError:
            raise ValueError(f"Path {path} attempts to escape the sandbox")

        return path

    def _check_size_limit(self, size: int) -> bool:
        """
        Check if adding a file of the given size would exceed the sandbox limit.

        Args:
            size: The size of the file to add

        Returns:
            True if the size is acceptable, False otherwise
        """
        return self._current_size + size <= self.max_size

    def _update_current_size(self):
        """Update the current size of all files in the sandbox."""
        total_size = 0
        for path in self.root_dir.glob('**/*'):
            if path.is_file():
                total_size += path.stat().st_size

        self._current_size = total_size

    def list_files(self, directory: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """
        List files in the sandbox or a subdirectory.

        Args:
            directory: Optional subdirectory to list

        Returns:
            A list of dictionaries with file information
        """
        if directory:
            dir_path = self._resolve_path(directory)
        else:
            dir_path = self.root_dir

        if not dir_path.exists() or not dir_path.is_dir():
            raise ValueError(f"Directory {dir_path} does not exist")

        files = []
        for path in dir_path.glob('*'):
            rel_path = path.relative_to(self.root_dir)
            file_info = {
                'name': path.name,
                'path': str(rel_path),
                'is_dir': path.is_dir(),
                'size': path.stat().st_size if path.is_file() else None,
                'modified': path.stat().st_mtime if path.exists() else None,
            }
            files.append(file_info)

        return files

    def read_file(self, path: Union[str, Path], binary: bool = False) -> Union[str, bytes]:
        """
        Read a file from the sandbox.

        Args:
            path: The path to the file
            binary: Whether to read in binary mode

        Returns:
            The file contents as string or bytes
        """
        file_path = self._resolve_path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File {path} does not exist in sandbox")

        if not file_path.is_file():
            raise ValueError(f"Path {path} is not a file")

        mode = 'rb' if binary else 'r'
        with open(file_path, mode) as f:
            return f.read()

    def write_file(self, path: Union[str, Path], content: Union[str, bytes], binary: bool = False) -> int:
        """
        Write content to a file in the sandbox.

        Args:
            path: The path to the file
            content: The content to write
            binary: Whether to write in binary mode

        Returns:
            The number of bytes written
        """
        file_path = self._resolve_path(path)

        # Create parent directories if they don't exist
        os.makedirs(file_path.parent, exist_ok=True)

        # Check size limit
        content_size = len(content)
        if not self._check_size_limit(content_size):
            raise ValueError(f"Writing {content_size} bytes would exceed the sandbox size limit of {self.max_size} bytes")

        # Write the file
        mode = 'wb' if binary else 'w'
        with open(file_path, mode) as f:
            if binary:
                if isinstance(content, str):
                    content = content.encode('utf-8')
                bytes_written = f.write(content)
            else:
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                bytes_written = f.write(content)

        # Update current size
        self._update_current_size()

        return bytes_written

    def append_file(self, path: Union[str, Path], content: Union[str, bytes], binary: bool = False) -> int:
        """
        Append content to a file in the sandbox.

        Args:
            path: The path to the file
            content: The content to append
            binary: Whether to append in binary mode

        Returns:
            The number of bytes written
        """
        file_path = self._resolve_path(path)

        # Create parent directories if they don't exist
        os.makedirs(file_path.parent, exist_ok=True)

        # Check size limit
        content_size = len(content)
        if not self._check_size_limit(content_size):
            raise ValueError(f"Appending {content_size} bytes would exceed the sandbox size limit of {self.max_size} bytes")

        # Append to the file
        mode = 'ab' if binary else 'a'
        with open(file_path, mode) as f:
            if binary:
                if isinstance(content, str):
                    content = content.encode('utf-8')
                bytes_written = f.write(content)
            else:
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                bytes_written = f.write(content)

        # Update current size
        self._update_current_size()

        return bytes_written

    def delete_file(self, path: Union[str, Path]) -> bool:
        """
        Delete a file from the sandbox.

        Args:
            path: The path to the file

        Returns:
            True if the file was deleted, False otherwise
        """
        file_path = self._resolve_path(path)

        if not file_path.exists():
            return False

        if file_path.is_dir():
            raise ValueError(f"Path {path} is a directory, use delete_directory instead")

        file_path.unlink()

        # Update current size
        self._update_current_size()

        return True

    def create_directory(self, path: Union[str, Path]) -> bool:
        """
        Create a directory in the sandbox.

        Args:
            path: The path to the directory

        Returns:
            True if the directory was created, False if it already existed
        """
        dir_path = self._resolve_path(path)

        if dir_path.exists():
            if dir_path.is_dir():
                return False
            else:
                raise ValueError(f"Path {path} already exists and is not a directory")

        os.makedirs(dir_path, exist_ok=True)
        return True

    def delete_directory(self, path: Union[str, Path], recursive: bool = False) -> bool:
        """
        Delete a directory from the sandbox.

        Args:
            path: The path to the directory
            recursive: Whether to delete recursively

        Returns:
            True if the directory was deleted, False otherwise
        """
        dir_path = self._resolve_path(path)

        if not dir_path.exists():
            return False

        if not dir_path.is_dir():
            raise ValueError(f"Path {path} is not a directory")

        if recursive:
            shutil.rmtree(dir_path)
        else:
            try:
                dir_path.rmdir()
            except OSError:
                raise ValueError(f"Directory {path} is not empty, use recursive=True to delete")

        # Update current size
        self._update_current_size()

        return True

    def copy_file(self, src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """
        Copy a file within the sandbox.

        Args:
            src: The source path
            dst: The destination path

        Returns:
            True if the file was copied, False otherwise
        """
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)

        if not src_path.exists():
            raise FileNotFoundError(f"Source file {src} does not exist")

        if not src_path.is_file():
            raise ValueError(f"Source path {src} is not a file")

        # Check size limit
        file_size = src_path.stat().st_size
        if not self._check_size_limit(file_size):
            raise ValueError(f"Copying a {file_size} byte file would exceed the sandbox size limit")

        # Create parent directories if they don't exist
        os.makedirs(dst_path.parent, exist_ok=True)

        shutil.copy2(src_path, dst_path)

        # Update current size
        self._update_current_size()

        return True

    def move_file(self, src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """
        Move a file within the sandbox.

        Args:
            src: The source path
            dst: The destination path

        Returns:
            True if the file was moved, False otherwise
        """
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)

        if not src_path.exists():
            raise FileNotFoundError(f"Source file {src} does not exist")

        if not src_path.is_file():
            raise ValueError(f"Source path {src} is not a file")

        # Create parent directories if they don't exist
        os.makedirs(dst_path.parent, exist_ok=True)

        shutil.move(src_path, dst_path)

        return True

    def get_file_info(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get information about a file in the sandbox.

        Args:
            path: The path to the file

        Returns:
            A dictionary with file information
        """
        file_path = self._resolve_path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File {path} does not exist")

        rel_path = file_path.relative_to(self.root_dir)

        return {
            'name': file_path.name,
            'path': str(rel_path),
            'is_dir': file_path.is_dir(),
            'size': file_path.stat().st_size if file_path.is_file() else None,
            'modified': file_path.stat().st_mtime,
            'created': file_path.stat().st_ctime,
            'is_file': file_path.is_file(),
        }

    def get_sandbox_info(self) -> Dict[str, Any]:
        """
        Get information about the sandbox.

        Returns:
            A dictionary with sandbox information
        """
        self._update_current_size()

        return {
            'root_dir': str(self.root_dir),
            'current_size': self._current_size,
            'max_size': self.max_size,
            'file_count': len(list(self.root_dir.glob('**/*'))),
            'usage_percent': (self._current_size / self.max_size) * 100 if self.max_size > 0 else 0,
        }


# Create a global instance with default settings
default_file_sandbox = FileSandbox()
