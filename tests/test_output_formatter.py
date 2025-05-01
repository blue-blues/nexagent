"""
Test script for the OutputFormatter tool.

This script tests the fixes for the OutputFormatter tool, ensuring that all format methods
accept the indent and sort_keys parameters.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.tools.output_formatter import OutputFormatter
from app.logger import logger


async def test_output_formatter():
    """Test the OutputFormatter with various formats and parameters."""
    logger.info("Starting OutputFormatter test")
    
    # Create the OutputFormatter
    formatter = OutputFormatter()
    
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
    
    # Test all format methods with indent and sort_keys parameters
    formats = ["json", "yaml", "csv", "table", "text"]
    
    for format_type in formats:
        logger.info(f"Testing {format_type} format with indent=4 and sort_keys=True")
        try:
            result = await formatter.execute(
                data=test_data,
                format_type=format_type,
                indent=4,
                sort_keys=True
            )
            logger.info(f"{format_type.upper()} result type: {type(result.output)}")
            logger.info(f"{format_type.upper()} result: {result.output[:100]}...")
            logger.info(f"{format_type.upper()} format test passed")
        except Exception as e:
            logger.error(f"Error testing {format_type} format: {e}")
            return f"Test failed for {format_type} format: {e}"
    
    return "All format tests completed successfully"


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_output_formatter())
    print("\nFinal result:", result)
