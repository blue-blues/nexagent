import asyncio
import sys

from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.flow.integrated_flow import IntegratedFlow
from app.logger import logger
from app.session import session_manager


async def main():
    """
    Main entry point for the integrated AI assistant flow system.
    
    This script initializes the IntegratedFlow which provides a unified interface
    to both general-purpose and software development AI assistants. The system
    automatically routes queries to the appropriate specialized agent based on
    content analysis.
    """
    print("\n=== Integrated AI Assistant Flow System ===\n")
    print("This system combines:")
    print("1. General-purpose AI Assistant - for everyday tasks and queries")
    print("2. Software Development AI Assistant - for coding and technical tasks")
    print("\nYour queries will be automatically routed to the appropriate assistant.")
    
    # Initialize the integrated flow
    flow = IntegratedFlow()
    session = session_manager.create_session()
    
    print("\nIntegrated AI Assistant Flow initialized. Type 'exit' to quit.")
    print("Type 'stats' to see routing statistics.")
    
    try:
        while True:
            # Get user input
            if session.is_waiting():
                prompt = input("\nWhat would you like to do next? ")
            else:
                prompt = input("\nEnter your prompt: ")
                
            if prompt.lower() == 'exit':
                print("Exiting...")
                break
                
            if prompt.lower() == 'stats':
                # Display routing statistics
                if not flow.integrated_agent.routing_history:
                    print("No queries processed yet.")
                else:
                    total = len(flow.integrated_agent.routing_history)
                    dev_count = sum(1 for entry in flow.integrated_agent.routing_history if entry["is_code_related"])
                    general_count = total - dev_count
                    
                    print(f"\nRouting Statistics:")
                    print(f"Total queries processed: {total}")
                    print(f"Routed to Software Dev Agent: {dev_count} ({dev_count/total*100:.1f}%)")
                    print(f"Routed to General-Purpose Agent: {general_count} ({general_count/total*100:.1f}%)")
                    
                    # Show the last 5 routing decisions
                    print("\nRecent routing decisions:")
                    for i, entry in enumerate(flow.integrated_agent.routing_history[-5:]):
                        agent_type = "Software Dev" if entry["is_code_related"] else "General-Purpose"
                        prompt_preview = entry["prompt"][:50] + "..." if len(entry["prompt"]) > 50 else entry["prompt"]
                        print(f"{i+1}. '{prompt_preview}' → {agent_type} Agent")
                continue
                
            if not prompt.strip():
                logger.warning("Empty prompt provided. Please enter a valid prompt.")
                continue
            
            # Mark session as active
            session.mark_active()
            
            # Process the request through the integrated flow
            logger.warning("Processing your request...")
            try:
                start_time = time.time()
                result = await asyncio.wait_for(
                    flow.execute(prompt),
                    timeout=3600,  # 60 minute timeout for the entire execution
                )
                elapsed_time = time.time() - start_time
                logger.info(f"Request processed in {elapsed_time:.2f} seconds")
                logger.info(result)
                
                # Record task in session history
                success = flow.integrated_agent.state == "FINISHED"
                session.add_task(prompt, result, success)
                
                # Mark session as waiting for next input
                session.mark_waiting()
                
            except asyncio.TimeoutError:
                logger.error("Request processing timed out after 1 hour")
                logger.info(
                    "Operation terminated due to timeout. Please try a simpler request."
                )
                session.add_task(prompt, "Request timed out", False)
            
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
        session.mark_terminated()
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        session.mark_terminated()


if __name__ == "__main__":
    # Add missing import
    import time
    
    asyncio.run(main())