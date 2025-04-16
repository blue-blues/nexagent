#!/usr/bin/env python
"""
Simple demo script for the conversation folder organization feature.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tool.output_organizer import OutputOrganizer


async def simulate_conversation(conversation_id: str):
    """Simulate a conversation and save outputs."""
    print(f"Simulating conversation with ID: {conversation_id}")

    # Initialize the output organizer
    output_organizer = OutputOrganizer()

    # Set the active conversation
    await output_organizer.execute(
        action="set_active_conversation",
        conversation_id=conversation_id
    )

    # Simulate user message
    user_message = "Tell me about Python programming language"
    print(f"\nUser: {user_message}")

    # Simulate agent response
    agent_response = """Python is a high-level, interpreted programming language known for its readability and versatility.
It was created by Guido van Rossum and first released in 1991. Python's design philosophy emphasizes code readability
with its notable use of significant whitespace. Its language constructs and object-oriented approach aim to help programmers
write clear, logical code for small and large-scale projects.

Python is dynamically typed and garbage-collected. It supports multiple programming paradigms, including structured,
object-oriented, and functional programming. Python is often described as a "batteries included" language due to its
comprehensive standard library."""
    print(f"\nAgent: {agent_response[:100]}...\n")

    # Save the user message
    await output_organizer.execute(
        action="save_output",
        output_name="user_message",
        output_content=user_message,
        output_type="message"
    )

    # Save the agent response
    await output_organizer.execute(
        action="save_output",
        output_name="agent_response",
        output_content=agent_response,
        output_type="message"
    )

    # Simulate user follow-up message
    user_followup = "What are the key features of Python?"
    print(f"User: {user_followup}")

    # Simulate agent follow-up response
    agent_followup = """Key features of Python include:

1. Easy to Learn and Use: Python has a simple and straightforward syntax, making it accessible for beginners.

2. Readable and Maintainable: Python's clean syntax emphasizes readability, reducing the cost of program maintenance.

3. Interpreted Language: Python code is executed line by line, making debugging easier.

4. Dynamically Typed: You don't need to declare variable types, as the interpreter assigns them at runtime.

5. Object-Oriented: Python supports object-oriented programming with classes and objects.

6. Extensive Libraries: Python has a rich set of libraries and frameworks for various tasks like web development (Django, Flask),
   data analysis (Pandas, NumPy), machine learning (TensorFlow, PyTorch), etc.

7. Cross-Platform: Python runs on various operating systems like Windows, macOS, and Linux.

8. Free and Open Source: Python is freely available and can be distributed.

9. Integration Features: Python can be integrated with other languages like C, C++, and Java.

10. Scalable: Python is used in small scripts to large applications and is highly scalable."""
    print(f"\nAgent: {agent_followup[:100]}...\n")

    # Save the user follow-up message
    await output_organizer.execute(
        action="save_output",
        output_name="user_followup",
        output_content=user_followup,
        output_type="message"
    )

    # Save the agent follow-up response
    await output_organizer.execute(
        action="save_output",
        output_name="agent_followup",
        output_content=agent_followup,
        output_type="message"
    )

    # Simulate generating a code snippet
    code_snippet = '''def hello_world():
    """ A simple function that prints 'Hello, World!' """
    print("Hello, World!")


if __name__ == "__main__":
    hello_world()
'''
    print("Agent generated a code snippet:")
    print(f"\n{code_snippet}\n")

    # Save the code snippet
    await output_organizer.execute(
        action="save_output",
        output_name="hello_world_example",
        output_content=code_snippet,
        output_type="code"
    )

    # List all outputs
    result = await output_organizer.execute(
        action="list_outputs"
    )

    print(f"Outputs saved in conversation folder: {result.output}\n")


async def main():
    """Run the demo."""
    print("=== Simple Conversation Folder Organization Demo ===\n")

    # Generate a unique conversation ID
    conversation_id = f"demo_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    print(f"Generated conversation ID: {conversation_id}\n")

    # Simulate a conversation
    await simulate_conversation(conversation_id)

    # Show the folder structure
    folder_path = os.path.join(os.getcwd(), "data_store", "conversations", conversation_id)
    print(f"Conversation folder: {folder_path}")

    if os.path.exists(folder_path):
        print("\nFolder structure:")
        for root, _, files in os.walk(folder_path):
            level = root.replace(folder_path, '').count(os.sep)
            indent = ' ' * 4 * level
            print(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 4 * (level + 1)
            for file in files:
                print(f"{sub_indent}{file}")

    print("\nDemo completed!")


if __name__ == "__main__":
    asyncio.run(main())
