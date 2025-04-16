#!/usr/bin/env python
"""
Test script for the AdaptiveLearningSystem.

This script tests the AdaptiveLearningSystem to ensure it's working correctly,
particularly the load_state and save_state methods.
"""

import os
import sys
import tempfile
import shutil
import traceback

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.learning import AdaptiveLearningSystem
from app.logger import logger


def test_adaptive_learning_system():
    """Test the AdaptiveLearningSystem."""
    print("Starting test of AdaptiveLearningSystem...")

    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")

    try:
        # Create an AdaptiveLearningSystem
        print("Creating AdaptiveLearningSystem...")
        try:
            learning_system = AdaptiveLearningSystem()
            print("Successfully created AdaptiveLearningSystem")
            print(f"Type: {type(learning_system)}")
            print(f"Dir: {dir(learning_system)}")
        except Exception as e:
            print(f"Error creating AdaptiveLearningSystem: {str(e)}")
            traceback.print_exc()
            return

        # Test saving state
        print("\nTesting save_state...")
        try:
            learning_system.save_state(temp_dir)
            print("Successfully called save_state")
        except Exception as e:
            print(f"Error calling save_state: {str(e)}")
            traceback.print_exc()

        # Verify that the files were created
        strategies_path = os.path.join(temp_dir, "strategies.json")
        counter_path = os.path.join(temp_dir, "counter.json")

        if os.path.exists(strategies_path):
            print(f"✓ Strategies file created at {strategies_path}")
        else:
            print(f"✗ Strategies file not created at {strategies_path}")

        if os.path.exists(counter_path):
            print(f"✓ Counter file created at {counter_path}")
        else:
            print(f"✗ Counter file not created at {counter_path}")

        # Test loading state
        print("\nTesting load_state...")
        try:
            learning_system.load_state(temp_dir)
            print("Successfully called load_state")
        except Exception as e:
            print(f"Error calling load_state: {str(e)}")
            traceback.print_exc()

        print("\nTest completed!")

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        traceback.print_exc()

    finally:
        # Clean up the temporary directory
        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Error cleaning up temporary directory: {str(e)}")


if __name__ == "__main__":
    test_adaptive_learning_system()
