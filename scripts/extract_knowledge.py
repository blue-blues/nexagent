"""
Script to extract knowledge from past interactions.

This script analyzes past interactions stored in the Adaptive Learning System
and extracts generalizable knowledge that can be used to improve future responses.
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.learning import AdaptiveLearningSystem
from app.logger import logger


async def extract_knowledge(state_dir: str, task_type: str = None, limit: int = 100):
    """
    Extract knowledge from past interactions.
    
    Args:
        state_dir: Directory where the learning system state is stored
        task_type: Optional task type to filter by
        limit: Maximum number of interactions to analyze
    """
    print(f"Extracting knowledge from past interactions...")
    
    # Create the learning system
    learning_system = AdaptiveLearningSystem()
    
    # Load the state if it exists
    try:
        learning_system.load_state(state_dir)
        print(f"Loaded learning system state from {state_dir}")
    except Exception as e:
        print(f"Error loading learning system state: {str(e)}")
        print("Starting with a fresh learning system")
    
    # Get statistics before extraction
    stats_before = learning_system.memory_store.get_statistics()
    print(f"Current statistics:")
    print(f"- Total interactions: {stats_before.get('total_count', 0)}")
    print(f"- Success rate: {stats_before.get('success_rate', 0) * 100:.1f}%")
    
    # Extract knowledge
    result = learning_system.extract_knowledge(task_type=task_type, limit=limit)
    
    print(f"\nKnowledge extraction results:")
    print(f"- Interactions analyzed: {result.get('interactions_analyzed', 0)}")
    print(f"- Nodes created: {result.get('nodes_created', 0)}")
    print(f"- Relations created: {result.get('relations_created', 0)}")
    print(f"- Templates created: {result.get('templates_created', 0)}")
    print(f"- Rules created: {result.get('rules_created', 0)}")
    
    # Adapt strategies based on performance
    adaptations = learning_system.adapt_strategies()
    
    print(f"\nStrategy adaptation results:")
    print(f"- Adaptations made: {len(adaptations)}")
    for i, adaptation in enumerate(adaptations):
        print(f"  {i+1}. Task type: {adaptation.get('task_type')}")
        print(f"     Original strategy: {adaptation.get('original_strategy_id')}")
        print(f"     Variant strategy: {adaptation.get('variant_strategy_id')}")
        print(f"     Parameter changes: {adaptation.get('parameter_changes')}")
    
    # Get improvement priorities
    priorities = learning_system.get_improvement_priorities()
    
    print(f"\nImprovement priorities:")
    print(f"- Task types:")
    for task_type in priorities.get("task_types", []):
        print(f"  - {task_type['task_type']}: {task_type['negative_rate'] * 100:.1f}% negative feedback - {task_type['priority']} priority")
    
    print(f"- Tools:")
    for tool in priorities.get("tools", []):
        print(f"  - {tool['tool']}: {tool['negative_rate'] * 100:.1f}% negative feedback - {tool['priority']} priority")
    
    # Save the updated state
    learning_system.save_state(state_dir)
    print(f"\nSaved updated learning system state to {state_dir}")
    
    # Generate reports
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
    parser = argparse.ArgumentParser(description="Extract knowledge from past interactions")
    parser.add_argument("--state-dir", type=str, default=os.path.join(os.path.expanduser("~"), ".nexagent", "learning_state"),
                        help="Directory where the learning system state is stored")
    parser.add_argument("--task-type", type=str, default=None,
                        help="Task type to filter by")
    parser.add_argument("--limit", type=int, default=100,
                        help="Maximum number of interactions to analyze")
    
    args = parser.parse_args()
    
    # Create the state directory if it doesn't exist
    os.makedirs(args.state_dir, exist_ok=True)
    
    # Run the extraction
    asyncio.run(extract_knowledge(args.state_dir, args.task_type, args.limit))


if __name__ == "__main__":
    main()
