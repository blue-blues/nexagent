"""
User Input Handler CLI

This module provides a command-line interface for handling user input requests
during agent execution.
"""

import argparse
import sys
from typing import List, Optional

from app.util.user_input_manager import input_manager
from app.logger import logger


def list_requests():
    """List all pending input requests."""
    pending_requests = input_manager.get_pending_requests()

    if not pending_requests:
        print("\033[1;33mNo pending input requests.\033[0m")
        return

    print(f"\n\033[1;32mFound {len(pending_requests)} pending input request(s):\033[0m")
    print("="*80)

    for req_id, req_data in pending_requests.items():
        text = req_data.get("text", "")
        timestamp = req_data.get("timestamp", "")

        print(f"\033[1;36mRequest ID: \033[1;33m{req_id}\033[0m")
        print(f"\033[1;36mTimestamp: \033[0m{timestamp}")
        print(f"\033[1;36mQuestion: \033[0m\n{text}")

        # Add metadata if available
        metadata = req_data.get("metadata", {})
        if metadata:
            if "attachments" in metadata and metadata["attachments"]:
                attachments = metadata["attachments"]
                if isinstance(attachments, str):
                    attachments = [attachments]
                print(f"\033[1;36mAttachments: \033[0m{', '.join(attachments)}")

            if "suggest_user_takeover" in metadata and metadata["suggest_user_takeover"] != "none":
                print(f"\033[1;36mSuggested takeover: \033[0m{metadata['suggest_user_takeover']}")

        print("-"*80)


def submit_response(request_id: str, response: str):
    """Submit a response to a pending input request."""
    if not input_manager.pending_requests.get(request_id):
        print(f"\033[1;31mError: No pending request found with ID {request_id}\033[0m")
        return False

    # Get the request details for confirmation
    request_data = input_manager.pending_requests.get(request_id, {})
    text = request_data.get("text", "")

    # Show a confirmation of what we're responding to
    print("\n" + "="*80)
    print(f"\033[1;36mSubmitting response to request: \033[1;33m{request_id}\033[0m")
    print(f"\033[1;36mQuestion: \033[0m\n{text[:150]}{'...' if len(text) > 150 else ''}")
    print(f"\033[1;36mYour response: \033[0m\n{response}")
    print("-"*80)

    success = input_manager.submit_response(request_id, response)
    if success:
        print(f"\033[1;32mResponse submitted successfully for request {request_id}\033[0m")
    else:
        print(f"\033[1;31mFailed to submit response for request {request_id}\033[0m")

    return success


def main(args: Optional[List[str]] = None):
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Handle user input requests for Nexagent")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command
    list_parser = subparsers.add_parser("list", help="List pending input requests")

    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit a response to a pending input request")
    submit_parser.add_argument("request_id", help="ID of the request to respond to")
    submit_parser.add_argument("response", help="Response to submit")

    # Parse arguments
    parsed_args = parser.parse_args(args)

    # Execute command
    if parsed_args.command == "list":
        list_requests()
    elif parsed_args.command == "submit":
        submit_response(parsed_args.request_id, parsed_args.response)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
