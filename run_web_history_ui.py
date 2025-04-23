"""
Script to run the Web Browsing History UI Component demo.
"""

import os
import sys
import argparse

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the web browsing history CLI
from app.ui.web_browsing_history_cli import main

if __name__ == "__main__":
    main()
