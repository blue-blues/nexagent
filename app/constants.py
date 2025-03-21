"""
Constants module to avoid circular imports between config and logger
"""
import os
from pathlib import Path

# Define project root path
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))