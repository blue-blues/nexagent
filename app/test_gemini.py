import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm import LLM


async def test_llm():
    try:
        # Initialize the LLM client
        llm = LLM()
        print(f"Using model: {llm.model}")
        print(f"API type: {llm.api_type}")
        print(f"Base URL: {llm.base_url}")
        
        # Send a simple test message
        response = await llm.ask([{"role": "user", "content": "Hello, who are you?"}])
        print(f"Response: {response}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_llm())
    sys.exit(0 if success else 1)