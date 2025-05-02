from typing import Dict, Any, Union, List, Optional
import json
import csv
import os
from pathlib import Path
from urllib.parse import urlparse
from app.config import config
from app.logger import logger
from app.exceptions import DataProcessingError
from app.tools.output_formatter import OutputFormatter
from app.tools.base import BaseTool, ToolResult


class DataProcessor(BaseTool):
    name: str = "data_processor"
    description: str = """Process and format data in various human-readable formats.
    Use this tool to transform raw data into well-structured, readable formats.
    Supports JSON, YAML, CSV, and table formats with proper indentation and structure.
    """
    formatter: Optional[OutputFormatter] = None
    allowed_domains: Optional[List[str]] = None
    allowed_content_types: Optional[List[str]] = None
    parameters: dict = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "(required) The data to process and format.",
            },
            "format": {
                "type": "string",
                "description": "(optional) The desired output format (json, yaml, csv, table, text).",
                "enum": ["json", "yaml", "csv", "table", "text"],
                "default": "json",
            },
            "output_file": {
                "type": "string",
                "description": "(optional) Path to save the formatted output. If not provided, returns formatted string.",
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

    def __init__(self):
        super().__init__()
        self.formatter = OutputFormatter()
        self.allowed_domains = getattr(config.llm.get('default', {}), 'allowed_domains', None)
        self.allowed_content_types = getattr(config.llm.get('default', {}), 'allowed_content_types', [])

    async def execute(
        self,
        data: Union[Dict[str, Any], List],
        format: str = "json",
        output_file: Optional[str] = None,
        indent: int = 2,
        sort_keys: bool = False
    ) -> ToolResult:
        """Process and format data with options for improved readability.

        Args:
            data: The data to process and format
            format: The desired output format (json, yaml, csv, table, text)
            output_file: Optional path to save the formatted output
            indent: Number of spaces for indentation in JSON format
            sort_keys: Whether to sort dictionary keys in output

        Returns:
            ToolResult with formatted data or file path information
        """
        try:
            # Format the data according to the specified format
            formatted_data = self.formatter.format(
                data,
                format_type=format,
                indent=indent,
                sort_keys=sort_keys
            )

            # Save to file if output_file is specified
            if output_file:
                output_path = Path(output_file)
                self._save_formatted_data(formatted_data, output_path)
                return ToolResult(output=f"Data successfully processed and saved to {output_file}")
            else:
                # Return the formatted data directly
                return ToolResult(output=formatted_data)

        except Exception as e:
            logger.error(f"Data processing failed: {str(e)}")
            return ToolResult(output=f"Error processing data: {str(e)}", error=str(e))

    def process_from_url(self, data: Dict[str, Any], url: str, content_type: str, format: str = "json") -> Path:
        """Process scraped data with ethical validation and format detection"""
        self._validate_source(url, content_type)

        try:
            output_path = self._get_output_path(url, format)
            formatted_data = self.formatter.format(data, format_type=format)
            self._save_formatted_data(formatted_data, output_path)
            logger.info(f"Successfully processed data from {url}")
            return output_path
        except Exception as e:
            logger.error(f"Data processing failed: {str(e)}")
            raise DataProcessingError(f"Data processing error: {str(e)}")

    def _validate_source(self, url: str, content_type: str):
        """Validate data source against ethical scraping policies"""
        parsed_url = urlparse(url)

        if self.allowed_domains and parsed_url.netloc not in self.allowed_domains:
            raise ValueError(f"Domain {parsed_url.netloc} not in allowed list")

        if self.allowed_content_types and content_type not in self.allowed_content_types:
            raise ValueError(f"Content type {content_type} not permitted")

    def _get_output_path(self, url: str, format: str = "json") -> Path:
        """Generate output path based on source URL and format"""
        parsed_url = urlparse(url)
        base_name = parsed_url.path.split('/')[-1] or 'data'
        extension = "." + format if format != "table" else ".txt"
        return Path(config.PROJECT_ROOT / 'processed_data' / f"{base_name}{extension}")

    def _save_formatted_data(self, formatted_data: str, output_path: Path):
        """Save formatted data to the specified path"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_data)