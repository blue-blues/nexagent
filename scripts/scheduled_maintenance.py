"""
Scheduled maintenance script for the Adaptive Learning System.

This script performs maintenance tasks on the Adaptive Learning System,
including extracting knowledge, analyzing performance, and cleaning up old data.
It can be scheduled to run automatically using cron (Linux/macOS) or Task Scheduler (Windows).

Example cron entry to run daily at 3 AM:
0 3 * * * /path/to/python /path/to/scripts/scheduled_maintenance.py

Example Task Scheduler command:
python C:\\path\\to\\scripts\\scheduled_maintenance.py
"""

import os
import sys
import time
import argparse
import asyncio
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.learning import AdaptiveLearningSystem
from app.logger import logger


async def perform_maintenance(state_dir: str, task: str = "all", days: int = 30, limit: int = 100):
    """
    Perform maintenance tasks on the Adaptive Learning System.
    
    Args:
        state_dir: Directory where the learning system state is stored
        task: Maintenance task to perform (extract, analyze, cleanup, or all)
        days: Number of days to analyze or keep data for
        limit: Maximum number of interactions to analyze
    """
    print(f"=== Adaptive Learning System Maintenance ===")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"State directory: {state_dir}")
    
    # Create the learning system
    learning_system = AdaptiveLearningSystem()
    
    # Load the state if it exists
    try:
        learning_system.load_state(state_dir)
        print(f"Loaded learning system state from {state_dir}")
    except Exception as e:
        print(f"Error loading learning system state: {str(e)}")
        print("Starting with a fresh learning system")
    
    # Get statistics before maintenance
    stats_before = learning_system.memory_store.get_statistics()
    print(f"\nCurrent statistics:")
    print(f"- Total interactions: {stats_before.get('total_count', 0)}")
    print(f"- Success rate: {stats_before.get('success_rate', 0) * 100:.1f}%")
    print(f"- Average execution time: {stats_before.get('avg_execution_time', 0):.2f} seconds")
    
    # Perform the requested maintenance task(s)
    if task in ["extract", "all"]:
        await extract_knowledge(learning_system, limit)
    
    if task in ["analyze", "all"]:
        analyze_performance(learning_system, days)
    
    if task in ["cleanup", "all"]:
        cleanup_old_data(learning_system, days * 3)  # Keep data for 3x the analysis period
    
    # Save the updated state
    learning_system.save_state(state_dir)
    print(f"\nSaved updated learning system state to {state_dir}")
    
    # Get statistics after maintenance
    stats_after = learning_system.memory_store.get_statistics()
    print(f"\nStatistics after maintenance:")
    print(f"- Total interactions: {stats_after.get('total_count', 0)}")
    print(f"- Success rate: {stats_after.get('success_rate', 0) * 100:.1f}%")
    print(f"- Average execution time: {stats_after.get('avg_execution_time', 0):.2f} seconds")
    
    print(f"\nMaintenance completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


async def extract_knowledge(learning_system: AdaptiveLearningSystem, limit: int):
    """
    Extract knowledge from past interactions.
    
    Args:
        learning_system: The learning system to extract knowledge from
        limit: Maximum number of interactions to analyze
    """
    print(f"\n=== Extracting Knowledge ===")
    
    # Extract knowledge
    result = learning_system.extract_knowledge(limit=limit)
    
    print(f"Knowledge extraction results:")
    print(f"- Interactions analyzed: {result.get('interactions_analyzed', 0)}")
    print(f"- Nodes created: {result.get('nodes_created', 0)}")
    print(f"- Relations created: {result.get('relations_created', 0)}")
    print(f"- Templates created: {result.get('templates_created', 0)}")
    print(f"- Rules created: {result.get('rules_created', 0)}")
    
    # Adapt strategies based on performance
    adaptations = learning_system.adapt_strategies()
    
    print(f"\nStrategy adaptation results:")
    print(f"- Adaptations made: {len(adaptations)}")
    for i, adaptation in enumerate(adaptations[:5]):  # Show only the first 5 adaptations
        print(f"  {i+1}. Task type: {adaptation.get('task_type')}")
        print(f"     Original strategy: {adaptation.get('original_strategy_id')}")
        print(f"     Variant strategy: {adaptation.get('variant_strategy_id')}")


def analyze_performance(learning_system: AdaptiveLearningSystem, days: int):
    """
    Analyze performance and generate reports.
    
    Args:
        learning_system: The learning system to analyze
        days: Number of days to analyze
    """
    print(f"\n=== Analyzing Performance ===")
    
    # Analyze overall performance
    analysis = learning_system.analyze_performance(days=days)
    
    print(f"Analysis results:")
    print(f"- Records analyzed: {analysis.get('record_count', 0)}")
    
    if "success_rate" in analysis:
        success_rate = analysis["success_rate"]["success_rate"] * 100
        print(f"- Success rate: {success_rate:.1f}%")
    
    if "execution_time" in analysis:
        avg_time = analysis["execution_time"]["avg_execution_time"]
        print(f"- Average execution time: {avg_time:.2f} seconds")
    
    # Identify strengths and weaknesses
    strengths_and_weaknesses = learning_system.identify_strengths_and_weaknesses()
    
    print(f"\nStrengths:")
    for strength in strengths_and_weaknesses.get("strengths", [])[:3]:  # Show only the top 3 strengths
        print(f"- {strength['task_type']}: {strength['success_rate'] * 100:.1f}% success rate")
    
    print(f"\nWeaknesses:")
    for weakness in strengths_and_weaknesses.get("weaknesses", [])[:3]:  # Show only the top 3 weaknesses
        print(f"- {weakness['task_type']}: {weakness['success_rate'] * 100:.1f}% success rate")
    
    # Generate reports
    performance_report = learning_system.generate_performance_report()
    feedback_report = learning_system.generate_feedback_report()
    
    # Save reports to files
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(os.path.join(reports_dir, f"performance_report_{timestamp}.md"), "w") as f:
        f.write(performance_report)
    
    with open(os.path.join(reports_dir, f"feedback_report_{timestamp}.md"), "w") as f:
        f.write(feedback_report)
    
    print(f"\nReports saved to {reports_dir}")


def cleanup_old_data(learning_system: AdaptiveLearningSystem, days: int):
    """
    Clean up old data from the Adaptive Learning System.
    
    Args:
        learning_system: The learning system to clean up
        days: Number of days to keep data for
    """
    print(f"\n=== Cleaning Up Old Data ===")
    
    # Get statistics before cleanup
    stats_before = learning_system.memory_store.get_statistics()
    
    # Clean up old records
    deleted_count = learning_system.memory_store.clear_old_records(days=days)
    
    print(f"Cleanup results:")
    print(f"- Deleted {deleted_count} records older than {days} days")
    
    # Get statistics after cleanup
    stats_after = learning_system.memory_store.get_statistics()
    print(f"- Records remaining: {stats_after.get('total_count', 0)}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Perform maintenance tasks on the Adaptive Learning System")
    parser.add_argument("--state-dir", type=str, default=os.path.join(os.path.expanduser("~"), ".nexagent", "learning_state"),
                        help="Directory where the learning system state is stored")
    parser.add_argument("--task", type=str, choices=["extract", "analyze", "cleanup", "all"], default="all",
                        help="Maintenance task to perform")
    parser.add_argument("--days", type=int, default=30,
                        help="Number of days to analyze or keep data for")
    parser.add_argument("--limit", type=int, default=100,
                        help="Maximum number of interactions to analyze")
    
    args = parser.parse_args()
    
    # Create the state directory if it doesn't exist
    os.makedirs(args.state_dir, exist_ok=True)
    
    # Run the maintenance
    asyncio.run(perform_maintenance(args.state_dir, args.task, args.days, args.limit))


if __name__ == "__main__":
    main()
