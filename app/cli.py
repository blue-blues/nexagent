import asyncio
import time
from typing import Dict
import uuid

from app.flow.integrated_flow import IntegratedFlow
from app.logger import logger
from app.session import session_manager
from datetime import datetime

# Active flows and sessions
active_flows: Dict[str, IntegratedFlow] = {}

async def process_message(message: str, session_id: str = None):
    """Process a chat message"""
    try:
        # Get or create session ID
        session_id = session_id or str(uuid.uuid4())
        
        # Get or create flow for this session
        if session_id not in active_flows:
            active_flows[session_id] = IntegratedFlow()
            session_manager.create_session(session_id=session_id)
        
        flow = active_flows[session_id]
        session = session_manager.get_session(session_id)
        
        # Process the message
        logger.info(f"Processing message for session {session_id}: {message}")
        session.mark_active()
        
        # Execute the flow with the message
        result = await asyncio.wait_for(
            flow.execute(message),
            timeout=300,  # 5 minute timeout
        )
        
        # Record task in session history
        success = flow.integrated_agent.state == "FINISHED"
        session.add_task(message, result, success)
        session.mark_waiting()
        
        # Get routing information
        is_code_related = None
        if flow.integrated_agent.routing_history:
            is_code_related = flow.integrated_agent.routing_history[-1]["is_code_related"]
        
        return {
            "message": result,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "is_code_related": is_code_related
        }
    
    except asyncio.TimeoutError:
        logger.error("Request processing timed out")
        return {"error": "Request timed out", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        return {"error": f"Error processing chat: {str(e)}", "session_id": session_id}

async def main():
    """Main entry point for the CLI version of NexAgent"""
    print("\n=== NexAgent CLI ===\n")
    print("This system combines general-purpose and software development capabilities in one interface.")
    print("Your queries will be automatically routed to the appropriate assistant based on content.")
    
    # Create a session
    session_id = str(uuid.uuid4())
    session = session_manager.create_session(session_id=session_id)
    
    print("\nNexAgent initialized. Type 'exit' to quit.")
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
                # Get the flow for this session
                flow = active_flows.get(session_id)
                if not flow or not flow.integrated_agent.routing_history:
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
            
            # Process the request
            logger.warning("Processing your request...")
            try:
                start_time = time.time()
                result = await process_message(prompt, session_id)
                elapsed_time = time.time() - start_time
                logger.info(f"Request processed in {elapsed_time:.2f} seconds")
                
                if "error" in result:
                    print(f"\nError: {result['error']}")
                else:
                    print(f"\n{result['message']}")
                
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"\nAn error occurred: {e}")
            
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
        session.mark_terminated()

if __name__ == "__main__":
    asyncio.run(main())