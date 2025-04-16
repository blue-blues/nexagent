"""
Enhanced Nexagent Demo

This script demonstrates the enhanced Nexagent Bot with Devika-inspired features,
including AI planning, contextual keyword extraction, and state tracking.
"""

import asyncio
import time
import json
import os
import sys

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.enhanced_planning_agent import EnhancedPlanningAgent
from app.agent.context_agent import ContextAgent
from app.agent.reporter_agent import ReporterAgent
from app.flow.enhanced_planning_flow import EnhancedPlanningFlow
from app.state.agent_state_tracker import AgentStateTracker, ActionType
from app.tool.input_parser import InputParser
from app.tool.keyword_extractor import KeywordExtractor
from app.tool.state_visualizer import StateVisualizer


async def main():
    """
    Run the enhanced Nexagent demo.
    """
    print("\n=== Enhanced Nexagent Demo ===\n")
    print("This demo showcases the enhanced Nexagent Bot with Devika-inspired features.")
    
    # Create a shared state tracker
    state_tracker = AgentStateTracker()
    
    # Create the agents
    context_agent = ContextAgent()
    planning_agent = EnhancedPlanningAgent()
    reporter_agent = ReporterAgent(state_tracker=state_tracker)
    
    # Create the planning flow
    planning_flow = EnhancedPlanningFlow(
        agents={"planning": planning_agent},
        primary_agent_key="planning"
    )
    
    # Track the demo start
    demo_start_action = state_tracker.track_action(
        agent_id="demo",
        action_type=ActionType.SYSTEM,
        description="Started Enhanced Nexagent Demo"
    )
    state_tracker.start_action(demo_start_action)
    
    # Get user input
    print("\nEnter a high-level task for the enhanced Nexagent Bot to plan and execute:")
    user_request = input("> ")
    
    if not user_request.strip():
        print("No input provided. Exiting demo.")
        return
    
    # Track the user request
    request_action = state_tracker.track_action(
        agent_id="user",
        action_type=ActionType.USER_INTERACTION,
        description=f"User request: {user_request[:50]}...",
        metadata={"request": user_request}
    )
    state_tracker.start_action(request_action)
    state_tracker.complete_action(request_action)
    
    # Step 1: Analyze the request with the context agent
    print("\n=== Step 1: Analyzing Request ===")
    context_analysis_action = state_tracker.track_action(
        agent_id="demo",
        action_type=ActionType.SYSTEM,
        description="Analyzing request with context agent"
    )
    state_tracker.start_action(context_analysis_action)
    
    context_result = await context_agent.analyze_request(user_request)
    
    # Extract keywords for display
    keywords = [k.get("keyword") for k in context_result.get("keywords", [])]
    domain = context_result.get("domain", "Unknown")
    
    print(f"Detected Domain: {domain}")
    print(f"Extracted Keywords: {', '.join(keywords[:10])}")
    
    state_tracker.complete_action(context_analysis_action, result={"domain": domain, "keywords": keywords})
    
    # Step 2: Create a plan with the enhanced planning agent
    print("\n=== Step 2: Creating Plan ===")
    planning_action = state_tracker.track_action(
        agent_id="demo",
        action_type=ActionType.SYSTEM,
        description="Creating plan with enhanced planning agent"
    )
    state_tracker.start_action(planning_action)
    
    # Update the reporter agent state
    await reporter_agent.update_agent_state("demo", {
        "current_task": "Creating plan",
        "progress": 0.3,
        "status": "in_progress"
    })
    
    # Generate a progress report
    progress_report = await reporter_agent.generate_progress_report()
    print(progress_report)
    
    # Create the plan
    plan_result = await planning_flow.execute(user_request)
    
    print("\n=== Generated Plan ===")
    print(plan_result)
    
    state_tracker.complete_action(planning_action, result={"plan_created": True})
    
    # Update the reporter agent state
    await reporter_agent.update_agent_state("demo", {
        "current_task": "Plan created",
        "progress": 0.7,
        "status": "completed"
    })
    
    # Generate a final report
    print("\n=== Final Execution Summary ===")
    final_report = await reporter_agent.generate_execution_summary()
    print(final_report)
    
    # Complete the demo
    state_tracker.complete_action(demo_start_action)
    
    print("\n=== Demo Completed ===")
    print("The enhanced Nexagent Bot has successfully analyzed the request and created a plan.")
    print("In a full implementation, the plan would now be executed by specialized agents.")


if __name__ == "__main__":
    asyncio.run(main())
