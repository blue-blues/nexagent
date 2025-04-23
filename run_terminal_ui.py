"""
Script to run the Terminal UI Component demo.
"""

import os
import sys
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the terminal CLI
from app.ui.terminal_cli import main

if __name__ == "__main__":
    asyncio.run(main())
