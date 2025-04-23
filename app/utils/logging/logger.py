"""
Logger Module

This module provides a unified logging interface for the application.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

# Import constants if available, otherwise use default values
try:
    from app.constants import PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = Path(os.getcwd())

# Configure logs directory
LOGS_DIR = PROJECT_ROOT / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Generate log filename with timestamp
log_filename = datetime.now().strftime("%Y%m%d%H%M%S") + ".log"
log_path = LOGS_DIR / log_filename

# Configure logger
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO")  # Add stderr handler
logger.add(
    log_path,
    level="DEBUG",
    rotation="500 MB",
    retention="10 days",
    compression="zip",
)


def configure_logger(
    log_level: str = "INFO",
    log_to_console: bool = True,
    log_to_file: bool = True,
    log_dir: Optional[Path] = None,
    log_format: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
) -> None:
    """
    Configure the logger with custom settings.

    Args:
        log_level: Logging level
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        log_dir: Directory for log files
        log_format: Format for log messages
    """
    logger.remove()  # Remove all handlers

    # Add console handler if requested
    if log_to_console:
        logger.add(sys.stderr, level=log_level, format=log_format)

    # Add file handler if requested
    if log_to_file:
        if log_dir is None:
            log_dir = LOGS_DIR

        # Create log directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_file = log_dir / f"{timestamp}.log"

        logger.add(
            log_file,
            level=log_level,
            format=log_format,
            rotation="500 MB",
            retention="10 days",
            compression="zip",
        )

    logger.info(f"Logger configured with level {log_level}")


__all__ = ["logger", "configure_logger"]
