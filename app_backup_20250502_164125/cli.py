import asyncio
import time
import os
import shutil
from pathlib import Path
from typing import Dict, Optional, List
import uuid
import re

from app.flow.integrated_flow import IntegratedFlow
from app.logger import logger
from app.session import session_manager
from app.tools.file_attachment_processor import FileAttachmentProcessor
from app.tools.planning import PlanningTool
from datetime import datetime

# Active flows and sessions
active_flows: Dict[str, IntegratedFlow] = {}

# Store active plans for each session
active_plans: Dict[str, str] = {}

async def handle_plan_command(prompt: str, session_id: str, flows: Dict[str, IntegratedFlow]):
    """
    Handle the plan command for managing plan versions.

    Args:
        prompt: The user's input prompt
        session_id: The current session ID
        flows: Dictionary of active flows
    """
    # Get the flow for this session
    flow = flows.get(session_id)
    if not flow:
        print("Error: No active session found.")
        return

    # Get the integrated agent
    agent = flow.integrated_agent
    if not agent:
        print("Error: No integrated agent available.")
        return

    # Create a planning tool if not available in the agent's tools
    planning_tool = None

    # Try to find the planning tool in the agent's tools
    try:
        for tool in agent.available_tools.tools:
            if tool.name == "planning":
                planning_tool = tool
                break
    except (AttributeError, TypeError) as e:
        logger.warning(f"Error accessing agent tools: {str(e)}")

    # If planning tool not found, create a new one
    if not planning_tool:
        try:
            from app.tools.planning import PlanningTool
            planning_tool = PlanningTool()
            logger.info("Created new PlanningTool instance")
        except ImportError as e:
            print(f"Error: Planning tool module not available. {str(e)}")
            return

    # Parse the command
    parts = prompt.split(maxsplit=1)
    if len(parts) == 1:
        # Just 'plan' - show help
        show_plan_help()
        return

    command = parts[1].strip()

    # Handle different plan commands
    if command == "help":
        show_plan_help()
    elif command == "list":
        # List all plans
        result = await planning_tool.execute(command="list")
        print(result.output)
    elif command.startswith("create "):
        # Create a new plan
        # Format: plan create <plan_id> <title>
        create_parts = command.split(maxsplit=2)
        if len(create_parts) < 3:
            print("Error: Missing plan ID or title.")
            print("Usage: plan create <plan_id> <title>")
            return

        plan_id = create_parts[1]
        title = create_parts[2]

        result = await planning_tool.execute(
            command="create",
            plan_id=plan_id,
            title=title
        )

        print(result.output)

        # Set as active plan for this session
        active_plans[session_id] = plan_id
    elif command.startswith("get "):
        # Get a plan
        # Format: plan get <plan_id>
        get_parts = command.split(maxsplit=1)
        if len(get_parts) < 2:
            print("Error: Missing plan ID.")
            print("Usage: plan get <plan_id>")
            return

        plan_id = get_parts[1]

        result = await planning_tool.execute(
            command="get",
            plan_id=plan_id
        )

        print(result.output)
    elif command.startswith("update "):
        # Update a plan
        # Format: plan update <plan_id> <title>
        update_parts = command.split(maxsplit=2)
        if len(update_parts) < 3:
            print("Error: Missing plan ID or title.")
            print("Usage: plan update <plan_id> <title>")
            return

        plan_id = update_parts[1]
        title = update_parts[2]

        result = await planning_tool.execute(
            command="update",
            plan_id=plan_id,
            title=title
        )

        print(result.output)
    elif command.startswith("version create "):
        # Create a version
        # Format: plan version create <plan_id> <version_id> <description>
        version_parts = command.split(maxsplit=4)
        if len(version_parts) < 4:
            print("Error: Missing parameters.")
            print("Usage: plan version create <plan_id> <version_id> <description>")
            return

        plan_id = version_parts[2]
        version_id = version_parts[3]
        description = version_parts[4] if len(version_parts) > 4 else f"Version {version_id}"

        result = await planning_tool.execute(
            command="create_version",
            plan_id=plan_id,
            version_id=version_id,
            version_description=description
        )

        print(result.output)
    elif command.startswith("version list "):
        # List versions
        # Format: plan version list <plan_id>
        version_parts = command.split(maxsplit=2)
        if len(version_parts) < 3:
            print("Error: Missing plan ID.")
            print("Usage: plan version list <plan_id>")
            return

        plan_id = version_parts[2]

        result = await planning_tool.execute(
            command="list_versions",
            plan_id=plan_id
        )

        print(result.output)
    elif command.startswith("version get "):
        # Get a version
        # Format: plan version get <plan_id> <version_id>
        version_parts = command.split(maxsplit=3)
        if len(version_parts) < 4:
            print("Error: Missing parameters.")
            print("Usage: plan version get <plan_id> <version_id>")
            return

        plan_id = version_parts[2]
        version_id = version_parts[3]

        result = await planning_tool.execute(
            command="get_version",
            plan_id=plan_id,
            version_id=version_id
        )

        print(result.output)
    elif command.startswith("version compare "):
        # Compare versions
        # Format: plan version compare <plan_id> <version_id1> <version_id2>
        version_parts = command.split(maxsplit=4)
        if len(version_parts) < 5:
            print("Error: Missing parameters.")
            print("Usage: plan version compare <plan_id> <version_id1> <version_id2>")
            return

        plan_id = version_parts[2]
        version_id = version_parts[3]
        compare_with_version = version_parts[4]

        result = await planning_tool.execute(
            command="compare_versions",
            plan_id=plan_id,
            version_id=version_id,
            compare_with_version=compare_with_version
        )

        print(result.output)
    elif command.startswith("version rollback "):
        # Rollback to a version
        # Format: plan version rollback <plan_id> <version_id>
        version_parts = command.split(maxsplit=3)
        if len(version_parts) < 4:
            print("Error: Missing parameters.")
            print("Usage: plan version rollback <plan_id> <version_id>")
            return

        plan_id = version_parts[2]
        version_id = version_parts[3]

        result = await planning_tool.execute(
            command="rollback",
            plan_id=plan_id,
            version_id=version_id
        )

        print(result.output)
    elif command.startswith("version history "):
        # Get version history
        # Format: plan version history <plan_id>
        version_parts = command.split(maxsplit=2)
        if len(version_parts) < 3:
            print("Error: Missing plan ID.")
            print("Usage: plan version history <plan_id>")
            return

        plan_id = version_parts[2]

        result = await planning_tool.execute(
            command="get_version_history",
            plan_id=plan_id
        )

        print(result.output)
    else:
        print(f"Unknown plan command: {command}")
        show_plan_help()

def show_plan_help():
    """
    Show help for the plan command.
    """
    print("\nPlan Versioning System Commands:\n")
    print("  plan help                                - Show this help message")
    print("  plan list                                - List all plans")
    print("  plan create <plan_id> <title>           - Create a new plan")
    print("  plan get <plan_id>                      - Get a plan")
    print("  plan update <plan_id> <title>           - Update a plan")
    print("  plan version create <plan_id> <version_id> <description>  - Create a version")
    print("  plan version list <plan_id>             - List versions of a plan")
    print("  plan version get <plan_id> <version_id> - Get a specific version")
    print("  plan version compare <plan_id> <version_id1> <version_id2> - Compare versions")
    print("  plan version rollback <plan_id> <version_id> - Rollback to a version")
    print("  plan version history <plan_id>          - Get version history")

async def process_message(message: str, session_id: str = None, file_attachment: str = None):
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

        # Prepare the input message with file attachment if provided
        input_message = message
        if file_attachment and os.path.exists(file_attachment):
            # Process the file
            processor = FileAttachmentProcessor()
            file_result = await processor.execute(
                file_path=file_attachment,
                conversation_id=session_id,
                process_content=True
            )

            # If file content was processed successfully, include it in the message
            if not file_result.error and isinstance(file_result.output, dict) and file_result.output.get("content"):
                file_name = os.path.basename(file_attachment)
                input_message = f"{message}\n\nFile Content ({file_name}):\n{file_result.output.get('content')}"
                logger.info(f"File attachment {file_name} included in message processing")

        # Execute the flow with the message
        result = await asyncio.wait_for(
            flow.execute(input_message),
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
    # Variable to store attached file path
    attached_file = None

    print("\n=== NexAgent CLI ===\n")
    print("This system combines general-purpose and software development capabilities in one interface.")
    print("Your queries will be automatically routed to the appropriate assistant based on content.")

    # Create a session
    session_id = str(uuid.uuid4())
    session = session_manager.create_session(session_id=session_id)

    print("\nNexAgent initialized. Type 'exit' to quit.")
    print("Type 'stats' to see routing statistics.")
    print("Type 'upload <file_path>' to upload and process a file.")
    print("Type 'attach <file_path>' to attach a file to your next message.")
    print("Type 'plan' to access the plan versioning system.")

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

            # Handle file upload command
            if prompt.lower().startswith('upload '):
                file_path = prompt[7:].strip()
                if not os.path.exists(file_path):
                    print(f"File not found: {file_path}")
                    continue

                print(f"Processing file: {file_path}")
                try:
                    # Create a conversation folder if needed
                    conversation_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations", session_id))
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
                        conversation_id=session_id,
                        process_content=True
                    )

                    if result.error:
                        print(f"Error processing file: {result.output}")
                    else:
                        print(f"File uploaded successfully: {file_name}")
                        print(f"File saved to: {destination_path}")

                        # If content was processed, ask the user if they want to analyze it
                        if isinstance(result.output, dict) and result.output.get("content"):
                            analyze = input("\nWould you like to analyze this file? (y/n): ")
                            if analyze.lower() == 'y':
                                # Create a prompt with the file content
                                file_prompt = f"Please analyze the content of the file '{file_name}':\n\n{result.output.get('content')}"

                                # Process the request
                                print("Processing file analysis request... (This may take a moment)")
                                result = await process_message(file_prompt, session_id)

                                if "error" in result:
                                    print(f"\nError: {result['error']}")
                                else:
                                    print(f"\n{result['message']}")
                except Exception as e:
                    logger.error(f"Error uploading file: {str(e)}")
                    print(f"Error uploading file: {str(e)}")

                continue

            # Handle file attach command
            if prompt.lower().startswith('attach '):
                file_path = prompt[7:].strip()
                if not os.path.exists(file_path):
                    print(f"File not found: {file_path}")
                    attached_file = None
                else:
                    # Create a conversation folder if needed
                    conversation_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations", session_id))
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

            # Handle plan command
            if prompt.lower() == 'plan' or prompt.lower().startswith('plan '):
                try:
                    await handle_plan_command(prompt, session_id, active_flows)
                except Exception as e:
                    logger.error(f"Error handling plan command: {str(e)}")
                    print(f"\nError handling plan command: {str(e)}")
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

                # Check if there's an attached file
                current_file = None
                if 'attached_file' in locals() and attached_file:
                    print(f"Processing with attached file: {os.path.basename(attached_file)}")
                    current_file = attached_file
                    # Reset the attached file after using it
                    attached_file = None

                result = await process_message(prompt, session_id, current_file)
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