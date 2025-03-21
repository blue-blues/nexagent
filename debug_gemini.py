import asyncio
import sys
import traceback
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.llm import LLM


async def debug_llm():
    try:
        # Initialize the LLM client
        print("Initializing LLM client...")
        llm = LLM()
        print(f"Using model: {llm.model}")
        print(f"API type: {llm.api_type}")
        print(f"Base URL: {llm.base_url}")
        print(f"Client type: {type(llm.client).__name__}")
        
        # Print client attributes
        print("\nClient attributes:")
        for attr in dir(llm.client):
            if not attr.startswith('_'):
                print(f"  {attr}")
        
        # Print chat completion attributes
        print("\nChat completion attributes:")
        for attr in dir(llm.client.chat):
            if not attr.startswith('_'):
                print(f"  {attr}")
        
        # Send a simple test message
        print("\nSending test message...")
        response = await llm.ask([{"role": "user", "content": "Hello, who are you?"}], stream=False)
        print(f"Response: {response}")
        
        return True
    except Exception as e:
        print(f"\nError: {repr(e)}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(debug_llm())
    sys.exit(0 if success else 1)