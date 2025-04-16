"""
Script to analyze performance and generate reports.

This script analyzes the performance of the Adaptive Learning System
and generates comprehensive reports.
"""

import os
import sys
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.learning import AdaptiveLearningSystem
from app.logger import logger


def analyze_performance(state_dir: str, days: int = 30, task_type: str = None):
    """
    Analyze performance and generate reports.
    
    Args:
        state_dir: Directory where the learning system state is stored
        days: Number of days to analyze
        task_type: Optional task type to filter by
    """
    print(f"Analyzing performance for the past {days} days...")
    
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
    
    # Get statistics
    stats = learning_system.memory_store.get_statistics()
    print(f"Current statistics:")
    print(f"- Total interactions: {stats.get('total_count', 0)}")
    print(f"- Success rate: {stats.get('success_rate', 0) * 100:.1f}%")
    print(f"- Average execution time: {stats.get('avg_execution_time', 0):.2f} seconds")
    
    # Analyze performance
    if task_type:
        print(f"\nAnalyzing performance for task type: {task_type}")
        analysis = learning_system.analyze_performance(task_type=task_type, days=days)
    else:
        print(f"\nAnalyzing overall performance")
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
    print(f"\nIdentifying strengths and weaknesses...")
    strengths_and_weaknesses = learning_system.identify_strengths_and_weaknesses()
    
    print(f"Strengths:")
    for strength in strengths_and_weaknesses.get("strengths", []):
        print(f"- {strength['task_type']}: {strength['success_rate'] * 100:.1f}% success rate")
    
    print(f"\nWeaknesses:")
    for weakness in strengths_and_weaknesses.get("weaknesses", []):
        print(f"- {weakness['task_type']}: {weakness['success_rate'] * 100:.1f}% success rate")
    
    # Get improvement priorities
    print(f"\nImprovement priorities:")
    priorities = learning_system.get_improvement_priorities()
    
    print(f"Task types:")
    for task_type in priorities.get("task_types", []):
        print(f"- {task_type['task_type']}: {task_type['negative_rate'] * 100:.1f}% negative feedback - {task_type['priority']} priority")
    
    print(f"\nTools:")
    for tool in priorities.get("tools", []):
        print(f"- {tool['tool']}: {tool['negative_rate'] * 100:.1f}% negative feedback - {tool['priority']} priority")
    
    # Generate reports
    print(f"\nGenerating reports...")
    performance_report = learning_system.generate_performance_report()
    feedback_report = learning_system.generate_feedback_report()
    
    # Save reports to files
    reports_dir = os.path.join(state_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(os.path.join(reports_dir, f"performance_report_{timestamp}.md"), "w") as f:
        f.write(performance_report)
    
    with open(os.path.join(reports_dir, f"feedback_report_{timestamp}.md"), "w") as f:
        f.write(feedback_report)
    
    print(f"\nReports saved to {reports_dir}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Analyze performance and generate reports")
    parser.add_argument("--state-dir", type=str, default=os.path.join(os.path.expanduser("~"), ".nexagent", "learning_state"),
                        help="Directory where the learning system state is stored")
    parser.add_argument("--days", type=int, default=30,
                        help="Number of days to analyze")
    parser.add_argument("--task-type", type=str, default=None,
                        help="Task type to filter by")
    
    args = parser.parse_args()
    
    # Run the analysis
    analyze_performance(args.state_dir, args.days, args.task_type)


if __name__ == "__main__":
    main()
