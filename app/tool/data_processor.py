from typing import Dict, Any
import json
import csv
from pathlib import Path
from urllib.parse import urlparse
from app.config import config
from app.logger import logger
from app.exceptions import DataProcessingError


class DataProcessor:
    def __init__(self):
        self.allowed_domains = config.llm['default'].allowed_domains
        self.allowed_content_types = config.llm['default'].allowed_content_types

    def process(self, data: Dict[str, Any], url: str, content_type: str) -> Path:
        """Process scraped data with ethical validation and format detection"""
        self._validate_source(url, content_type)
        
        try:
            output_path = self._get_output_path(url)
            self._save_data(data, output_path)
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
        
        if content_type not in self.allowed_content_types:
            raise ValueError(f"Content type {content_type} not permitted")

    def _get_output_path(self, url: str) -> Path:
        """Generate output path based on source URL and content type"""
        parsed_url = urlparse(url)
        base_name = parsed_url.path.split('/')[-1] or 'data'
        return Path(config.PROJECT_ROOT / 'processed_data' / f"{base_name}.json")

    def _save_data(self, data: Dict[str, Any], output_path: Path):
        """Save processed data in appropriate format"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.suffix == '.json':
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
        elif output_path.suffix == '.csv':
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                for key, value in data.items():
                    writer.writerow([key, str(value)])
        else:
            raise ValueError("Unsupported output format")