import os
import json
import re
from typing import Dict, Any, Union, List, Optional

import aiofiles

# Try to import from different locations
try:
    from app.tools.base import BaseTool, ToolResult
    from app.tools.output_formatter import OutputFormatter
except ImportError:
    try:
        from app.core.tool.base import BaseTool, ToolResult
        from app.core.tool.output_formatter import OutputFormatter
    except ImportError:
        # Define minimal classes if imports fail
        class ToolResult:
            def __init__(self, output=None, error=None):
                self.output = output
                self.error = error

        class BaseTool:
            """Fallback BaseTool implementation."""
            name = "base_tool"
            description = "Base tool class"
            parameters = {}

        class OutputFormatter:
            def format(self, content, format_type="text", indent=2):
                if isinstance(content, (dict, list)) and format_type == "json":
                    import json
                    return json.dumps(content, indent=indent)
                return str(content)
from app.logger import logger


class FileSaver(BaseTool):
    name: str = "file_saver"
    description: str = """Save content to a local file at a specified path with formatting options.
    Use this tool when you need to save text, code, or generated content to a file on the local filesystem.
    Supports automatic formatting for data structures in various formats (JSON, YAML, CSV, table).
    Also supports binary content for image and other binary files.
    """
    formatter: Optional[OutputFormatter] = None
    parameters: dict = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "(required) The content to save to the file. Can be a string, data structure (dict/list), or binary data.",
            },
            "file_path": {
                "type": "string",
                "description": "(required) The path where the file should be saved, including filename and extension.",
            },
            "format": {
                "type": "string",
                "description": "(optional) Format to use when saving data structures (json, yaml, csv, table, text).",
                "enum": ["json", "yaml", "csv", "table", "text", "auto", "binary"],
                "default": "auto",
            },
            "mode": {
                "type": "string",
                "description": "(optional) The file opening mode. Default is 'w' for write. Use 'a' for append, 'wb' for binary write.",
                "enum": ["w", "a", "wb", "ab"],
                "default": "w",
            },
            "indent": {
                "type": "integer",
                "description": "(optional) Number of spaces for indentation in JSON format.",
                "default": 2,
            },
            "pretty": {
                "type": "boolean",
                "description": "(optional) Whether to format the output for improved readability.",
                "default": True,
            },
        },
        "required": ["content", "file_path"],
    }

    def __init__(self):
        # Initialize BaseTool without parameters, matching the pattern used in DataProcessor
        super().__init__()
        self.formatter = OutputFormatter()

    async def execute(
        self,
        content: Union[str, Dict[str, Any], List, bytes],
        file_path: str,
        format: str = "auto",
        mode: str = "w",
        indent: int = 2,
        pretty: bool = True
    ) -> ToolResult:
        """
        Save content to a file at the specified path with formatting options.

        Args:
            content: The content to save (string, data structure, or binary data)
            file_path: The path where the file should be saved
            format: Format to use for data structures (json, yaml, csv, table, text, auto, binary)
            mode: The file opening mode ('w' for write, 'a' for append, 'wb' for binary write)
            indent: Number of spaces for indentation in JSON format
            pretty: Whether to format the output for improved readability

        Returns:
            ToolResult with a message indicating the result of the operation
        """
        try:
            # Validate file path
            if not file_path or not isinstance(file_path, str):
                return ToolResult(output="Invalid file path provided", error=True)

            # Check for potentially unsafe paths
            if self._is_unsafe_path(file_path):
                error_msg = f"Potentially unsafe file path: {file_path}"
                logger.error(error_msg)
                return ToolResult(output=error_msg, error=True)

            # Normalize path to prevent directory traversal attacks
            file_path = os.path.normpath(file_path)

            # Ensure the directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                except OSError as e:
                    error_msg = f"Failed to create directory {directory}: {str(e)}"
                    logger.error(error_msg)
                    return ToolResult(output=error_msg, error=True)

            # Handle binary content
            if isinstance(content, bytes) or format == "binary":
                return await self._save_binary_content(content, file_path, mode)

            # Determine format based on file extension if set to auto
            if format == "auto":
                format = self._detect_format_from_path(file_path)

            # Format the content if it's a data structure and pretty printing is enabled
            final_content = self._prepare_content(content, format, indent, pretty)

            # Write to the file
            try:
                # Use binary mode if content appears to be binary
                if self._is_likely_binary(final_content):
                    logger.warning(f"Content appears to be binary, switching to binary mode for file: {file_path}")
                    return await self._save_binary_content(final_content.encode('utf-8', errors='replace'), file_path, 'wb')

                async with aiofiles.open(file_path, mode, encoding="utf-8") as file:
                    await file.write(final_content)
            except UnicodeEncodeError:
                # Fallback to a different encoding if UTF-8 fails
                logger.warning(f"UTF-8 encoding failed, trying with 'utf-8-sig' for file: {file_path}")
                async with aiofiles.open(file_path, mode, encoding="utf-8-sig") as file:
                    await file.write(final_content)

            return ToolResult(output=f"Content successfully saved to {file_path}")
        except PermissionError:
            error_msg = f"Permission denied when writing to {file_path}"
            logger.error(error_msg)
            return ToolResult(output=error_msg, error=True)
        except FileNotFoundError:
            error_msg = f"Directory does not exist or cannot be created: {directory}"
            logger.error(error_msg)
            return ToolResult(output=error_msg, error=True)
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return ToolResult(output=f"Error saving file: {str(e)}", error=True)

    async def _save_binary_content(self, content: bytes, file_path: str, mode: str = "wb") -> ToolResult:
        """Save binary content to a file"""
        try:
            # Ensure mode is binary
            if not mode.endswith('b'):
                mode = mode + 'b'

            # Convert to bytes if not already
            if not isinstance(content, bytes):
                if isinstance(content, str):
                    content = content.encode('utf-8')
                else:
                    content = str(content).encode('utf-8')

            async with aiofiles.open(file_path, mode) as file:
                await file.write(content)

            return ToolResult(output=f"Binary content successfully saved to {file_path}")
        except Exception as e:
            error_msg = f"Error saving binary file: {str(e)}"
            logger.error(error_msg)
            return ToolResult(output=error_msg, error=True)

    def _is_unsafe_path(self, file_path: str) -> bool:
        """Check if a file path might be unsafe"""
        # Check for absolute paths that might be system critical
        unsafe_patterns = [
            r'^/etc/',
            r'^/var/log/',
            r'^/boot/',
            r'^/proc/',
            r'^/sys/',
            r'^/dev/',
            r'^C:\\Windows\\',
            r'^C:\\Program Files',
            r'^C:\\Windows\\System32',
        ]

        for pattern in unsafe_patterns:
            if re.match(pattern, file_path, re.IGNORECASE):
                return True

        return False

    def _is_likely_binary(self, content: str) -> bool:
        """Determine if content is likely binary based on null bytes or high concentration of non-printable chars"""
        if not isinstance(content, str):
            return False

        # Check for null bytes which indicate binary content
        if '\x00' in content:
            return True

        # Check for high concentration of non-printable characters
        non_printable = 0
        sample_size = min(len(content), 1000)  # Check first 1000 chars
        for i in range(sample_size):
            if ord(content[i]) < 32 and content[i] not in '\n\r\t':
                non_printable += 1

        # If more than 10% are non-printable, likely binary
        return non_printable > (sample_size * 0.1)

    def _detect_format_from_path(self, file_path: str) -> str:
        """Detect the appropriate format based on file extension"""
        if not file_path:
            return "text"

        extension = os.path.splitext(file_path)[1].lower()

        # Binary formats
        binary_extensions = {
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".webp",  # Images
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",  # Documents
            ".zip", ".tar", ".gz", ".7z", ".rar",  # Archives
            ".exe", ".dll", ".so", ".bin", ".dat"  # Executables and binary data
        }

        if extension in binary_extensions:
            return "binary"

        format_map = {
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".csv": "csv",
            ".md": "text",
            ".txt": "text",
            ".html": "text",
            ".htm": "text",
            ".xml": "text",
            ".py": "text",
            ".js": "text",
            ".ts": "text",
            ".css": "text",
            ".sql": "text",
            ".sh": "text",
            ".bat": "text",
            ".ps1": "text",
            ".toml": "text",
            ".ini": "text",
            ".cfg": "text",
        }

        return format_map.get(extension, "text")

    def _prepare_content(self, content: Union[str, Dict, List], format: str, indent: int, pretty: bool) -> str:
        """Prepare content for saving, applying formatting if needed"""
        # Handle None or empty content
        if content is None:
            return ""

        # If content is already a string and pretty printing is disabled, return as is
        if isinstance(content, str) and not pretty:
            return content

        # If content is a data structure, format it according to the specified format
        if isinstance(content, (dict, list)) and pretty:
            try:
                return self.formatter.format(content, format_type=format, indent=indent)
            except Exception as e:
                logger.warning(f"Error formatting content: {str(e)}. Falling back to string representation.")
                return str(content)

        # For string content with pretty printing enabled, try to parse and format if it looks like JSON
        if isinstance(content, str) and pretty:
            content_stripped = content.strip()
            if content_stripped and content_stripped[0] in ('{', '[') and content_stripped[-1] in ('}', ']'):
                try:
                    data = json.loads(content)
                    return self.formatter.format(data, format_type=format, indent=indent)
                except json.JSONDecodeError:
                    # Not valid JSON, return as is
                    pass

        # Default case: return content as string
        return str(content)
