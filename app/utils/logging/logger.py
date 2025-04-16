import os
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from app.constants import PROJECT_ROOT  # Import from constants instead of config

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

__all__ = ["logger"]
