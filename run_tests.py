"""
Script to run tests with proper Python path.
"""

import os
import sys
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Run the tests
if __name__ == "__main__":
    # Run all tests in the tests directory
    test_suite = unittest.defaultTestLoader.discover('tests')
    unittest.TextTestRunner().run(test_suite)
