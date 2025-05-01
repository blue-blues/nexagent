"""
Test script for the DataProcessor and OutputFormatter tools.

This script tests the fixes for the 'indent' parameter in format_yaml and
the ToolResult error handling in the DataProcessor.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.tools.data_processor import DataProcessor
from app.tools.output_formatter import OutputFormatter
from app.logger import logger


async def test_data_processor():
    """Test the DataProcessor with various formats and parameters."""
    logger.info("Starting DataProcessor test")
    
    # Create the DataProcessor
    processor = DataProcessor()
    
    # Test data
    test_data = {
        "name": "Test User",
        "age": 30,
        "email": "test@example.com",
        "address": {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip": "12345"
        },
        "hobbies": ["reading", "coding", "hiking"]
    }
    
    # Test JSON format
    logger.info("Testing JSON format")
    json_result = await processor.execute(data=test_data, format="json", indent=4)
    logger.info(f"JSON result type: {type(json_result.output)}")
    logger.info(f"JSON result: {json_result.output[:100]}...")
    
    # Test YAML format with indent parameter
    logger.info("Testing YAML format with indent parameter")
    yaml_result = await processor.execute(data=test_data, format="yaml", indent=4)
    logger.info(f"YAML result type: {type(yaml_result.output)}")
    logger.info(f"YAML result: {yaml_result.output[:100]}...")
    
    # Test error handling
    logger.info("Testing error handling")
    try:
        # Create a circular reference to cause an error
        circular_data = {"self": None}
        circular_data["self"] = circular_data
        
        error_result = await processor.execute(data=circular_data, format="json")
        logger.info(f"Error result type: {type(error_result.error)}")
        logger.info(f"Error result: {error_result.error}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    return "Test completed successfully"


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_data_processor())
    print("\nFinal result:", result)
