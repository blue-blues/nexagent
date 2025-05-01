#!/usr/bin/env python3
"""
Nexagent Main Entry Point

This is the main entry point for the Nexagent application.
"""

import asyncio
import traceback
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Import from the new architecture
from app.ui.cli.cli import main as cli_main
from app.utils.logging.logger import logger

# Legacy imports - will be migrated to the new architecture
from app.flow.integrated_flow import IntegratedFlow
from app.session import session_manager
from app.timeline.timeline import Timeline
from app.timeline.events import create_user_input_event, create_error_event
from app.integration.adaptive_nexagent import AdaptiveNexagentIntegration
from app.agent.manus_agent import ManusAgent


async def process_request(prompt: str, adaptive_nexagent: AdaptiveNexagentIntegration, session_id: Optional[str] = None, processing_mode: str = "auto", file_attachment: Optional[str] = None) -> dict:
    """
    Process a user request through the adaptive nexagent integration.

    Args:
        prompt: The user's input prompt
        adaptive_nexagent: The AdaptiveNexagentIntegration instance
        session_id: Optional session ID
        processing_mode: Processing mode ('auto', 'chat', or 'agent')
        file_attachment: Optional path to a file attachment

    Returns:
        A dictionary with the processing results
    """
    try:
        # Process the prompt through the adaptive nexagent
        context = {"processing_mode": processing_mode}

        # Add file attachment to context if provided
        if file_attachment and os.path.exists(file_attachment):
            context["file_attachment"] = file_attachment

        response = await adaptive_nexagent.process_prompt(
            prompt=prompt,
            conversation_id=session_id,
            context=context
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
    # Variable to store attached file path
    attached_file = None
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
            from app.tools.file_attachment_processor import FileAttachmentProcessor
            from app.tools.planning import PlanningTool
            # TaskAnalytics is not available yet, so we'll skip it for now
            # Use Terminate from the terminate module
            from app.tools.terminate import Terminate

            tools = ToolCollection(
                PythonExecute(),
                WebSearch(),
                EnhancedBrowserTool(),
                ConversationFileSaver(),
                MessageClassifier(),
                FileAttachmentProcessor(),
                PlanningTool(),
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
    print("Type 'upload <file_path>' to upload and process a file.")
    print("Type 'attach <file_path>' to attach a file to your next message.")
    print("The system is running in Manus AI mode.")

    # Always use Manus mode
    processing_mode = "manus"

    # Initialize ManusAgent
    manus_agent = ManusAgent()
    logger.info("ManusAgent initialized with timeline and memory capabilities")

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
                print("Only Manus mode is available. The system is already in Manus mode.")
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

            if prompt.lower().startswith('attach '):
                file_path = prompt[7:].strip()
                if not os.path.exists(file_path):
                    print(f"File not found: {file_path}")
                    attached_file = None
                else:
                    # Create a conversation folder if needed
                    conversation_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations", session.session_id))
                    attachments_folder = conversation_folder / "attachments"
                    attachments_folder.mkdir(parents=True, exist_ok=True)

                    # Copy the file to the attachments folder
                    file_name = os.path.basename(file_path)
                    destination_path = str(attachments_folder / file_name)
                    shutil.copy2(file_path, destination_path)

                    attached_file = destination_path
                    print(f"File attached: {file_name}")
                    print(f"File saved to: {destination_path}")
                    print("The file will be processed with your next message.")
                continue

            if prompt.lower().startswith('upload '):
                file_path = prompt[7:].strip()
                if not os.path.exists(file_path):
                    print(f"File not found: {file_path}")
                    continue

                print(f"Processing file: {file_path}")
                try:
                    # Create a conversation folder if needed
                    conversation_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations", session.session_id))
                    attachments_folder = conversation_folder / "attachments"
                    attachments_folder.mkdir(parents=True, exist_ok=True)

                    # Copy the file to the attachments folder
                    file_name = os.path.basename(file_path)
                    destination_path = str(attachments_folder / file_name)
                    shutil.copy2(file_path, destination_path)

                    # Process the file
                    processor = FileAttachmentProcessor()
                    result = await processor.execute(
                        file_path=destination_path,
                        conversation_id=session.session_id,
                        process_content=True
                    )

                    if result.error:
                        print(f"Error processing file: {result.output}")
                    else:
                        print(f"File uploaded successfully: {file_name}")
                        print(f"File saved to: {destination_path}")

                        # If content was processed, ask the user if they want to analyze it
                        if result.output.get("content"):
                            analyze = input("\nWould you like to analyze this file? (y/n): ")
                            if analyze.lower() == 'y':
                                # Create a prompt with the file content
                                file_prompt = f"Please analyze the content of the file '{file_name}':\n\n{result.output.get('content')}"

                                # Process the request
                                print("Processing file analysis request... (This may take a moment)")
                                response = await asyncio.wait_for(
                                    process_request(file_prompt, adaptive_nexagent, session.session_id, processing_mode),
                                    timeout=3600,  # 60 minute timeout
                                )

                                # Extract the result and metadata
                                result = response["result"]
                                timeline = response["timeline"]
                                success = response["success"]
                                elapsed_time = response.get("elapsed_time", 0)

                                # Log the result
                                if success:
                                    logger.info(f"File analysis completed successfully in {elapsed_time:.2f} seconds")
                                    print(f"\nFile analysis completed in {elapsed_time:.2f} seconds")
                                else:
                                    logger.warning(f"File analysis failed: {response.get('error', 'Unknown error')}")
                                    print(f"\nFile analysis failed: {response.get('error', 'Unknown error')}")

                                # Record task in session history
                                session.add_task(
                                    prompt=file_prompt,
                                    result=result,
                                    success=success,
                                    timeline_data=timeline.to_dict() if timeline else None
                                )
                except Exception as e:
                    logger.error(f"Error uploading file: {str(e)}")
                    print(f"Error uploading file: {str(e)}")

                continue

            if not prompt.strip():
                logger.warning("Empty prompt provided. Please enter a valid prompt.")
                continue

            # Mark session as active
            session.mark_active()

            # Process the request through the ManusAgent
            logger.warning("Processing your request with Manus AI...")
            print("Processing your request with Manus AI... (This may take a moment)")

            # Process the request with a timeout
            try:
                # Check if there's an attached file
                if attached_file:
                    print(f"Processing with attached file: {attached_file}")
                    # Add file attachment to prompt
                    prompt = f"[File attached: {os.path.basename(attached_file)}]\n\n{prompt}"
                    # Reset the attached file after using it
                    attached_file = None

                # Use ManusAgent directly
                start_time = asyncio.get_event_loop().time()
                result = await manus_agent.run(prompt)
                elapsed_time = asyncio.get_event_loop().time() - start_time

                # Create a response similar to what process_request returns
                response = {
                    "result": result,
                    "success": True,
                    "elapsed_time": elapsed_time,
                    "timeline": manus_agent.timeline,
                    "task_type": "manus_task",
                    "agent_id": "manus_agent",
                    "tools_used": [tool.name for tool in manus_agent.available_tools.tools if hasattr(tool, "name")],
                    "interaction_id": f"manus_{int(start_time)}"
                }

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


def legacy_main():
    """Legacy main function - will be removed in future versions"""
    return asyncio.run(main())


if __name__ == "__main__":
    # Check if we should use the new CLI or the legacy interface
    if "--new" in sys.argv:
        # Remove the --new flag from sys.argv
        sys.argv.remove("--new")
        # Use the new CLI
        sys.exit(cli_main())
    else:
        # Use the legacy interface with a deprecation warning
        print("WARNING: Using legacy interface. This will be removed in future versions.")
        print("Use --new flag to use the new interface.")
        legacy_main()
