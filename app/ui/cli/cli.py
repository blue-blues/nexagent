"""
Command Line Interface Module

This module provides a command-line interface for the application.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional

from app.agent.factory.agent_factory import AgentFactory
from app.core.config.config import config, config_loader
from app.utils.logging.logger import logger, configure_logger


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
        "--agent", "-a",
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
