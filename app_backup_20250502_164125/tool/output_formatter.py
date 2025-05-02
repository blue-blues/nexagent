import json
import csv
import tabulate
import yaml
from typing import Dict, Any, List, Union
from pathlib import Path
from app.logger import logger


class OutputFormatter:
    """A tool for formatting output data in various human-readable formats.
    
    This tool provides methods to format data in different styles (JSON, YAML, CSV, Table)
    with proper indentation, coloring, and structure to improve readability.
    """
    
    def __init__(self):
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
    
    def format_yaml(self, data: Union[Dict, List]) -> str:
        """Format data as YAML.
        
        Args:
            data: The data to format
            
        Returns:
            Formatted YAML string
        """
        try:
            return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"Error formatting YAML: {str(e)}")
            return self.format_json(data)  # Fallback to JSON
    
    def format_csv(self, data: Union[Dict, List]) -> str:
        """Format data as CSV.
        
        For dictionaries, keys become column headers and values become rows.
        For lists of dictionaries, keys from the first item become headers.
        
        Args:
            data: The data to format
            
        Returns:
            Formatted CSV string
        """
        try:
            output = []
            if isinstance(data, dict):
                # Convert simple dict to CSV with keys as headers
                output.append(','.join([str(k) for k in data.keys()]))
                output.append(','.join([str(v) for v in data.values()]))
            elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
                # Use keys from first dict as headers
                if data:
                    headers = list(data[0].keys())
                    output.append(','.join([str(h) for h in headers]))
                    for item in data:
                        output.append(','.join([str(item.get(h, '')) for h in headers]))
            else:
                # Fallback for other structures
                return f"Cannot format as CSV: {type(data).__name__}"
                
            return '\n'.join(output)
        except Exception as e:
            logger.error(f"Error formatting CSV: {str(e)}")
            return self.format_text(data)  # Fallback to text
    
    def format_table(self, data: Union[Dict, List], headers: str = "keys") -> str:
        """Format data as an ASCII table.
        
        Args:
            data: The data to format
            headers: Table header style ('keys', 'firstrow', etc.)
            
        Returns:
            Formatted table string
        """
        try:
            if isinstance(data, dict):
                # Convert dict to table with keys and values columns
                table_data = [[k, v] for k, v in data.items()]
                return tabulate.tabulate(table_data, headers=["Key", "Value"], tablefmt="grid")
            elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
                # Convert list of dicts to table
                return tabulate.tabulate(data, headers=headers, tablefmt="grid")
            else:
                # Fallback for other structures
                return f"Cannot format as table: {type(data).__name__}"
        except Exception as e:
            logger.error(f"Error formatting table: {str(e)}")
            return self.format_text(data)  # Fallback to text
    
    def format_text(self, data: Any) -> str:
        """Format data as plain text with basic structure.
        
        Args:
            data: The data to format
            
        Returns:
            Formatted text string
        """
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                lines.append(f"{k}: {v}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = []
            for i, item in enumerate(data):
                lines.append(f"{i+1}. {item}")
            return "\n".join(lines)
        else:
            return str(data)