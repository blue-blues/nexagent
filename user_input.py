"""
User Input Handler

This script provides a command-line interface for handling user input requests
during agent execution.

Usage:
  python user_input.py list
  python user_input.py submit <request_id> <response>
  python user_input.py interactive
"""

import sys
import os
import time

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.cli.user_input_handler import list_requests, submit_response
from app.util.user_input_manager import input_manager


def interactive_mode():
    """Run in interactive mode, continuously checking for and responding to requests."""
    print("\033[1;32m=== Nexagent Interactive User Input Mode ===\033[0m")
    print("Continuously monitoring for user input requests...")
    print("Press Ctrl+C to exit")
    print()
    
    try:
        while True:
            # Check for pending requests
            pending_requests = input_manager.get_pending_requests()
            
            if pending_requests:
                # Display all pending requests
                list_requests()
                
                # Ask which request to respond to
                request_id = input("\n\033[1;36mEnter request ID to respond to (or 'refresh' to check again): \033[0m")
                
                if request_id.lower() == 'refresh':
                    continue
                
                if request_id not in pending_requests:
                    print(f"\033[1;31mError: No pending request found with ID {request_id}\033[0m")
                    continue
                
                # Get the response
                print("\n\033[1;36mEnter your response (type on multiple lines, use Ctrl+D or Ctrl+Z+Enter to finish):\033[0m")
                response_lines = []
                
                try:
                    while True:
                        line = input()
                        response_lines.append(line)
                except EOFError:
                    response = "\n".join(response_lines)
                
                # Submit the response
                submit_response(request_id, response)
            else:
                print("\033[1;33mNo pending input requests. Waiting...\033[0m", end="\r")
                time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\033[1;32mExiting interactive mode\033[0m")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_requests()
    elif command == "submit":
        if len(sys.argv) < 4:
            print("Error: Missing arguments for submit command")
            print("Usage: python user_input.py submit <request_id> <response>")
            return
        
        request_id = sys.argv[2]
        response = sys.argv[3]
        submit_response(request_id, response)
    elif command == "interactive":
        interactive_mode()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
