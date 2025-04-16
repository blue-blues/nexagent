#!/usr/bin/env python
"""
Command-line tool to view conversation history.

This script provides a simple command-line interface to view the conversation history
stored in the Nexagent conversation memory.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List, Optional

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.memory.conversation_memory import conversation_memory


def format_timestamp(timestamp: float) -> str:
    """Format a timestamp as a human-readable string."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


async def list_conversations(max_conversations: Optional[int] = None) -> None:
    """List all conversations in the memory."""
    # Get recent conversations
    conversations = conversation_memory.get_recent_conversations(max_conversations)
    
    if not conversations:
        print("No conversations found.")
        return
    
    # Print conversations
    print(f"Found {len(conversations)} conversations:")
    print("-" * 80)
    for i, conversation in enumerate(conversations):
        print(f"{i+1}. Conversation ID: {conversation.conversation_id}")
        print(f"   Last updated: {format_timestamp(conversation.last_updated)}")
        print(f"   Entries: {conversation.entry_count}")
        if conversation.topic:
            print(f"   Topic: {conversation.topic}")
        print("-" * 80)


async def view_conversation(conversation_id: str, max_entries: Optional[int] = None) -> None:
    """View a specific conversation."""
    # Get conversation entries
    entries = conversation_memory.get_conversation_history(conversation_id, max_entries)
    
    if not entries:
        print(f"No entries found for conversation {conversation_id}.")
        return
    
    # Print conversation entries
    print(f"Conversation {conversation_id} ({len(entries)} entries):")
    print("=" * 80)
    for i, entry in enumerate(entries):
        print(f"Entry {i+1} - {format_timestamp(entry.timestamp)}")
        print(f"User: {entry.user_prompt}")
        print(f"Assistant: {entry.bot_response}")
        if entry.metadata:
            print(f"Metadata: {json.dumps(entry.metadata, indent=2)}")
        print("-" * 80)


async def clear_conversation(conversation_id: str) -> None:
    """Clear a specific conversation."""
    # Clear conversation
    conversation_memory.clear_conversation(conversation_id)
    print(f"Cleared conversation {conversation_id}.")


async def clear_all_conversations() -> None:
    """Clear all conversations."""
    # Clear all conversations
    conversation_memory.clear_all()
    print("Cleared all conversations.")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="View Nexagent conversation history")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List conversations command
    list_parser = subparsers.add_parser("list", help="List all conversations")
    list_parser.add_argument("--max", type=int, help="Maximum number of conversations to show")
    
    # View conversation command
    view_parser = subparsers.add_parser("view", help="View a specific conversation")
    view_parser.add_argument("conversation_id", help="ID of the conversation to view")
    view_parser.add_argument("--max", type=int, help="Maximum number of entries to show")
    
    # Clear conversation command
    clear_parser = subparsers.add_parser("clear", help="Clear a specific conversation")
    clear_parser.add_argument("conversation_id", help="ID of the conversation to clear")
    
    # Clear all conversations command
    clear_all_parser = subparsers.add_parser("clear-all", help="Clear all conversations")
    
    args = parser.parse_args()
    
    if args.command == "list":
        await list_conversations(args.max)
    elif args.command == "view":
        await view_conversation(args.conversation_id, args.max)
    elif args.command == "clear":
        await clear_conversation(args.conversation_id)
    elif args.command == "clear-all":
        await clear_all_conversations()
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
