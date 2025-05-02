import json
import csv
import tabulate
import yaml
from typing import Dict, Any, List, Union, Optional
from pathlib import Path
from app.logger import logger
from app.tools.base import BaseTool, ToolResult


class OutputFormatter(BaseTool):
    """A tool for formatting output data in various human-readable formats.

    This tool provides methods to format data in different styles (JSON, YAML, CSV, Table)
    with proper indentation, coloring, and structure to improve readability.
    """

    name: str = "output_formatter"
    description: str = "Format data in various human-readable formats (JSON, YAML, CSV, Table)"
    parameters: dict = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "(required) The data to format (dictionary or list).",
            },
            "format_type": {
                "type": "string",
                "description": "(optional) The desired output format (json, yaml, csv, table, text).",
                "default": "json",
                "enum": ["json", "yaml", "csv", "table", "text"],
            },
            "indent": {
                "type": "integer",
                "description": "(optional) Number of spaces for indentation in JSON format.",
                "default": 2,
            },
            "sort_keys": {
                "type": "boolean",
                "description": "(optional) Whether to sort dictionary keys in output.",
                "default": False,
            },
        },
        "required": ["data"],
    }
    formats: Dict[str, Any] = None

    def __init__(self):
        super().__init__()
        self.formats = {
            "json": self.format_json,
            "yaml": self.format_yaml,
            "csv": self.format_csv,
            "table": self.format_table,
            "text": self.format_text
        }

    def format(self, data: Union[Dict, List], format_type: str = "json", **kwargs) -> str:
        """Format data according to the specified format type.

        Args:
            data: The data to format (dictionary or list)
            format_type: The desired output format (json, yaml, csv, table, text)
            **kwargs: Additional format-specific parameters

        Returns:
            Formatted string representation of the data
        """
        if format_type not in self.formats:
            logger.warning(f"Unknown format type: {format_type}, defaulting to JSON")
            format_type = "json"

        return self.formats[format_type](data, **kwargs)

    def format_json(self, data: Union[Dict, List], indent: int = 2, sort_keys: bool = False) -> str:
        """Format data as indented, readable JSON.

        Args:
            data: The data to format
            indent: Number of spaces for indentation
            sort_keys: Whether to sort dictionary keys

        Returns:
            Formatted JSON string
        """
        try:
            return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error formatting JSON: {str(e)}")
            return str(data)

    def format_yaml(self, data: Union[Dict, List], indent: int = 2, sort_keys: bool = False) -> str:
        """Format data as YAML.

        Args:
            data: The data to format
            indent: Number of spaces for indentation (default: 2)
            sort_keys: Whether to sort dictionary keys (default: False)

        Returns:
            Formatted YAML string
        """
        try:
            # PyYAML doesn't directly support indent as a parameter like json.dumps
            # Instead, it uses a default_flow_style=False for block style formatting
            # and sort_keys for key sorting
            return yaml.dump(
                data,
                default_flow_style=False,
                sort_keys=sort_keys,
                allow_unicode=True,
                indent=indent  # This sets the indentation level
            )
        except Exception as e:
            logger.error(f"Error formatting YAML: {str(e)}")
            return self.format_json(data, indent=indent, sort_keys=sort_keys)  # Fallback to JSON

    def format_csv(self, data: Union[Dict, List], indent: int = 2, sort_keys: bool = False) -> str:
        """Format data as CSV.

        For dictionaries, keys become column headers and values become rows.
        For lists of dictionaries, keys from the first item become headers.

        Args:
            data: The data to format
            indent: Number of spaces for indentation (ignored for CSV format, included for API compatibility)
            sort_keys: Whether to sort dictionary keys (used when converting dict to CSV)

        Returns:
            Formatted CSV string
        """
        try:
            output = []
            if isinstance(data, dict):
                # Convert simple dict to CSV with keys as headers
                # Sort keys if requested
                if sort_keys:
                    keys = sorted(data.keys())
                    values = [data[k] for k in keys]
                else:
                    keys = data.keys()
                    values = data.values()

                output.append(','.join([str(k) for k in keys]))
                output.append(','.join([str(v) for v in values]))
            elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
                # Use keys from first dict as headers
                if data:
                    # Get all unique keys from all dictionaries
                    all_keys = set()
                    for item in data:
                        all_keys.update(item.keys())

                    # Sort keys if requested
                    headers = sorted(all_keys) if sort_keys else list(all_keys)

                    output.append(','.join([str(h) for h in headers]))
                    for item in data:
                        output.append(','.join([str(item.get(h, '')) for h in headers]))
            else:
                # Fallback for other structures
                return f"Cannot format as CSV: {type(data).__name__}"

            return '\n'.join(output)
        except Exception as e:
            logger.error(f"Error formatting CSV: {str(e)}")
            return self.format_text(data, indent=indent, sort_keys=sort_keys)  # Fallback to text

    def format_table(self, data: Union[Dict, List], headers: str = "keys", indent: int = 2, sort_keys: bool = False) -> str:
        """Format data as an ASCII table.

        Args:
            data: The data to format
            headers: Table header style ('keys', 'firstrow', etc.)
            indent: Number of spaces for indentation (ignored for table format, included for API compatibility)
            sort_keys: Whether to sort dictionary keys (used when converting dict to table)

        Returns:
            Formatted table string
        """
        try:
            if isinstance(data, dict):
                # Convert dict to table with keys and values columns
                # Sort keys if requested
                items = sorted(data.items()) if sort_keys else data.items()
                table_data = [[k, v] for k, v in items]
                return tabulate.tabulate(table_data, headers=["Key", "Value"], tablefmt="grid")
            elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
                # Convert list of dicts to table
                return tabulate.tabulate(data, headers=headers, tablefmt="grid")
            else:
                # Fallback for other structures
                return f"Cannot format as table: {type(data).__name__}"
        except Exception as e:
            logger.error(f"Error formatting table: {str(e)}")
            return self.format_text(data, indent=indent, sort_keys=sort_keys)  # Fallback to text

    def format_text(self, data: Any, indent: int = 2, sort_keys: bool = False) -> str:
        """Format data as plain text with basic structure.

        Args:
            data: The data to format
            indent: Number of spaces for indentation (used for nested structures)
            sort_keys: Whether to sort dictionary keys

        Returns:
            Formatted text string
        """
        if isinstance(data, dict):
            lines = []
            # Sort keys if requested
            items = sorted(data.items()) if sort_keys else data.items()
            for k, v in items:
                if isinstance(v, (dict, list)):
                    # Format nested structures with indentation
                    v_str = self.format_text(v, indent, sort_keys)
                    # Indent nested lines
                    v_str = "\n" + "\n".join(" " * indent + line for line in v_str.split("\n"))
                    lines.append(f"{k}:{v_str}")
                else:
                    lines.append(f"{k}: {v}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = []
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    # Format nested structures with indentation
                    item_str = self.format_text(item, indent, sort_keys)
                    # Indent nested lines
                    item_str = "\n" + "\n".join(" " * indent + line for line in item_str.split("\n"))
                    lines.append(f"{i+1}.{item_str}")
                else:
                    lines.append(f"{i+1}. {item}")
            return "\n".join(lines)
        else:
            return str(data)

    async def execute(
        self,
        data: Union[Dict[str, Any], List],
        format_type: str = "json",
        indent: int = 2,
        sort_keys: bool = False
    ) -> ToolResult:
        """Execute the tool to format data with options for improved readability.

        Args:
            data: The data to format
            format_type: The desired output format (json, yaml, csv, table, text)
            indent: Number of spaces for indentation in JSON format
            sort_keys: Whether to sort dictionary keys in output

        Returns:
            ToolResult with formatted data
        """
        try:
            # Format the data according to the specified format
            formatted_data = self.format(
                data,
                format_type=format_type,
                indent=indent,
                sort_keys=sort_keys
            )

            # Return the formatted data
            return ToolResult(output=formatted_data)

        except Exception as e:
            logger.error(f"Data formatting failed: {str(e)}")
            return ToolResult(output=f"Error formatting data: {str(e)}", error=str(e))