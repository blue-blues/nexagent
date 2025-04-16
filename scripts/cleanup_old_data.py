"""
Script to clean up old data from the Adaptive Learning System.

This script removes old interaction records to manage storage growth
while preserving important knowledge.
"""

import os
import sys
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.learning import AdaptiveLearningSystem
from app.logger import logger


def cleanup_old_data(state_dir: str, days: int = 90):
    """
    Clean up old data from the Adaptive Learning System.
    
    Args:
        state_dir: Directory where the learning system state is stored
        days: Number of days to keep data for
    """
    print(f"Cleaning up data older than {days} days...")
    
    # Create the learning system
    learning_system = AdaptiveLearningSystem()
    
    # Load the state if it exists
    try:
        learning_system.load_state(state_dir)
        print(f"Loaded learning system state from {state_dir}")
    except Exception as e:
        print(f"Error loading learning system state: {str(e)}")
        print("Starting with a fresh learning system")
        return
    
    # Get statistics before cleanup
    stats_before = learning_system.memory_store.get_statistics()
    print(f"Current statistics:")
    print(f"- Total interactions: {stats_before.get('total_count', 0)}")
    
    # Extract knowledge before cleanup to ensure it's preserved
    print(f"\nExtracting knowledge before cleanup...")
    learning_system.extract_knowledge()
    
    # Clean up old records
    deleted_count = learning_system.memory_store.clear_old_records(days=days)
    
    print(f"\nCleanup results:")
    print(f"- Deleted {deleted_count} old records")
    
    # Get statistics after cleanup
    stats_after = learning_system.memory_store.get_statistics()
    print(f"\nStatistics after cleanup:")
    print(f"- Total interactions: {stats_after.get('total_count', 0)}")
    print(f"- Records removed: {stats_before.get('total_count', 0) - stats_after.get('total_count', 0)}")
    
    # Save the updated state
    learning_system.save_state(state_dir)
    print(f"\nSaved updated learning system state to {state_dir}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Clean up old data from the Adaptive Learning System")
    parser.add_argument("--state-dir", type=str, default=os.path.join(os.path.expanduser("~"), ".nexagent", "learning_state"),
                        help="Directory where the learning system state is stored")
    parser.add_argument("--days", type=int, default=90,
                        help="Number of days to keep data for")
    
    args = parser.parse_args()
    
    # Run the cleanup
    cleanup_old_data(args.state_dir, args.days)


if __name__ == "__main__":
    main()
