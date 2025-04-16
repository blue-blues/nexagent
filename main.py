import asyncio
import traceback
import os
from typing import Optional

from app.flow.integrated_flow import IntegratedFlow
from app.logger import logger
from app.session import session_manager
from app.timeline.timeline import Timeline
from app.timeline.events import create_user_input_event, create_error_event
from app.integration.adaptive_nexagent import AdaptiveNexagentIntegration


async def process_request(prompt: str, adaptive_nexagent: AdaptiveNexagentIntegration, session_id: Optional[str] = None, processing_mode: str = "auto") -> dict:
    """
    Process a user request through the adaptive nexagent integration.

    Args:
        prompt: The user's input prompt
        adaptive_nexagent: The AdaptiveNexagentIntegration instance
        session_id: Optional session ID
        processing_mode: Processing mode ('auto', 'chat', or 'agent')

    Returns:
        A dictionary with the processing results
    """
    try:
        # Process the prompt through the adaptive nexagent
        response = await adaptive_nexagent.process_prompt(
            prompt=prompt,
            conversation_id=session_id,
            context={"processing_mode": processing_mode}
        )

        # Extract the result and timeline
        result = response["response"]
        timeline = adaptive_nexagent.timeline
        success = response["success"]
        elapsed_time = response.get("execution_time", 0)

        return {
            "result": result,
            "success": success,
            "elapsed_time": elapsed_time,
            "timeline": timeline,
            "task_type": response.get("task_type"),
            "agent_id": response.get("agent_id"),
            "tools_used": response.get("tools_used", []),
            "interaction_id": response.get("interaction_id")
        }

    except asyncio.TimeoutError:
        error_msg = "Request processing timed out"
        logger.error(error_msg)

        # Create a timeline for this error
        timeline = Timeline()
        create_user_input_event(timeline, prompt)
        create_error_event(timeline, error_msg, "timeout")

        return {
            "result": "Request timed out. Please try a simpler request.",
            "success": False,
            "error": error_msg,
            "error_type": "TimeoutError",
            "timeline": timeline
        }

    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        # Create a timeline for this error
        timeline = Timeline()
        create_user_input_event(timeline, prompt)
        create_error_event(timeline, str(e), "execution")

        return {
            "result": f"An error occurred while processing your request: {str(e)}",
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timeline": timeline
        }


async def main():
    """
    Main entry point for the Adaptive Nexagent system.

    This script initializes the Adaptive Nexagent which provides a unified interface
    with continuous learning capabilities. The system automatically adapts to user
    interactions and improves over time.
    """
    print("\n=== Adaptive Nexagent AI Assistant System ===\n")
    print("This system combines general-purpose and specialized capabilities with adaptive learning.")
    print("Your interactions help the system improve over time.")

    # Create the learning system state directory if it doesn't exist
    state_dir = os.path.join(os.path.expanduser("~"), ".nexagent", "learning_state")
    os.makedirs(state_dir, exist_ok=True)

    # Initialize the integrated flow
    flow = IntegratedFlow()

    # Initialize the adaptive nexagent integration
    try:
        # Get tools from the integrated agent if available
        if hasattr(flow, 'integrated_agent') and hasattr(flow.integrated_agent, 'available_tools'):
            tools = flow.integrated_agent.available_tools
        else:
            # If available_tools is not available, create a new ToolCollection
            from app.tools import ToolCollection
            from app.tools.code import PythonExecute
            from app.tools.browser import WebSearch, EnhancedBrowserTool
            from app.tools.conversation_file_saver import ConversationFileSaver
            from app.tools.message_classifier import MessageClassifier
            # TaskAnalytics is not available yet, so we'll skip it for now
            # Use Terminate from the terminate module
            from app.tools.terminate import Terminate

            tools = ToolCollection(
                PythonExecute(),
                WebSearch(),
                EnhancedBrowserTool(),
                ConversationFileSaver(),
                MessageClassifier(),
                # TaskAnalytics is not available yet
                Terminate()
            )

        # Initialize with both flow and tools to ensure proper setup
        adaptive_nexagent = AdaptiveNexagentIntegration(
            flow=flow,
            tools=tools,
            state_directory=state_dir
        )
    except Exception as e:
        logger.error(f"Error initializing adaptive nexagent: {str(e)}")
        # Fallback to simpler initialization
        adaptive_nexagent = AdaptiveNexagentIntegration(
            flow=flow,
            state_directory=state_dir
        )

    # Create a session
    session = session_manager.create_session()

    print("\nAdaptive Nexagent initialized. Type 'exit' to quit.")
    print("Type 'stats' to see performance statistics.")
    print("Type 'feedback' to provide feedback on the last response.")
    print("Type 'save' to save the learning system state.")
    print("Type 'mode chat' to use chat mode, 'mode agent' to use agent mode, or 'mode auto' to use automatic detection.")

    # Default processing mode
    processing_mode = "auto"

    try:
        while True:
            # Get user input
            if session.is_waiting():
                prompt = input("\nWhat would you like to do next? ")
            else:
                prompt = input("\nEnter your prompt: ")

            if prompt.lower() == 'exit':
                print("Saving learning state and exiting...")
                adaptive_nexagent.save_state(state_dir)
                break

            if prompt.lower() == 'stats':
                # Display performance statistics
                print("\nGenerating performance report...")
                report = adaptive_nexagent.generate_performance_report()
                print("\n" + report)
                continue

            if prompt.lower().startswith('mode '):
                mode = prompt.lower().split(' ')[1] if len(prompt.lower().split(' ')) > 1 else ''
                if mode in ['chat', 'agent', 'auto']:
                    processing_mode = mode
                    print(f"Processing mode set to: {processing_mode}")
                else:
                    print("Invalid mode. Available modes: 'chat', 'agent', 'auto'")
                continue

            if prompt.lower() == 'feedback':
                if not adaptive_nexagent.last_interaction_id:
                    print("No previous interaction to provide feedback for.")
                    continue

                # Get feedback from the user
                rating = input("Rate the last response (1-5): ")
                try:
                    rating = int(rating)
                    if rating < 1 or rating > 5:
                        raise ValueError("Rating must be between 1 and 5")
                except ValueError:
                    print("Invalid rating. Please enter a number between 1 and 5.")
                    continue

                feedback_text = input("Provide any additional feedback: ")

                # Record the feedback
                adaptive_nexagent.record_explicit_feedback(
                    interaction_id=adaptive_nexagent.last_interaction_id,
                    content=feedback_text,
                    rating=rating,
                    positive=rating > 3
                )

                print("Thank you for your feedback!")
                continue

            if prompt.lower() == 'save':
                print("Saving learning system state...")
                adaptive_nexagent.save_state(state_dir)
                print("State saved successfully.")
                continue

            if not prompt.strip():
                logger.warning("Empty prompt provided. Please enter a valid prompt.")
                continue

            # Mark session as active
            session.mark_active()

            # Process the request through the adaptive nexagent
            logger.warning(f"Processing your request in {processing_mode} mode...")
            print(f"Processing your request in {processing_mode} mode... (This may take a moment)")

            # Process the request with a timeout
            try:
                response = await asyncio.wait_for(
                    process_request(prompt, adaptive_nexagent, session.session_id, processing_mode),
                    timeout=3600,  # 60 minute timeout for the entire execution
                )

                # Extract the result and metadata
                result = response["result"]
                timeline = response["timeline"]
                success = response["success"]
                elapsed_time = response.get("elapsed_time", 0)
                task_type = response.get("task_type", "unknown")
                agent_id = response.get("agent_id", "unknown")
                tools_used = response.get("tools_used", [])

                # Log the result
                if success:
                    logger.info(f"Request processed successfully in {elapsed_time:.2f} seconds")
                    print(f"\nRequest completed in {elapsed_time:.2f} seconds")
                    print(f"Task type: {task_type}")
                    print(f"Agent used: {agent_id}")
                    if tools_used:
                        print(f"Tools used: {', '.join(tools_used)}")
                else:
                    logger.warning(f"Request processing failed: {response.get('error', 'Unknown error')}")
                    print(f"\nRequest failed: {response.get('error', 'Unknown error')}")

                # Record task in session history with timeline data
                session.add_task(
                    prompt=prompt,
                    result=result,
                    success=success,
                    timeline_data=timeline.to_dict() if timeline else None,
                    metadata={
                        "task_type": task_type,
                        "agent_id": agent_id,
                        "tools_used": tools_used,
                        "interaction_id": response.get("interaction_id")
                    }
                )

                # Mark session as waiting for next input
                session.mark_waiting()

            except asyncio.TimeoutError:
                logger.error("Request processing timed out after 1 hour")
                print("\nRequest timed out after 1 hour. Please try a simpler request.")
                session.add_task(
                    prompt=prompt,
                    result="Request timed out after 1 hour. Please try a simpler request.",
                    success=False
                )
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {str(e)}")
                logger.error(traceback.format_exc())
                print(f"\nAn unexpected error occurred: {str(e)}")
                session.add_task(
                    prompt=prompt,
                    result=f"An unexpected error occurred: {str(e)}",
                    success=False
                )

    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
        print("Saving learning state before exiting...")
        adaptive_nexagent.save_state(state_dir)
        session.mark_terminated()


if __name__ == "__main__":
    asyncio.run(main())
