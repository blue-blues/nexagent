"""
Command Line Interface Module

This module provides a command-line interface for the application.
"""

import argparse
import asyncio
import os
import sys
import shutil
from pathlib import Path
from typing import List, Optional

from app.agent.factory.agent_factory import AgentFactory
from app.core.config.config import config, config_loader
from app.utils.logging.logger import logger, configure_logger

# Import file attachment processor
try:
    from app.tools.file_attachment_processor import FileAttachmentProcessor
except ImportError:
    logger.warning("FileAttachmentProcessor not available, file attachment functionality will be limited")
    FileAttachmentProcessor = None


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: Command-line arguments to parse

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Nexagent CLI")

    # General options
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    # Agent options
    parser.add_argument(
        "--agent", "-g",
        type=str,
        help="Agent type to use",
    )
    parser.add_argument(
        "--max-steps", "-m",
        type=int,
        help="Maximum steps for agent execution",
    )

    # Input options
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input text or file path",
    )
    parser.add_argument(
        "--file", "-f",
        action="store_true",
        help="Treat input as a file path",
    )
    parser.add_argument(
        "--attach", "-a",
        type=str,
        help="Path to a file to attach to the conversation",
    )
    parser.add_argument(
        "--process-attachment",
        action="store_true",
        default=True,
        help="Process the attached file content (default: True)",
    )

    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path",
    )

    # Parse arguments
    return parser.parse_args(args)


async def run_cli(args: argparse.Namespace) -> int:
    """
    Run the CLI application.

    Args:
        args: Parsed command-line arguments

    Returns:
        int: Exit code
    """
    # Configure logging
    log_level = "DEBUG" if args.debug or args.verbose else "INFO"
    configure_logger(log_level=log_level)

    # Load configuration
    if args.config:
        try:
            config_loader.reload(args.config)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return 1

    # Override configuration with command-line arguments
    if args.debug:
        config.debug = True

    # Get agent type
    agent_type = args.agent or config.agent.default_agent

    # Get available agent types
    available_agents = AgentFactory.get_available_agent_types()
    if not available_agents:
        logger.error("No agent types registered")
        return 1

    if agent_type not in available_agents:
        logger.error(f"Unknown agent type: {agent_type}")
        logger.info(f"Available agent types: {', '.join(available_agents)}")
        return 1

    # Get input
    input_text = args.input
    if args.file and input_text:
        try:
            with open(input_text, "r") as f:
                input_text = f.read()
        except Exception as e:
            logger.error(f"Error reading input file: {str(e)}")
            return 1

    # Process file attachment if provided
    attachment_content = None
    if args.attach:
        try:
            # Create a unique conversation ID for this session
            conversation_id = f"cli_session_{int(asyncio.get_event_loop().time())}"

            # Create conversation folder structure
            conversation_folder = Path(os.path.join(os.getcwd(), "data_store", "conversations", conversation_id))
            attachments_folder = conversation_folder / "attachments"
            attachments_folder.mkdir(parents=True, exist_ok=True)

            # Copy the file to the attachments folder
            file_name = os.path.basename(args.attach)
            destination_path = str(attachments_folder / file_name)
            shutil.copy2(args.attach, destination_path)

            logger.info(f"Attached file: {file_name}")

            # Process the file if requested
            if args.process_attachment:
                if FileAttachmentProcessor is not None:
                    # Use the FileAttachmentProcessor if available
                    processor = FileAttachmentProcessor()
                    result = await processor.execute(
                        file_path=destination_path,
                        conversation_id=conversation_id,
                        process_content=True
                    )

                    if not result.error and isinstance(result.output, dict) and result.output.get("content"):
                        attachment_content = result.output.get("content")
                        logger.info(f"Processed attachment content ({len(attachment_content)} characters)")
                else:
                    # Fallback to basic file reading if FileAttachmentProcessor is not available
                    try:
                        # Only process text files in the fallback mode
                        _, ext = os.path.splitext(file_name)
                        if ext.lower() in [".txt", ".md", ".py", ".js", ".html", ".xml", ".json", ".csv"]:
                            with open(destination_path, "r", encoding="utf-8") as f:
                                attachment_content = f.read()
                            logger.info(f"Basic file processing: Read {len(attachment_content)} characters from {file_name}")
                        else:
                            logger.warning(f"Cannot process file with extension {ext} in fallback mode")
                    except Exception as file_read_error:
                        logger.error(f"Error reading file in fallback mode: {str(file_read_error)}")

                # Append attachment content to input if content was successfully processed
                if attachment_content:
                    # Append attachment content to input if input is provided
                    if input_text:
                        input_text = f"{input_text}\n\nFile Content ({file_name}):\n{attachment_content}"
                    else:
                        input_text = f"Process this file content:\n\nFile Content ({file_name}):\n{attachment_content}"
        except Exception as e:
            logger.error(f"Error processing attachment: {str(e)}")
            # Continue without the attachment

    if not input_text:
        logger.error("No input provided")
        return 1

    # Create agent
    try:
        agent = AgentFactory.create_agent(
            agent_type=agent_type,
            name=f"CLI_{agent_type}",
            max_steps=args.max_steps or config.agent.max_steps,
        )
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        return 1

    # Run agent
    try:
        logger.info(f"Running agent: {agent.name}")
        result = await agent.run()

        # Output result
        if args.output:
            try:
                with open(args.output, "w") as f:
                    f.write(result)
                logger.info(f"Output written to {args.output}")
            except Exception as e:
                logger.error(f"Error writing output: {str(e)}")
                return 1
        else:
            print(result)

        return 0
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        return 1


def main() -> int:
    """
    Main entry point for the CLI application.

    Returns:
        int: Exit code
    """
    args = parse_args()
    return asyncio.run(run_cli(args))


if __name__ == "__main__":
    sys.exit(main())
